# Integration Tests for GTD Tool Servers

This directory contains integration tests that verify:
1. OpenWebUI configuration and database state
2. Tool server connectivity and health
3. **LLM function calling** - Real LLMs calling tools via function calling

## ⚠️ HONEST ASSESSMENT - LLM Tests

**Status**: `test_llm_function_calling.py` is **WRITTEN BUT NOT RUN**.

**What this means:**
- ❌ **Code has never been executed** (no OPENAI_API_KEY available)
- ❌ **Don't know if tests pass** (they skip without API key)
- ❌ **Don't know if function schemas are correct**
- ❌ **Don't know if LLM will actually call the tools**
- ❌ **Don't know if cleanup works**
- ❌ **Cost estimate ($0.03) is theoretical**

**What IS true:**
- ✅ Code structure looks correct
- ✅ Uses proper OpenAI client library
- ✅ Has proper skip behavior
- ✅ Cleanup logic is present

**To actually validate these tests:**
```bash
export OPENAI_API_KEY="your-key-here"
pytest test_llm_function_calling.py -v -s
```

If they pass - great! If they fail - please report the issues so the tests can be fixed.

---

## Test Files

### `test_openwebui_api.py`
Tests OpenWebUI configuration, database, and connectivity.

**What it tests:**
- Container health
- Database tables and structure
- Tool server registrations
- Configuration validation

**Run:**
```bash
source .venv/bin/activate
pytest test_openwebui_api.py -v
```

### `test_llm_function_calling.py` ⭐ **NEW**
Tests that actual LLMs can use function calling to interact with tool servers.

**What it tests:**
- LLM creates Todoist task via function calling
- LLM creates CalDAV event via function calling
- LLM performs multi-step GTD workflow

**Prerequisites:**
1. Tool servers running (`docker-compose up -d`)
2. `OPENAI_API_KEY` in environment
3. Optional: `TOOL_API_KEY` if authentication enabled

**Run:**
```bash
# Setup
source .venv/bin/activate
pip install -r requirements.txt

# Run tests (requires OPENAI_API_KEY)
export OPENAI_API_KEY="sk-proj-..."
pytest test_llm_function_calling.py -v -s

# Run with authentication
export TOOL_API_KEY="your-secret-key"
pytest test_llm_function_calling.py -v -s
```

**Skip behavior:**
- Tests automatically skip if `OPENAI_API_KEY` not set
- This prevents accidental API usage/costs
- Use `-v` flag to see skip reason

**Costs:**
- Each test uses gpt-4o-mini (~$0.01 per test)
- 3 tests total = ~$0.03
- Tasks/events created are automatically cleaned up

## Test Coverage

| Test Type | What's Tested | What's NOT Tested |
|-----------|---------------|-------------------|
| Unit tests | Individual endpoints with mocks | Real API calls |
| Integration tests | Container connectivity, DB state | LLM usage |
| **LLM tests** | **Real LLM calling tools** | **OpenWebUI GUI** |

## Installation

```bash
# Create virtual environment
python3 -m venv .venv

# Activate
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Example Test Output

```
test_llm_function_calling.py::TestLLMFunctionCalling::test_llm_creates_todoist_task
✅ LLM successfully created task: 8234567890
PASSED

test_llm_function_calling.py::TestLLMFunctionCalling::test_llm_creates_calendar_event
✅ LLM successfully created event: abc123-def456
PASSED

test_llm_function_calling.py::TestLLMFunctionCalling::test_llm_multi_step_workflow
✅ Created task: 8234567891
✅ Created event: ghi789-jkl012
PASSED
```

## Environment Variables

```bash
# Required for LLM tests
export OPENAI_API_KEY="sk-proj-..."

# Optional: Tool authentication
export TOOL_API_KEY="your-secret-key"

# Optional: Todoist/CalDAV credentials (if testing actual APIs)
export TODOIST_API_KEY="..."
export CALDAV_URL="..."
export CALDAV_USERNAME="..."
export CALDAV_PASSWORD="..."
```

## Troubleshooting

**Tests skip with "OPENAI_API_KEY not set":**
- This is expected behavior
- Set `OPENAI_API_KEY` in environment to enable tests

**401 Unauthorized:**
- Tool authentication is enabled
- Set `TOOL_API_KEY` environment variable

**Connection refused:**
- Tool servers not running
- Run `docker-compose up -d todoist-tool caldav-tool`

**Function call returns 404/500:**
- Check tool server logs: `docker logs openwebui-todoist`
- Verify tool schema matches API

## CI/CD Integration

```yaml
# .github/workflows/llm-tests.yml
name: LLM Function Calling Tests

on:
  workflow_dispatch:  # Manual trigger only (costs money)

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Start services
        run: docker-compose up -d
      - name: Run LLM tests
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          cd tests/integration
          pip install -r requirements.txt
          pytest test_llm_function_calling.py -v
```

## Future Improvements

- [ ] Add tests for other LLM providers (Anthropic, Groq)
- [ ] Test error handling (LLM retry on tool failure)
- [ ] Test multi-turn conversations
- [ ] Test tool chaining (task → event → reminder)
- [ ] Add browser automation (Playwright/Selenium)
- [ ] Test OpenWebUI GUI directly
