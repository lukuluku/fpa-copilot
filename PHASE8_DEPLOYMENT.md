# Phase 8: Deploy to Azure Container Apps

**Objective:** Ship Phase 7 code (locally tested, production-ready) to Azure.

**Status:** Ready to begin

---

## What You're Deploying

**Git:** `main` branch, latest commit `2d90527`

Two services:

### Backend
- **Code:** `backend/` + `src/` + `mcp-server/`
- **Entry point:** `backend/api.py`
- **Runtime:** Python 3.12 + FastAPI
- **Port:** 8000
- **Environment:** `.env` with `ANTHROPIC_API_KEY`

### Frontend
- **Code:** `frontend/`
- **Build:** `npm run build`
- **Runtime:** Node.js 18+
- **Port:** 3000
- **Environment:** `.env.local` with `NEXT_PUBLIC_API_URL`

---

## Deployment Checklist

### 1. Prerequisites
- [ ] Azure account with active subscription
- [ ] Azure CLI installed locally (`az --version`)
- [ ] Docker installed (`docker --version`)
- [ ] GitHub repo access

### 2. Create Azure Resources
```bash
# Resource group
az group create --name fpa-copilot-rg --location eastus

# Container Registry
az acr create --resource-group fpa-copilot-rg \
  --name fpacopilotregistry --sku Basic

# Get registry login credentials
az acr credential show --resource-group fpa-copilot-rg \
  --name fpacopilotregistry
```

### 3. Build Docker Images

**Backend Dockerfile** (create `backend/Dockerfile`):
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
ENV PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "backend.api:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Frontend Dockerfile** (create `frontend/Dockerfile`):
```dockerfile
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:18-alpine
WORKDIR /app
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package*.json ./
ENV NEXT_PUBLIC_API_URL=https://fpa-copilot-backend.azurecontainerapps.io
EXPOSE 3000
CMD ["npm", "start"]
```

**Build & push:**
```bash
# Login to registry
az acr login --name fpacopilotregistry

# Build and push backend
docker build -t fpa-copilot-backend:latest backend/
docker tag fpa-copilot-backend:latest \
  fpacopilotregistry.azurecr.io/fpa-copilot-backend:latest
docker push fpacopilotregistry.azurecr.io/fpa-copilot-backend:latest

# Build and push frontend
docker build -t fpa-copilot-frontend:latest frontend/
docker tag fpa-copilot-frontend:latest \
  fpacopilotregistry.azurecr.io/fpa-copilot-frontend:latest
docker push fpacopilotregistry.azurecr.io/fpa-copilot-frontend:latest
```

### 4. Deploy to Container Apps

```bash
# Enable Container Apps extension
az extension add --name containerapp --upgrade

# Deploy backend
az containerapp create \
  --name fpa-copilot-backend \
  --resource-group fpa-copilot-rg \
  --image fpacopilotregistry.azurecr.io/fpa-copilot-backend:latest \
  --target-port 8000 \
  --ingress external \
  --environment-variables ANTHROPIC_API_KEY=YOUR_KEY_HERE \
  --registry-server fpacopilotregistry.azurecr.io \
  --registry-username YOUR_USERNAME \
  --registry-password YOUR_PASSWORD

# Deploy frontend
az containerapp create \
  --name fpa-copilot-frontend \
  --resource-group fpa-copilot-rg \
  --image fpacopilotregistry.azurecr.io/fpa-copilot-frontend:latest \
  --target-port 3000 \
  --ingress external \
  --environment-variables NEXT_PUBLIC_API_URL=https://fpa-copilot-backend.azurecontainerapps.io \
  --registry-server fpacopilotregistry.azurecr.io \
  --registry-username YOUR_USERNAME \
  --registry-password YOUR_PASSWORD
```

### 5. Verify Deployment
```bash
# Get URLs
az containerapp show --name fpa-copilot-backend \
  --resource-group fpa-copilot-rg \
  --query properties.configuration.ingress.fqdn

az containerapp show --name fpa-copilot-frontend \
  --resource-group fpa-copilot-rg \
  --query properties.configuration.ingress.fqdn
```

### 6. Test End-to-End
- [ ] Open frontend URL in browser
- [ ] Upload a CSV
- [ ] Ask a question
- [ ] Verify response with traces
- [ ] Check guardrails status

### 7. Optional: CI/CD Pipeline
Create `.github/workflows/deploy.yml` to auto-deploy on `main` push.

---

## What to Know

### Services Architecture
```
User → Frontend (Node.js) → Backend (Python/FastAPI) → Claude API
                ↓
         Guardrails + Traces
```

### Environment Variables

**Backend (.env):**
- `ANTHROPIC_API_KEY` — Required, from Anthropic console
- `RATE_LIMIT_PER_MIN` — Default 20
- `QUERY_CAP_PER_SESSION` — Default 50
- `DAILY_COST_CEILING` — Default 10.0

**Frontend (.env.local):**
- `NEXT_PUBLIC_API_URL` — Backend FQDN (Azure Container Apps provides this)

### Known Limits
- Single replica (minReplicas=0, maxReplicas=1) per ADR-01
- In-memory session storage (no horizontal scaling yet)
- Data loaded at startup (~2s cold boot)

### Testing Endpoints

**Backend:**
```
GET  /status              → Health check
POST /query               → Execute question
GET  /guardrails/{sid}    → Session status
```

**Frontend:**
```
/        → Upload page
/query   → Chat interface
```

---

## Troubleshooting

**Container won't start:**
- Check logs: `az containerapp logs show --name fpa-copilot-backend`
- Verify env vars: `az containerapp show --name fpa-copilot-backend`

**Frontend can't reach backend:**
- Verify `NEXT_PUBLIC_API_URL` is correct
- Check CORS headers (should be open for internal Azure traffic)
- Test: `curl https://fpa-copilot-backend.azurecontainerapps.io/status`

**High latency:**
- Check cold start (first request is slow, ~2s for data loading)
- Monitor container CPU/memory in Azure portal

---

## Success Criteria

- [ ] Frontend loads at Azure URL
- [ ] Can upload CSV
- [ ] Can ask questions
- [ ] Responses include traces
- [ ] Guardrails enforced
- [ ] Rate limit blocks excess requests
- [ ] All endpoints respond
- [ ] No 500 errors

---

## Files to Create

1. `backend/Dockerfile`
2. `frontend/Dockerfile`
3. `.github/workflows/deploy.yml` (optional, for CI/CD)

## Files to Update

1. `frontend/.env.local` — Add `NEXT_PUBLIC_API_URL`
2. `backend/.env` — Add `ANTHROPIC_API_KEY` (Azure secrets management)

---

## Success = System Live

Once deployed:
- Backend: `https://fpa-copilot-backend.azurecontainerapps.io`
- Frontend: `https://fpa-copilot-frontend.azurecontainerapps.io`
- Users can upload data and ask financial questions
- All guardrails active
- Production-ready

---

## Next: Phase 9+

After Phase 8 deployment:
- Monitor real-world accuracy
- Implement user feedback
- Scale to multiple replicas (Phase 9)
- Add persistent storage
- Integrate with live ERP systems
