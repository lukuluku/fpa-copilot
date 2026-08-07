#!/bin/bash

# Phase 8: Deploy to Azure Container Apps
# This script automates the deployment of Phase 7 code to Azure

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
RESOURCE_GROUP="fpa-copilot-rg"
REGISTRY_NAME="fpacopilotregistry"
LOCATION="eastus"
BACKEND_APP_NAME="fpa-copilot-backend"
FRONTEND_APP_NAME="fpa-copilot-frontend"
BACKEND_IMAGE="fpa-copilot-backend:latest"
FRONTEND_IMAGE="fpa-copilot-frontend:latest"
ENVIRONMENT_NAME="fpa-copilot-env"

echo -e "${BLUE}=== FP&A Copilot Azure Deployment ===${NC}\n"

# Check prerequisites
echo -e "${BLUE}Step 1: Checking prerequisites...${NC}"
if ! command -v az &> /dev/null; then
    echo -e "${RED}Azure CLI not found. Please install it first.${NC}"
    exit 1
fi
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Docker not found. Please install it first.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Prerequisites met${NC}\n"

# Get Azure subscription
echo -e "${BLUE}Step 2: Checking Azure subscription...${NC}"
SUBSCRIPTION=$(az account show --query id -o tsv 2>/dev/null || echo "")
if [ -z "$SUBSCRIPTION" ]; then
    echo -e "${RED}Not logged into Azure. Running 'az login'...${NC}"
    az login
    SUBSCRIPTION=$(az account show --query id -o tsv)
fi
echo -e "${GREEN}✓ Using subscription: $SUBSCRIPTION${NC}\n"

# Create resource group
echo -e "${BLUE}Step 3: Creating/verifying resource group...${NC}"
if az group exists --name $RESOURCE_GROUP --query value -o tsv | grep -q true; then
    echo -e "${GREEN}✓ Resource group '$RESOURCE_GROUP' exists${NC}"
else
    echo "Creating resource group..."
    az group create --name $RESOURCE_GROUP --location $LOCATION
    echo -e "${GREEN}✓ Resource group created${NC}"
fi
echo

# Create container registry
echo -e "${BLUE}Step 4: Creating/verifying Container Registry...${NC}"
if az acr show --resource-group $RESOURCE_GROUP --name $REGISTRY_NAME &>/dev/null; then
    echo -e "${GREEN}✓ Container Registry '$REGISTRY_NAME' exists${NC}"
else
    echo "Creating container registry..."
    az acr create --resource-group $RESOURCE_GROUP \
        --name $REGISTRY_NAME --sku Basic
    echo -e "${GREEN}✓ Container Registry created${NC}"
fi
echo

# Login to container registry
echo -e "${BLUE}Step 5: Logging into Container Registry...${NC}"
az acr login --name $REGISTRY_NAME
echo -e "${GREEN}✓ Logged into registry${NC}\n"

# Build and push backend image
echo -e "${BLUE}Step 6: Building and pushing backend image...${NC}"
REGISTRY_URL="${REGISTRY_NAME}.azurecr.io"
BACKEND_FULL_IMAGE="${REGISTRY_URL}/${BACKEND_IMAGE}"

echo "Building backend image: $BACKEND_IMAGE"
docker build -t $BACKEND_IMAGE -f backend/Dockerfile .

echo "Tagging image: $BACKEND_FULL_IMAGE"
docker tag $BACKEND_IMAGE $BACKEND_FULL_IMAGE

echo "Pushing image to registry..."
docker push $BACKEND_FULL_IMAGE
echo -e "${GREEN}✓ Backend image pushed${NC}\n"

# Build and push frontend image
echo -e "${BLUE}Step 7: Building and pushing frontend image...${NC}"
FRONTEND_FULL_IMAGE="${REGISTRY_URL}/${FRONTEND_IMAGE}"

echo "Building frontend image: $FRONTEND_IMAGE"
docker build -t $FRONTEND_IMAGE -f frontend/Dockerfile .

echo "Tagging image: $FRONTEND_FULL_IMAGE"
docker tag $FRONTEND_IMAGE $FRONTEND_FULL_IMAGE

echo "Pushing image to registry..."
docker push $FRONTEND_FULL_IMAGE
echo -e "${GREEN}✓ Frontend image pushed${NC}\n"

# Get registry credentials
echo -e "${BLUE}Step 8: Retrieving registry credentials...${NC}"
REGISTRY_USER=$(az acr credential show --resource-group $RESOURCE_GROUP \
    --name $REGISTRY_NAME --query username -o tsv)
REGISTRY_PASS=$(az acr credential show --resource-group $RESOURCE_GROUP \
    --name $REGISTRY_NAME --query passwords[0].value -o tsv)
echo -e "${GREEN}✓ Credentials retrieved${NC}\n"

# Check for environment variables
echo -e "${BLUE}Step 9: Checking for required environment variables...${NC}"
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo -e "${RED}ANTHROPIC_API_KEY not set. Please set it:${NC}"
    echo "export ANTHROPIC_API_KEY='your-key-here'"
    exit 1
fi
echo -e "${GREEN}✓ ANTHROPIC_API_KEY is set${NC}\n"

# Enable Container Apps extension
echo -e "${BLUE}Step 10: Enabling Container Apps extension...${NC}"
az extension add --name containerapp --upgrade 2>/dev/null || true
echo -e "${GREEN}✓ Extension ready${NC}\n"

