#!/usr/bin/env bash
# Send the registration receipt to each address already stored in DynamoDB.
# One message per email address. Does not notify organizers.

set -euo pipefail

REGION="${AWS_REGION:-us-east-1}"
FROM="${CONFIRMATION_FROM_EMAIL:-}"
STACK_NAME="${WORKSHOP_REGISTER_STACK:-ears-conn-workshop-register}"

if [[ -z "$FROM" ]]; then
  echo "CONFIRMATION_FROM_EMAIL is required." >&2
  exit 1
fi

TABLE_NAME=$(aws cloudformation describe-stack-resources \
  --stack-name "$STACK_NAME" \
  --region "$REGION" \
  --query "StackResources[?LogicalResourceId=='WorkshopSubmissionsTable'].PhysicalResourceId" \
  --output text)

if [[ -z "$TABLE_NAME" || "$TABLE_NAME" == "None" ]]; then
  echo "Could not find WorkshopSubmissionsTable in stack $STACK_NAME." >&2
  exit 1
fi

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
export TABLE_NAME REGION FROM ROOT
python3 - <<'PY'
import base64, json, os, subprocess, sys, time
sys.path.insert(0, os.path.join(os.environ["ROOT"], "aws/workshop-register/src"))
from confirmation_email import build_confirmation, registrant_message

table = os.environ["TABLE_NAME"]
region = os.environ["REGION"]
raw_from = os.environ["FROM"].strip()
if "<" in raw_from and raw_from.endswith(">"):
    from_name, from_address = raw_from[:-1].split("<", 1)
    from_name = from_name.strip().strip('"') or "EARS-CONN"
    from_address = from_address.strip()
else:
    from_name, from_address = "EARS-CONN", raw_from
site = "https://ears-conn.com"
tiers = {
    "conf_early": "Conference — early bird ($50)",
    "conf_standard": "Conference — regular ($100)",
    "conf_student": "Conference — student ($20)",
    "conf_free_request": "Conference — limited free ticket request ($0, CUNY students only)",
    "workshop_full": "Workshop — full in person ($600, includes conference)",
    "workshop_online": "Workshop — online ($500, includes conference)",
}

def unwrap(attr):
    if not isinstance(attr, dict):
        return attr
    if "S" in attr:
        return attr["S"]
    if "N" in attr:
        return attr["N"]
    if "BOOL" in attr:
        return attr["BOOL"]
    if "NULL" in attr:
        return ""
    return ""

items = []
start_key = None
while True:
    cmd = ["aws", "dynamodb", "scan", "--table-name", table, "--region", region, "--output", "json"]
    if start_key:
        cmd.extend(["--exclusive-start-key", json.dumps(start_key)])
    page = json.loads(subprocess.check_output(cmd, text=True))
    for raw in page.get("Items") or []:
        items.append({k: unwrap(v) for k, v in raw.items()})
    start_key = page.get("LastEvaluatedKey")
    if not start_key:
        break

by_email = {}
for item in items:
    email = str(item.get("email") or "").strip().lower()
    if not email:
        continue
    prev = by_email.get(email)
    if prev is None or (item.get("submittedAt") or "") >= (prev.get("submittedAt") or ""):
        by_email[email] = item

print(f"Registrations={len(items)} UniqueEmails={len(by_email)}")

def esc(value):
    return (str(value)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;"))

sent = 0
failed = []
for email, item in sorted(by_email.items()):
    name = item.get("full_name") or "participant"
    tier_key = str(item.get("registration_tier") or "")
    tier = tiers.get(tier_key, tier_key or "registration")
    next_steps = (
        "This message confirms that we received your registration request. "
        "Organizers will follow up by email with payment or access details, "
        "and with Autoware seat confirmation when applicable."
    )
    if tier_key == "conf_free_request":
        next_steps = (
            "Free tickets are only for CUNY students. "
            "Organizers will review this request and confirm eligibility by email."
        )
    content = build_confirmation(
        name=name,
        email=email,
        tier_key=tier_key,
        tier_label=tier,
        site=site,
        participation_mode=str(item.get("participation_mode") or ""),
        next_steps=next_steps,
    )
    message = registrant_message(
        from_name=from_name,
        from_address=from_address,
        to_address=email,
        content=content,
    )
    payload = {
        "Source": from_address,
        "Destinations": [email],
        "RawMessage": {"Data": base64.b64encode(message.as_bytes()).decode("ascii")},
    }
    path = "ses-message.json"
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh)
    result = subprocess.run(
        ["aws", "ses", "send-raw-email", "--region", region, "--cli-input-json", f"file://{path}"],
        text=True,
        capture_output=True,
    )
    if result.returncode == 0:
        sent += 1
        print(f"SENT {email}")
    else:
        err = (result.stderr or result.stdout or "send failed").strip().splitlines()[-1]
        failed.append(email)
        print(f"FAILED {email} {err}")
    time.sleep(0.2)

try:
    os.remove("ses-message.json")
except OSError:
    pass

print(f"Sent={sent} Failed={len(failed)}")
if failed:
    raise SystemExit(1)
PY
