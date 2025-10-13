# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

OpenWebUI configured for **GTD (Getting Things Done) workflows**: multi-cloud LLM access, TTS/STT, file management, version control, task management, and calendar integration.

**HONEST ASSESSMENT (Updated 2025-10-12):**
- This is **NOT a minimal GTD setup** despite previous claims
- Currently running: OpenWebUI + ChromaDB + LiteLLM + Redis + SearXNG + Tika + 4 GTD tools (filesystem, git, todoist, caldav)
- Total: 10 containers (not the "minimal 5" originally documented)
- **LiteLLM is the gateway**: All API calls go through LiteLLM proxy at `http://litellm:4000`
- **Models updated Oct 2025**: All providers verified current as of October 2025, outdated models removed (gemini-1.5-* → gemini-2.5-*)

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

## Common Commands

```bash
# Stack management
docker-compose up -d                    # Start all services (OpenWebUI + 4 tools)
docker-compose down                     # Stop all services
docker-compose logs -f openwebui        # View logs
docker-compose ps                       # Check service status

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

## GTD Tool Servers

**All tool servers follow same pattern:**
- Base image: `python:3.10.12-slim`
- Run as non-root `appuser` (UID 10001)
- Expose port 8000 internally
- Health check on `/` or `/docs` endpoint

**Filesystem & Git tools (from openapi-servers repo):**
- **CRITICAL**: Both mount `~/ai-workspace:/workspace` (docker-compose.yml lines 85, 109)
- **SECURITY RISK**: LLM has **write access** to this directory - can modify/delete files
- Sandboxed to `/workspace` only (cannot access other paths)
- **Workspace is a git repo** - initialized with README.md
- For read-only: Add `:ro` suffix: `~/ai-workspace:/workspace:ro`

**Todoist tool (custom):**
- Location: `todoist-tool/main.py`
- Endpoints: `/tasks` (list, create), `/tasks/{id}` (get, update, delete), `/tasks/{id}/close` (complete)
- Uses Todoist REST API v2: https://api.todoist.com/rest/v2
- Requires: `TODOIST_API_KEY` from .env

**CalDAV/CardDAV tool (custom):**
- Location: `caldav-tool/main.py`
- Endpoints:
  - Calendar: `/calendars`, `/events` (list, create)
  - Contacts: `/addressbooks`, `/contacts` (list, create)
- Uses Python `caldav` library
- Requires: `CALDAV_URL`, `CALDAV_USERNAME`, `CALDAV_PASSWORD`
- Optional: Separate CardDAV creds (defaults to CalDAV)

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
```

**What is tested:**
- Health check endpoints
- All CRUD operations (list, create, get, update, delete)
- Error handling (network errors, timeouts, API errors)
- Retry logic with exponential backoff
- Request parameter validation
- Response format validation

**Test reports:**
- HTML coverage reports: `{tool}/htmlcov/index.html`
- Terminal output shows: passed/failed tests, coverage percentage, missing lines
- Tests use mocking to avoid real API calls

**When to run tests:**
- Before committing changes to tool code
- After adding new features or endpoints
- After dependency updates
- As part of CI/CD pipeline

## Budget Controls ($30/month target)

**Default model enforcement:**
- `DEFAULT_MODELS=gpt-4o-mini` in docker-compose.yml forces cheap model
- **All API calls go through LiteLLM** which has caching enabled (saves $$)

**Current model pricing (Oct 2025, per 1M tokens):**

| Model | Input | Output | Use Case |
|-------|-------|--------|----------|
| **gpt-4.1-mini** | $0.15 | $0.60 | **NEW** - Best budget option |
| **gpt-4o-mini** | $0.15 | $0.60 | Current default, proven reliable |
| gpt-4o | $2.50 | $10.00 | Complex tasks only |
| **claude-sonnet-4-5** | $3.00 | $15.00 | **NEW** - Most capable Claude |
| claude-3-5-sonnet | $3.00 | $15.00 | Previous flagship |
| claude-3-5-haiku | $1.00 | $5.00 | Fast, cheap Claude |
| **llama-3.3-70b** | $0.59 | $0.79 | Groq (very fast, cheap) |
| llama-3.1-8b | $0.05 | $0.08 | Groq (fastest, cheapest) |
| **gemini-2.5-pro** | $1.25 | $5.00 | **NEW** - Replaced 1.5-pro |
| **gemini-2.5-flash** | $0.075 | $0.30 | **NEW** - Replaced 1.5-flash |
| gemini-2.0-flash | $0.075 | $0.30 | Alternative budget option |

