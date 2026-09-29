#!/usr/bin/env bash
# Create or refresh the ears-conn.com SES identity in this account and print the DNS records Cloudflare must publish.
# Requires AWS CLI credentials that can call sesv2 in us-east-1 (the registration API account).

set -euo pipefail

REGION="${AWS_REGION:-us-east-1}"
DOMAIN="ears-conn.com"
MAIL_FROM="mail.ears-conn.com"

if ! aws sesv2 get-email-identity --email-identity "$DOMAIN" --region "$REGION" >/dev/null 2>&1; then
  aws sesv2 create-email-identity --email-identity "$DOMAIN" --region "$REGION" >/dev/null
fi

aws sesv2 put-email-identity-mail-from-attributes \
  --email-identity "$DOMAIN" \
  --mail-from-domain "$MAIL_FROM" \
  --behavior-on-mx-failure USE_DEFAULT_VALUE \
  --region "$REGION" >/dev/null

PROD=$(aws sesv2 get-account --region "$REGION" --query 'ProductionAccessEnabled' --output text)
if [[ "$PROD" != "True" ]]; then
  aws sesv2 put-account-details \
    --region "$REGION" \
    --mail-type TRANSACTIONAL \
    --website-url "https://ears-conn.com" \
    --contact-language EN \
    --production-access-enabled \
    --additional-contact-email-addresses "aliarb1990@gmail.com" \
    --use-case-description "EARS-CONN 2027 is a small academic conference (https://ears-conn.com). We send transactional email only: a confirmation receipt after someone submits the public registration form, plus an optional notice to the organizers. Recipients are people who registered themselves. We do not send marketing or purchased lists. Expected volume is well under a few hundred messages for the event."
fi

echo "ProductionAccessEnabled=$(aws sesv2 get-account --region "$REGION" --query 'ProductionAccessEnabled' --output text)"
echo "VerificationStatus=$(aws sesv2 get-email-identity --email-identity "$DOMAIN" --region "$REGION" --query 'VerificationStatus' --output text)"
echo "MailFromDomainStatus=$(aws sesv2 get-email-identity --email-identity "$DOMAIN" --region "$REGION" --query 'MailFromAttributes.MailFromDomainStatus' --output text)"

aws sesv2 get-email-identity --email-identity "$DOMAIN" --region "$REGION" \
  --query 'DkimAttributes.Tokens' --output text | tr '\t' '\n' | while read -r token; do
  [[ -z "$token" || "$token" == "None" ]] && continue
  echo "CNAME ${token}._domainkey.${DOMAIN} ${token}.dkim.amazonses.com"
done

echo "MX ${MAIL_FROM} 10 feedback-smtp.${REGION}.amazonses.com"
echo "TXT ${MAIL_FROM} v=spf1 include:amazonses.com ~all"
