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

export FROM TO
python3 - <<'PY'
import json, os
to = os.environ["TO"]
text = f"""Hello,

This is a test of the EARS-CONN registration receipt. It does not create a registration.

Thank you for registering for EARS-CONN (Embodied-AI for Autonomous, Reliable, and Safe Connected Operations in Networked Environments, through Digital-Earth).

Registration option: Conference — early bird ($50)
Email on file: {to}

This message confirms that we received your registration request. Organizers will follow up by email with payment or access details, and with Autoware seat confirmation when applicable.

Event site: https://ears-conn.com

— EARS-CONN organizers
"""
html = f"""<p>Hello,</p>
<p>This is a test of the EARS-CONN registration receipt. It does not create a registration.</p>
<p>Thank you for registering for <strong>EARS-CONN</strong> (Embodied-AI for Autonomous, Reliable, and Safe Connected Operations in Networked Environments, through Digital-Earth).</p>
<p><strong>Registration option:</strong> Conference — early bird ($50)<br>
<strong>Email on file:</strong> {to}</p>
<p>This message confirms that we received your registration request. Organizers will follow up by email with payment or access details, and with Autoware seat confirmation when applicable.</p>
<p>Event site: <a href="https://ears-conn.com">https://ears-conn.com</a></p>
<p>— EARS-CONN organizers</p>
"""
payload = {
    "Source": os.environ["FROM"],
    "Destination": {"ToAddresses": [to]},
    "Message": {
        "Subject": {"Data": "EARS-CONN registration received", "Charset": "UTF-8"},
        "Body": {
            "Text": {"Data": text, "Charset": "UTF-8"},
            "Html": {"Data": html, "Charset": "UTF-8"},
        },
    },
}
with open("ses-message.json", "w", encoding="utf-8") as fh:
    json.dump(payload, fh)
PY

aws ses send-email --region "$REGION" --cli-input-json file://ses-message.json
rm -f ses-message.json
echo "Sent registration receipt to ${TO}"
