# Pedix — Cloud Infrastructure (Deployed)

> **Status**: ✅ 100% Production Live — August 2026
> **Region**: `ap-southeast-1` (Singapore)
> **Cost Strategy**: 100% AWS Free Tier Maximised (~$0.05/month for Bedrock only)

---

## 🌐 Live Endpoints

| Service | URL |
|---|---|
| **Frontend** (CloudFront CDN) | https://d2bx3usq72976a.cloudfront.net |
| **API Gateway** (REST + SSE) | https://96hnl890q4.execute-api.ap-southeast-1.amazonaws.com/prod |
| **Health Check** | https://96hnl890q4.execute-api.ap-southeast-1.amazonaws.com/prod/api/health |

---

## 🏗 Architecture Diagram

![PediCompass AWS Cloud Architecture](Pedix-architecture.drawio.png)

**Request Flow:**
```
User (Browser)
  └─► Amazon CloudFront (CDN + HTTPS)
        ├─► Amazon S3              — Static React frontend assets
        └─► Amazon API Gateway ──── /api/* requests
                  │  (Cognito JWT Authorizer validates token)
                  │  VPC Link (pedix-vpclink)
                  ▼
        ┌─ Default VPC (172.31.0.0/16) ─────────────────────┐
        │  Application Load Balancer - Internal              │
        │    └─► Target Group pedix-backend-tg (Port 8000)  │
        │          └─► EC2: Pedix-Backend-Server             │
        │                ├── FastAPI Backend (Port 8000)     │
        │                └── Qdrant Vector DB (Port 6333)    │
        └────────────────────────────────────────────────────┘
                  │
        ┌─────────┼──────────────────────────┐
        ▼         ▼                          ▼
  DynamoDB    Amazon Bedrock           AWS Lambda
  (4 Tables)  (Claude Haiku)     (Post Confirmation)
                                         ▲
                               Amazon Cognito ◄──► API Gateway (JWT Validation)
                               Amazon CloudWatch ◄── Logs (Lambda + API GW + EC2)
```

---

## ☁️ AWS Resources Deployed

### 🌍 Networking

| Resource | Value |
|---|---|
| **VPC** | Default VPC (`vpc-06b04fb658817aa7c`) |
| **VPC CIDR** | `172.31.0.0/16` |
| **Region** | `ap-southeast-1` (Singapore) |
| **Availability Zones** | `ap-southeast-1a` + `ap-southeast-1b` |

> **Why Default VPC?** Using the Default VPC eliminates the need for a NAT Gateway (~$32/month). EC2 has a public IP and can reach AWS services (Bedrock, DynamoDB, Cognito) directly through the Internet Gateway that is pre-configured on the Default VPC.

---

### 🖥 Compute — EC2

| Attribute | Value |
|---|---|
| **Instance Name** | `Pedix-Backend-Server` |
| **Instance Type** | `t2.micro` / `t3.micro` (Free Tier Eligible) |
| **AMI** | Ubuntu Server 26.04 LTS |
| **Public IPv4** | `47.129.182.229` |
| **Private IPv4** | `172.31.42.140` |
| **Storage** | 30 GiB gp3 EBS + 2 GiB Swap (virtual memory) |
| **IAM Role** | `Pedix-EC2-Role` (no hardcoded credentials) |
| **Security Group** | `pedix-ec2-sg` |
| **Key Pair** | `pedix-ec2-key.pem` |

**Security Group Rules (`pedix-ec2-sg`):**

| Direction | Port | Source | Purpose |
|---|---|---|---|
| Inbound | 22 (SSH) | `0.0.0.0/0` | Admin SSH access |
| Inbound | 8000 (HTTP) | `pedix-alb-sg` only | Zero-Trust: ALB traffic only |
| Outbound | All | `0.0.0.0/0` | Internet access (Bedrock, DynamoDB, etc.) |

---

### 🔧 Application Runtime (on EC2)

