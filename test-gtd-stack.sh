#!/bin/bash

# GTD Stack Integration Test Script
# Tests all components: containers, tools, OpenWebUI settings

# Don't exit on errors - we want to run all tests
set +e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test results
PASSED=0
FAILED=0
WARNINGS=0

print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

print_test() {
    echo -e "${YELLOW}[TEST]${NC} $1"
}

print_pass() {
    echo -e "${GREEN}[PASS]${NC} $1"
    ((PASSED++))
}

print_fail() {
    echo -e "${RED}[FAIL]${NC} $1"
    ((FAILED++))
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
    ((WARNINGS++))
}

# Test 1: Container Health
print_header "Test 1: Container Health Status"

CONTAINERS=("openwebui" "filesystem-tool" "git-tool" "todoist-tool" "caldav-tool")
for container in "${CONTAINERS[@]}"; do
    print_test "Checking $container health..."
    # docker-compose ps --format json outputs newline-delimited JSON, not an array
    STATUS=$(docker-compose ps --format json | jq -r "select(.Service==\"$container\") | .Health" 2>/dev/null || echo "unknown")

    if [ "$STATUS" == "healthy" ]; then
        print_pass "$container is healthy"
    elif [ "$STATUS" == "null" ] || [ "$STATUS" == "" ] || [ "$STATUS" == "unknown" ]; then
        # Check if running (some containers don't have health checks)
        STATE=$(docker-compose ps --format json | jq -r "select(.Service==\"$container\") | .State" 2>/dev/null || echo "unknown")
        if [ "$STATE" == "running" ]; then
            print_warn "$container is running (no health check defined)"
        else
            print_fail "$container is not running (state: $STATE)"
        fi
    else
        print_fail "$container is unhealthy (status: $STATUS)"
    fi
done

# Test 2: Tool Server Endpoints
print_header "Test 2: Tool Server Health Endpoints"

TOOLS=(
    "filesystem:8006:/docs"
    "git:8003:/docs"
    "todoist:8007:/"
    "caldav:8008:/"
)

