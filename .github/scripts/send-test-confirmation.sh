#!/usr/bin/env bash
# Send one registration receipt through the account that owns the ears-conn.com SES identity.
# Usage: TO_EMAIL=person@example.com CONFIRMATION_FROM_EMAIL=noreply@ears-conn.com ./send-test-confirmation.sh

set -euo pipefail

REGION="${AWS_REGION:-us-east-1}"
FROM="${CONFIRMATION_FROM_EMAIL:-}"
TO="${TO_EMAIL:-}"

if [[ -z "$FROM" || -z "$TO" ]]; then
  echo "CONFIRMATION_FROM_EMAIL and TO_EMAIL are required." >&2
  exit 1
fi

echo "ProductionAccessEnabled=$(aws sesv2 get-account --region "$REGION" --query 'ProductionAccessEnabled' --output text)"

PROD=$(aws sesv2 get-account --region "$REGION" --query 'ProductionAccessEnabled' --output text)
RECIPIENT_STATUS=$(aws sesv2 get-email-identity --email-identity "$TO" --region "$REGION" --query 'VerifiedForSendingStatus' --output text 2>/dev/null || true)
echo "RecipientVerified=${RECIPIENT_STATUS:-missing}"
if [[ "$PROD" != "True" && "$RECIPIENT_STATUS" != "True" ]]; then
  aws ses verify-email-identity --email-address "$TO" --region "$REGION"
  echo "Amazon SES verification message sent to ${TO}. The registration receipt can be delivered after that address is confirmed."
  exit 0
fi
echo "VerificationStatus=$(aws sesv2 get-email-identity --email-identity ears-conn.com --region "$REGION" --query 'VerificationStatus' --output text)"
echo "VerifiedForSending=$(aws sesv2 get-email-identity --email-identity ears-conn.com --region "$REGION" --query 'VerifiedForSendingStatus' --output text)"
echo "DkimStatus=$(aws sesv2 get-email-identity --email-identity ears-conn.com --region "$REGION" --query 'DkimAttributes.Status' --output text)"

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
export FROM TO ROOT
python3 - <<'PY'
import base64, json, os, sys
sys.path.insert(0, os.path.join(os.environ["ROOT"], "aws/workshop-register/src"))
from confirmation_email import build_confirmation, registrant_message

to = os.environ["TO"]
raw_from = os.environ["FROM"].strip()
if "<" in raw_from and raw_from.endswith(">"):
    from_name, from_address = raw_from[:-1].split("<", 1)
    from_name = from_name.strip().strip('"') or "EARS-CONN"
    from_address = from_address.strip()
else:
    from_name, from_address = "EARS-CONN", raw_from
content = build_confirmation(
    name="there",
    email=to,
    tier_key="conf_early",
    tier_label="Conference — early bird ($50)",
    site="https://ears-conn.com",
    participation_mode="in_person",
    next_steps=(
        "This is a sample of the registration confirmation. It does not create a registration. "
        "Organizers will follow up by email with payment or access details when a real registration is submitted."
    ),
)
message = registrant_message(
    from_name=from_name,
    from_address=from_address,
    to_address=to,
    content=content,
)
payload = {
    "Source": from_address,
    "Destinations": [to],
    "RawMessage": {"Data": base64.b64encode(message.as_bytes()).decode("ascii")},
}
with open("ses-message.json", "w", encoding="utf-8") as fh:
    json.dump(payload, fh)
PY

aws ses send-raw-email --region "$REGION" --cli-input-json file://ses-message.json
rm -f ses-message.json
echo "Sent registration receipt to ${TO}"
