# Option 3: Cloud Deployment Guide

## AWS Deployment

### AWS ECS/Fargate

1. **Build and push Docker image:**
```bash
aws ecr create-repository --repository-name uapk-gateway
docker build -t uapk-gateway -f backend/Dockerfile .
docker tag uapk-gateway:latest <account-id>.dkr.ecr.<region>.amazonaws.com/uapk-gateway:latest
aws ecr get-login-password | docker login --username AWS --password-stdin <account-id>.dkr.ecr.<region>.amazonaws.com
docker push <account-id>.dkr.ecr.<region>.amazonaws.com/uapk-gateway:latest
```

2. **Create RDS PostgreSQL database:**
```bash
aws rds create-db-instance \
  --db-instance-identifier uapk-db \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --master-username uapk \
  --master-user-password <secure-password> \
  --allocated-storage 20
```

3. **Create ECS task definition:**
```bash
# Save this as task-definition.json
{
  "family": "uapk-gateway",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "containerDefinitions": [{
    "name": "uapk-gateway",
    "image": "<account-id>.dkr.ecr.<region>.amazonaws.com/uapk-gateway:latest",
    "portMappings": [{
      "containerPort": 8000,
      "protocol": "tcp"
    }],
    "environment": [
      {"name": "ENVIRONMENT", "value": "production"},
      {"name": "SECRET_KEY", "value": "<generate-with-openssl>"},
      {"name": "DATABASE_URL", "value": "postgresql+asyncpg://..."},
      {"name": "GATEWAY_FERNET_KEY", "value": "<generate>"},
      {"name": "GATEWAY_ED25519_PRIVATE_KEY", "value": "<generate>"}
    ]
  }]
}

aws ecs register-task-definition --cli-input-json file://task-definition.json
```

4. **Create ECS service:**
```bash
aws ecs create-service \
  --cluster default \
  --service-name uapk-gateway \
  --task-definition uapk-gateway \
  --desired-count 2 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx],securityGroups=[sg-xxx],assignPublicIp=ENABLED}"
```

---

## GCP Cloud Run

1. **Build and deploy:**
```bash
gcloud builds submit --tag gcr.io/<project-id>/uapk-gateway
gcloud run deploy uapk-gateway \
  --image gcr.io/<project-id>/uapk-gateway \
  --platform managed \
  --region us-central1 \
  --set-env-vars ENVIRONMENT=production,SECRET_KEY=xxx,DATABASE_URL=xxx \
  --allow-unauthenticated \
  --memory 1Gi \
  --cpu 1
```

2. **Create Cloud SQL database:**
```bash
gcloud sql instances create uapk-db \
  --database-version=POSTGRES_14 \
  --tier=db-f1-micro \
  --region=us-central1

gcloud sql databases create uapk --instance=uapk-db
```

---

## Azure Container Instances

1. **Create resource group:**
```bash
az group create --name uapk-rg --location eastus
```

2. **Create PostgreSQL:**
```bash
az postgres server create \
  --resource-group uapk-rg \
  --name uapk-db \
  --sku-name B_Gen5_1 \
  --admin-user uapk \
  --admin-password <password>
```

3. **Deploy container:**
```bash
az container create \
  --resource-group uapk-rg \
  --name uapk-gateway \
  --image <your-registry>/uapk-gateway:latest \
  --cpu 1 --memory 1 \
  --ports 8000 \
  --environment-variables \
    ENVIRONMENT=production \
    SECRET_KEY=xxx \
    DATABASE_URL=xxx
```

---

## Required Environment Variables

Generate these before deployment:

```bash
# SECRET_KEY
openssl rand -hex 32

# GATEWAY_FERNET_KEY
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# GATEWAY_ED25519_PRIVATE_KEY
ssh-keygen -t ed25519 -f gateway_key -N ''
cat gateway_key
```