for tool in "${TOOLS[@]}"; do
    IFS=: read -r NAME PORT ENDPOINT <<< "$tool"
    print_test "Testing $NAME tool on port $PORT..."

    RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:$PORT$ENDPOINT 2>/dev/null || echo "000")
    if [ "$RESPONSE" == "200" ]; then
        if [ "$ENDPOINT" == "/" ]; then
            BODY=$(curl -s http://localhost:$PORT$ENDPOINT 2>/dev/null)
            if echo "$BODY" | grep -q "healthy"; then
                print_pass "$NAME tool is healthy"
            else
                print_warn "$NAME tool responded 200 but no 'healthy' in body"
            fi
        else
            print_pass "$NAME tool is accessible (OpenAPI docs available)"
        fi
    else
        print_fail "$NAME tool not responding (HTTP $RESPONSE)"
    fi
done

# Test 3: Todoist API
print_header "Test 3: Todoist API Connectivity"

print_test "Fetching Todoist tasks..."
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8007/tasks 2>/dev/null || echo "000")
if [ "$RESPONSE" == "200" ]; then
    TASKS=$(curl -s http://localhost:8007/tasks 2>/dev/null)
    TASK_COUNT=$(echo "$TASKS" | jq '. | length' 2>/dev/null || echo "0")
    print_pass "Todoist API connected (found $TASK_COUNT tasks)"
else
    print_fail "Todoist API not responding (HTTP $RESPONSE)"
fi

# Test 4: CalDAV API
print_header "Test 4: CalDAV API Connectivity"

print_test "Fetching CalDAV calendars..."
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8008/calendars 2>/dev/null || echo "000")
if [ "$RESPONSE" == "200" ]; then
    CALENDARS=$(curl -s http://localhost:8008/calendars 2>/dev/null)
    CAL_COUNT=$(echo "$CALENDARS" | jq '. | length' 2>/dev/null || echo "0")
    print_pass "CalDAV API connected (found $CAL_COUNT calendars)"

    # Try to get events
    print_test "Fetching CalDAV events..."
    EVENT_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8008/events?days=30" 2>/dev/null || echo "000")
    if [ "$EVENT_RESPONSE" == "200" ]; then
        EVENTS=$(curl -s "http://localhost:8008/events?days=30" 2>/dev/null)
        EVENT_COUNT=$(echo "$EVENTS" | jq '. | length' 2>/dev/null || echo "0")
        print_pass "CalDAV events fetched (found $EVENT_COUNT events)"
    else
        print_fail "CalDAV events not accessible (HTTP $EVENT_RESPONSE)"
    fi
else
    print_fail "CalDAV API not responding (HTTP $RESPONSE)"
fi

# Test 5: Filesystem Tool
print_header "Test 5: Filesystem Tool Operations"

print_test "Listing workspace directory via Filesystem API..."
LIST_RESPONSE=$(curl -s -X POST http://localhost:8006/list_directory \
    -H "Content-Type: application/json" \
    -d '{"path":"/workspace"}' \
    2>/dev/null)

if echo "$LIST_RESPONSE" | jq -e 'if type=="array" then true else false end' >/dev/null 2>&1; then
    FILE_COUNT=$(echo "$LIST_RESPONSE" | jq -r 'length' 2>/dev/null || echo "0")
    print_pass "Filesystem tool accessible (found $FILE_COUNT items in workspace)"

    # Test file creation
    print_test "Creating test file via Filesystem API..."
    TEST_FILE="test-$(date +%s).txt"
    TEST_CONTENT="GTD stack test - $(date)"

    CREATE_RESPONSE=$(curl -s -X POST http://localhost:8006/write_file \
        -H "Content-Type: application/json" \
        -d "{\"path\":\"/workspace/$TEST_FILE\",\"content\":\"$TEST_CONTENT\"}" \
        2>/dev/null)

    if echo "$CREATE_RESPONSE" | jq -e '.message' >/dev/null 2>&1; then
        print_pass "File created via Filesystem tool"

        # Verify file exists in workspace
        if [ -f ~/ai-workspace/"$TEST_FILE" ]; then
            print_pass "File verified in ~/ai-workspace/$TEST_FILE"
            # Cleanup
            rm -f ~/ai-workspace/"$TEST_FILE"
        else
            print_fail "File not found in ~/ai-workspace/$TEST_FILE"
        fi
    else
        print_fail "Failed to create file via Filesystem tool"
    fi
else
    print_fail "Filesystem tool not accessible"
fi

# Test 6: Git Tool
print_header "Test 6: Git Tool Operations"

print_test "Checking git log via Git tool..."
GIT_RESPONSE=$(curl -s -X POST http://localhost:8003/log \
    -H "Content-Type: application/json" \
    -d '{"repo_path":"/workspace","limit":1}' \
    2>/dev/null)

if echo "$GIT_RESPONSE" | jq -e '.commits' >/dev/null 2>&1; then
    COMMIT_COUNT=$(echo "$GIT_RESPONSE" | jq -r '.commits | length' 2>/dev/null || echo "0")
    print_pass "Git tool accessible (found $COMMIT_COUNT recent commits)"

    # Verify workspace is a git repo
    if [ -d ~/ai-workspace/.git ]; then
        print_pass "~/ai-workspace is a git repository"
    else
        print_fail "~/ai-workspace is not a git repository"
    fi
else
    print_fail "Git tool not responding or workspace not a git repo"
fi

# Test 7: OpenWebUI Settings vs docker-compose
print_header "Test 7: OpenWebUI Configuration Validation"

print_test "Checking OpenWebUI environment variables..."

# Extract key settings from docker-compose.yml
COMPOSE_FILE="docker-compose.yml"
if [ ! -f "$COMPOSE_FILE" ]; then
    print_fail "docker-compose.yml not found"
else
    # Check ENABLE_SIGNUP
    SIGNUP=$(grep "ENABLE_SIGNUP" "$COMPOSE_FILE" | grep -v "^[[:space:]]*#" | grep -v "^#" | head -1 | sed 's/.*ENABLE_SIGNUP=//' | sed 's/#.*//' | tr -d ' "' || echo "not_found")
    if [ "$SIGNUP" == "false" ]; then
        print_pass "ENABLE_SIGNUP=false (admin-only mode)"
    elif [ "$SIGNUP" == "true" ]; then
        print_warn "ENABLE_SIGNUP=true (signups enabled - consider disabling)"
    else
        print_warn "ENABLE_SIGNUP not found in docker-compose.yml"
    fi

    # Check DEFAULT_MODELS
    DEFAULT_MODEL=$(grep "DEFAULT_MODELS" "$COMPOSE_FILE" | grep -v "^[[:space:]]*#" | grep -v "^#" | head -1 | sed 's/.*DEFAULT_MODELS=//' | sed 's/#.*//' | tr -d ' "' || echo "not_found")
    if echo "$DEFAULT_MODEL" | grep -q "gpt-4o-mini"; then
        print_pass "DEFAULT_MODELS includes gpt-4o-mini (budget control)"
    else
        print_warn "DEFAULT_MODELS does not include gpt-4o-mini: $DEFAULT_MODEL"
    fi

    # Check ENABLE_FUNCTION_CALLING
    FUNCTION_CALLING=$(grep "ENABLE_FUNCTION_CALLING" "$COMPOSE_FILE" | grep -v "^[[:space:]]*#" | grep -v "^#" | head -1 | sed 's/.*ENABLE_FUNCTION_CALLING=//' | sed 's/#.*//' | tr -d ' "' || echo "not_found")
    if [ "$FUNCTION_CALLING" == "true" ]; then
        print_pass "ENABLE_FUNCTION_CALLING=true (tools enabled)"
    else
        print_fail "ENABLE_FUNCTION_CALLING not true: $FUNCTION_CALLING"
    fi

    # Check workspace mount
    print_test "Checking workspace mount..."
    WORKSPACE_MOUNT=$(grep "ai-workspace:/workspace" "$COMPOSE_FILE" | grep -v "^#" | wc -l | tr -d ' ')
    if [ "$WORKSPACE_MOUNT" -ge "2" ]; then
        print_pass "Workspace mounted for filesystem and git tools"
    else
        print_fail "Workspace mount not found or incomplete (expected 2+, found $WORKSPACE_MOUNT)"
    fi
fi

# Test 8: OpenWebUI Web Interface
print_header "Test 8: OpenWebUI Web Interface"

print_test "Checking OpenWebUI web interface..."
WEB_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/ 2>/dev/null || echo "000")
if [ "$WEB_RESPONSE" == "200" ]; then
    print_pass "OpenWebUI web interface accessible at http://localhost:8080"
