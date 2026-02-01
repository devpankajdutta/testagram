# Testagram - Image Service Layer

Scalable backend service for image upload and metadata storage using FastAPI, S3, and DynamoDB.
This project uses **LocalStack** to emulate AWS services locally and supports both local (FastAPI) and serverless (Lambda/API Gateway) execution.

## Features
- **Upload Image**: Binary upload to S3 + Metadata storage in DynamoDB.
- **List Images**: Search with multi-tag and filename filters.
- **View/Download**: Get image metadata and a secure presigned S3 URL.
- **Delete Image**: Atomic removal from storage and database.
- **Serverless Ready**: Integrated with **Mangum** for AWS Lambda deployment.
- **Smart Config**: Automatic AWS endpoint discovery for LocalStack environments.

---

## 🚀 Quick Start (Local Development)

### 1. Prerequisites
- **Python 3.11+**
- **Docker Desktop** (for LocalStack)

### 2. Setup
```powershell
# Clone the repository and enter the directory
python -m venv .venv
.\.venv\Scripts\Activate
pip install -r requirements.txt
```

### 3. Start Infrastructure
```bash
# Start LocalStack (S3, DynamoDB, SSM)
docker-compose up -d
```

### 4. Run Locally
```bash
uvicorn app.main:app --reload --env-file dev.env --reload-exclude build
```
- **Interactive Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Health Check**: `curl http://127.0.0.1:8000/`

---

## ☁️ Serverless Deployment (LocalStack)

To deploy the application as a Lambda function behind an API Gateway:

### 1. Run Deployment Script
If on Windows, it is recommended to run this via **WSL** (Linux) to ensure dependency compatibility:
```bash
python3 deploy.py
```
This script automates:
- Dependency packaging into `function.zip`.
- IAM Role and Lambda function creation.
- API Gateway (REST V1) configuration.
- **ROOT_PATH** environment variable setup for Swagger UI.

### 2. Access the Deployed API
The script will output a URL like:
`http://localhost:4566/restapis/{api_id}/dev/_user_request_/docs`

### 3. Verification
Run the automated verification script:
```bash
python verify_deployment.py
```

---

## 🧪 Testing
Run the suite to verify all S3 and DynamoDB integrations:
```bash
pytest -v
```

## 📁 Project Structure
- `app/`: Main FastAPI application.
- `deploy.py`: Deployment orchestrator for AWS/LocalStack.
- `handler.py`: Lambda function entry point.
- `dev.env`: Local development configurations.
- `docker-compose.yml`: LocalStack service definition.

## 🛠️ Tech Stack
- **Framework**: FastAPI (Python)
- **AWS Adapter**: Mangum
- **Storage**: AWS S3 (Async via aioboto3)
- **Database**: AWS DynamoDB
- **Infrastructure Emulator**: LocalStack
