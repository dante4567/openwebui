#!/bin/bash

# Tool Integration Testing Script
#
# WHAT THIS TESTS:
# - OpenWebUI can reach tool servers via Docker network
# - OpenAPI schemas are valid and accessible
# - Tools are registered in OpenWebUI database
# - Tool endpoints return valid data
# - Caching provides performance improvements
#
# WHAT THIS DOES NOT TEST:
# - LLM actually calling tools via function calling
# - OpenWebUI → LiteLLM → Cloud API → Tool flow
# - Web UI interactions
# - Concurrent requests
#
# This is an INTEGRATION test, not a true E2E test.

set +e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PASSED=0
FAILED=0

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

# Test 1: OpenWebUI can reach tool servers (from inside container)
print_header "Test 1: OpenWebUI → Tool Server Connectivity"

# filesystem/git use /docs, todoist/caldav use /
TOOLS=("filesystem-tool:8000:/docs" "git-tool:8000:/docs" "todoist-tool:8000:/" "caldav-tool:8000:/")
for tool in "${TOOLS[@]}"; do
    IFS=: read -r NAME PORT ENDPOINT <<< "$tool"
    print_test "OpenWebUI → $NAME connectivity..."

    # Test from inside OpenWebUI container
    RESPONSE=$(docker exec openwebui curl -s -o /dev/null -w "%{http_code}" http://$NAME:$PORT$ENDPOINT 2>/dev/null || echo "000")
    if [ "$RESPONSE" == "200" ]; then
        print_pass "OpenWebUI can reach $NAME (HTTP $RESPONSE)"
    else
        print_fail "OpenWebUI cannot reach $NAME (HTTP $RESPONSE)"
    fi
done

# Test 2: OpenWebUI can fetch OpenAPI schemas
print_header "Test 2: OpenAPI Schema Discovery"

for tool in "${TOOLS[@]}"; do
    IFS=: read -r NAME PORT <<< "$tool"
    print_test "Fetching OpenAPI schema from $NAME..."

    SCHEMA=$(docker exec openwebui curl -s http://$NAME:$PORT/openapi.json 2>/dev/null)
    if echo "$SCHEMA" | jq -e '.openapi' >/dev/null 2>&1; then
        VERSION=$(echo "$SCHEMA" | jq -r '.openapi' 2>/dev/null)
        TITLE=$(echo "$SCHEMA" | jq -r '.info.title' 2>/dev/null)
        PATHS_COUNT=$(echo "$SCHEMA" | jq -r '.paths | length' 2>/dev/null)
        print_pass "$NAME schema valid (OpenAPI $VERSION, $PATHS_COUNT endpoints, title: $TITLE)"
    else
        print_fail "$NAME schema invalid or not accessible"
    fi
done

# Test 3: Tool registration in OpenWebUI database
print_header "Test 3: Tool Registration in OpenWebUI Database"

print_test "Checking if tools are registered in OpenWebUI..."

# Copy database from container
docker cp openwebui:/app/backend/data/webui.db /tmp/webui-e2e-test.db 2>/dev/null
if [ $? -eq 0 ]; then
    # Query config table for tool servers
    TOOL_SERVERS=$(sqlite3 /tmp/webui-e2e-test.db "SELECT data FROM config WHERE id=1" 2>/dev/null | jq -r '.tool_server.connections // [] | length' 2>/dev/null || echo "0")

    if [ "$TOOL_SERVERS" -gt 0 ]; then
        print_pass "Found $TOOL_SERVERS tool server(s) registered in OpenWebUI config"

        # List registered tools
        REGISTERED=$(sqlite3 /tmp/webui-e2e-test.db "SELECT data FROM config WHERE id=1" 2>/dev/null | jq -r '.tool_server.connections[] | .name' 2>/dev/null)
        while IFS= read -r name; do
            if [ -n "$name" ]; then
                echo -e "  ${GREEN}→${NC} $name"
            fi
        done <<< "$REGISTERED"
    else
        print_fail "No tool servers registered in OpenWebUI (check Admin Settings → Tools)"
    fi

    # Cleanup
    rm -f /tmp/webui-e2e-test.db
else
    print_fail "Could not access OpenWebUI database"
fi

# Test 4: Tool endpoints work via OpenWebUI container
print_header "Test 4: Tool Functionality (via OpenWebUI network)"

print_test "Testing Todoist tool list tasks..."
TASKS=$(docker exec openwebui curl -s http://todoist-tool:8000/tasks 2>/dev/null)
if echo "$TASKS" | jq -e 'if type=="array" then true else false end' >/dev/null 2>&1; then
    TASK_COUNT=$(echo "$TASKS" | jq 'length' 2>/dev/null)
    print_pass "Todoist tool functional ($TASK_COUNT tasks returned)"
else
    print_fail "Todoist tool not returning valid data"
fi

print_test "Testing CalDAV tool list calendars..."
CALENDARS=$(docker exec openwebui curl -s http://caldav-tool:8000/calendars 2>/dev/null)
if echo "$CALENDARS" | jq -e 'if type=="array" then true else false end' >/dev/null 2>&1; then
    CAL_COUNT=$(echo "$CALENDARS" | jq 'length' 2>/dev/null)
    print_pass "CalDAV tool functional ($CAL_COUNT calendars returned)"
else
    print_fail "CalDAV tool not returning valid data"
fi

print_test "Testing Filesystem tool list workspace..."
FS_LIST=$(docker exec openwebui curl -s -X POST http://filesystem-tool:8000/list_directory \
    -H "Content-Type: application/json" \
    -d '{"path":"/workspace"}' 2>/dev/null)
if echo "$FS_LIST" | jq -e 'if type=="array" then true else false end' >/dev/null 2>&1; then
    FILE_COUNT=$(echo "$FS_LIST" | jq 'length' 2>/dev/null)
    print_pass "Filesystem tool functional ($FILE_COUNT items in workspace)"
else
    print_fail "Filesystem tool not returning valid data"
fi

print_test "Testing Git tool log..."
GIT_LOG=$(docker exec openwebui curl -s -X POST http://git-tool:8000/log \
    -H "Content-Type: application/json" \
    -d '{"repo_path":"/workspace","limit":1}' 2>/dev/null)
if echo "$GIT_LOG" | jq -e '.commits' >/dev/null 2>&1; then
    COMMIT_COUNT=$(echo "$GIT_LOG" | jq -r '.commits | length' 2>/dev/null)
    print_pass "Git tool functional ($COMMIT_COUNT commits returned)"
else
    print_fail "Git tool not returning valid data"
fi

# Test 5: Enhanced health checks
print_header "Test 5: Enhanced Health Check Endpoints"

print_test "Testing Todoist enhanced health check..."
TODOIST_HEALTH=$(docker exec openwebui curl -s http://todoist-tool:8000/health 2>/dev/null)
if echo "$TODOIST_HEALTH" | jq -e '.todoist_api.status' >/dev/null 2>&1; then
    API_STATUS=$(echo "$TODOIST_HEALTH" | jq -r '.todoist_api.status' 2>/dev/null)
    LATENCY=$(echo "$TODOIST_HEALTH" | jq -r '.todoist_api.latency_ms' 2>/dev/null)
    CACHE_ENTRIES=$(echo "$TODOIST_HEALTH" | jq -r '.cache.entries' 2>/dev/null)
    print_pass "Todoist health check: $API_STATUS (latency: ${LATENCY}ms, cache: $CACHE_ENTRIES entries)"
else
    print_fail "Todoist enhanced health check not working"
fi

print_test "Testing CalDAV enhanced health check..."
CALDAV_HEALTH=$(docker exec openwebui curl -s http://caldav-tool:8000/health 2>/dev/null)
if echo "$CALDAV_HEALTH" | jq -e '.caldav.status' >/dev/null 2>&1; then
    API_STATUS=$(echo "$CALDAV_HEALTH" | jq -r '.caldav.status' 2>/dev/null)
    LATENCY=$(echo "$CALDAV_HEALTH" | jq -r '.caldav.latency_ms' 2>/dev/null)
    CAL_COUNT=$(echo "$CALDAV_HEALTH" | jq -r '.caldav.calendar_count' 2>/dev/null)
    CACHE_ENTRIES=$(echo "$CALDAV_HEALTH" | jq -r '.cache.entries' 2>/dev/null)
    print_pass "CalDAV health check: $API_STATUS (latency: ${LATENCY}ms, calendars: $CAL_COUNT, cache: $CACHE_ENTRIES entries)"
else
    print_fail "CalDAV enhanced health check not working"
fi

# Test 6: Tool caching behavior
print_header "Test 6: Tool Caching Performance"

print_test "Testing Todoist tool caching (first request)..."
START1=$(date +%s%N)
docker exec openwebui curl -s "http://todoist-tool:8000/tasks?limit=10" >/dev/null 2>&1
END1=$(date +%s%N)
LATENCY1=$(( (END1 - START1) / 1000000 ))  # Convert to ms

print_test "Testing Todoist tool caching (second request - should be cached)..."
START2=$(date +%s%N)
docker exec openwebui curl -s "http://todoist-tool:8000/tasks?limit=10" >/dev/null 2>&1
END2=$(date +%s%N)
LATENCY2=$(( (END2 - START2) / 1000000 ))  # Convert to ms

if [ "$LATENCY2" -lt "$((LATENCY1 / 2))" ]; then
    SPEEDUP=$(( LATENCY1 / LATENCY2 ))
    print_pass "Caching working! Second request ${SPEEDUP}x faster (${LATENCY1}ms → ${LATENCY2}ms)"
else
    print_fail "Caching may not be working (${LATENCY1}ms → ${LATENCY2}ms, expected 2x+ speedup)"
fi

# Summary
print_header "Test Summary"
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ All E2E tests passed!${NC}"
    exit 0
else
    echo -e "${RED}❌ Some E2E tests failed${NC}"
    exit 1
fi
