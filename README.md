# PediCompass — Local Development Setup

## Prerequisites

- Python 3.11+
- Node.js 20+
- Docker Desktop (for Qdrant)
- AWS CLI (`pip install awscli`)
- AWS credentials configured with access to: Bedrock, DynamoDB, Cognito

---

## Quick Start

### 1. Clone & configure environment

```bash
cp .env.example .env
# Fill in all values in .env — see comments in .env.example for instructions
```

### 2. Start Qdrant (vector database)

```bash
docker compose up -d
# Verify: curl http://localhost:6333/healthz
```

### 3. Set up backend

```bash
cd backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate      # Windows
# source venv/bin/activate  # macOS/Linux

# Install PyTorch CPU-only FIRST (avoids pulling heavy CUDA build)
pip install torch --index-url https://download.pytorch.org/whl/cpu

# Install remaining dependencies
pip install -r requirements.txt

# Run backend (from the backend/ directory, with .env in code/)
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Verify: curl http://localhost:8000/api/health
```

### 4. Set up frontend

```bash
cd frontend
npm install
npm run dev
# Open: http://localhost:5173
```

---

## AWS Configuration Guide

You need to supply values for these variables in `.env`. Run each command to find the right value.

### AWS Region
Use `ap-southeast-1` (Singapore) for better latency or if cross-region inference is available for your models there.

### AWS Credentials
```bash
# Create IAM user with least-privilege policy (see below), then:
aws configure
# Enter Access Key ID, Secret Access Key, region (ap-southeast-1), output format (json)
```

Required IAM permissions:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {"Effect": "Allow", "Action": ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"], "Resource": "*"},
    {"Effect": "Allow", "Action": "dynamodb:*", "Resource": "arn:aws:dynamodb:ap-southeast-1:*:table/pedicompass_*"},
    {"Effect": "Allow", "Action": "cognito-idp:*", "Resource": "*"}
  ]
}
```

### Bedrock Model ID
```bash
# List all available inference profiles (use the inferenceProfileId, NOT foundationModelId)
aws bedrock list-inference-profiles --region ap-southeast-1 --query "inferenceProfileSummaries[?contains(inferenceProfileName, 'Sonnet')]"
```
Copy the `inferenceProfileId` value (e.g. `ap.anthropic.claude-3-5-sonnet-20241022-v2:0`) into `BEDROCK_MODEL_ID`.

```bash
# Also get Haiku profile for ingestion (cheaper)
aws bedrock list-inference-profiles --region ap-southeast-1 --query "inferenceProfileSummaries[?contains(inferenceProfileName, 'Haiku')]"
```

### Cognito
```bash
# List user pools
aws cognito-idp list-user-pools --max-results 10 --region ap-southeast-1

# List app clients for your pool
aws cognito-idp list-user-pool-clients --user-pool-id YOUR_POOL_ID --region ap-southeast-1
```

---

## Running the Ingestion Pipeline

```bash
cd ingestion

# Install ingestion dependencies (separate venv recommended)
python -m venv venv
venv\Scripts\activate
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt

# Run ingestion (Qdrant must be running first)
python run_ingestion.py --file data/nice_cg160.pdf --source NICE
python run_ingestion.py --file data/who_pocket_book.pdf --source WHO
```

---

## Running Tests

```bash
cd backend
pytest tests/ -v
```

---

## Architecture Overview

```
Frontend (React+Vite :5173) → Backend (FastAPI :8000) → Qdrant (:6333)
                                      ↓
                              AWS Bedrock (Claude Sonnet)
                              AWS DynamoDB
                              AWS Cognito
```

See `../implementation_plan.md` for full architecture details.
