# Testing Guide

**HONEST ASSESSMENT:**
- ✅ Comprehensive testing for local development
- ✅ Tests cover tool functionality, caching, database schema
- ✅ **LLM function calling tests** (requires OPENAI_API_KEY, ~$0.03)
- ❌ NO browser automation (web UI not tested)
- ❌ NO load/performance testing
- ❌ NO concurrent request testing

## Quick Reference

```bash
# Unit tests (fast, isolated)
./run-tests.sh                    # All tools: 58 tests, ~30s

# Integration tests (medium, real services)
./test-gtd-stack.sh               # Stack validation: 27 checks, ~40s

# Tool integration tests (NOT true E2E)
./test-e2e-tools.sh               # Tool servers: 16 tests, ~30s

# Database/Config tests (Python, detailed)
./run-integration-tests.sh        # OpenWebUI internals: 26 tests, ~8s

# LLM function calling tests (requires API key, costs ~$0.03)
cd tests/integration && source .venv/bin/activate
export OPENAI_API_KEY="sk-proj-..."
pytest test_llm_function_calling.py -v -s   # 3 tests, ~10s
```

## Test Levels

### 1. Unit Tests (86%/75% coverage)
**Command:** `./run-tests.sh [todoist|caldav]`

**Tests:**
- Todoist: 31 tests (caching, filtering, health, retries, auth)
- CalDAV: 27 tests (timezone, PATCH, relative dates, caching, auth)

**Speed:** 30 seconds
**When:** Before every commit

### 2. Integration Tests (9 critical areas)
**Command:** `./test-gtd-stack.sh`

**Tests:**
1. Container health (10 services)
2. Tool endpoints (4 servers)
3. Todoist API (CRUD lifecycle)
4. CalDAV API (create, read, delete, verify)
5. Filesystem operations
6. Git operations
7. Config validation
8. OpenWebUI web interface
9. Model availability & pricing

**Speed:** 30-60 seconds
**When:** Before major changes, after stack updates

### 3. Tool Integration Tests (16 checks)
**Command:** `./test-e2e-tools.sh`

**⚠️ NOT true E2E:** Does not test LLM function calling or web UI

**What it tests:**
- OpenWebUI → Tool connectivity via Docker network (4)
- OpenAPI schema discovery (4)
- Tool registration in database (1)
- Tool functionality from OpenWebUI container (4)
- Enhanced health checks (2)
- Caching performance (1: 18-43x speedup!)

**What it does NOT test:**
- ❌ LLM actually calling tools
- ❌ OpenWebUI → LiteLLM → Cloud API flow
- ❌ Web UI interactions
- ❌ Concurrent requests

**Speed:** 20-40 seconds
**When:** Verifying tool connectivity and registration

### 4. Database/Config Tests (26 tests)
**Command:** `./run-integration-tests.sh`

**Tests:**
- Database schema (3)
- Configuration data (4)
- Tool registration (3)
- Model configuration (3)
- User accounts (3)
- Chat history (2)
- OpenWebUI API (2)
- Tool server endpoints (4)
- Prompt configuration (2)

**Speed:** 8 seconds
**When:** Debugging config issues, verifying database integrity

### 5. LLM Function Calling Tests (3 tests) ⭐ **NEW**
**Command:**
```bash
cd tests/integration && source .venv/bin/activate
export OPENAI_API_KEY="sk-proj-..."
pytest test_llm_function_calling.py -v -s
```

**Tests:**
- LLM creates Todoist task via function calling
- LLM creates CalDAV event via function calling
- LLM performs multi-step GTD workflow (task + event)

**What it tests:**
- ✅ Real LLM (gpt-4o-mini) decides to call tools
- ✅ Function calling schema parsing
- ✅ Tool server execution
- ✅ Result verification
- ✅ Cleanup (tasks/events deleted after test)

**What it does NOT test:**
- ❌ OpenWebUI GUI
- ❌ Multi-turn conversations
- ❌ Other LLM providers (Anthropic, Groq)

**Prerequisites:**
- `OPENAI_API_KEY` in environment (tests skip if not set)
- Tool servers running
- Optional: `TOOL_API_KEY` if authentication enabled

**Cost:** ~$0.03 (3 tests × $0.01 each)
**Speed:** ~10-15 seconds (API calls)
**When:** Verifying LLM → tool integration, before releases

## Test Output

**Unit tests:**
```
37 passed, 10 warnings in 16.22s
Coverage: todoist-tool 82%, caldav-tool 77%
```

**Integration tests:**
```
Passed: 27
Failed: 0
✅ All integration tests passed!
```

**E2E tests:**
```
Passed: 16
Failed: 0
Caching: 18-43x speedup (3939ms → 213ms)
✅ All E2E tests passed!
```

**Database tests:**
```
26 passed in 8.45s
✅ Database schema validated
✅ 5 tool servers registered
✅ Models, users, prompts verified
```

## Run All Tests

```bash
#!/bin/bash
echo "Running full test suite..."
./run-tests.sh && \
./test-gtd-stack.sh && \
./test-e2e-tools.sh && \
./run-integration-tests.sh
echo "✅ All tests passed!"
```

Total time: ~70 seconds

## What's Actually Tested vs Not Tested

### ✅ Tested (Good Coverage)
- Tool server code (unit tests with mocking)
- Container health and connectivity
- API endpoints and responses
- Database schema and configuration
- Tool registration in OpenWebUI
- Caching performance (measured 18-43x speedup)
- Error handling and retries
- Input validation

### ❌ NOT Tested (Gaps)
- **LLM function calling**: No tests that actually have an LLM call tools
- **Web UI**: No browser automation (Playwright/Cypress)
- **Load testing**: No performance/stress tests
- **Concurrent requests**: No thread-safety testing
- **Security**: No penetration testing
- **Real workflows**: No GTD workflow automation tests
- **Distributed caching**: Redis implementation doesn't exist
- **Production scenarios**: No failover, circuit breaker tests

### ⚠️ Partially Tested
- Caching: Works in tests, but cache lost on restart not tested
- Error scenarios: Some errors tested, but not exhaustive
- Tool integration: Connectivity tested, but not LLM invocation

## Recommendations

**For production deployment, you need:**
1. LLM function calling tests with real API keys
2. Browser automation tests (Playwright)
3. Load testing (k6, Locust)
4. Security audit
5. Monitoring integration
6. Backup/restore testing

**Current testing is sufficient for:**
- Local development
- Single-user usage
- Tool development iteration
- Regression detection
