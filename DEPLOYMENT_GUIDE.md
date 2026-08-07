# Phase 7 → Phase 8: Azure Container Apps Deployment Guide

This guide walks you through deploying Phase 7 (locally tested) to Azure Container Apps with automated CI/CD.

## Quick Start

```bash
cd /Users/adedotunadebiaye/fpa-copilot
export ANTHROPIC_API_KEY="your-key-here"
./deploy.sh
```

The script handles everything: Azure setup, Docker builds, image pushes, and deployment.

---

## Prerequisites

### 1. Install Required Tools

```bash
# Azure CLI
# macOS with Homebrew:
brew install azure-cli

# Verify
az --version

# Docker (required)
# Download from https://www.docker.com/products/docker-desktop
docker --version
```

### 2. Azure Account Setup

```bash
# Login to Azure
az login

# Verify subscription
az account show

# Set default subscription (if needed)
az account set --subscription <subscription-id>
```

### 3. Anthropic API Key

Get your API key from https://console.anthropic.com/account/keys

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

---

## Deployment Steps

### Option A: Automated Script (Recommended)

```bash
cd /Users/adedotunadebiaye/fpa-copilot
export ANTHROPIC_API_KEY="sk-ant-..."
./deploy.sh
```

The script will:
1. ✓ Check prerequisites
2. ✓ Create Azure resource group
3. ✓ Create container registry
4. ✓ Build backend Docker image
5. ✓ Build frontend Docker image
6. ✓ Push images to registry
7. ✓ Deploy backend container app
8. ✓ Deploy frontend container app
9. ✓ Verify deployments
10. ✓ Provide access URLs

**Estimated time:** 5-10 minutes

---

### Option B: Manual Steps

#### Step 1: Create Azure Resources

```bash
# Define variables
RESOURCE_GROUP="fpa-copilot-rg"
REGISTRY_NAME="fpacopilotregistry"
LOCATION="eastus"

# Create resource group
az group create \
  --name $RESOURCE_GROUP \
  --location $LOCATION

# Create container registry
az acr create \
  --resource-group $RESOURCE_GROUP \
  --name $REGISTRY_NAME \
  --sku Basic

# Login to registry
az acr login --name $REGISTRY_NAME
```

#### Step 2: Build Docker Images

```bash
cd /Users/adedotunadebiaye/fpa-copilot

# Build backend
docker build -t fpa-copilot-backend:latest -f backend/Dockerfile .

# Build frontend
docker build -t fpa-copilot-frontend:latest -f frontend/Dockerfile .
```

#### Step 3: Push Images to Registry

```bash
REGISTRY="fpacopilotregistry.azurecr.io"

# Push backend
docker tag fpa-copilot-backend:latest $REGISTRY/fpa-copilot-backend:latest
docker push $REGISTRY/fpa-copilot-backend:latest

# Push frontend
docker tag fpa-copilot-frontend:latest $REGISTRY/fpa-copilot-frontend:latest
docker push $REGISTRY/fpa-copilot-frontend:latest

# Verify
az acr repository list --name fpacopilotregistry
```

#### Step 4: Create Container Apps Environment

```bash
ENVIRONMENT_NAME="fpa-copilot-env"

az extension add --name containerapp --upgrade

az containerapp env create \
  --name $ENVIRONMENT_NAME \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION
```

#### Step 5: Deploy Backend

```bash
# Get registry credentials
REGISTRY_USER=$(az acr credential show \
  --resource-group $RESOURCE_GROUP \
  --name $REGISTRY_NAME \
  --query username -o tsv)

REGISTRY_PASS=$(az acr credential show \
  --resource-group $RESOURCE_GROUP \
  --name $REGISTRY_NAME \
  --query passwords[0].value -o tsv)

# Deploy backend
az containerapp create \
  --name fpa-copilot-backend \
  --resource-group $RESOURCE_GROUP \
  --environment $ENVIRONMENT_NAME \
  --image $REGISTRY/fpa-copilot-backend:latest \
  --target-port 8000 \
  --ingress external \
  --env-vars \
    ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" \
    RATE_LIMIT_PER_MIN=20 \
    QUERY_CAP_PER_SESSION=50 \
    DAILY_COST_CEILING=10.0 \
  --registry-server $REGISTRY \
  --registry-username $REGISTRY_USER \
  --registry-password $REGISTRY_PASS
```

