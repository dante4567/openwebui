# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Quick Reference

**Most Common Commands:**
```bash
./test-gtd-stack.sh              # Run full integration test (9 critical areas)
./run-tests.sh                   # Run unit tests (todoist + caldav)
docker-compose up -d             # Start all services (10 containers)
docker-compose logs -f openwebui # View OpenWebUI logs
docker-compose ps                # Check service health
```

**Most Common Tasks:**
- **Edit tool server code**: Edit `todoist-tool/main.py` → `./run-tests.sh todoist` → `docker-compose build todoist-tool` → `docker-compose up -d todoist-tool`
- **Test full stack**: `./test-gtd-stack.sh` (checks containers, tools, API connectivity, config, models)
- **Update model pricing**: Edit `CLAUDE.md` budget section + `test-gtd-stack.sh` EXPECTED_MODELS array
- **Debug tool registration**: Check `test-gtd-stack.sh` Test 8 (queries OpenWebUI config table for Global Tool Servers)
- **Fix LiteLLM routing**: See Troubleshooting section #7 (models bypass LiteLLM, no caching)

**Key Files:**
- `docker-compose.yml`: Service definitions (10 containers, line references in docs)
- `test-gtd-stack.sh`: Integration tests (9 critical areas, exit code 0 = all pass)
- `run-tests.sh`: Unit tests (todoist + caldav, 87%/92% coverage)
- `CLAUDE.md`: This file (architecture, commands, troubleshooting)
- `MODEL-UPDATE-STRATEGY.md`: Model currency tracking (monthly review recommended)

## Project Overview

OpenWebUI configured for **GTD (Getting Things Done) workflows**: multi-cloud LLM access, TTS/STT, file management, version control, task management, and calendar integration.

**Architecture Type**: Microservices-based Docker Compose stack with tool servers extending LLM capabilities via OpenAPI.

**Technology Stack**:
- **Frontend**: OpenWebUI (Python/FastAPI + Svelte)
- **Vector DB**: ChromaDB (Python)
- **LLM Gateway**: LiteLLM (Python + Redis caching)
- **Tool Servers**: FastAPI microservices (Python 3.10)
- **Orchestration**: Docker Compose
- **Testing**: pytest + pytest-cov + httpx for mocking
- **CI/CD**: GitHub Actions (unit tests, integration tests, dependabot)

**HONEST ASSESSMENT (Updated 2025-10-14):**
- This is **NOT a minimal GTD setup** despite previous claims
- Currently running: OpenWebUI + ChromaDB + LiteLLM + Redis + SearXNG + Tika + 4 GTD tools (filesystem, git, todoist, caldav)
- Total: 10 containers (not the "minimal 5" originally documented)
- **LiteLLM is the gateway**: All API calls go through LiteLLM proxy at `http://litellm:4000`
- **Pricing updated Oct 2025**: All pricing verified accurate as of October 14, 2025 via web search
- **Models updated Oct 2025**: Using current models - GPT-4.1-mini, Claude Sonnet 4.5, Gemini 2.5, Llama 3.3

## Architecture

```
OpenWebUI (8080) → Multi-cloud LLM GUI
├── LiteLLM Proxy (4000): Unified gateway with caching, fallbacks, cost tracking
│   ├── OpenAI: gpt-4.1-mini, gpt-4o-mini, gpt-4o
│   ├── Anthropic: claude-sonnet-4-5, claude-3-5-sonnet, claude-3-5-haiku
│   ├── Groq: llama-3.3-70b, llama-3.1-8b (fast & cheap)
│   └── Google: gemini-2.5-pro, gemini-2.5-flash, gemini-2.0-flash
├── Redis (6379): Response caching for LiteLLM
├── ChromaDB (3000): Vector database for RAG
├── SearXNG (8081): Web search (better than DuckDuckGo)
├── Tika (9998): Document parsing (100+ formats, OCR)
├── TTS/STT: OpenAI Whisper + TTS
└── GTD Tool Servers:
    ├── Filesystem (8006): Read/write files in ~/ai-workspace
    ├── Git (8003): Version control in ~/ai-workspace
    ├── Todoist (8007): Task management via Todoist API
    └── CalDAV (8008): Calendar + contacts via CalDAV/CardDAV
```

