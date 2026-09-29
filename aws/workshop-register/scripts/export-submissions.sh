#!/usr/bin/env bash
# Export all registrations from DynamoDB as CSV (default) or JSON.
# Requires: AWS CLI v2, Python 3, credentials with dynamodb:Scan on the table
#   (and cloudformation:DescribeStackResources to resolve the table name).
#
# Usage (from repo root, after aws sso login):
#   ./aws/workshop-register/scripts/export-submissions.sh
#   ./aws/workshop-register/scripts/export-submissions.sh > registrations.csv
#   ./aws/workshop-register/scripts/export-submissions.sh --json > registrations.json
#
# Env:
#   WORKSHOP_REGISTER_STACK  default ears-conn-workshop-register
#   AWS_REGION / AWS_DEFAULT_REGION  default us-east-1
#   AWS_PROFILE  e.g. asaslabs

set -euo pipefail

STACK_NAME="${WORKSHOP_REGISTER_STACK:-ears-conn-workshop-register}"
REGION="${AWS_REGION:-${AWS_DEFAULT_REGION:-us-east-1}}"
FORMAT="csv"

for arg in "$@"; do
  case "$arg" in
    --json|-j) FORMAT="json" ;;
    --help|-h)
      sed -n '2,16p' "$0" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *)
      echo "Unknown option: $arg (use --json or --help)" >&2
      exit 1
      ;;
  esac
done

TABLE_NAME=$(aws cloudformation describe-stack-resources \
  --stack-name "$STACK_NAME" \
  --region "$REGION" \
  --query "StackResources[?LogicalResourceId=='WorkshopSubmissionsTable'].PhysicalResourceId" \
  --output text)

if [[ -z "$TABLE_NAME" || "$TABLE_NAME" == "None" ]]; then
  echo "Could not find DynamoDB table WorkshopSubmissionsTable in stack $STACK_NAME ($REGION)." >&2
  exit 1
fi

export TABLE_NAME REGION FORMAT
python3 - <<'PY'
import csv
import json
import os
import subprocess
import sys

table = os.environ["TABLE_NAME"]
region = os.environ["REGION"]
fmt = os.environ["FORMAT"]

fields = [
    "submittedAt",
    "full_name",
    "email",
    "phone",
    "country_code",
    "registration_tier",
    "participation_mode",
    "affiliation",
    "role",
    "recommended_by",
    "ros_autoware_experience",
    "bring_laptop",
    "accessibility_notes",
    "ack_limited_seats",
    "id",
    "sourceIp",
]

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
    if "L" in attr:
        return json.dumps([unwrap(x) for x in attr["L"]])
    if "M" in attr:
        return json.dumps({k: unwrap(v) for k, v in attr["M"].items()})
    return json.dumps(attr)

items = []
start_key = None
while True:
    cmd = [
        "aws", "dynamodb", "scan",
        "--table-name", table,
        "--region", region,
        "--output", "json",
    ]
    if start_key:
        cmd.extend(["--exclusive-start-key", json.dumps(start_key)])
    page = json.loads(subprocess.check_output(cmd, text=True))
    for raw in page.get("Items") or []:
        items.append({k: unwrap(v) for k, v in raw.items()})
    start_key = page.get("LastEvaluatedKey")
    if not start_key:
        break

items.sort(key=lambda r: (r.get("submittedAt") or "", r.get("email") or ""))

if fmt == "json":
    json.dump(items, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
else:
    writer = csv.DictWriter(sys.stdout, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    for row in items:
        writer.writerow({k: row.get(k, "") for k in fields})

print(f"# exported {len(items)} registration(s) from {table}", file=sys.stderr)
PY