#### Step 6: Deploy Frontend

```bash
# Get backend URL
BACKEND_URL=$(az containerapp show \
  --name fpa-copilot-backend \
  --resource-group $RESOURCE_GROUP \
  --query properties.configuration.ingress.fqdn -o tsv)

# Deploy frontend
az containerapp create \
  --name fpa-copilot-frontend \
  --resource-group $RESOURCE_GROUP \
  --environment $ENVIRONMENT_NAME \
  --image $REGISTRY/fpa-copilot-frontend:latest \
  --target-port 3000 \
  --ingress external \
  --env-vars NEXT_PUBLIC_API_URL="https://$BACKEND_URL" \
  --registry-server $REGISTRY \
  --registry-username $REGISTRY_USER \
  --registry-password $REGISTRY_PASS
```

#### Step 7: Get URLs

```bash
# Backend URL
az containerapp show --name fpa-copilot-backend \
  --resource-group $RESOURCE_GROUP \
  --query properties.configuration.ingress.fqdn -o tsv

# Frontend URL
az containerapp show --name fpa-copilot-frontend \
  --resource-group $RESOURCE_GROUP \
  --query properties.configuration.ingress.fqdn -o tsv
```

---

## Verification & Testing

### 1. Check Service Status

```bash
# Backend health check
curl https://fpa-copilot-backend.azurecontainerapps.io/status

# Expected response:
# {
#   "status": "ok",
#   "version": "0.7",
#   "guardrails": {...}
# }
```

### 2. View Logs

```bash
# Backend logs
az containerapp logs show \
  --name fpa-copilot-backend \
  --resource-group fpa-copilot-rg

# Frontend logs
az containerapp logs show \
  --name fpa-copilot-frontend \
  --resource-group fpa-copilot-rg
```

### 3. Manual Testing

1. Open frontend URL in browser
2. Upload a CSV file (use `data/sample_budget_data.csv`)
3. Ask a financial question:
   - "What was the total revenue in Q1?"
   - "Compare marketing spend across regions"
4. Verify:
   - ✓ Response is returned
   - ✓ Traces are included
   - ✓ Guardrails status shows rate limits
   - ✓ No 500 errors in logs

### 4. Load Test

```bash
# Test backend endpoint
for i in {1..10}; do
  curl -X POST https://fpa-copilot-backend.azurecontainerapps.io/query \
    -H "Content-Type: application/json" \
    -d '{"query": "What is revenue?"}' &
done
wait

# Check rate limiting
curl -X GET 'https://fpa-copilot-backend.azurecontainerapps.io/guardrails/test-session'
```

---

## Success Criteria

- [ ] Frontend loads at Azure URL
- [ ] Can upload CSV without errors
- [ ] Can ask questions and get responses
- [ ] Responses include traces
- [ ] Guardrails enforced (rate limiting works)
- [ ] No 500 errors in logs
- [ ] Health check `/status` returns "ok"
- [ ] Both services scale to 1 replica

---

## Useful Commands

### Update Deployment

After code changes:

```bash
# Rebuild and push backend
docker build -t fpacopilotregistry.azurecr.io/fpa-copilot-backend:latest -f backend/Dockerfile .
docker push fpacopilotregistry.azurecr.io/fpa-copilot-backend:latest

# Update running container
az containerapp update \
  --name fpa-copilot-backend \
  --resource-group fpa-copilot-rg \
  --image fpacopilotregistry.azurecr.io/fpa-copilot-backend:latest

# Frontend (similar)
docker build -t fpacopilotregistry.azurecr.io/fpa-copilot-frontend:latest -f frontend/Dockerfile .
docker push fpacopilotregistry.azurecr.io/fpa-copilot-frontend:latest

az containerapp update \
  --name fpa-copilot-frontend \
  --resource-group fpa-copilot-rg \
  --image fpacopilotregistry.azurecr.io/fpa-copilot-frontend:latest
```

