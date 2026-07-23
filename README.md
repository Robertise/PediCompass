# Pedix - Local Development Setup

Welcome to the Pedix project! This guide will walk you through setting up and running the entire application locally, from vector database ingestion to firing up the frontend and backend servers.

---

## 📋 Table of Contents
1. [Prerequisites](#-prerequisites)
2. [Step 1: Environment Configuration](#️-step-1-environment-configuration)
3. [Step 2: Start Qdrant (Vector Database)](#-step-2-start-qdrant-vector-database)
4. [Step 3: Run Data Ingestion](#-step-3-run-data-ingestion)
5. [Step 4: Start Backend](#-step-4-start-backend)
6. [Step 5: Start Frontend](#-step-5-start-frontend)
7. [Running Tests (Optional)](#-running-tests-optional)
8. [AWS Configuration Guide](#️-aws-configuration-guide)
9. [Architecture Overview](#-architecture-overview)

---

## 📌 Prerequisites

Before you begin, ensure you have the following installed on your machine:
- **Python 3.11+**
- **Node.js 20+**
- **Docker Desktop** (Required for Qdrant vector database)
- **AWS CLI** (`pip install awscli`)
- **AWS Account** with credentials configured for access to: Amazon Bedrock, DynamoDB, Cognito

---

## 🛠️ Step 1: Environment Configuration

First, you need to set up your environment variables.

```bash
# Clone the repository (if you haven't already) and navigate to the project root
# Copy the example environment file
cp .env.example .env
```

**Action Required:** Open `.env` and fill in all the necessary AWS and application configurations. Refer to the [AWS Configuration Guide](#️-aws-configuration-guide) section below if you need help finding these values.

---

## 🐳 Step 2: Start Qdrant (Vector Database)

We use Qdrant to store and query vectorized medical documents.

```bash
# Start the Qdrant container in the background
docker compose up -d

# Verify Qdrant is running healthily
curl http://localhost:6333/healthz
```

---

## 🧠 Step 3: Run Data Ingestion

Before the AI can answer queries accurately, we must ingest the medical data into Qdrant.
Make sure **Docker (Qdrant)** is running and your `.env` file is fully configured with your AWS credentials.

```bash
# Navigate to the ingestion directory
cd ingestion

# Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate      # Windows
# source venv/bin/activate  # macOS/Linux

# Install dependencies (CPU-only PyTorch recommended for local runs to avoid heavy downloads)
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
```

### Run Batch Ingestion (Recommended)

To ingest all the foundational medical documents with Contextual Retrieval enabled, we have provided a batch script:

```bash
# For Windows:
run_ingestion.bat

# For macOS/Linux (you can run commands manually or create a shell script):
# python run_ingestion.py --file data/fever_under_5s.md --source NICE
# ... (see run_ingestion.bat for full list of files)
```

> **Note:** If AWS rate limits are hit during ingestion, the script will automatically pause for 60 seconds and retry (up to 7 times).

### Ingesting Large Files Separately

The batch script above processes 7 out of the 8 data files. The final file (`hospital_care_for_children.md`) is significantly larger and is intentionally left out of the batch run. 

To ingest this large file, run it separately. You can optionally use the `--skip-context` flag if you want to disable Contextual Retrieval (via Haiku) to save time/cost on this massive file:

```bash
# Run with Contextual Retrieval enabled (may take a long time and hit AWS rate limits)
python run_ingestion.py --file data/hospital_care_for_children.md --source WHO

# OR Run WITHOUT Contextual Retrieval (faster, saves Bedrock costs)
python run_ingestion.py --file data/hospital_care_for_children.md --source WHO --skip-context
```

---

## ⚙️ Step 4: Start Backend

The backend is built with FastAPI. Open a **new terminal window**.

```bash
# Navigate to the backend directory from project root
cd backend

# Create and activate a virtual environment (Separate from ingestion env is recommended)
python -m venv venv
venv\Scripts\activate      # Windows
# source venv/bin/activate  # macOS/Linux

# Install PyTorch CPU-only FIRST
pip install torch --index-url https://download.pytorch.org/whl/cpu

# Install the rest of the backend dependencies
pip install -r requirements.txt

# Start the FastAPI server (it will automatically pick up the .env in the root folder)
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

> **Verify Backend:** Open your browser and go to `http://localhost:8000/api/health`

---

## 💻 Step 5: Start Frontend

The frontend is built with React and Vite. Open a **new terminal window** to keep the backend running.

```bash
# Navigate to the frontend directory from project root
cd frontend

# Install Node modules
npm install

# Start the Vite development server
npm run dev
```

> **View App:** Open your browser and navigate to `http://localhost:5173`

---

## 🧪 Running Tests (Optional)

To ensure everything is working correctly on the backend side:

```bash
# Inside the backend directory (with the virtual environment activated)
pytest tests/ -v
```

---

## ☁️ AWS Configuration Guide

You need to supply values for several variables in `.env`. Here is how to find them using the AWS CLI.

### AWS Region
Use `ap-southeast-1` (Singapore) for better latency or if cross-region inference is available for your models there.

### AWS Credentials
```bash
# Configure your AWS CLI after creating an IAM user with the required policies
aws configure
# Enter Access Key ID, Secret Access Key, region (e.g., ap-southeast-1), output format (json)
```

**Required IAM permissions (JSON Policy):**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {"Effect": "Allow", "Action": ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"], "Resource": "*"},
    {"Effect": "Allow", "Action": "dynamodb:*", "Resource": "arn:aws:dynamodb:ap-southeast-1:*:table/pedix_*"},
    {"Effect": "Allow", "Action": "cognito-idp:*", "Resource": "*"}
  ]
}
```

### Bedrock Model ID
```bash
# List all available Claude Sonnet profiles (use inferenceProfileId)
aws bedrock list-inference-profiles --region ap-southeast-1 --query "inferenceProfileSummaries[?contains(inferenceProfileName, 'Sonnet')]"
```
Copy the `inferenceProfileId` value (e.g., `ap.anthropic.claude-3-5-sonnet-20241022-v2:0`) into `BEDROCK_MODEL_ID` in your `.env` file.

```bash
# Also get the Haiku profile for faster/cheaper ingestion
aws bedrock list-inference-profiles --region ap-southeast-1 --query "inferenceProfileSummaries[?contains(inferenceProfileName, 'Haiku')]"
```

### Cognito
```bash
# List your User Pools to find the Pool ID
aws cognito-idp list-user-pools --max-results 10 --region ap-southeast-1

# List App Clients for your specific Pool ID to find the Client ID
aws cognito-idp list-user-pool-clients --user-pool-id YOUR_POOL_ID --region ap-southeast-1
```

---

## 🏗 Architecture Overview

```text
Frontend (React+Vite :5173) 
       │
       ▼
Backend (FastAPI :8000) ────────► Qdrant (Vector DB :6333)
       │
       ▼
AWS Cloud Services
 ├─► Amazon Bedrock (Claude Sonnet / Haiku)
 ├─► Amazon DynamoDB (Chat History & Metadata)
 └─► Amazon Cognito (Authentication)
```

*See `../implementation_plan.md` (if available) for deeper architectural details.*