else
    print_fail "OpenWebUI web interface not responding (HTTP $WEB_RESPONSE)"
fi

# Test 9: Model Availability & Pricing
print_header "Test 9: Model Availability & Pricing"

print_test "Checking expected models are configured..."

# Expected budget-friendly models
EXPECTED_MODELS=(
    "gpt-4o-mini:OpenAI:0.15:0.60"
    "gpt-4o:OpenAI:2.50:10.00"
    "claude-3-5-sonnet:Anthropic:3.00:15.00"
    "gemini-1.5-pro:Google:1.25:5.00"
    "llama-3.3-70b:Groq:0.59:0.79"
)

# Known outdated/expensive models to warn about
OUTDATED_MODELS=(
    "gpt-4-turbo"
    "gpt-4-1106"
    "claude-3-opus"
    "gpt-3.5-turbo"
)

# Check if API keys are set and test them with real API calls
print_test "Verifying API keys are configured..."
KEYS_CONFIGURED=0
KEYS_WORKING=0

# Try to get API keys from .env first
if [ -f ".env" ]; then
    set -a
    source .env 2>/dev/null
    set +a
fi

# Also try to get from OpenWebUI container environment (only if not already set from .env)
if [ -z "$OPENAI_API_KEY" ]; then
    CONTAINER_KEY=$(docker exec openwebui printenv OPENAI_API_KEY 2>/dev/null || echo "")
    if [ -n "$CONTAINER_KEY" ]; then
        OPENAI_API_KEY="$CONTAINER_KEY"
    fi