| Component | Details |
|---|---|
| **Backend** | FastAPI + Uvicorn, `--workers 1`, Port `8000` |
| **Service Manager** | `systemd` (`pedix-backend.service`, auto-restart on failure) |
| **Vector DB** | Qdrant Docker (`qdrant/qdrant:latest`), Port `6333` (localhost only) |
| **Qdrant Storage** | `/opt/pedicompass/qdrant_data` (persistent on EBS) |
| **Project Path** | `/home/ubuntu/pedix/` |

> **Why `--workers 1`?** The SSE streaming endpoint uses an in-memory `PendingRequestStore` to correlate `POST /api/chat/register` and `GET /api/chat/stream` requests. This store is not shared across OS processes — using `--workers 2+` causes `Request ID expired or not found` errors for roughly half of all streaming requests.

---

### ⚖️ Load Balancer

| Attribute | Value |
|---|---|
| **Name** | `pedix-internal-alb` |
| **Scheme** | **Internal** (Private to VPC, no public IP) |
| **IP Address Type** | IPv4 |
| **VPC** | Default VPC (`172.31.0.0/16`) |
| **Subnets** | `ap-southeast-1a` + `ap-southeast-1b` |
| **Security Group** | `pedix-alb-sg` (Inbound HTTP Port 80 from `0.0.0.0/0`) |
| **Listener** | HTTP Port `80` → Forward to `pedix-backend-tg` |
| **ARN** | `arn:aws:elasticloadbalancing:ap-southeast-1:638954280521:loadbalancer/app/pedix-internal-alb/cd4fab931a8b0ccb` |

**Target Group (`pedix-backend-tg`):**

| Attribute | Value |
|---|---|
| **Protocol / Port** | HTTP / `8000` |
| **Target Type** | Instance |
| **Health Check Path** | `/api/health` |
| **Health Check Interval** | 30 seconds |
| **Registered Target** | `Pedix-Backend-Server` (`172.31.42.140:8000`) |
| **Health Status** | ✅ Healthy |
| **ARN** | `arn:aws:elasticloadbalancing:ap-southeast-1:638954280521:targetgroup/pedix-backend-tg/45c2461da2133ca8` |

> **Why Internal ALB?** AWS API Gateway (REST) with VPC Link requires an ALB or NLB as the integration target — it cannot route directly to a private EC2 IP. The Internal ALB serves as the mandatory bridge between the public API Gateway and the private EC2 instance, while also providing health checking and a foundation for future horizontal scaling.

---

### 🔌 API Gateway

| Attribute | Value |
|---|---|
| **API Name** | `Pedix-API` |
| **API ID** | `96hnl890q4` |
| **Type** | Regional REST API |
| **Stage** | `prod` |
| **Invoke URL** | `https://96hnl890q4.execute-api.ap-southeast-1.amazonaws.com/prod` |
| **Authorizer** | `PedixCognitoAuthorizer` (Cognito JWT, token source: `Authorization` header) |

**VPC Link:**

| Attribute | Value |
|---|---|
| **Name** | `pedix-vpclink` |
| **ID** | `fzvy02` |
| **Target** | `pedix-internal-alb` |
| **Status** | ✅ Available |

**Resource Integrations:**

| Resource | Method | Transfer Mode | Target |
|---|---|---|---|
| `/api/{proxy+}` | ANY | Buffered | VPC Link → ALB |
| `/api/chat/stream` | GET | **Stream** (SSE real-time) | VPC Link → ALB |
| `/api/chat/{proxy+}` | ANY | Buffered | VPC Link → ALB |

---

### 📦 Storage & CDN

**Amazon S3:**

| Attribute | Value |
|---|---|
| **Bucket Name** | `pedix-frontend-prod` |
| **Access** | Private (Block All Public Access enabled) |
| **Contents** | React + Vite production build (`dist/`) |

**Amazon CloudFront:**

