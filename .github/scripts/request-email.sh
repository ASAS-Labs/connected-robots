#!/usr/bin/env bash
# Request an email from the EARS-CONN SES identity through the "Send email" GitHub workflow.
# Needs only `gh` auth with write access to the repo; no AWS login.
#
# Usage:
#   .github/scripts/request-email.sh --to a@x.com [--cc b@y.com,c@z.com] [--bcc ...] \
#     [--reply-to ...] --subject "Subject" [--body-file body.txt] [--dry-run] [--no-wait]
# The body is read from --body-file, or from stdin when no file is given.

set -euo pipefail

REPO="${EMAIL_REPO:-ASAS-Labs/connected-robots}"
WORKFLOW="send-email.yml"
TO="" CC="" BCC="" REPLY_TO="" SUBJECT="" BODY_FILE="" DRY_RUN=false WAIT=true

while [[ $# -gt 0 ]]; do
  case "$1" in
    --to) TO="$2"; shift 2 ;;
    --cc) CC="$2"; shift 2 ;;
    --bcc) BCC="$2"; shift 2 ;;
    --reply-to) REPLY_TO="$2"; shift 2 ;;
    --subject) SUBJECT="$2"; shift 2 ;;
    --body-file) BODY_FILE="$2"; shift 2 ;;
    --dry-run) DRY_RUN=true; shift ;;
    --no-wait) WAIT=false; shift ;;
    -h|--help) sed -n '2,9p' "$0"; exit 0 ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

if [[ -z "$TO" || -z "$SUBJECT" ]]; then
  echo "--to and --subject are required." >&2
  exit 1
fi
if [[ -n "$BODY_FILE" ]]; then
  BODY="$(cat "$BODY_FILE")"
else
  BODY="$(cat)"
fi
if [[ -z "${BODY//[[:space:]]/}" ]]; then
  echo "Body is empty." >&2
  exit 1
fi

export TO CC BCC REPLY_TO SUBJECT BODY DRY_RUN
python3 -c '
import json, os
print(json.dumps({
    "to": os.environ["TO"], "cc": os.environ["CC"], "bcc": os.environ["BCC"],
    "reply_to": os.environ["REPLY_TO"], "subject": os.environ["SUBJECT"],
    "body": os.environ["BODY"], "dry_run": os.environ["DRY_RUN"],
}))' | gh workflow run "$WORKFLOW" -R "$REPO" --ref main --json

echo "Requested send-email run on ${REPO}."
[[ "$WAIT" == true ]] || exit 0

sleep 5
RUN_ID="$(gh run list -R "$REPO" --workflow "$WORKFLOW" -L 1 --json databaseId -q '.[0].databaseId')"
gh run watch "$RUN_ID" -R "$REPO" --exit-status >/dev/null || {
  gh run view "$RUN_ID" -R "$REPO" --log-failed | tail -20
  exit 1
}
gh run view "$RUN_ID" -R "$REPO" --log | rg -o 'Recipients:.*|Sent\. SES MessageId=.*|Dry run:.*' || true
