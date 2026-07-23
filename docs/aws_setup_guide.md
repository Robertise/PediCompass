# Pedix AWS Setup Guide (Least Privilege Architecture)

This document outlines the required AWS configurations to deploy Pedix securely, focusing on Cognito Authentication, IAM Roles, and API Gateway Authorizers.

## 1. Cognito User Pool Setup

The authentication flow relies entirely on Cognito User Pools. **Identity Pools are NOT required** since the client never interacts directly with AWS services (all traffic flows through the FastAPI backend).

1. Create a **Cognito User Pool**.
2. Enable `USER_PASSWORD_AUTH` in the App Client settings.
3. Create two User Groups exactly as named:
   * `pedix-users` (Default group for regular users)
   * `pedix-admins` (Admin group)

> **Important:** Never configure an automatic way to join `pedix-admins`. Admins must be added manually by the AWS Root Account via the AWS Console or AWS CLI.

## 2. Post Confirmation Lambda Trigger

To automate assigning new users to the `pedix-users` group, we use a Lambda trigger. 
This Lambda fires *after* a user successfully verifies their email address.

### Lambda Code (Python)

```python
import boto3

def handler(event, context):
    client = boto3.client('cognito-idp')
    client.admin_add_user_to_group(
        UserPoolId=event['userPoolId'],
        Username=event['userName'],
        GroupName='pedix-users'
    )
    # CRITICAL: Must return the event object to continue the Cognito flow
    return event
```

### IAM Role for Lambda (`PedixLambdaRole`)

Attach this execution role to the Lambda function. It strictly allows adding users to groups and basic CloudWatch logging.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "CognitoAddUserToGroup",
      "Effect": "Allow",
      "Action": ["cognito-idp:AdminAddUserToGroup"],
      "Resource": "arn:aws:cognito-idp:REGION:ACCOUNT_ID:userpool/USER_POOL_ID"
    },
    {
      "Sid": "BasicLambdaLogs",
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    }
  ]
}
```

**Trigger Configuration:** Go to your Cognito User Pool -> Triggers -> Select **Post Confirmation** -> Choose your Lambda function.

## 3. IAM Role for FastAPI Backend (`PedixEC2Role`)

The FastAPI application will run on an EC2 instance. Rather than hardcoding `.env` credentials, the EC2 instance will assume an IAM Role via an Instance Profile.

Attach this role to your EC2 instance.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "BedrockInvoke",
      "Effect": "Allow",
      "Action": ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
      "Resource": "arn:aws:bedrock:*::foundation-model/anthropic.claude-*"
    },
    {
      "Sid": "DynamoDBAccess",
      "Effect": "Allow",
      "Action": [
        "dynamodb:PutItem", "dynamodb:GetItem", "dynamodb:UpdateItem",
        "dynamodb:DeleteItem", "dynamodb:Query", "dynamodb:Scan"
      ],
      "Resource": [
        "arn:aws:dynamodb:REGION:ACCOUNT_ID:table/pedix_*"
      ]
    },
    {
      "Sid": "CloudWatchMetrics",
      "Effect": "Allow",
      "Action": [
        "cloudwatch:PutMetricData",
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "*"
    }
  ]
}
```

*Note: The FastAPI code (`config.py`, `dynamodb_client.py`, etc.) is already written to gracefully fallback to this IAM Role if `AWS_ACCESS_KEY_ID` is omitted from the environment.*

## 4. API Gateway Authorizer

Use a **Cognito User Pool Authorizer** at the API Gateway layer to block unauthenticated requests *before* they hit EC2.

- **Authorization type:** Cognito User Pools
- **Cognito User Pool:** Select your Pedix User Pool
- **Token source:** `Authorization` header
- **Apply to:** All API routes (`/api/*`), EXCEPT for:
  - `/api/health`
  - `/api/auth/register`
  - `/api/auth/login`
  - `/api/auth/verify`
  - `/api/auth/resend-code`

> **Note on Admin Access:** Do NOT use API Gateway to enforce the `pedix-admins` group check. That requires a custom Lambda Authorizer which is overkill. The API Gateway will simply validate that the JWT signature and expiry are correct. The actual role-based access control (RBAC) is enforced safely within FastAPI using the `get_admin_user` dependency on routes like `/api/analytics`.

## 5. Resource Tagging

Ensure all AWS resources (EC2, Cognito, DynamoDB, Lambda, IAM Roles) are tagged for cost tracking:

*   **Project**: `Pedix`
*   **Environment**: `dev` (or `prod`)