| Attribute | Value |
|---|---|
| **Distribution Domain** | `d2bx3usq72976a.cloudfront.net` |
| **Default Root Object** | `index.html` |
| **SPA Fallback** | HTTP 403 + 404 errors → `/index.html` (response code 200) |
| **Origin 1 — S3** | `pedix-frontend-prod.s3.ap-southeast-1.amazonaws.com` — path `*` (static assets) |
| **Origin 2 — API GW** | `96hnl890q4.execute-api.ap-southeast-1.amazonaws.com` — path `/api/*` (caching disabled) |

> **Cache Invalidation Note:** After deploying new frontend builds to S3, run a CloudFront invalidation (`/*`) to flush stale cached `index.html` and JS bundles.

---

### 🔐 Authentication

**Amazon Cognito:**

| Attribute | Value |
|---|---|
| **User Pool ID** | `ap-southeast-1_Osm01gaEp` |
| **App Client ID** | `2eh8v88egbs0khrutkemnjtceu` |
| **Region** | `ap-southeast-1` |
| **Auth Flow** | `USER_PASSWORD_AUTH` |
| **User Groups** | `pedix-users` (default), `pedix-admins` (manually assigned only) |
| **Post Confirmation Trigger** | `Pedix-PostConfirmation` Lambda |

**AWS Lambda — Post Confirmation:**

| Attribute | Value |
|---|---|
| **Function Name** | `Pedix-PostConfirmation` |
| **Runtime** | Python 3.12 |
| **Trigger** | Cognito Post Confirmation (fires after email verification) |
| **Execution Role** | `Pedix-PostConfirmation-Role` |
| **Purpose** | Auto-assigns newly verified users to the `pedix-users` Cognito group |
| **Logs** | CloudWatch `/aws/lambda/Pedix-PostConfirmation` (automatic) |

---

### 🗄 Database

**Amazon DynamoDB — On-Demand (`PAY_PER_REQUEST`):**

| Table | Primary Key | TTL | Purpose |
|---|---|---|---|
| `pedix_sessions` | `session_id` | 24 hours | Conversation message history |
| `pedix_profiles` | `user_id` + `profile_id` | None (permanent) | Child health profiles |
| `pedix_analytics_log` | `log_id` + GSI `date_partition-index` | 90 days | Admin usage analytics |
| `pedix_documents` | `doc_id` | None (permanent) | Knowledge base document registry |

> All tables are auto-created on backend startup via the FastAPI lifespan event in `backend/main.py`.

---

### 🤖 AI Models (Amazon Bedrock)

| Environment Variable | Model ID | Usage |
|---|---|---|
| `BEDROCK_MODEL_ID` | `global.anthropic.claude-haiku-4-5-20251001-v1:0` | Runtime agentic reasoning (all stages) |
| `BEDROCK_HAIKU_MODEL_ID` | `global.anthropic.claude-haiku-4-5-20251001-v1:0` | Ingestion contextual retrieval + safety screen |

> Both variables use Claude Haiku. The original design planned Claude 3.5 Sonnet for `BEDROCK_MODEL_ID`, but Sonnet's low throughput on the Free Tier caused throttling. Haiku provides sufficient reasoning quality for the agentic triage workflow at lower cost and higher throughput.

---

### 📊 Monitoring

**Amazon CloudWatch** — log sources:

| Source | Log Group / Stream | Notes |
|---|---|---|
| Lambda `Pedix-PostConfirmation` | `/aws/lambda/Pedix-PostConfirmation` | Automatic (no config needed) |
| API Gateway `Pedix-API` | API Gateway access logs | Configured in stage settings |
| EC2 `Pedix-Backend-Server` | CloudWatch Agent | Application and system logs |

---

## 💰 Cost Summary

