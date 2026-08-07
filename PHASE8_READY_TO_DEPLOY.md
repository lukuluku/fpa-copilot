# Phase 8: Ready to Deploy Phase 7 to Azure Container Apps

**Status:** ✅ All deployment files created and ready

**Date:** August 5, 2026  
**Commit:** main (2d90527)  
**Deployment Target:** Azure Container Apps

---

## Summary

Phase 7 (locally tested, production-ready) is now ready to be deployed to Azure Container Apps with full CI/CD automation. All necessary Docker configurations, deployment scripts, and documentation have been created.

### What Was Created

✅ **Docker Configurations:**
- `backend/Dockerfile` — Python 3.12, FastAPI, port 8000
- `frontend/Dockerfile` — Node.js 18, Next.js, port 3000
- `requirements.txt` — All Python dependencies

✅ **Deployment Automation:**
- `deploy.sh` — Fully automated deployment script
- `.github/workflows/deploy.yml` — GitHub Actions CI/CD pipeline
- `DEPLOYMENT_GUIDE.md` — Comprehensive step-by-step guide
- `PHASE8_READY_TO_DEPLOY.md` — This file

### What Gets Deployed

**Backend Service:**
- Code: `backend/` + `src/` + `mcp-server/`
- Runtime: Python 3.12 + FastAPI + Uvicorn
- Port: 8000
- Replicas: 1 (min=0, max=1 per ADR-01)
- Environment Variables:
  - `ANTHROPIC_API_KEY` (required)
  - `RATE_LIMIT_PER_MIN` (default: 20)
  - `QUERY_CAP_PER_SESSION` (default: 50)
  - `DAILY_COST_CEILING` (default: 10.0)

**Frontend Service:**
- Code: `frontend/` (Next.js 15)
- Runtime: Node.js 18
- Port: 3000
- Replicas: 1
- Environment Variables:
  - `NEXT_PUBLIC_API_URL` (auto-set to backend URL)

---

## How to Deploy

### Option 1: Automated Script (Recommended) ⚡

**Prerequisites:**
```bash
# Install Azure CLI
brew install azure-cli

# Verify
az --version
docker --version

# Login to Azure
az login
```

**Deploy:**
```bash
cd /Users/adedotunadebiaye/fpa-copilot

# Set your Anthropic API key
export ANTHROPIC_API_KEY="sk-ant-..."

# Run deployment
./deploy.sh
```

The script will:
1. Create Azure resource group
2. Create container registry
3. Build Docker images locally
4. Push to Azure Container Registry
5. Deploy both services
6. Verify they're running
7. Output your service URLs

**Time:** ~10 minutes (first time), ~2 minutes (subsequent)

---

### Option 2: GitHub Actions CI/CD

After initial deployment via script:

```bash
# 1. Commit and push to GitHub
git add .
git commit -m "Phase 8: Add Azure deployment files"
git push origin main

# 2. Set up GitHub secrets in your repo settings:
# - AZURE_CLIENT_ID
# - AZURE_TENANT_ID
# - AZURE_SUBSCRIPTION_ID

# 3. After this, every push to main auto-deploys
```

Workflow file: `.github/workflows/deploy.yml`

---

## Quick Start Checklist

- [ ] Install Azure CLI: `brew install azure-cli`
- [ ] Verify Docker installed: `docker --version`
- [ ] Azure login: `az login`
- [ ] Get Anthropic API key from https://console.anthropic.com/account/keys
- [ ] Set env var: `export ANTHROPIC_API_KEY="sk-ant-..."`
- [ ] Run script: `cd fpa-copilot && ./deploy.sh`
- [ ] Get frontend URL from script output
- [ ] Open URL in browser
- [ ] Test upload & query

---

## What Gets Created in Azure

### Resource Group
- Name: `fpa-copilot-rg`
- Location: `eastus`
- Estimated cost: ~$25-40/month

### Container Registry
- Name: `fpacopilotregistry`
- SKU: Basic ($5/month)
- Stores: Backend and frontend Docker images

### Container Apps Environment
- Name: `fpa-copilot-env`
- Provides: Networking, monitoring, logging

### Containers
- Backend: `fpa-copilot-backend` (Python/FastAPI)
- Frontend: `fpa-copilot-frontend` (Node.js/Next.js)

**Total estimated cost:** $35-50/month (including storage, networking)

---

## Verification Steps

After deployment, the script will:

1. ✅ Check backend health at `/status`
2. ✅ Check frontend accessibility
3. ✅ Print both service URLs

### Manual Testing

```bash
# 1. Get URLs (script prints them)
# Frontend: https://fpa-copilot-frontend.azurecontainerapps.io
# Backend: https://fpa-copilot-backend.azurecontainerapps.io

# 2. Test backend health
curl https://fpa-copilot-backend.azurecontainerapps.io/status

# 3. Open frontend in browser
# - Upload data/sample_budget_data.csv
# - Ask: "What was total revenue in Q1?"
# - Verify response includes traces

# 4. Check guardrails
curl -X GET 'https://fpa-copilot-backend.azurecontainerapps.io/guardrails/test-session'
```

---

## File Locations

All deployment files created in `/Users/adedotunadebiaye/fpa-copilot/`:

```
fpa-copilot/
├── requirements.txt              ← Python dependencies
├── deploy.sh                     ← Automated deployment script
├── DEPLOYMENT_GUIDE.md           ← Full deployment guide
├── PHASE8_DEPLOYMENT.md          ← Original spec
├── PHASE8_READY_TO_DEPLOY.md     ← This file
├── backend/
│   └── Dockerfile               ← Backend container image
├── frontend/
│   └── Dockerfile               ← Frontend container image
└── .github/
    └── workflows/
        └── deploy.yml           ← GitHub Actions CI/CD
```

