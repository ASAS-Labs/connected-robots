#!/usr/bin/env bash
# Print how many workshop pre-registrations are in DynamoDB (one item per submit).
# Requires: AWS CLI v2, credentials with dynamodb:Scan on the table (and cloudformation:DescribeStackResources to resolve the table name).
# Usage:
#   ./aws/workshop-register/scripts/count-submissions.sh

set -euo pipefail

STACK_NAME="${WORKSHOP_REGISTER_STACK:-ears-conn-workshop-register}"
REGION="${AWS_REGION:-${AWS_DEFAULT_REGION:-us-east-1}}"

TABLE_NAME=$(aws cloudformation describe-stack-resources \
  --stack-name "$STACK_NAME" \
  --region "$REGION" \
  --query "StackResources[?LogicalResourceId=='WorkshopSubmissionsTable'].PhysicalResourceId" \
  --output text)

if [[ -z "$TABLE_NAME" || "$TABLE_NAME" == "None" ]]; then
  echo "Could not find DynamoDB table WorkshopSubmissionsTable in stack $STACK_NAME ($REGION)." >&2
  exit 1
fi

COUNT=$(aws dynamodb scan \
  --table-name "$TABLE_NAME" \
  --region "$REGION" \
  --select COUNT \
  --query Count \
  --output text)

echo "Workshop pre-registrations: $COUNT"
echo "(table: $TABLE_NAME, stack: $STACK_NAME, region: $REGION)"
