# AWS CLI with IAM Identity Center (SSO)

Use this so `aws` commands (including `scripts/count-submissions.sh` and `sam deploy`) use short-lived SSO sessions instead of long-lived access keys.

## ASAS Labs account

EARS-CONN / workshop resources live in the **asaslabs** AWS account. During `aws configure sso`, when the CLI lists available accounts, choose the one whose **name** is **asaslabs** (the **12-digit account ID** is the unique identifier; the name helps you pick the right account). You can name your CLI profile `asaslabs` so it stays obvious in `~/.aws/config` (any profile name is allowed).

## One-time: interactive setup

1. Install or update the [AWS CLI v2](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) (v2.2 or newer for SSO).

2. In the AWS console, your admin should give you:
   - **SSO start URL** (e.g. `https://d-xxxxxxxxxx.awsapps.com/start`)
   - **SSO Region** (e.g. `us-east-1`, often where Identity Center is registered)
   - **Account ID** and **role name** (from your permission set), or you discover them during setup.

3. Run the guided wizard (replace values when prompted):

   ```bash
   aws configure sso
   ```

   Answer the prompts. When asked for **CLI default client Region**, use the region you deploy in (e.g. `us-east-1` for this project). For **CLI default output format**, `json` is fine.

4. The wizard writes a **profile** to `~/.aws/config` (and may create `~/.aws/credentials` for the SSO cache). Note the **profile name** you chose (e.g. `asaslabs`).

## Use the profile every session

```bash
export AWS_PROFILE=asaslabs
aws sso login
```

`aws sso login` opens a browser; after success, the profile works until the session expires (hours; your org sets this).

Check:

```bash
aws sts get-caller-identity
```

## workshop-register scripts

From the repo root, after `aws sso login`:

```bash
export AWS_PROFILE=asaslabs
./aws/workshop-register/scripts/count-submissions.sh
```

Or one line:

```bash
AWS_PROFILE=asaslabs aws sso login && AWS_PROFILE=asaslabs ./aws/workshop-register/scripts/count-submissions.sh
```

## Example `~/.aws/config` fragment (after `aws configure sso`)

Replace the account ID and role with what Identity Center shows for **asaslabs**.

```ini
[profile asaslabs]
sso_start_url = https://d-xxxxxxxxxx.awsapps.com/start
sso_region = us-east-1
sso_account_id = 123456789012
sso_role_name = AdministratorAccess
region = us-east-1
output = json
```

## Troubleshooting

- **Token has expired** or **The SSO session has expired…** — Run `aws sso login` again (with the same `AWS_PROFILE`).
- **No such file `~/.aws/config`** — Run `aws configure sso` once to create it.
- **Access denied** on DynamoDB / CloudFormation — Your SSO permission set must allow `dynamodb:Scan` (or `DescribeTable` + read) and `cloudformation:DescribeStackResources` on the `ears-conn-workshop-register` resources, or use a role that can read that account.

For official reference, see [AWS CLI IAM Identity Center](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sso.html).