**Key relationships:**
- OpenWebUI → LiteLLM → All cloud APIs (OpenAI, Anthropic, Groq, Google)
- LiteLLM → Redis: Response caching to reduce API costs
- OpenWebUI → ChromaDB: Vector storage for RAG documents
- OpenWebUI → SearXNG: Web search queries
- OpenWebUI → Tika: Document parsing for RAG
- OpenWebUI → GTD tools: Function calling via OpenAPI
- Filesystem + Git tools: Share `~/ai-workspace` git repo
- Todoist tool: CRUD tasks via Todoist REST API
- CalDAV tool: Calendar events + contacts via CalDAV/CardDAV protocol

**Network addresses (CRITICAL):**
- Internal (for OpenWebUI config): `http://litellm:4000`, `http://filesystem-tool:8000`, `http://todoist-tool:8000`, etc.
- External (for testing): `http://localhost:4000` (LiteLLM), `http://localhost:8006` (filesystem), `http://localhost:8007` (todoist), etc.
- **Never use localhost URLs in OpenWebUI GUI** - containers can't reach host network

## Development Approach

**Architecture Pattern**: Microservices communicating via Docker network
- Each tool server is an independent FastAPI application
- OpenWebUI discovers tools via OpenAPI spec endpoints
- All services defined in `docker-compose.yml` with health checks
- Configuration via environment variables (`.env` file, never committed)

**Code Conventions**:
- Python tool servers: FastAPI + Pydantic for validation
- Modern async patterns where beneficial
- Structured logging with JSON output
- Retry logic with exponential backoff for API calls (3 retries, 1s/2s/4s)
- Non-root containers (UID 10001) for security

**Development Workflow**:
1. **Local changes**: Edit tool server code in `todoist-tool/main.py` or `caldav-tool/main.py`
2. **Test locally**: `./run-tests.sh todoist` (runs pytest with mocking)
3. **Rebuild container**: `docker-compose build todoist-tool`
4. **Restart service**: `docker-compose up -d todoist-tool`
5. **Verify**: `curl http://localhost:8007/` (should return {"status":"healthy"})
6. **Integration test**: `./test-gtd-stack.sh` (full stack validation)

**Adding a new tool server**:
1. Create `new-tool/` directory with `main.py`, `Dockerfile`, `requirements.txt`
2. Add FastAPI app with health check endpoint (`GET /`)
3. Define endpoints with Pydantic models for request/response validation
4. Add `openapi.json` generation (FastAPI does this automatically at `/openapi.json`)
5. Add service to `docker-compose.yml` (copy pattern from todoist-tool)
6. Add to `test-gtd-stack.sh` for integration testing
7. Register in OpenWebUI: Admin Settings → Tools → Add Tool Server → `http://new-tool:8000`

## Common Commands

```bash
# Stack management
docker-compose up -d                    # Start all services (10 containers)
docker-compose down                     # Stop all services
docker-compose logs -f openwebui        # View logs
docker-compose logs -f todoist-tool     # View specific tool logs
docker-compose ps                       # Check service status
docker-compose restart <service>        # Restart specific service

# Quick container health check
docker-compose ps --format json | jq -r '.[] | "\(.Service): \(.State) (\(.Health // "no healthcheck"))"'

# Configuration backup/restore
# OpenWebUI settings can be exported/imported via the web UI:
# Settings → Admin → Database → Export/Import (JSON format)
# Includes: models, tools, prompts, documents, users, chats
# Useful for: backups, migration, version control

# Testing
./test-gtd-stack.sh                     # Run full integration test suite
                                        # Tests: containers, tools, APIs, config, models

# Tool server development
docker-compose build todoist-tool       # Rebuild after code changes
docker-compose up -d todoist-tool       # Restart with new image
curl http://localhost:8007/             # Test health endpoint

# Unit tests for GTD tool servers
./run-tests.sh                          # Run all tests (todoist + caldav)
./run-tests.sh todoist                  # Run only todoist-tool tests
./run-tests.sh caldav                   # Run only caldav-tool tests
# Test reports: todoist-tool/htmlcov/index.html, caldav-tool/htmlcov/index.html
# Coverage: todoist-tool: 87%, caldav-tool: 92%

# Workspace access (git repo for AI)
cd ~/ai-workspace                       # Direct access to workspace
git log                                 # View AI commits
ls -la ~/ai-workspace                   # View files

# Test GTD workflow
curl http://localhost:8007/tasks        # List Todoist tasks
curl http://localhost:8008/calendars    # List CalDAV calendars
curl http://localhost:8006/docs         # Filesystem tool OpenAPI docs
curl http://localhost:8003/docs         # Git tool OpenAPI docs
```

