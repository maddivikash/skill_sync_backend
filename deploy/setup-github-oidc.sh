#!/usr/bin/env bash
# One-time IAM bootstrap for the GitHub Actions deploy pipeline.
#
#   bash deploy/setup-github-oidc.sh
#
# Creates (idempotently):
#   1. The GitHub OIDC identity provider, so GitHub Actions can prove to AWS
#      "this token really came from a workflow in repo X on branch Y" without
#      any stored AWS keys.
#   2. Role github-actions-deploy, assumable ONLY by this repo's main/master
#      workflows via that provider.
#   3. A least-privilege inline policy: send the deploy command to the one
#      app instance and read the command's result. Nothing else.
set -euo pipefail

ACCOUNT=720443382372
REGION=ap-south-1
REPO=maddivikash/skill_sync_backend
ROLE=github-actions-deploy
INSTANCE=i-0c8a6ad86684312c4
PROVIDER_ARN="arn:aws:iam::${ACCOUNT}:oidc-provider/token.actions.githubusercontent.com"

# --- 1. OIDC provider (skip if it exists) ---------------------------------
if aws iam get-open-id-connect-provider --open-id-connect-provider-arn "$PROVIDER_ARN" >/dev/null 2>&1; then
  echo "OIDC provider already exists."
else
  aws iam create-open-id-connect-provider \
    --url https://token.actions.githubusercontent.com \
    --client-id-list sts.amazonaws.com \
    --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1
  echo "OIDC provider created."
fi

# --- 2. Role with trust policy scoped to this repo's deploy branches ------
TRUST=$(cat <<JSON
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Federated": "${PROVIDER_ARN}"},
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringEquals": {"token.actions.githubusercontent.com:aud": "sts.amazonaws.com"},
      "StringLike": {"token.actions.githubusercontent.com:sub": [
        "repo:${REPO}:ref:refs/heads/main",
        "repo:${REPO}:ref:refs/heads/master"
      ]}
    }
  }]
}
JSON
)
if aws iam get-role --role-name "$ROLE" >/dev/null 2>&1; then
  aws iam update-assume-role-policy --role-name "$ROLE" --policy-document "$TRUST"
  echo "Role exists; trust policy refreshed."
else
  aws iam create-role --role-name "$ROLE" \
    --assume-role-policy-document "$TRUST" \
    --description "GitHub Actions: deploy skill_sync via SSM" \
    --max-session-duration 3600 >/dev/null
  echo "Role created."
fi

# --- 3. Least-privilege permissions ---------------------------------------
POLICY=$(cat <<JSON
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "SendDeployCommand",
      "Effect": "Allow",
      "Action": "ssm:SendCommand",
      "Resource": [
        "arn:aws:ec2:${REGION}:${ACCOUNT}:instance/${INSTANCE}",
        "arn:aws:ssm:${REGION}::document/AWS-RunShellScript"
      ]
    },
    {
      "Sid": "ReadCommandResult",
      "Effect": "Allow",
      "Action": "ssm:GetCommandInvocation",
      "Resource": "arn:aws:ssm:${REGION}:${ACCOUNT}:*"
    }
  ]
}
JSON
)
aws iam put-role-policy --role-name "$ROLE" \
  --policy-name deploy-via-ssm --policy-document "$POLICY"
echo "Policy attached. Role ARN: arn:aws:iam::${ACCOUNT}:role/${ROLE}"
echo "Done. Pushes to main/master will now deploy via .github/workflows/deploy.yml."