**Cost estimates:**
- Typical agentic session (50k in, 10k out):
  - llama-3.1-8b (Groq): ~$0.003 (CHEAPEST)
  - gemini-2.5-flash: ~$0.007
  - gpt-4.1-mini: ~$0.014
  - llama-3.3-70b (Groq): ~$0.037
- $30/month = ~2000 gpt-4.1-mini sessions = 65/day

**LiteLLM caching benefits:**
- Redis caching enabled - repeated queries cost $0
- Fallback chains prevent expensive failures
- Cost tracking: Check http://localhost:4000 (UI: admin/admin)

**Cost monitoring:**
- LiteLLM dashboard: http://localhost:4000 (tracks all usage)
- OpenAI: https://platform.openai.com/usage
- Groq: https://console.groq.com/
- Anthropic: https://console.anthropic.com/
- Google: https://console.cloud.google.com/

**Recommendations:**
- Use **Groq's llama-3.1-8b for cheapest** ($0.003/session - 10x cheaper than GPT-4o-mini)
- Use gemini-2.5-flash for budget Google ($0.007/session)
- Use gpt-4.1-mini or gpt-4o-mini for OpenAI (best balance $0.014/session)
- Use llama-3.3-70b (Groq) for best Groq performance ($0.037/session)
- Avoid gpt-4o and claude-sonnet unless necessary (expensive)
- LiteLLM caching saves 50-80% on repeated queries
- Monitor usage weekly via LiteLLM dashboard

## Troubleshooting

**Common issues:**

1. **Tool not working in chat**: Small models lack tool support. Use GPT-4.1-mini or GPT-4o-mini (best balance), Claude Sonnet 4.5, or Gemini 2.0 Flash.

   **Note on Gemini 2.5 models**: These are reasoning models that "think" before responding:
   - gemini-2.5-pro: Needs 100-300 max_tokens (uses ~157 reasoning + text tokens)
   - gemini-2.5-flash: Needs 50-200 max_tokens (uses ~21 reasoning + text tokens)
   - gemini-2.0-flash: Standard model, works with normal 5-20 tokens
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

**Debug connectivity:**
```bash
# Test from OpenWebUI container
docker exec openwebui curl http://filesystem-tool:8000/docs
docker exec openwebui curl http://git-tool:8000/docs
docker exec openwebui curl http://todoist-tool:8000/
docker exec openwebui curl http://caldav-tool:8000/
```

## Key Gotchas

1. **Workspace location**: Files created by LLM are in `~/ai-workspace` (NOT `~/input-rag`). This is a git repo.

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
- Runs on every push/PR to main or develop
- Tests both todoist-tool and caldav-tool independently
- Coverage reporting to Codecov
- Fails if tests fail or coverage drops
- Typical run time: ~2-3 minutes

✅ **Integration Tests** (`.github/workflows/integration-tests.yml`)
- Runs on push/PR to main, or manually via workflow_dispatch
- Tests:
  - Docker image builds
  - Container health checks
  - Configuration validation (docker-compose.yml syntax)
  - Security checks (no hardcoded API keys)
  - Documentation completeness
  - Markdown link validation
- Typical run time: ~5-10 minutes

✅ **Dependency Updates** (`.github/dependabot.yml`)
- Weekly automated PRs for dependency updates
- Tracks: GitHub Actions, Python packages (pip), Docker base images
- Groups minor/patch updates together
- Auto-labels PRs by component (todoist-tool, caldav-tool, github-actions)

**CI Status:**
- All workflows use latest GitHub Actions versions (v4-v5)
- Python 3.10 for consistency with production containers
- Pip caching for faster builds
- Parallel test execution for speed

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