fi
if [ -z "$ANTHROPIC_API_KEY" ]; then
    CONTAINER_KEY=$(docker exec openwebui printenv ANTHROPIC_API_KEY 2>/dev/null || echo "")
    if [ -n "$CONTAINER_KEY" ]; then
        ANTHROPIC_API_KEY="$CONTAINER_KEY"
    fi
fi
if [ -z "$GOOGLE_API_KEY" ]; then
    CONTAINER_KEY=$(docker exec openwebui printenv GOOGLE_API_KEY 2>/dev/null || echo "")
    if [ -n "$CONTAINER_KEY" ]; then
        GOOGLE_API_KEY="$CONTAINER_KEY"
    fi
fi
if [ -z "$GROQ_API_KEY" ]; then
    CONTAINER_KEY=$(docker exec openwebui printenv GROQ_API_KEY 2>/dev/null || echo "")
    if [ -n "$CONTAINER_KEY" ]; then
        GROQ_API_KEY="$CONTAINER_KEY"
    fi
fi

# Test OpenAI API
if [ -n "$OPENAI_API_KEY" ] && [ "$OPENAI_API_KEY" != "your-key-here" ]; then
        ((KEYS_CONFIGURED++))
        print_test "Testing OpenAI API with real request..."
        OPENAI_RESPONSE=$(curl -s -X POST "https://api.openai.com/v1/chat/completions" \
            -H "Authorization: Bearer $OPENAI_API_KEY" \
            -H "Content-Type: application/json" \
            -d '{
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": "test"}],
                "max_tokens": 5
            }' 2>/dev/null)

        if echo "$OPENAI_RESPONSE" | jq -e '.choices[0].message.content' >/dev/null 2>&1; then
            print_pass "OpenAI API key working (gpt-4o-mini)"
            ((KEYS_WORKING++))
        else
            ERROR=$(echo "$OPENAI_RESPONSE" | jq -r '.error.message // "unknown error"' 2>/dev/null || echo "connection failed")
            print_fail "OpenAI API key invalid or quota exceeded: $ERROR"
        fi
    fi

    # Test Anthropic API
    if [ -n "$ANTHROPIC_API_KEY" ] && [ "$ANTHROPIC_API_KEY" != "your-key-here" ]; then
        ((KEYS_CONFIGURED++))
        print_test "Testing Anthropic API with real request..."
        ANTHROPIC_RESPONSE=$(curl -s -X POST "https://api.anthropic.com/v1/messages" \
            -H "x-api-key: $ANTHROPIC_API_KEY" \
            -H "anthropic-version: 2023-06-01" \
            -H "Content-Type: application/json" \
            -d '{
                "model": "claude-3-5-sonnet-20241022",
                "max_tokens": 10,
                "messages": [{"role": "user", "content": "test"}]
            }' 2>/dev/null)

        if echo "$ANTHROPIC_RESPONSE" | jq -e '.content[0].text' >/dev/null 2>&1; then
            print_pass "Anthropic API key working (claude-3.5-sonnet)"
            ((KEYS_WORKING++))
        else
            ERROR=$(echo "$ANTHROPIC_RESPONSE" | jq -r '.error.message // "unknown error"' 2>/dev/null || echo "connection failed")
            print_warn "Anthropic API: $ERROR"
        fi
    fi

    # Test Google API
    if [ -n "$GOOGLE_API_KEY" ] && [ "$GOOGLE_API_KEY" != "your-key-here" ]; then
        ((KEYS_CONFIGURED++))
        print_test "Testing Google API with real request..."
        GOOGLE_RESPONSE=$(curl -s -X POST "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=$GOOGLE_API_KEY" \
            -H "Content-Type: application/json" \
            -d '{
                "contents": [{"parts":[{"text":"test"}]}],
                "generationConfig": {"maxOutputTokens": 5}
            }' 2>/dev/null)

        if echo "$GOOGLE_RESPONSE" | jq -e '.candidates[0].content.parts[0].text' >/dev/null 2>&1; then
            print_pass "Google API key working (gemini-1.5-flash)"
            ((KEYS_WORKING++))
        else
            ERROR=$(echo "$GOOGLE_RESPONSE" | jq -r '.error.message // "unknown error"' 2>/dev/null || echo "connection failed")
            print_warn "Google API: $ERROR"
        fi
    fi

    # Test Groq API
    if [ -n "$GROQ_API_KEY" ] && [ "$GROQ_API_KEY" != "your-key-here" ]; then
        ((KEYS_CONFIGURED++))
        print_test "Testing Groq API with real request..."
        GROQ_RESPONSE=$(curl -s -X POST "https://api.groq.com/openai/v1/chat/completions" \
            -H "Authorization: Bearer $GROQ_API_KEY" \
            -H "Content-Type: application/json" \
            -d '{
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": "test"}],
                "max_tokens": 5
            }' 2>/dev/null)

        if echo "$GROQ_RESPONSE" | jq -e '.choices[0].message.content' >/dev/null 2>&1; then
            print_pass "Groq API key working (llama-3.3-70b)"
            ((KEYS_WORKING++))
        else
            ERROR=$(echo "$GROQ_RESPONSE" | jq -r '.error.message // "unknown error"' 2>/dev/null || echo "connection failed")
            print_warn "Groq API: $ERROR"
        fi
    fi

    # Summary
    if [ $KEYS_CONFIGURED -eq 0 ]; then
        print_warn "No API keys found in environment. Keys may be configured via OpenWebUI web UI (Settings → Connections)"
    elif [ $KEYS_WORKING -eq 0 ]; then
        print_fail "$KEYS_CONFIGURED API keys configured but none are working"
    elif [ $KEYS_WORKING -lt $KEYS_CONFIGURED ]; then
        print_warn "$KEYS_WORKING/$KEYS_CONFIGURED API keys working (some have issues)"
    else
        print_pass "All $KEYS_WORKING/$KEYS_CONFIGURED API keys tested and working"
    fi

