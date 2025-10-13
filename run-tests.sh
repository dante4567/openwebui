#!/bin/bash
# Run unit tests for GTD tool servers
#
# Usage:
#   ./run-tests.sh          # Run all tests
#   ./run-tests.sh todoist  # Run only todoist-tool tests
#   ./run-tests.sh caldav   # Run only caldav-tool tests

set -e  # Exit on error

echo "======================================"
echo "GTD Tool Servers - Unit Test Runner"
echo "======================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to run tests for a tool
run_tool_tests() {
    local tool=$1
    echo ""
    echo -e "${YELLOW}Testing: $tool${NC}"
    echo "--------------------------------------"

    cd "$tool"

    # Install test dependencies if needed
    if [ ! -d ".venv-test" ]; then
        echo "Creating test virtual environment..."
        python3 -m venv .venv-test
        source .venv-test/bin/activate
        pip install -q --upgrade pip
        pip install -q -r requirements-test.txt
        # Install production dependencies too
        pip install -q fastapi uvicorn requests python-dotenv
        if [ "$tool" = "caldav-tool" ]; then
            pip install -q caldav vobject
        fi
    else
        source .venv-test/bin/activate
    fi

    # Run tests with coverage
    pytest tests/ -v --cov=. --cov-report=term-missing --cov-report=html

    local exit_code=$?
    deactivate
    cd ..

    if [ $exit_code -eq 0 ]; then
        echo -e "${GREEN}✅ $tool tests passed${NC}"
    else
        echo -e "${RED}❌ $tool tests failed${NC}"
        return $exit_code
    fi
}

# Main logic
if [ "$1" = "todoist" ]; then
    run_tool_tests "todoist-tool"
elif [ "$1" = "caldav" ]; then
    run_tool_tests "caldav-tool"
else
    # Run all tests
    run_tool_tests "todoist-tool"
    run_tool_tests "caldav-tool"
fi

echo ""
echo "======================================"
echo -e "${GREEN}All tests completed!${NC}"
echo "======================================"
echo ""
echo "Coverage reports generated in:"
echo "  - todoist-tool/htmlcov/index.html"
echo "  - caldav-tool/htmlcov/index.html"