### Scale Replicas

```bash
# Set minReplicas and maxReplicas
az containerapp update \
  --name fpa-copilot-backend \
  --resource-group fpa-copilot-rg \
  --min-replicas 1 \
  --max-replicas 3
```

### Update Environment Variables

```bash
az containerapp update \
  --name fpa-copilot-backend \
  --resource-group fpa-copilot-rg \
  --set-env-vars RATE_LIMIT_PER_MIN=30
```

### View Resource Details

```bash
# Show container app configuration
az containerapp show \
  --name fpa-copilot-backend \
  --resource-group fpa-copilot-rg

# Show scaling settings
az containerapp show \
  --name fpa-copilot-backend \
  --resource-group fpa-copilot-rg \
  --query properties.template.scale
```

### Delete Deployment

```bash
# Delete resource group (deletes everything)
az group delete --name fpa-copilot-rg --yes
```

---

## Troubleshooting

### Container Won't Start

```bash
# Check logs
az containerapp logs show \
  --name fpa-copilot-backend \
  --resource-group fpa-copilot-rg

# Check configuration
az containerapp show \
  --name fpa-copilot-backend \
  --resource-group fpa-copilot-rg
```

**Common issues:**
- `ModuleNotFoundError`: Check requirements.txt is copied in Dockerfile
- `ANTHROPIC_API_KEY not set`: Verify env vars with `--show-all` flag
- Port mismatch: Backend uses 8000, frontend uses 3000

### Frontend Can't Reach Backend

```bash
# Verify NEXT_PUBLIC_API_URL is set
az containerapp show \
  --name fpa-copilot-frontend \
  --resource-group fpa-copilot-rg \
  --query properties.template.containers[0].env

# Update if wrong
BACKEND_URL=$(az containerapp show \
  --name fpa-copilot-backend \
  --resource-group fpa-copilot-rg \
  --query properties.configuration.ingress.fqdn -o tsv)

az containerapp update \
  --name fpa-copilot-frontend \
  --resource-group fpa-copilot-rg \
  --set-env-vars NEXT_PUBLIC_API_URL="https://$BACKEND_URL"
```

### High Latency

- **First request slow?** Cold start (2-3 seconds) is normal for Python/data loading
- **Consistent slowness?** Check CPU/memory in Azure portal
- **Network delays?** Verify region is `eastus` (close to most US users)

### Docker Build Fails

```bash
# Clean up and rebuild
docker system prune -a
docker build -t fpa-copilot-backend:latest -f backend/Dockerfile . --no-cache
```

---

## Next Steps (Phase 9+)

1. **Monitoring**: Set up Azure Application Insights
2. **Logging**: Use Azure Log Analytics
3. **Scaling**: Configure auto-scaling policies
4. **Database**: Add Azure Cosmos DB for session storage
5. **CI/CD**: Configure GitHub Actions (see `.github/workflows/deploy.yml`)

---

## Architecture

```
                    Internet
                       |
         ┌─────────────┼─────────────┐
         |                           |
    User Browser                  Mobile
         |                           |
         └─────────────┬─────────────┘
                       |
              Frontend Container
             (Node.js Next.js:3000)
                       |
              Backend Container
             (Python FastAPI:8000)
                       |
              Claude API + Guardrails
                       |
                   Responses
```

---

## Files Created

- `requirements.txt` — Python dependencies
- `backend/Dockerfile` — Backend container image
- `frontend/Dockerfile` — Frontend container image
- `deploy.sh` — Automated deployment script
- `.github/workflows/deploy.yml` — CI/CD pipeline
- `DEPLOYMENT_GUIDE.md` — This file

---

## References

- [Azure Container Apps Documentation](https://learn.microsoft.com/en-us/azure/container-apps/)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)
- [Next.js Production Builds](https://nextjs.org/docs/advanced-features/output-file-tracing)
- [Docker Best Practices](https://docs.docker.com/develop/develop-images/dockerfile_best-practices/)

---

**Status:** Phase 8 Ready to Deploy ✓
