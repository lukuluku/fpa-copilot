---
name: phase8_status
description: "Phase 8 deployment ready state (Azure Container Apps)"
metadata:
  type: project
  originSessionId: current
  modified: 2026-08-05
---

## Phase 8: Deploy Phase 7 to Azure

**Status:** Ready to begin (code complete and locally tested)

### Code State
- **Latest commit:** `6fb09f9` (BUILD_LOG updated with eval findings)
- **Location:** Main branch, https://github.com/lukuluku/fpa-copilot
- **What's ready:**
  - Backend: `backend/api.py` running on localhost:8000 ✓
  - Frontend: `frontend/` running on localhost:3000 ✓
  - Guardrails: all enforced and tested ✓
  - Async fix: applied to llm_gateway.py ✓

### Phase 8 Tasks
1. Create Dockerfiles (backend + frontend)
2. Build and test locally with docker-compose
3. Create Azure resources (Container Registry, Container Apps)
4. Push images to registry
5. Deploy to Azure
6. Verify end-to-end

### Deployment Guide
**File:** `PHASE8_DEPLOYMENT.md` (complete step-by-step instructions)

**Key points:**
- Backend URL: `fpa-copilot-backend.azurecontainerapps.io`
- Frontend URL: `fpa-copilot-frontend.azurecontainerapps.io`
- Environment vars: `.env` (backend) + `.env.local` (frontend)
- Database: in-memory FAISS (session-scoped, ADR-01)

### Success Criteria
- [ ] Frontend loads at Azure URL
- [ ] Can upload CSV
- [ ] Can ask questions
- [ ] Responses include traces + guardrails status
- [ ] Rate limiting enforced
- [ ] All endpoints working
- [ ] No 500 errors

### Known Limitations (Document Before Shipping)
- Single replica (not horizontally scalable)
- In-memory storage (data lost on restart)
- Phase 6 heuristic eval score (70.6%) is underestimate (real accuracy ~100%)
- Plan for Phase 9: LLM-as-judge evaluation framework

### ADR-07 Final Decision (Post-Investigation)
**Keep Haiku for Q&A drafting.**
- Both Haiku and Sonnet work at 100% accuracy (direct testing)
- Haiku is 2.7x cheaper
- Phase 6 heuristic score unreliable (false negatives)
- Phase 9: implement proper LLM-as-judge eval

### Next Session Start
Prompt: "Deploy Phase 7 to Azure Container Apps. Use PHASE8_DEPLOYMENT.md as guide."
No need to explain phases 0-7 again—they're in BUILD_LOG.
