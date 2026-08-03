# Pedix — Setup Guide

This guide covers both **local development** setup and **AWS service configuration** required to run Pedix.

> For the full deployed cloud infrastructure and live resource IDs, see [`docs/cloud_setup.md`](cloud_setup.md).

---

## 📋 Table of Contents

**Part 1 — Local Development**
1. [Prerequisites](#1-prerequisites)
2. [Environment Variables](#2-environment-variables)
3. [Start Qdrant (Vector Database)](#3-start-qdrant-vector-database)
4. [Run Data Ingestion](#4-run-data-ingestion)
5. [Start Backend](#5-start-backend)
6. [Start Frontend](#6-start-frontend)

**Part 2 — AWS Service Configuration**
7. [IAM Roles & Policies](#7-iam-roles--policies)
8. [Amazon Cognito User Pool](#8-amazon-cognito-user-pool)
9. [Post Confirmation Lambda Trigger](#9-post-confirmation-lambda-trigger)
10. [Amazon DynamoDB Tables](#10-amazon-dynamodb-tables)
11. [Amazon Bedrock Inference Profiles](#11-amazon-bedrock-inference-profiles)
12. [API Gateway Authorizer](#12-api-gateway-authorizer)
13. [Resource Tagging](#13-resource-tagging)

---

# Part 1 — Local Development

## 1. Prerequisites

Ensure the following are installed before starting:

| Tool | Minimum Version | Purpose |
|---|---|---|
| **Python** | 3.11+ | Backend & ingestion runtime |
| **Node.js** | 20+ | Frontend build toolchain |
| **Docker Desktop** | Latest | Qdrant vector database container |
| **AWS CLI** | v2 | AWS service access |
| **Git** | Latest | Repository management |

Install AWS CLI:
```bash
pip install awscli
```

Configure AWS credentials (required for Bedrock, DynamoDB, Cognito access):
```bash
aws configure
# Enter: Access Key ID, Secret Access Key, region (ap-southeast-1), output format (json)
```

---

## 2. Environment Variables

Copy the example environment file and fill in your values:

```bash
cp .env.example .env
```

Open `.env` and configure:

```bash
# ─── AWS ──────────────────────────────────────────────────────────────────────
AWS_REGION=ap-southeast-1
# For local dev: provide IAM user credentials
# For EC2 deployment: leave blank — the EC2 IAM Role is used automatically
AWS_ACCESS_KEY_ID=your_access_key_id_here
AWS_SECRET_ACCESS_KEY=your_secret_access_key_here

# ─── Bedrock ──────────────────────────────────────────────────────────────────
# Must use the inference profile ID, NOT the foundation model ID.
# Using a bare model ID causes: ValidationException: on-demand throughput isn't supported.
BEDROCK_MODEL_ID=global.anthropic.claude-haiku-4-5-20251001-v1:0
BEDROCK_HAIKU_MODEL_ID=global.anthropic.claude-haiku-4-5-20251001-v1:0

# ─── Cognito ──────────────────────────────────────────────────────────────────
COGNITO_USER_POOL_ID=ap-southeast-1_XXXXXXXXX
COGNITO_CLIENT_ID=XXXXXXXXXXXXXXXXXXXXXXXXXX
COGNITO_REGION=ap-southeast-1

# ─── DynamoDB ─────────────────────────────────────────────────────────────────
DYNAMODB_TABLE_PREFIX=pedix_

# ─── Qdrant (local Docker) ────────────────────────────────────────────────────
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION=pedix_kb

# ─── App ──────────────────────────────────────────────────────────────────────
FRONTEND_URL=http://localhost:5173
```

See [Section 11](#11-amazon-bedrock-inference-profiles) for how to find inference profile IDs via CLI.

---

## 3. Start Qdrant (Vector Database)

Qdrant runs as a Docker container. From the **project root**:

```bash
# Start the Qdrant container in the background
docker compose up -d

# Verify Qdrant is running
curl http://localhost:6333/healthz
```

---

## 4. Run Data Ingestion

Ingest the medical knowledge base documents into Qdrant before starting the backend.

**Requirements:** Docker (Qdrant) must be running and `.env` must be fully configured.

```bash
# Navigate to the ingestion directory
cd ingestion

# Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate       # Windows
# source venv/bin/activate  # macOS/Linux

# Install PyTorch CPU-only first (avoids heavy GPU downloads)
pip install torch --index-url https://download.pytorch.org/whl/cpu

# Install remaining ingestion dependencies
pip install -r requirements.txt
```

### Batch Ingestion (Recommended)

Ingest the 7 core medical documents with Contextual Retrieval enabled:

```bash
# Windows:
run_ingestion.bat

# macOS/Linux (run manually or adapt to a shell script):
# python run_ingestion.py --file data/fever_under_5s.md --source NICE
# ... (see run_ingestion.bat for the full file list)
```

> If AWS rate limits are hit during ingestion, the script automatically pauses for 60 seconds and retries (up to 7 times).

### Large File Ingestion (Separate Step)

`hospital_care_for_children.md` is significantly larger and is excluded from the batch script. Run it separately:

```bash
# With Contextual Retrieval (slower, higher cost):
python run_ingestion.py --file data/hospital_care_for_children.md --source WHO

# Without Contextual Retrieval (faster, lower cost):
python run_ingestion.py --file data/hospital_care_for_children.md --source WHO --skip-context
```

---

## 5. Start Backend

Open a **new terminal window**:

```bash
# Navigate to the backend directory
cd backend

# Create and activate a virtual environment (keep separate from ingestion venv)
python -m venv venv
venv\Scripts\activate       # Windows
# source venv/bin/activate  # macOS/Linux

# Install PyTorch CPU-only first
pip install torch --index-url https://download.pytorch.org/whl/cpu

# Install backend dependencies
pip install -r requirements.txt

# Start the FastAPI server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

> **Verify:** Open `http://localhost:8000/api/health` — should return `{"status":"ok","service":"pedix-backend"}`

> **⚠️ Important — `--workers 1`:** The SSE streaming endpoint uses an in-memory `PendingRequestStore` that is not shared across processes. Do **not** use `--workers 2+` in any environment (local or production) — it will cause `Request ID expired or not found` errors for streaming requests.

---

## 6. Start Frontend

Open another **new terminal window**:

```bash
# Navigate to the frontend directory
cd frontend

# Install Node.js dependencies
npm install

# Start the Vite development server
npm run dev
```

> **View App:** Open `http://localhost:5173`

---

# Part 2 — AWS Service Configuration

> These steps are required to set up the underlying AWS services. The deployed production environment is already configured — refer to [`docs/cloud_setup.md`](cloud_setup.md) for live resource IDs.

---

## 7. IAM Roles & Policies

### 7.1 `Pedix-EC2-Role` — Backend EC2 Instance

- **Trusted Entity**: `ec2.amazonaws.com`
- **Purpose**: Attached to the EC2 instance as an Instance Profile. Grants temporary AWS access without requiring hardcoded static keys in `.env`.
- **Managed Policy**: `AmazonSSMManagedInstanceCore` (enables AWS Systems Manager Session Manager for secure admin shell without opening public SSH).

**Custom Inline Policy — `Pedix-EC2-Permissions`:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "BedrockAccess",
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": "*"
    },
    {
      "Sid": "DynamoDBListTables",
      "Effect": "Allow",
      "Action": [
        "dynamodb:ListTables"
      ],
      "Resource": "*"
    },
    {
      "Sid": "DynamoDBAccess",
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem",
        "dynamodb:Query",
        "dynamodb:Scan"
      ],
      "Resource": [
        "arn:aws:dynamodb:*:*:table/pedix_*",
        "arn:aws:dynamodb:*:*:table/pedix_*/index/*"
      ]
    }
  ]
}
```

> **Note:** `dynamodb:ListTables` requires `Resource: "*"` — it cannot be scoped to specific tables.

> **Note:** The FastAPI application (`config.py`, `dynamodb_client.py`) is written to automatically fall back to the IAM Instance Profile when `AWS_ACCESS_KEY_ID` is absent from `.env`.

---

### 7.2 `Pedix-PostConfirmation-Role` — Lambda Execution Role

- **Trusted Entity**: `lambda.amazonaws.com`
- **Purpose**: Execution role for the Cognito Post-Confirmation Lambda trigger.
- **Managed Policy**: `AWSLambdaBasicExecutionRole` (allows Lambda to write execution logs to CloudWatch Logs).

**Custom Inline Policy — `Pedix-Cognito-GroupAssignment`:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cognito-idp:AdminAddUserToGroup"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## 8. Amazon Cognito User Pool

1. Create a **Cognito User Pool** in region `ap-southeast-1`.
2. Enable `USER_PASSWORD_AUTH` in the App Client settings.
3. Create two User Groups with **exactly** these names:
   - `pedix-users` — Default group for all registered users
   - `pedix-admins` — Admin group (manually assigned only)

> **Security Note:** Never configure automatic assignment to `pedix-admins`. Admins must be added manually via the AWS Console or AWS CLI by the root account.

---

## 9. Post Confirmation Lambda Trigger

This Lambda fires automatically after a user successfully verifies their email, adding them to the `pedix-users` group.

**Function Runtime:** Python 3.12

**Lambda Code:**

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

**Trigger Configuration:** Cognito User Pool → **User pool properties** → **Add Lambda trigger** → **Sign-up** → **Post confirmation trigger** → Select your Lambda function.

Attach the `Pedix-PostConfirmation-Role` as the Lambda execution role.

---

## 10. Amazon DynamoDB Tables

All four tables use **On-Demand (`PAY_PER_REQUEST`)** capacity mode and the table prefix `pedix_`.

> Tables are **auto-created on first backend startup** via the FastAPI lifespan event in `backend/main.py`. You do not need to create them manually.

| Table | Partition Key | Sort Key | TTL Attribute |
|---|---|---|---|
| `pedix_sessions` | `session_id` (String) | — | `expires_at` (24h) |
| `pedix_profiles` | `user_id` (String) | `profile_id` (String) | — |
| `pedix_analytics_log` | `log_id` (String) | `timestamp` (String) | `expires_at` (90d) |
| `pedix_documents` | `doc_id` (String) | — | — |

`pedix_analytics_log` also requires a GSI named `date_partition-index` on the `date_partition` attribute.

---

## 11. Amazon Bedrock Inference Profiles

Bedrock requires **inference profile IDs** — using bare foundation model IDs causes a `ValidationException`.

```bash
# List Claude Sonnet inference profiles
aws bedrock list-inference-profiles \
  --region ap-southeast-1 \
  --query "inferenceProfileSummaries[?contains(inferenceProfileName, 'Sonnet')]"

# List Claude Haiku inference profiles
aws bedrock list-inference-profiles \
  --region ap-southeast-1 \
  --query "inferenceProfileSummaries[?contains(inferenceProfileName, 'Haiku')]"
```

Copy the `inferenceProfileId` value (e.g. `global.anthropic.claude-haiku-4-5-20251001-v1:0`) into `BEDROCK_MODEL_ID` and `BEDROCK_HAIKU_MODEL_ID` in `.env`.

You must first enable Anthropic model access in the [Bedrock Console](https://console.aws.amazon.com/bedrock/home#/modelaccess) before inference profiles become available.

---

## 12. API Gateway Authorizer

Use a **Cognito User Pool Authorizer** at the API Gateway level to block unauthenticated requests before they reach EC2.

- **Authorizer Type**: Cognito User Pools
- **Token Source**: `Authorization` header
- **Apply to**: All API routes (`/api/*`) **except** the following public endpoints:
  - `GET /api/health`
  - `POST /api/auth/register`
  - `POST /api/auth/login`
  - `POST /api/auth/verify`
  - `POST /api/auth/resend-code`

> **Admin RBAC Note:** Do **not** use API Gateway to enforce `pedix-admins` group access — that requires a custom Lambda Authorizer. API Gateway validates only JWT signature and expiry. Admin-only route protection (e.g. `/api/analytics`) is handled safely inside FastAPI via the `get_admin_user` dependency.

---

## 13. Resource Tagging

Tag all AWS resources (EC2, Cognito, DynamoDB, Lambda, IAM Roles, ALB, S3, CloudFront) for cost tracking and resource organisation:

| Tag Key | Tag Value |
|---|---|
| `Project` | `Pedix` |
| `Environment` | `dev` or `prod` |
