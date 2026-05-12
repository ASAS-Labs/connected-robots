# Workshop pre-registration API (AWS-only)

Stack: **HTTP API (API Gateway)** → **Lambda (Python 3.12)** → **DynamoDB** (on-demand billing). Submissions are stored as items keyed by UUID. No third-party form services.

## Prerequisites

- AWS CLI configured (`aws sts get-caller-identity`)
- [SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html) (`sam --version`)

The function uses **boto3** from the Lambda runtime. `sam build` does **not** require Node.js.

## Deploy

```bash
cd aws/workshop-register
sam build
sam deploy --guided
```

Use stack name `ears-conn-workshop-register` (or your choice). Set **PublicSiteOrigin** to the exact origin where `register.html` is served (scheme + host, no trailing slash).

After deploy, copy output **RegisterEndpoint** (full URL ending in `/register`).

## Wire the static site

In `register.html`, set the URL from the stack output:

```html
<script>
  window.__WORKSHOP_REGISTER_POST_URL__ = 'https://xxxxxxxx.execute-api.us-east-1.amazonaws.com/register';
</script>
```

## Read submissions

**Count pre-registrations** (after `aws login`):

```bash
./aws/workshop-register/scripts/count-submissions.sh
```

**Console:** DynamoDB → Tables → stack output **SubmissionsTableName** → Explore table items.

## GitHub Actions

Workflow: `.github/workflows/deploy-workshop-api.yml` runs when `aws/workshop-register/**` changes. Repository **must** include this `aws/workshop-register` directory so the runner `working-directory` exists.

Secrets **`AWS_ACCESS_KEY_ID`** and **`AWS_SECRET_ACCESS_KEY`** must belong to an IAM principal that can deploy SAM stacks.

### IAM: fix `AccessDenied` on `cloudformation:CreateChangeSet`

If deployment fails with:

`User ... is not authorized to perform: cloudformation:CreateChangeSet on resource ... stack/aws-sam-cli-managed-default/...`

then the CI user (for example `earsconn-dev`) cannot manage **CloudFormation**, including the **SAM-managed** stack that `--resolve-s3` uses for deployment artifacts.

**Account admin:** attach policies so this user can create changesets and deploy stacks. In practice that usually means at least:

| Area | Why |
|------|-----|
| **CloudFormation** | Create/update/delete stacks (`ears-conn-workshop-register`, `aws-sam-cli-managed-default`, nested stacks) |
| **S3** | Artifact uploads when using `--resolve-s3` (SAM CLI bucket in `us-east-1`) |
| **IAM** | `sam deploy --capabilities CAPABILITY_IAM` creates/updates roles |
| **Lambda, API Gateway v2, DynamoDB, Logs** | Resources defined in `template.yaml` |

Practical options:

1. **Managed policies for a dedicated deploy user** (simplest for small teams): attach **`AWSCloudFormationFullAccess`**, **`IAMFullAccess`** (or a narrower pass-role policy if you lock it down later), and **`AmazonS3FullAccess`** or a bucket-scoped policy for the SAM artifact bucket in **`us-east-1`**, plus **`AWSLambda_FullAccess`**, **`AmazonAPIGatewayAdministrator`**, **`AmazonDynamoDBFullAccess`**, **`CloudWatchLogsFullAccess`** as needed—or use **`AdministratorAccess`** only if your org allows it for this CI user.

2. **Least privilege:** build a custom policy from [AWS SAM permissions](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/sam-permissions.html) and scope resources.

After updating IAM, re-run the workflow (or **`sam deploy`** locally with the same keys).

### Regional note

The workflow uses **`aws-region: us-east-1`**. Policies and any artifact bucket must allow actions in that region.