## Configuration

**Environment variables** (`.env` file, never committed):
- `WEBUI_SECRET_KEY`: Generate with `openssl rand -hex 32`
- API keys: `OPENAI_API_KEY`, `GROQ_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`
- GTD tools: `TODOIST_API_KEY`, `CALDAV_URL`, `CALDAV_USERNAME`, `CALDAV_PASSWORD`
- Optional: `CARDDAV_URL`, `CARDDAV_USERNAME`, `CARDDAV_PASSWORD` (defaults to CalDAV creds)
- See `.env.example` for full list

**Key settings in docker-compose.yml:**
- `ENABLE_SIGNUP=false`: Admin-only (set `true` temporarily for first user creation)
- `DEFAULT_MODELS=gpt-4o-mini`: Force cheap model as default (budget control)
- `TASK_MODEL=gpt-4o-mini`: Cloud model for background tasks
- `ENABLE_FUNCTION_CALLING=true`: Tool/agentic capabilities enabled
- `ENABLE_MEMORY=false`: Disabled (requires ChromaDB)
- All RAG settings: Commented out (not needed for GTD)

**RAG/Embedding Configuration** (OpenWebUI database):
- **Embedding Engine**: `openai` (configured in OpenWebUI)
- **Embedding Model**: `text-embedding-3-large` (updated 2025-10-16)
- **Use Case**: German + English documents (multilingual optimized)
- **Performance**: 80.5% RAG accuracy, 88.8% contextual understanding, 54.9% multilingual
- **Cost**: $0.13 per 1M tokens (~$0.07/month for typical usage)
- **Alternative**: `text-embedding-3-small` ($0.02 per 1M tokens, 75.8% RAG accuracy - only if embedding millions of docs)
- **Storage**: Configured in OpenWebUI database (`/app/backend/data/webui.db` → config table → rag.embedding_model)
- **Note**: This setting is stored in OpenWebUI's database, not in docker-compose.yml or .env

## GTD Tool Servers

**Tool Server Architecture**:
- **Pattern**: FastAPI app + Pydantic validation + OpenAPI schema
- **Base image**: `python:3.10.12-slim`
- **Security**: Non-root `appuser` (UID 10001)
- **Networking**: Expose port 8000 internally (mapped to 800X externally)
- **Health checks**: `/` or `/docs` endpoint
- **Discovery**: OpenWebUI reads `/openapi.json` to discover functions
- **Retry logic**: Exponential backoff for external API calls (Todoist, CalDAV)
- **Error handling**: Structured JSON responses with status codes

**Tool Server File Structure** (todoist-tool, caldav-tool):
```
tool-name/
├── main.py              # FastAPI app with endpoints
├── Dockerfile           # Multi-stage build (testing not included in prod)
├── requirements.txt     # Production dependencies
├── requirements-test.txt # Test dependencies (pytest, pytest-cov, httpx)
└── tests/
    └── test_main.py     # Unit tests with mocked API calls
```

**Filesystem & Git tools (from openapi-servers repo):**
- **CRITICAL**: Both mount `~/ai-workspace:/workspace` (docker-compose.yml lines 85, 109)
- **SECURITY RISK**: LLM has **write access** to this directory - can modify/delete files
- Sandboxed to `/workspace` only (cannot access other paths)
- **Workspace is a git repo** - initialized with README.md
- For read-only: Add `:ro` suffix: `~/ai-workspace:/workspace:ro`

