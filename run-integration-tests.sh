#!/bin/bash

# OpenWebUI Integration Test Runner
# Tests database schema, configuration, and API endpoints

set -e

echo "======================================"
echo "OpenWebUI Integration Tests"
echo "======================================"
echo ""

# Check if virtual environment exists
if [ ! -d "tests/integration/.venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv tests/integration/.venv
    source tests/integration/.venv/bin/activate
    pip install -q -r tests/integration/requirements.txt
    echo "✅ Virtual environment created"
else
    source tests/integration/.venv/bin/activate
fi

echo "Running integration tests..."
echo ""

# Run pytest with compact output
pytest tests/integration/test_openwebui_api.py -q --tb=line

echo ""
echo "======================================"
echo "✅ Integration tests completed"
echo "======================================"