# Create Container Apps environment (if needed)
echo -e "${BLUE}Step 11: Creating/verifying Container Apps environment...${NC}"
if az containerapp env show --resource-group $RESOURCE_GROUP \
    --name $ENVIRONMENT_NAME &>/dev/null; then
    echo -e "${GREEN}✓ Environment '$ENVIRONMENT_NAME' exists${NC}"
else
    echo "Creating Container Apps environment..."
    az containerapp env create --name $ENVIRONMENT_NAME \
        --resource-group $RESOURCE_GROUP --location $LOCATION
    echo -e "${GREEN}✓ Environment created${NC}"
fi
echo

# Deploy backend
echo -e "${BLUE}Step 12: Deploying backend to Container Apps...${NC}"
if az containerapp show --name $BACKEND_APP_NAME \
    --resource-group $RESOURCE_GROUP &>/dev/null; then
    echo "Updating existing backend app..."
    az containerapp update \
        --name $BACKEND_APP_NAME \
        --resource-group $RESOURCE_GROUP \
        --image $BACKEND_FULL_IMAGE
else
    echo "Creating new backend app..."
    az containerapp create \
        --name $BACKEND_APP_NAME \
        --resource-group $RESOURCE_GROUP \
        --environment $ENVIRONMENT_NAME \
        --image $BACKEND_FULL_IMAGE \
        --target-port 8000 \
        --ingress external \
        --env-vars \
            ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" \
            RATE_LIMIT_PER_MIN=20 \
            QUERY_CAP_PER_SESSION=50 \
            DAILY_COST_CEILING=10.0 \
        --registry-server $REGISTRY_URL \
        --registry-username $REGISTRY_USER \
        --registry-password $REGISTRY_PASS
fi
echo -e "${GREEN}✓ Backend deployed${NC}\n"

# Get backend URL
echo -e "${BLUE}Step 13: Retrieving backend URL...${NC}"
BACKEND_URL=$(az containerapp show --name $BACKEND_APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --query properties.configuration.ingress.fqdn -o tsv)
echo -e "${GREEN}✓ Backend URL: $BACKEND_URL${NC}\n"

# Deploy frontend
echo -e "${BLUE}Step 14: Deploying frontend to Container Apps...${NC}"
if az containerapp show --name $FRONTEND_APP_NAME \
    --resource-group $RESOURCE_GROUP &>/dev/null; then
    echo "Updating existing frontend app..."
    az containerapp update \
        --name $FRONTEND_APP_NAME \
        --resource-group $RESOURCE_GROUP \
        --image $FRONTEND_FULL_IMAGE \
        --env-vars NEXT_PUBLIC_API_URL="https://$BACKEND_URL"
else
    echo "Creating new frontend app..."
    az containerapp create \
        --name $FRONTEND_APP_NAME \
        --resource-group $RESOURCE_GROUP \
        --environment $ENVIRONMENT_NAME \
        --image $FRONTEND_FULL_IMAGE \
        --target-port 3000 \
        --ingress external \
        --env-vars NEXT_PUBLIC_API_URL="https://$BACKEND_URL" \
        --registry-server $REGISTRY_URL \
        --registry-username $REGISTRY_USER \
        --registry-password $REGISTRY_PASS
fi
echo -e "${GREEN}✓ Frontend deployed${NC}\n"

# Get frontend URL
echo -e "${BLUE}Step 15: Retrieving frontend URL...${NC}"
FRONTEND_URL=$(az containerapp show --name $FRONTEND_APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --query properties.configuration.ingress.fqdn -o tsv)
echo -e "${GREEN}✓ Frontend URL: $FRONTEND_URL${NC}\n"

# Verify deployment
echo -e "${BLUE}Step 16: Verifying deployment...${NC}"
echo "Waiting for services to be ready..."
sleep 10

echo "Testing backend health..."
if curl -s "https://$BACKEND_URL/status" | grep -q "ok"; then
    echo -e "${GREEN}✓ Backend is healthy${NC}"
else
    echo -e "${RED}✗ Backend health check failed${NC}"
fi

echo "Testing frontend..."
if curl -s "https://$FRONTEND_URL" | grep -q "html" || curl -s -o /dev/null -w "%{http_code}" "https://$FRONTEND_URL" | grep -q "200\|308"; then
    echo -e "${GREEN}✓ Frontend is accessible${NC}"
else
    echo -e "${RED}✗ Frontend check failed (may still be starting)${NC}"
fi
echo

# Summary
echo -e "${GREEN}=== Deployment Complete ===${NC}\n"
echo -e "${BLUE}Access your application:${NC}"
echo -e "  Frontend: ${GREEN}https://$FRONTEND_URL${NC}"
echo -e "  Backend:  ${GREEN}https://$BACKEND_URL${NC}"
echo
echo -e "${BLUE}Useful commands:${NC}"
echo "  View logs:     az containerapp logs show --name $BACKEND_APP_NAME --resource-group $RESOURCE_GROUP"
echo "  Update:        az containerapp update --name $BACKEND_APP_NAME --resource-group $RESOURCE_GROUP --image $BACKEND_FULL_IMAGE"
echo "  Delete:        az group delete --name $RESOURCE_GROUP"
echo
echo -e "${BLUE}Next steps:${NC}"
echo "  1. Open frontend URL in your browser"
echo "  2. Upload a CSV file"
echo "  3. Ask a financial question"
echo "  4. Verify the response includes traces"
echo "  5. Check guardrails status"
echo
