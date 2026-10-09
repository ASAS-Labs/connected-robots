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

export TABLE_NAME REGION FROM
python3 - <<'PY'
import json, os, subprocess, time

table = os.environ["TABLE_NAME"]
region = os.environ["REGION"]
raw_from = os.environ["FROM"].strip()
if "<" in raw_from and raw_from.endswith(">"):
    source = raw_from
else:
    source = f"EARS-CONN <{raw_from}>"
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
        next_steps += (
            " Next steps for this request: free tickets are only for CUNY students. "
            "Organizers will review your request and confirm eligibility by email."
        )
    text = (
        f"Hello {name},\n\n"
        "Thank you for registering for EARS-CONN (Embodied AI and Remote Sensing "
        "for Sustainable, Safe Connected Cities).\n\n"
        f"Registration option: {tier}\n"
        f"Email on file: {email}\n\n"
        f"{next_steps}\n\n"
        f"Event site: {site}\n\n"
        "— EARS-CONN organizers\n"
    )
    html = (
        f"<p>Hello {esc(name)},</p>"
        "<p>Thank you for registering for <strong>EARS-CONN</strong> "
        "(Embodied AI and Remote Sensing for Sustainable, Safe Connected Cities).</p>"
        f"<p><strong>Registration option:</strong> {esc(tier)}<br>"
        f"<strong>Email on file:</strong> {esc(email)}</p>"
        f"<p>{esc(next_steps)}</p>"
        f'<p>Event site: <a href="{site}">{site}</a></p>'
        "<p>— EARS-CONN organizers</p>"
    )
    payload = {
        "Source": source,
        "Destination": {"ToAddresses": [email]},
        "Message": {
            "Subject": {"Data": "EARS-CONN registration received", "Charset": "UTF-8"},
            "Body": {
                "Text": {"Data": text, "Charset": "UTF-8"},
                "Html": {"Data": html, "Charset": "UTF-8"},
            },
        },
    }
    path = "ses-message.json"
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh)
    result = subprocess.run(
        ["aws", "ses", "send-email", "--region", region, "--cli-input-json", f"file://{path}"],
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