**Todoist tool (custom):**
- **Location**: `todoist-tool/main.py`
- **Endpoints**: `/tasks` (list, create), `/tasks/{id}` (get, update, delete), `/tasks/{id}/close` (complete)
- **External API**: Todoist REST API v2 (https://api.todoist.com/rest/v2)
- **Requires**: `TODOIST_API_KEY` from .env
- **Retry logic**: 3 attempts with exponential backoff (1s, 2s, 4s) for network errors
- **Error handling**: Returns 404 for not found, 500 for API errors, 503 for network issues

**CalDAV/CardDAV tool (custom):**
- **Location**: `caldav-tool/main.py`
- **Endpoints**:
  - Calendar: `/calendars` (list), `/events` (list, create), `/events/{uid}` (delete)
  - Contacts: `/addressbooks` (list), `/contacts` (list, create)
- **External API**: CalDAV/CardDAV protocol (uses Python `caldav` library)
- **Requires**: `CALDAV_URL`, `CALDAV_USERNAME`, `CALDAV_PASSWORD`
- **Optional**: Separate CardDAV creds (defaults to CalDAV)
- **Retry logic**: Built into `caldav` library (3 retries by default)
- **Error handling**: Returns 404 for not found, 500 for CalDAV errors, detailed error messages

**Code patterns used in tool servers:**
```python
# 1. FastAPI endpoint with Pydantic validation
@app.post("/tasks")
async def create_task(request: CreateTaskRequest):
    # Pydantic auto-validates request body
    # Returns validation error if fields missing/wrong type
    pass

# 2. Retry logic with exponential backoff
for attempt in range(MAX_RETRIES):
    try:
        response = requests.get(url, timeout=10)
        return response.json()
    except requests.RequestException as e:
        if attempt < MAX_RETRIES - 1:
            time.sleep(2 ** attempt)  # 1s, 2s, 4s
        else:
            raise HTTPException(status_code=503, detail=str(e))

# 3. Error response format
raise HTTPException(
    status_code=404,
    detail={"error": "Task not found", "task_id": task_id}
)

# 4. Health check endpoint (required for OpenWebUI)
@app.get("/")
async def health_check():
    return {"status": "healthy", "service": "todoist-tool"}
```

**Testing patterns:**
```python
# 1. Mock external API calls with httpx_mock
@pytest.mark.asyncio
async def test_create_task(httpx_mock):
    httpx_mock.add_response(
        url="https://api.todoist.com/rest/v2/tasks",
        method="POST",
        json={"id": "123", "content": "Test task"}
    )
    # Now call your endpoint, it will use mocked response

# 2. Test error handling
@pytest.mark.asyncio
async def test_network_error(httpx_mock):
    httpx_mock.add_exception(httpx.ConnectError("Network error"))
    # Verify your code returns 503 with retry logic

# 3. Test validation
async def test_invalid_request():
    response = client.post("/tasks", json={"invalid": "field"})
    assert response.status_code == 422  # Pydantic validation error
```

## Testing

**Unit tests for custom GTD tools:**
- **Test coverage**: todoist-tool (87%), caldav-tool (92%)
- **Test count**: 32 tests total (17 todoist, 15 caldav)
- **Technologies**: pytest, pytest-cov, pytest-mock, httpx
- **Location**: `todoist-tool/tests/`, `caldav-tool/tests/`

**Running tests:**
```bash
./run-tests.sh              # Run all tests (both tools)
./run-tests.sh todoist      # Run only todoist-tool tests
./run-tests.sh caldav       # Run only caldav-tool tests

# Run specific test file
cd todoist-tool && source .venv-test/bin/activate && pytest tests/test_main.py::test_health_check -v

# Run with verbose output and no coverage
cd todoist-tool && source .venv-test/bin/activate && pytest tests/ -vv

# Check coverage for specific module
cd caldav-tool && source .venv-test/bin/activate && pytest tests/ --cov=main --cov-report=term-missing
```

**What is tested:**
- Health check endpoints
- All CRUD operations (list, create, get, update, delete)
- Error handling (network errors, timeouts, API errors)
- Retry logic with exponential backoff (mocked with delays)
- Request parameter validation (Pydantic models)
- Response format validation (JSON structure)
- Edge cases (empty results, invalid IDs, missing fields)

**Test reports:**
- HTML coverage reports: `{tool}/htmlcov/index.html` (open in browser)
- Terminal output shows: passed/failed tests, coverage percentage, missing lines
- Tests use httpx mock for HTTP calls (no real API requests)

**Writing new tests:**
1. Add test function to `tests/test_main.py` (prefix with `test_`)
2. Use `@pytest.mark.asyncio` for async endpoints
3. Mock external API calls with `httpx_mock.add_response()`
4. Assert response status codes and JSON structure
5. Test both success and error paths
6. Run `./run-tests.sh <tool>` to verify

**When to run tests:**
- Before committing changes to tool code
- After adding new features or endpoints
- After dependency updates
- As part of CI/CD pipeline (automated on push)
- When debugging issues (add print statements to tests)

## Budget Controls ($30/month target)

**Default model enforcement:**
- `DEFAULT_MODELS=gpt-4o-mini` in docker-compose.yml forces cheap model
- **All API calls go through LiteLLM** which has caching enabled (saves $$)

**Current model pricing (Oct 2025, per 1M tokens - VERIFIED Oct 14, 2025):**

| Model | Input | Output | Use Case | Notes |
|-------|-------|--------|----------|-------|
| **gpt-4.1-mini** | $0.40 | $1.60 | Good balance of cost/performance | 1M token context |
| **gpt-4o-mini** | $0.15 | $0.60 | **BEST BUDGET** - Default choice | Proven reliable |
| gpt-4o | $2.50 | $10.00 | Complex tasks only | High quality |
| **claude-sonnet-4-5** | $3.00 | $15.00 | Best for coding (Sept 2025) | Latest flagship |
| claude-3-5-sonnet | $3.00 | $15.00 | Previous flagship | Still excellent |
| claude-3-5-haiku | $1.00 | $5.00 | Fast, cheap Claude | Good for simple tasks |
| **llama-3.3-70b** | $0.59 | $0.79 | Groq - very fast, cheap | Best Groq option |
| llama-3.1-8b | $0.05 | $0.08 | Groq - fastest, cheapest | Simple tasks |
| **gemini-2.5-pro** | $1.25 | $10.00 | Reasoning model (needs 100-300 tokens) | ⚠️ Price increased Jun 2025 |
| **gemini-2.5-flash** | $0.30 | $2.50 | Reasoning model (needs 50-200 tokens) | ⚠️ Price increased Jun 2025 |
| gemini-2.0-flash | $0.10 | $0.40 | Standard model (normal token usage) | Good budget choice |

**Cost estimates (50k in, 10k out per session):**
- llama-3.1-8b (Groq): ~$0.003 (CHEAPEST)
- gpt-4o-mini: ~$0.014 (BEST BUDGET BALANCE)
- gemini-2.0-flash: ~$0.009 (good Google option)
- gpt-4.1-mini: ~$0.036 (1M context, pricier than 4o-mini)
- gemini-2.5-flash: ~$0.040 (reasoning model, expensive!)
- llama-3.3-70b (Groq): ~$0.037

**Budget planning:**
- $30/month with gpt-4o-mini = ~2100 sessions = 70/day
- $30/month with gpt-4.1-mini = ~830 sessions = 27/day
- $30/month with gemini-2.5-flash = ~750 sessions = 25/day

**LiteLLM caching benefits:**
- Redis caching enabled - repeated queries cost $0
- Fallback chains prevent expensive failures
- Cost tracking in logs (verbose logging enabled)

**Cost monitoring:**
- **LiteLLM logs:** `docker logs openwebui-litellm | grep -i cost`
  - Shows cost per request in real-time
  - Token usage breakdown (input/output)
  - Model-specific costs
- **LiteLLM API:** `curl http://localhost:4000/spend/logs -H "Authorization: Bearer sk-1234"`
- OpenAI: https://platform.openai.com/usage (most detailed)
- Groq: https://console.groq.com/
- Anthropic: https://console.anthropic.com/
- Google: https://console.cloud.google.com/

**Note:** LiteLLM Admin UI requires PostgreSQL database (not enabled). Cost tracking via logs and provider dashboards is sufficient for GTD use case.

**Recommendations (Oct 2025):**
- **DEFAULT: gpt-4o-mini** - Best balance of quality/cost ($0.014/session)
- **CHEAPEST: llama-3.1-8b (Groq)** - For simple tasks ($0.003/session, 5x cheaper)
- **BUDGET GOOGLE: gemini-2.0-flash** - NOT 2.5-flash! ($0.009/session vs $0.040)
- **AVOID gpt-4.1-mini for budget** - 2.6x more expensive than gpt-4o-mini despite "mini" name
- **AVOID gemini-2.5 models for budget** - Reasoning models are expensive, use 2.0-flash instead
- Use gpt-4o, claude-sonnet-4-5 only for complex tasks (premium pricing)
- LiteLLM caching saves 50-80% on repeated queries
- Monitor usage weekly via provider dashboards

## Troubleshooting

**Common issues:**

1. **Tool not working in chat**: Small models lack tool support. Use GPT-4o-mini (recommended), GPT-4.1-mini, Claude Sonnet 4.5, or Gemini 2.0 Flash.

   **Note on Gemini model selection (Oct 2025):**
   - **Gemini 2.0 Flash**: Standard model, best for budget ($0.10/$0.40 per 1M tokens)
   - **Gemini 2.5 models**: Reasoning models that "think" before responding (EXPENSIVE!)
     - gemini-2.5-pro: Needs 100-300 max_tokens (~157 reasoning + text tokens) - $1.25/$10.00
     - gemini-2.5-flash: Needs 50-200 max_tokens (~21 reasoning + text tokens) - $0.30/$2.50
     - ⚠️ Gemini 2.5 pricing increased significantly in June 2025
     - Only use 2.5 models when you need reasoning capabilities and are OK with higher costs
   - If you get null/empty responses from 2.5 models, increase max_tokens parameter

2. **Tool server URL error in GUI**: Must use internal Docker network names:
   - ✅ Correct: `http://todoist-tool:8000`
   - ❌ Wrong: `http://localhost:8007`

3. **Todoist API errors**: Check `TODOIST_API_KEY` in `.env`. Get from: https://todoist.com/prefs/integrations/developer

4. **CalDAV connection failed**:
   - Verify `CALDAV_URL`, `CALDAV_USERNAME`, `CALDAV_PASSWORD` in `.env`
   - Test URL format (should end with /dav or /caldav)
   - iCloud users: Need app-specific password, not main password

5. **First login blocked**: Set `ENABLE_SIGNUP=true` in docker-compose.yml temporarily, create admin account, then set back to `false`

6. **Git operations fail**: Ensure `~/ai-workspace` is initialized as git repo:
   ```bash
   cd ~/ai-workspace && git status
   ```

7. **Models bypass LiteLLM (no caching, no fallbacks)**:
   - **Symptom**: Models work but Redis cache has low hit rate, or models are in OpenWebUI GUI with direct provider URLs
   - **Cause**: OpenWebUI database has manual API connections that bypass LiteLLM proxy
   - **Fix**: Run `python3 fix_litellm_routing.py` to update database, then restart OpenWebUI
   - **Verify**: All models should show `urlIdx: 0` in Settings → Admin → Models export, not multiple urlIdx values
   - **Test caching**: Make same API call twice - second call should be 10-20x faster (cached)

8. **Tools not showing in database / Understanding tool registration**:
   - **There are TWO types of tool servers** (as of Oct 2025):
     - **Global Tool Servers**: Admin-registered, server-side requests, shared across all users, stored in `config` table under `tool_server.connections`
     - **User Tool Servers**: User-registered, client-side requests, per-user, stored in `tool` table
   - **GTD tools are Global Tool Servers** (correct for production deployment)
   - **Database query**: Use `SELECT data FROM config WHERE id=1` and parse JSON `tool_server.connections` array
   - **NOT in tool table**: Querying `tool` table will show 0 results - this is expected
   - **Verification**: Test script now checks config table correctly (Test 8)

**Debug connectivity:**
```bash
# Test from OpenWebUI container
docker exec openwebui curl http://filesystem-tool:8000/docs
docker exec openwebui curl http://git-tool:8000/docs
docker exec openwebui curl http://todoist-tool:8000/
docker exec openwebui curl http://caldav-tool:8000/
```

## Key Gotchas

1. **Two different workspace directories** (often confused):
   - **`~/ai-workspace`**: For LLM file operations (mounted to filesystem-tool & git-tool)
     - Used by: Filesystem tool, Git tool (both share this directory)
     - Purpose: LLM can read/write files, commit to git
     - Mounted at: `~/ai-workspace:/workspace` (docker-compose.yml lines 87, 118)
     - Security: LLM has **write access** - can modify/delete files
     - Initialized as: Git repository with README.md
   - **`~/input-rag`**: For RAG documents (NOT mounted to containers in current setup)
     - Used by: Historically for RAG ingestion, but NOT currently used
     - Purpose: Originally intended for document upload to ChromaDB
     - Status: Directory exists but not referenced in docker-compose.yml
     - **Important**: README.md mentions this extensively but it's not part of active stack

   **TLDR**: Use `~/ai-workspace` for LLM file operations. `~/input-rag` is legacy/unused in current setup.

2. **LiteLLM is REQUIRED:**
   - All API calls go through LiteLLM proxy at `http://litellm:4000`
   - **Do NOT disable LiteLLM** - OpenWebUI won't work without it (configured in docker-compose.yml lines 352-368)
   - LiteLLM provides: caching (saves $$), fallbacks (reliability), cost tracking
   - Check if working: `curl http://localhost:4000/health` or http://localhost:4000

3. **Full stack is enabled (not minimal):**
   - Running: OpenWebUI + ChromaDB + LiteLLM + Redis + SearXNG + Tika + 4 GTD tools
   - ChromaDB: RAG vector storage (lines 27-42)
   - Redis: LiteLLM caching (lines 297-313)
   - SearXNG: Web search (lines 213-232)
   - Tika: Document parsing (lines 235-249)
   - Weather, Memory, Pipelines, Ollama, Docling: Commented out (not needed)
   - To disable extras: Comment out service in docker-compose.yml + remove from OpenWebUI env vars

3. **OpenWebUI config locations:**
   - OpenWebUI SQLite: `/app/backend/data/webui.db` (in `openwebui-data` volume)
   - Workspace files: `~/ai-workspace` (host mount, NOT a volume)
   - No ChromaDB - no vector storage

4. **CalDAV URL formats:**
   - iCloud: `https://caldav.icloud.com`
   - Nextcloud: `https://nextcloud.example.com/remote.php/dav`
   - Fastmail: `https://caldav.fastmail.com`
   - Use app-specific passwords for iCloud/Google

5. **Tool server source code:**
   - Filesystem/Git: Cloned from `github.com/open-webui/openapi-servers` during build
   - Todoist/CalDAV: Custom code in `todoist-tool/` and `caldav-tool/` directories

6. **TTS/STT enabled**: OpenAI Whisper (STT) and TTS (voice: alloy) configured. Costs: ~$0.006/minute (STT), ~$0.03/minute (TTS).

## Testing & CI/CD

**Integration test script**: `./test-gtd-stack.sh`
- Tests all 9 critical areas: containers, tool endpoints, API connectivity, file operations, git, config validation, web interface, model availability, pricing
- Run before major changes or after stack updates
- Returns exit code 0 if all critical tests pass

**What it tests:**
1. Container health (OpenWebUI, filesystem, git, todoist, caldav)
2. Tool server endpoints (health checks, OpenAPI docs)
3. Todoist API connectivity (task retrieval)
4. CalDAV API connectivity (calendar + event access)
5. Filesystem operations (list directory, create file, verify on host)
6. Git operations (log, workspace verification)
7. Configuration validation (docker-compose.yml settings match CLAUDE.md)
8. OpenWebUI web interface (port 8080 accessibility)
9. Model availability & pricing (API keys, budget-friendly models, outdated model detection, LiteLLM status)

**CI/CD (Automated via GitHub Actions):**

✅ **Unit Tests** (`.github/workflows/unit-tests.yml`)
- **Trigger**: Every push/PR to main or develop
- **Tests**: todoist-tool and caldav-tool independently
- **Coverage**: Reports to Codecov (fails if coverage drops below 80%)
- **Run time**: ~2-3 minutes
- **Python version**: 3.10 (matches production containers)
- **Caching**: pip packages cached for speed
- **Artifacts**: HTML coverage reports uploaded

✅ **Integration Tests** (`.github/workflows/integration-tests.yml`)
- **Trigger**: Push/PR to main, or manual via workflow_dispatch
- **Tests**:
  - Docker image builds (todoist-tool, caldav-tool, filesystem-tool, git-tool)
  - Container health checks (all 10 services)
  - **OpenWebUI configuration validation**:
    - Starts full OpenWebUI stack (OpenWebUI + all 4 tool servers)
    - Validates OpenWebUI API responds correctly
    - Verifies tool server connectivity from OpenWebUI container
    - **Queries OpenWebUI database**:
      - Lists all tables
      - Checks config settings
      - Verifies user accounts
      - Lists tool/function registrations
      - Shows model configuration
      - Displays prompts
    - Checks logs for critical errors
  - Configuration validation (docker-compose.yml syntax)
  - Security checks (no hardcoded API keys with `grep -r "sk-proj-" --exclude-dir=.git .`)
  - Documentation completeness (README.md, CLAUDE.md, MODEL-UPDATE-STRATEGY.md)
  - Markdown link validation
- **Run time**: ~10-15 minutes (longer due to full stack startup)
- **Matrix strategy**: Tests against multiple tool configurations

✅ **Dependency Updates** (`.github/dependabot.yml`)
- **Schedule**: Weekly automated PRs for dependency updates
- **Tracks**: GitHub Actions (v4-v5), Python packages (pip), Docker base images
- **Grouping**: Minor/patch updates grouped together
- **Auto-labels**: PRs labeled by component (todoist-tool, caldav-tool, github-actions)
- **Security**: Auto-merges security updates if tests pass

**CI Status**:
- All workflows use latest GitHub Actions versions (v4-v5)
- Python 3.10 for consistency with production containers
- Pip caching for faster builds (~30% speedup)
- Parallel test execution for speed (pytest-xdist)
- Fail-fast disabled to see all test results

**Debugging CI failures**:
```bash
# Reproduce unit test failure locally
./run-tests.sh todoist

# Reproduce integration test failure locally
./test-gtd-stack.sh

# Check specific workflow logs
gh run list --workflow=unit-tests.yml
gh run view <run-id> --log

# Re-run failed jobs
gh run rerun <run-id> --failed
```

**Local CI testing:**
```bash
# Run tests locally (same as CI)
./run-tests.sh

# Validate docker-compose.yml
docker-compose config

# Check for secrets in code
grep -r "sk-proj-" --exclude-dir=.git .
```

**LiteLLM routing (CRITICAL)**: All traffic MUST go through LiteLLM proxy
- Current setup: ALL API calls route through `http://litellm:4000` (verified Oct 2025)
- Benefits: Redis caching (50-80% cost savings), fallback chains, cost tracking
- If models appear in GUI but don't work: Check Settings → Connections, delete any manual API connections
- Script to fix routing: `python3 fix_litellm_routing.py` (updates OpenWebUI database)

**Model currency & updates**: See `MODEL-UPDATE-STRATEGY.md`
- Automated API checks verify models are current (run with test script)
- All models verified current as of October 2025
- Monthly review recommended (first Sunday)
- Provider update patterns and migration guides included

## Utility Scripts

**Experimental scripts for maintenance and debugging** (gitignored, not for production):

1. **fix_litellm_routing.py** - Fix OpenWebUI to route all LLM traffic through LiteLLM
   - **Purpose**: Update OpenWebUI database to use LiteLLM proxy instead of direct provider APIs
   - **When to use**: After fresh install, or if models bypass LiteLLM (no caching/fallbacks)
   - **How**: Copy database from container, run script, copy back, restart OpenWebUI
   - **Result**: All models route through `http://litellm:4000`, Redis caching works
   - **See**: Troubleshooting section #7 for detailed steps

2. **import_config_v2.py** - Import OpenWebUI configuration from JSON
   - **Purpose**: Bulk import settings, models, tools, prompts into OpenWebUI database
   - **When to use**: Restoring from backup, migrating to new instance
   - **How**: Place config JSON in `/tmp/config.json`, run script inside container
   - **Alternative**: Use OpenWebUI GUI: Settings → Admin → Database → Import

3. **get_llm_models.py** - Fetch current models and pricing from provider APIs
   - **Purpose**: Check what models are available from OpenAI, Anthropic, Google, Groq
   - **When to use**: Monthly review to detect new/deprecated models
   - **How**: `python3 get_llm_models.py` (requires `.env` with API keys)
   - **Output**: Model IDs with pricing and context window info

4. **fetch_models.sh** - Same as get_llm_models.py but in Bash
   - **Purpose**: Quick check of available models from all providers
   - **When to use**: Alternative to Python script, faster for quick checks
   - **How**: `./fetch_models.sh` (requires `.env` with API keys)
   - **Output**: Formatted list of models grouped by provider

5. **apply_model_visibility.py** - Set model visibility in OpenWebUI
   - **Purpose**: Bulk hide/show models in GUI based on JSON export
   - **When to use**: After adding new provider, want to hide low-quality models
   - **How**: Export models from GUI, edit JSON, run script
   - **Alternative**: Manually toggle visibility in Settings → Models

6. **show_rag_stats.py** - Display RAG document statistics and cost estimates
   - **Purpose**: Analyze ChromaDB usage, estimate token costs for RAG context
   - **When to use**: Monitor RAG costs, identify large documents
   - **How**: `docker exec openwebui python3 /app/show_rag_stats.py`
   - **Output**: Document count, total tokens, estimated monthly cost

**Best practices:**
- These scripts are **experimental** - always backup database before running
- Scripts are gitignored to prevent accidental commit of API keys
- For production use, prefer GUI operations or Docker exec commands
- Test scripts on backup database first

## GTD Workflow Example

**Test the full stack:**

1. "Create a markdown file called weekly-plan.md with sections for Monday-Friday"
2. "Add a task to each day: Monday = Review emails, Tuesday = Write report, etc."
3. "Save it to ~/ai-workspace/weekly-plan.md"
4. "Commit it to git with message 'Weekly plan for Oct 2025'"
5. "Add a Todoist task: 'Review weekly plan - Friday 5pm'"
6. "Schedule a calendar event: 'Weekly review - Friday 5-6pm'"

**If all 6 steps work:** You have a functioning GTD system.
