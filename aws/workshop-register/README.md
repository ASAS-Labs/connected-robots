# Workshop pre-registration API (AWS-only)

Stack: **HTTP API (API Gateway)** → **Lambda (Python 3.12)** → **DynamoDB** (on-demand billing). Submissions are stored as items keyed by UUID. No third-party form services.

## Prerequisites

- AWS CLI configured (`aws sts get-caller-identity`)
- [SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html) (`sam --version`)

The function is **Python 3.12** and only uses **boto3** (already in the Lambda runtime). `sam build` does **not** use Node.js, npm, or esbuild, so you do not need a local Node install.

## Deploy

```bash
cd aws/workshop-register
sam build
sam deploy --guided
```

Use stack name `ears-conn-workshop-register` (or your choice). Set **PublicSiteOrigin** to the exact origin where `workshop-register.html` is served (scheme + host, no trailing slash), for example `https://ears-conn.com`. If you use both `www` and apex, pick the one visitors use or extend the template with an extra allowed origin.

After deploy, copy output **RegisterEndpoint** (full URL ending in `/register`).

## Wire the static site

In `workshop-register.html`, set the URL from the stack output:

```html
<script>
  window.__WORKSHOP_REGISTER_POST_URL__ = 'https://xxxxxxxx.execute-api.us-east-1.amazonaws.com/register';
</script>
```

Redeploy the site to S3. Leave the string empty only while testing; the page shows a warning and disables submit until this is set.

## Bot resistance (Turnstile + honeypot)

The static form includes a **honeypot** field (`_gotcha`). For stronger protection, use **Cloudflare Turnstile** (no extra Lambda dependencies).

1. In the [Cloudflare dashboard](https://dash.cloudflare.com/), create a Turnstile widget for your site hostname (match **PublicSiteOrigin**).
2. Deploy the stack with the **secret** key (server verifies tokens):
   - `sam deploy ... --parameter-overrides TurnstileSecretKey=YOUR_SECRET`
   - Or set GitHub secret **`WORKSHOP_TURNSTILE_SECRET_KEY`** for `.github/workflows/deploy-workshop-api.yml`.
3. Set the **site** key in `workshop-register.html`: `window.__TURNSTILE_SITE_KEY__ = '...'` (public value).
   - Or set repo secret **`WORKSHOP_TURNSTILE_SITE_KEY`** so `.github/workflows/deploy.yml` can inject it when the HTML still has `window.__TURNSTILE_SITE_KEY__ = '';`.

If **TurnstileSecretKey** is empty, the Lambda skips verification (fine for local testing). In production, configure **both** the Lambda secret and the page site key; otherwise users may see submit enabled while the API rejects requests.

## Read submissions

- **Console:** DynamoDB → Tables → output **SubmissionsTableName** → Explore table items.
- **CLI example:** `aws dynamodb scan --table-name <SubmissionsTableName> --max-items 5`

## GitHub Actions

- **API:** `.github/workflows/deploy-workshop-api.yml` runs `sam build` / `sam deploy` when `aws/workshop-register/**` changes (or on manual dispatch). Extend IAM for the deploy user beyond S3: CloudFormation, Lambda, API Gateway, DynamoDB, IAM, and S3 (SAM artifacts when using `--resolve-s3`).
- **Static site:** `.github/workflows/deploy.yml` can inject the API URL automatically if you add repo secret **`WORKSHOP_REGISTER_POST_URL`** set to the **RegisterEndpoint** value (full `https://…/register` URL). If unset, `workshop-register.html` keeps the empty placeholder until you paste the URL manually.

## Optional next steps (not included here)

- Amazon SES email to organizers on each `PutItem`
- AWS WAF rate limiting on the HTTP API
- DynamoDB TTL attribute if you want rows to expire automatically