| Service | Free Tier Allowance | Monthly Cost |
|---|---|---|
| EC2 (t2.micro / t3.micro) | 750 hours/month | **$0** |
| EBS Storage (30 GiB gp3) | 30 GiB/month | **$0** |
| ALB | 750 hours/month (first 12 months) | **$0** |
| API Gateway | 1M requests/month | **$0** |
| CloudFront | 1 TB data transfer/month | **$0** |
| S3 | 5 GB storage + 20k GET requests | **$0** |
| DynamoDB | 25 GB storage + 25 RCU/WCU | **$0** |
| Cognito | 50,000 MAU | **$0** |
| Lambda | 1M requests/month + 400k GB-seconds | **$0** |
| CloudWatch | Basic metrics & log storage | **$0** |
| Amazon Bedrock | Pay-per-token (no free tier) | **~$0.05** |
| **Total Estimated** | | **~$0.05/month** |

---

## 🔐 Security Architecture

### Zero-Trust Network
- EC2 Port 8000 accepts traffic **only from `pedix-alb-sg`** — direct internet access to the backend is fully blocked at the Security Group level.
- Qdrant vector database is bound to `127.0.0.1:6333` only — not reachable from the network.

### IAM Least Privilege

**`Pedix-EC2-Role`** (EC2 Instance Profile — no static keys):
```json
{
  "Statement": [
    { "Sid": "BedrockAccess",
      "Action": ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
      "Resource": "*" },
    { "Sid": "DynamoDBListTables",
      "Action": ["dynamodb:ListTables"],
      "Resource": "*" },
    { "Sid": "DynamoDBAccess",
      "Action": ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem",
                 "dynamodb:DeleteItem", "dynamodb:Query", "dynamodb:Scan"],
      "Resource": ["arn:aws:dynamodb:*:*:table/pedix_*",
                   "arn:aws:dynamodb:*:*:table/pedix_*/index/*"] }
  ]
}
```

**`Pedix-PostConfirmation-Role`** (Lambda Execution Role):
```json
{
  "Statement": [
    { "Action": ["cognito-idp:AdminAddUserToGroup"], "Resource": "*" }
  ]
}
```
Plus AWS managed policy `AWSLambdaBasicExecutionRole` (CloudWatch log writes).

### Authentication & Authorisation
- **API Gateway**: `PedixCognitoAuthorizer` validates Cognito JWT on all `/api/*` routes (except public endpoints: `/api/health`, `/api/auth/register`, `/api/auth/login`, `/api/auth/verify`, `/api/auth/resend-code`).
- **FastAPI**: Secondary JWT verification via JWKS caching in `cognito_client.py` for defence-in-depth.
- **Admin RBAC**: `pedix-admins` group check enforced inside FastAPI via `get_admin_user` dependency — not at API Gateway level.
- **S3**: Private bucket — content served exclusively through CloudFront Origin Access.

---

## 🔄 Re-deployment Reference

If re-deploying from scratch, execute steps in this order:

| Step | Component | Notes |
|---|---|---|
| 1 | IAM Roles | `Pedix-EC2-Role` + `Pedix-PostConfirmation-Role` |
| 2 | Amazon Bedrock | Enable Anthropic model access in Bedrock Console |
| 3 | DynamoDB Tables | Auto-created on first backend startup |
| 4 | Cognito User Pool | Create pool, app client, groups, attach Lambda trigger |
| 5 | EC2 Instance | Launch, attach IAM role, configure Security Group, setup swap + Docker |
| 6 | Qdrant + Ingestion | Start container, run ingestion pipeline for all knowledge base files |
| 7 | Backend Service | Clone repo, configure `.env`, start `pedix-backend.service` |
| 8 | Internal ALB | Create Target Group + Internal ALB, register EC2, verify health |
| 9 | API Gateway | Create REST API, VPC Link, resource integrations, deploy `prod` stage |
| 10 | S3 + CloudFront | Build React app, upload to S3, create distribution, configure origins |
| 11 | Verify | `curl .../prod/api/health` → `{"status":"ok","service":"pedix-backend"}` |

See [`docs/setup.md`](setup.md) for detailed IAM policy JSON and Cognito configuration steps.