# Model currency check
print_test "Checking if models are up-to-date via API..."

# Check OpenAI models
if [ -n "$OPENAI_API_KEY" ]; then
    LATEST_GPT4O=$(curl -s "https://api.openai.com/v1/models" -H "Authorization: Bearer $OPENAI_API_KEY" 2>/dev/null | \
        jq -r '.data[]? | select(.id == "gpt-4o") | .id' 2>/dev/null || echo "")
    LATEST_GPT4O_MINI=$(curl -s "https://api.openai.com/v1/models" -H "Authorization: Bearer $OPENAI_API_KEY" 2>/dev/null | \
        jq -r '.data[]? | select(.id == "gpt-4o-mini") | .id' 2>/dev/null || echo "")

    if [ -n "$LATEST_GPT4O" ] && [ -n "$LATEST_GPT4O_MINI" ]; then
        print_pass "OpenAI models current: gpt-4o, gpt-4o-mini (2024)"
    else
        print_warn "Could not verify OpenAI model currency"
    fi
fi

# Check Anthropic model
if [ -n "$ANTHROPIC_API_KEY" ]; then
    ANTHROPIC_MODEL=$(curl -s "https://api.anthropic.com/v1/messages" \
        -H "x-api-key: $ANTHROPIC_API_KEY" \
        -H "anthropic-version: 2023-06-01" \
        -H "Content-Type: application/json" \
        -d '{"model":"claude-3-5-sonnet-20241022","max_tokens":5,"messages":[{"role":"user","content":"test"}]}' 2>/dev/null | \
        jq -r '.model // empty' 2>/dev/null)

    if [ "$ANTHROPIC_MODEL" == "claude-3-5-sonnet-20241022" ]; then
        print_pass "Anthropic model current: claude-3-5-sonnet-20241022 (Oct 2024)"
    else
        print_warn "Anthropic model version could not be verified"
    fi
