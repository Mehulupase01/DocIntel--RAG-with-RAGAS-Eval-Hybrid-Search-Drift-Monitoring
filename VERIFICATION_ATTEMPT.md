# Live Verification Attempt — 2026-04-16

## OpenRouter Key Testing

**New Key Provided:** `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`

**Status:** ⚠️ Key also returns `429 Too Many Requests` immediately

**Findings:**
- The new key was tested against `minimax/minimax-m2.5:free` endpoint
- OpenRouter responded with HTTP 429 within milliseconds
- Possible causes:
  1. The account associated with this key has exhausted its quota
  2. The account has not been provisioned with available credits/tokens
  3. The account may require additional configuration on OpenRouter's side
  4. Rate limiting on the account itself (vs. per-request limits)

**Action Items:**
- [ ] Verify the OpenRouter account has available credits
- [ ] Check OpenRouter dashboard for account status
- [ ] Confirm the key is correctly associated with an active subscription
- [ ] Once credits are available, re-run the eval verification

**Updated .env:**
The new key has been stored in `.env` for future use once OpenRouter budget is available:
```
OPENROUTER_API_KEY=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
```

---

## LangSmith Tracing Setup

### Configuration

LangSmith tracing is **correctly implemented** and **disabled by default** (safe for ops).

**Integration Points:**

1. **Initialization** (`apps/api/src/docintel/services/monitoring/langsmith_setup.py`):
   ```python
   - Sets LANGSMITH_API_KEY (if provided)
   - Sets LANGCHAIN_TRACING_V2 = "true"
   - Sets LANGCHAIN_PROJECT to configured project name
   ```

2. **Activation** (`apps/api/src/docintel/main.py` line 28-31):
   ```python
   langsmith_enabled = configure_langsmith()
   logger.info("docintel.langsmith", enabled=langsmith_enabled)
   ```

3. **Environment Variables** (`.env.example`):
   ```bash
   LANGSMITH_API_KEY=                # Leave empty to disable
   LANGSMITH_PROJECT=docintel-dev    # Project name when enabled
   LANGSMITH_TRACING=false           # Toggle activation
   ```

### How to Enable LangSmith Tracing

**To send traces to LangSmith:**

1. Get your LangSmith API key from https://smith.langchain.com/settings/api-keys
2. Update `.env`:
   ```bash
   LANGSMITH_API_KEY=ls_pub_xxx...your_actual_key_here
   LANGSMITH_TRACING=true
   LANGSMITH_PROJECT=docintel-dev    # or your project name
   ```
3. Restart the API:
   ```bash
   docker compose restart api
   # or
   uv run uvicorn docintel.main:app --reload --app-dir src
   ```
4. Check startup logs for:
   ```
   INFO:docintel.langsmith: enabled=True
   ```

### What Gets Traced

When enabled, LangSmith will trace:

1. **RAGAS Eval Runs** — via `langchain-openai` ChatOpenAI wrapper for the judge model
   - Every metric computation (faithfulness, context_precision, context_recall, answer_relevancy)
   - LLM calls to the judge
   - Retrieval chains

2. **Generation Calls** — via direct OpenRouterClient (currently not integrated with LangChain)
   - Generation endpoint calls are NOT currently traced to LangSmith
   - (This would require wrapping the OpenRouterClient in a LangChain LLMBase, which can be a future enhancement)

3. **Search/Retrieval** — not directly traced
   - (Retrieval steps are logged to metrics/structlog but not sent to LangSmith)

### Previous Verification

From **CLAUDE.md** (Phase 6 verification):
- ✅ Local uvicorn startup with `LANGSMITH_TRACING=true` + `LANGSMITH_API_KEY` showed:
  ```
  INFO:docintel.langsmith: enabled=True
  ```
- ✅ EU LangSmith project `docintel-dev` contained recent runs from the live judge smoke
- ✅ Traces included `ChatOpenAI` error traces and pending RAGAS chains

### Current State

- **Tracing:** Disabled by default (✅ safe)
- **Integration:** Correct and functional
- **Ready to enable:** Yes — provide valid LangSmith API key and set `LANGSMITH_TRACING=true`

---

## Phase 9 Status After Verification Attempt

| Component | Status | Notes |
|-----------|--------|-------|
| **Code Quality** | ✅ Clean | All tests passing, lint clean, no changes needed |
| **Documentation** | ✅ Fixed | Removed unauthorized backup model references |
| **Configuration** | ✅ Ready | Updated .env with new OpenRouter key (awaiting account credits) |
| **LangSmith** | ✅ Ready | Correctly integrated, disabled by default, can be enabled with API key |
| **Generation** | 🔴 Blocked | OpenRouter account needs credits (429 errors) |
| **Evaluation** | 🔴 Blocked | Same OpenRouter key issue |
| **Observability** | ✅ Ready | Metrics, structlog, and LangSmith all configured |

---

## Next Steps

### Immediate (OpenRouter Budget)
1. Verify OpenRouter account has available credits
2. Once available, re-run:
   ```bash
   uv run --directory apps/api python -m docintel.tools.run_eval --suite-version v1
   ```
3. Confirm: eval run completes with passing scores

### If Full Tracing Desired (LangSmith)
1. Obtain LangSmith API key from https://smith.langchain.com
2. Update `.env`:
   ```bash
   LANGSMITH_API_KEY=ls_pub_...
   LANGSMITH_TRACING=true
   ```
3. Restart API and run eval
4. Check traces at https://smith.langchain.com/o/[org]/projects/[project]

### Final Verification
Once OpenRouter credits are available:
```bash
# Full integration test
uv run --directory apps/api python -m docintel.tools.run_eval --suite-version v1

# Should show:
# ✅ 25 eval cases executed
# ✅ Mean scores computed (faithfulness, context_precision, etc.)
# ✅ Results persisted to Postgres
# ✅ All four metrics above thresholds
```

Then Phase 9 is **complete** and system is **production-ready**.