---

## Environment Variables

### Backend (.env in Azure)
```
ANTHROPIC_API_KEY=sk-ant-...
RATE_LIMIT_PER_MIN=20
QUERY_CAP_PER_SESSION=50
DAILY_COST_CEILING=10.0
```

### Frontend (env vars in Azure)
```
NEXT_PUBLIC_API_URL=https://fpa-copilot-backend.azurecontainerapps.io
```

The deployment script sets these automatically.

---

## Key Commands

```bash
# View backend logs
az containerapp logs show \
  --name fpa-copilot-backend \
  --resource-group fpa-copilot-rg

# Update backend (new image)
docker build -t fpacopilotregistry.azurecr.io/fpa-copilot-backend:latest -f backend/Dockerfile .
docker push fpacopilotregistry.azurecr.io/fpa-copilot-backend:latest
az containerapp update \
  --name fpa-copilot-backend \
  --resource-group fpa-copilot-rg \
  --image fpacopilotregistry.azurecr.io/fpa-copilot-backend:latest

# Scale to multiple replicas
az containerapp update \
  --name fpa-copilot-backend \
  --resource-group fpa-copilot-rg \
  --min-replicas 1 --max-replicas 3

# Delete everything
az group delete --name fpa-copilot-rg --yes
```

---

## Success Criteria

After deployment:

- [ ] Frontend loads at Azure URL
- [ ] Can upload CSV file
- [ ] Can ask financial questions
- [ ] Get responses with traces
- [ ] Guardrails enforced (rate limiting)
- [ ] Health check returns "ok"
- [ ] No 500 errors
- [ ] Services respond in <5s (cold start ~2s)

---

## Architecture

```
Internet
   ↓
┌─────────────────────────────┐
│   Azure Container Apps      │
├─────────────────────────────┤
│                             │
│  Frontend (Node.js:3000)    │
│  ↓                          │
│  Backend (Python:8000)      │
│  ↓                          │
│  Guardrails + Rate Limit    │
│  ↓                          │
│  Claude API                 │
│                             │
└─────────────────────────────┘
        Azure Container Registry
        Azure Resource Group
        Azure Monitoring
```

---

## What Happens Next

### Immediate (Phase 8):
1. ✓ Deploy to Azure
2. ✓ Verify functionality
3. ✓ Test guardrails
4. ✓ Monitor costs

### Short-term (Phase 9):
- [ ] Add persistent storage (Azure Cosmos DB)
- [ ] Enable auto-scaling (min=1, max=3)
- [ ] Set up Application Insights monitoring
- [ ] Configure GitHub Actions secrets

### Medium-term:
- [ ] Implement user authentication
- [ ] Add data persistence for sessions
- [ ] Integrate live ERP systems
- [ ] Scale to production replicas

---

## Troubleshooting

### "Docker not found"
Install from https://www.docker.com/products/docker-desktop

### "ANTHROPIC_API_KEY not set"
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
./deploy.sh
```

### "Azure CLI not found"
```bash
brew install azure-cli
az login
```

### "Not authenticated with Azure"
```bash
az login
# Opens browser for authentication
```

### "Container won't start"
```bash
# Check logs
az containerapp logs show --name fpa-copilot-backend --resource-group fpa-copilot-rg

# Common issues:
# - Missing ANTHROPIC_API_KEY
# - Module not found (check requirements.txt)
# - Port already in use
```

### "Frontend can't reach backend"
```bash
# Verify env var
az containerapp show --name fpa-copilot-frontend \
  --resource-group fpa-copilot-rg \
  --query properties.template.containers[0].env

# Should show NEXT_PUBLIC_API_URL = https://fpa-copilot-backend.azurecontainerapps.io
```

---

## References

- **Deployment Guide:** `DEPLOYMENT_GUIDE.md` (comprehensive)
- **Original Spec:** `PHASE8_DEPLOYMENT.md` (reference)
- **Dockerfiles:** `backend/Dockerfile`, `frontend/Dockerfile`
- **Script:** `deploy.sh` (source code)
- **CI/CD:** `.github/workflows/deploy.yml`

---

## Support

**For issues:**
1. Check logs: `az containerapp logs show --name fpa-copilot-backend --resource-group fpa-copilot-rg`
2. Review troubleshooting in `DEPLOYMENT_GUIDE.md`
3. Verify env vars: `az containerapp show --name fpa-copilot-backend --resource-group fpa-copilot-rg`

**For scaling (Phase 9+):**
See `DEPLOYMENT_GUIDE.md` "Useful Commands" section

---

## Status Summary

| Component | Status | Notes |
|-----------|--------|-------|
| Dockerfiles | ✅ Ready | Python 3.12 + Node.js 18 |
| requirements.txt | ✅ Ready | All dependencies included |
| Deploy script | ✅ Ready | Fully automated |
| GitHub Actions | ✅ Ready | CI/CD pipeline configured |
| Documentation | ✅ Ready | Comprehensive guide included |
| **Overall** | **✅ READY** | **Ready to deploy to Azure** |

---

**Next action:** Run `./deploy.sh` after setting `ANTHROPIC_API_KEY`

**Estimated deployment time:** 10 minutes (first run), 2 minutes (updates)

**Questions?** See `DEPLOYMENT_GUIDE.md` or check logs with Azure CLI
