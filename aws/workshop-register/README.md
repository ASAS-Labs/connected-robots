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

Use stack name `ears-conn-workshop-register` (or your choice). Set **PublicSiteOrigin** to the exact origin where `workshop-register.html` is served (scheme + host, no trailing slash).

After deploy, copy output **RegisterEndpoint** (full URL ending in `/register`).

## Wire the static site

In `workshop-register.html`, set the URL from the stack output:

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
