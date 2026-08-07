# Phase 8: Deployment Checklist

Use this checklist to track your Azure deployment progress.

---

## Pre-Deployment ✓

### Prerequisites
- [ ] Azure account created (with active subscription)
- [ ] Azure CLI installed (`brew install azure-cli`)
- [ ] Docker installed (https://www.docker.com/products/docker-desktop)
- [ ] Git configured locally
- [ ] Anthropic API key obtained (https://console.anthropic.com/account/keys)

### Setup
- [ ] Azure CLI authenticated (`az login`)
- [ ] Anthropic API key exported: `export ANTHROPIC_API_KEY="sk-ant-..."`
- [ ] Current directory: `/Users/adedotunadebiaye/fpa-copilot`
- [ ] Git branch: `main`
- [ ] Working directory clean: `git status` shows nothing to commit

---

## Deployment Files ✓

### Created Files
- [x] `requirements.txt` — Python 3.12 dependencies
- [x] `backend/Dockerfile` — Backend container image
- [x] `frontend/Dockerfile` — Frontend container image
- [x] `deploy.sh` — Automated deployment script (executable)
- [x] `.github/workflows/deploy.yml` — GitHub Actions CI/CD
- [x] `DEPLOYMENT_GUIDE.md` — Comprehensive guide
- [x] `PHASE8_READY_TO_DEPLOY.md` — Status document
- [x] `DEPLOYMENT_CHECKLIST.md` — This file

### File Verification
```bash
ls -la backend/Dockerfile frontend/Dockerfile deploy.sh requirements.txt .github/workflows/deploy.yml
```

---

## Deployment Steps

### Phase 8-1: Automated Deployment

- [ ] **Step 1:** Verify environment variable
  ```bash
  echo $ANTHROPIC_API_KEY
  # Should print your API key, not empty
  ```

- [ ] **Step 2:** Navigate to project directory
  ```bash
  cd /Users/adedotunadebiaye/fpa-copilot
  ```

- [ ] **Step 3:** Run deployment script
  ```bash
  ./deploy.sh
  # Script will guide you through authentication
  ```

- [ ] **Step 4:** Watch script progress
  - [ ] Resource group created
  - [ ] Container Registry created
  - [ ] Backend image built
  - [ ] Backend image pushed
  - [ ] Frontend image built
  - [ ] Frontend image pushed
  - [ ] Backend Container App deployed
  - [ ] Frontend Container App deployed
  - [ ] Health checks passed

- [ ] **Step 5:** Save the output URLs
  ```
  Frontend URL: https://fpa-copilot-frontend.azurecontainerapps.io
  Backend URL: https://fpa-copilot-backend.azurecontainerapps.io
  ```

**Expected time:** 10-15 minutes (first deployment)

---

## Post-Deployment Verification

### Immediate Checks

- [ ] **Backend Health Check**
  ```bash
  curl https://fpa-copilot-backend.azurecontainerapps.io/status
  # Should return: {"status": "ok", "version": "0.7", ...}
  ```

- [ ] **Frontend Accessibility**
  ```bash
  curl -I https://fpa-copilot-frontend.azurecontainerapps.io
  # Should return 200 or 308 (redirect to proper page)
  ```

- [ ] **View Container Logs**
  ```bash
  az containerapp logs show --name fpa-copilot-backend --resource-group fpa-copilot-rg | head -20
  ```

### Browser Testing

- [ ] **Open Frontend URL** in web browser
  - [ ] Page loads without errors
  - [ ] UI is responsive
  - [ ] No console errors (check browser DevTools)

- [ ] **Upload CSV File**
  - [ ] Navigate to upload section
  - [ ] Upload `data/sample_budget_data.csv`
  - [ ] File loads successfully
  - [ ] Status shows "Ready"

- [ ] **Ask a Question**
  - [ ] Enter: "What was the total revenue in Q1?"
  - [ ] Click submit
  - [ ] Response appears within 5 seconds
  - [ ] Response includes answer text
  - [ ] Traces are visible

- [ ] **Check Guardrails Status**
  - [ ] Look for rate limit information
  - [ ] Should show: "Requests: X/20 per minute"
  - [ ] Should show: "Queries: X/50 per session"

### Advanced Testing

- [ ] **Multiple Requests**
  ```bash
  for i in {1..5}; do
    curl -X POST https://fpa-copilot-backend.azurecontainerapps.io/query \
      -H "Content-Type: application/json" \
      -d '{"query": "What is revenue?"}' &
  done
  wait
  ```

- [ ] **Rate Limiting** (should return 429 after 20 requests/min)
  ```bash
  for i in {1..25}; do
    curl -X POST https://fpa-copilot-backend.azurecontainerapps.io/query \
      -H "Content-Type: application/json" \
      -d '{"query": "Test"}' &
  done
  wait
  # After 20, expect some to return 429 errors
  ```

- [ ] **Session Tracking**
  ```bash
  curl -X GET 'https://fpa-copilot-backend.azurecontainerapps.io/guardrails/my-session-id'
  # Should return guardrails status for that session
  ```

---

## Success Criteria

Check all that apply:

- [ ] Deployment script ran without errors
- [ ] Both services show in Azure portal
- [ ] Backend responds to `/status` with "ok"
- [ ] Frontend loads in browser
- [ ] Can upload CSV without errors
- [ ] Can ask questions and get responses
- [ ] Responses include trace information
- [ ] Rate limiting works (429 after limit)
- [ ] No 500 errors in logs
- [ ] Health checks pass

**Status:** All items checked = ✅ **Deployment Successful**

---

## Troubleshooting

### Issue: "ANTHROPIC_API_KEY not set"
**Solution:**
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
./deploy.sh
```

### Issue: "Docker command not found"
**Solution:**
1. Install Docker Desktop: https://www.docker.com/products/docker-desktop
2. Start Docker app
3. Verify: `docker --version`
4. Run: `./deploy.sh`

### Issue: "Not authenticated with Azure"
**Solution:**
```bash
az login
# Opens browser window for authentication
```

### Issue: "Container won't start"
**Solution:**
```bash
# Check logs
az containerapp logs show --name fpa-copilot-backend --resource-group fpa-copilot-rg

# Check configuration
az containerapp show --name fpa-copilot-backend --resource-group fpa-copilot-rg

# Look for errors about:
# - Missing ANTHROPIC_API_KEY
# - Module import errors (check requirements.txt)
# - Port conflicts
```

### Issue: "Frontend can't reach backend"
**Solution:**
```bash
# Check backend URL is set in frontend env vars
az containerapp show --name fpa-copilot-frontend \
  --resource-group fpa-copilot-rg \
  --query properties.template.containers[0].env

# If NEXT_PUBLIC_API_URL is wrong, update:
BACKEND_URL=$(az containerapp show --name fpa-copilot-backend \
  --resource-group fpa-copilot-rg \
  --query properties.configuration.ingress.fqdn -o tsv)

az containerapp update --name fpa-copilot-frontend \
  --resource-group fpa-copilot-rg \
  --set-env-vars NEXT_PUBLIC_API_URL="https://$BACKEND_URL"
```

### Issue: "High latency on first request"
**Note:** This is normal! Cold start includes:
- Python environment initialization: ~1s
- Data loading from CSV: ~1s
- Model initialization: ~1s
- Total: ~2-3 seconds for first request

Subsequent requests are fast (<500ms).

### Issue: "403 Forbidden from backend"
**Likely cause:** Rate limit exceeded
- Check logs: `az containerapp logs show --name fpa-copilot-backend --resource-group fpa-copilot-rg`
- Wait a minute and retry (rate limits reset per minute)

---

## What's Running

After successful deployment:

### Azure Resources
```
Resource Group: fpa-copilot-rg
├── Container Registry: fpacopilotregistry
│   ├── fpa-copilot-backend:latest
│   └── fpa-copilot-frontend:latest
└── Container Apps Environment: fpa-copilot-env
    ├── fpa-copilot-backend (Python:8000)
    │   └── Replicas: 1
    │   └── Status: Running
    └── fpa-copilot-frontend (Node.js:3000)
        └── Replicas: 1
        └── Status: Running
```

### Services
```
Frontend: https://fpa-copilot-frontend.azurecontainerapps.io
  ↓ (API calls to)
Backend: https://fpa-copilot-backend.azurecontainerapps.io
  ↓ (Calls)
Claude API (via Anthropic SDK)
```

---

## Next Steps (Phase 9+)

After successful deployment:

### Immediate (This Week)
- [ ] Monitor costs in Azure portal
- [ ] Test with real data
- [ ] Gather user feedback
- [ ] Document any issues

### Short-term (Next 2 weeks)
- [ ] Set up CI/CD: Configure GitHub Actions secrets
  - [ ] `AZURE_CLIENT_ID`
  - [ ] `AZURE_TENANT_ID`
  - [ ] `AZURE_SUBSCRIPTION_ID`
- [ ] Enable auto-scaling (min=1, max=3 replicas)
- [ ] Set up Application Insights monitoring
- [ ] Configure daily cost alerts

### Medium-term (Next Month)
- [ ] Add persistent storage (Azure Cosmos DB)
- [ ] Implement user sessions
- [ ] Add authentication
- [ ] Integrate live data sources

---

## Useful Commands for Later

### View Logs
```bash
az containerapp logs show --name fpa-copilot-backend --resource-group fpa-copilot-rg
```

### Update Code (After Changes)
```bash
# Rebuild and push
docker build -t fpacopilotregistry.azurecr.io/fpa-copilot-backend:latest -f backend/Dockerfile .
docker push fpacopilotregistry.azurecr.io/fpa-copilot-backend:latest

# Deploy update
az containerapp update --name fpa-copilot-backend \
  --resource-group fpa-copilot-rg \
  --image fpacopilotregistry.azurecr.io/fpa-copilot-backend:latest
```

### Scale Replicas
```bash
az containerapp update --name fpa-copilot-backend \
  --resource-group fpa-copilot-rg \
  --min-replicas 1 --max-replicas 3
```

### Delete Everything
```bash
az group delete --name fpa-copilot-rg --yes
```

---

## Sign-off

**Deployer:** ___________________  
**Date:** ___________________  
**Status:** ☐ Successful ☐ Failed  
**Notes:** _______________________________  

---

**For questions:** See `DEPLOYMENT_GUIDE.md` or check logs with Azure CLI