fi

# Check Groq models
if [ -n "$GROQ_API_KEY" ]; then
    GROQ_LLAMA=$(curl -s "https://api.groq.com/openai/v1/models" -H "Authorization: Bearer $GROQ_API_KEY" 2>/dev/null | \
        jq -r '.data[]? | select(.id == "llama-3.3-70b-versatile") | .id' 2>/dev/null || echo "")

    if [ -n "$GROQ_LLAMA" ]; then
        print_pass "Groq model current: llama-3.3-70b-versatile (2024)"
    else
        print_warn "Could not verify Groq model currency"
    fi
fi

# Note about Google
if [ -n "$GOOGLE_API_KEY" ]; then
    print_warn "Google Gemini models: Manual verification recommended (API restrictions)"
    echo "       Visit: https://ai.google.dev/gemini-api/docs/models/gemini"
fi

# Pricing verification
print_test "Verifying budget-friendly model pricing (as of Jan 2025)..."
echo ""
echo "  Expected pricing (per 1M tokens):"
for model_info in "${EXPECTED_MODELS[@]}"; do
    IFS=: read -r MODEL PROVIDER INPUT OUTPUT <<< "$model_info"
    echo "    • $MODEL ($PROVIDER): \$${INPUT} input / \$${OUTPUT} output"
done

print_warn "Verify pricing at provider websites before heavy usage"

# Check for outdated models in config
print_test "Checking for outdated/expensive models in docker-compose..."
OUTDATED_FOUND=0
for model in "${OUTDATED_MODELS[@]}"; do
    if grep -q "$model" docker-compose.yml 2>/dev/null; then
        print_warn "Found outdated model in config: $model"
        ((OUTDATED_FOUND++))
    fi
done

if [ $OUTDATED_FOUND -eq 0 ]; then
    print_pass "No outdated models found in configuration"
fi

# LiteLLM check
print_test "Checking LiteLLM proxy status..."
LITELLM_STATUS=$(docker-compose ps --format json | jq -r 'select(.Service=="litellm") | .State' 2>/dev/null || echo "not_found")
if [ "$LITELLM_STATUS" == "running" ]; then
    LITELLM_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:4000/health 2>/dev/null || echo "000")
    if [ "$LITELLM_RESPONSE" == "200" ]; then
        print_pass "LiteLLM proxy running (unified API available)"
        print_warn "Currently using direct API connections. Consider migrating to LiteLLM for unified interface."
    else
        print_warn "LiteLLM running but not responding (HTTP $LITELLM_RESPONSE)"
    fi
else
    print_warn "LiteLLM not running (state: $LITELLM_STATUS). Consider enabling for unified API."
fi

# Summary
print_header "Test Summary"

TOTAL=$((PASSED + FAILED + WARNINGS))
echo -e "${GREEN}Passed:   $PASSED${NC}"
echo -e "${RED}Failed:   $FAILED${NC}"
echo -e "${YELLOW}Warnings: $WARNINGS${NC}"
echo -e "Total:    $TOTAL"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ All critical tests passed!${NC}"
    echo ""
    echo "GTD Stack is ready for use:"
    echo "  • OpenWebUI: http://localhost:8080"
    echo "  • Workspace: ~/ai-workspace"
    echo "  • Tools: Filesystem, Git, Todoist, CalDAV"
    exit 0
else
    echo -e "${RED}❌ Some tests failed. Please review errors above.${NC}"
    exit 1
fi
