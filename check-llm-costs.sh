#!/bin/bash
# LLM Cost Monitoring Script for OpenWebUI + LiteLLM
# Analyzes LiteLLM logs to estimate costs and usage

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "============================================"
echo "LLM Cost Analysis - OpenWebUI GTD Stack"
echo "============================================"
echo

# Check if LiteLLM container is running
if ! docker ps --format '{{.Names}}' | grep -q "openwebui-litellm"; then
    echo "❌ LiteLLM container not running"
    echo "   Start it with: docker-compose up -d"
    exit 1
fi

# Function to analyze logs for a time period
analyze_period() {
    local hours=$1
    local label=$2

    echo "=== $label (last $hours hours) ==="

    # Extract cost information from logs
    local logs=$(docker logs openwebui-litellm --since ${hours}h 2>&1 | grep -i "cost=" || true)

    if [ -z "$logs" ]; then
        echo "⚠️  No cost data found in logs for this period"
        echo "   (This is normal if you haven't made any API calls)"
        echo
        return
    fi

    # Count requests
    local request_count=$(echo "$logs" | wc -l)
    echo "📊 Total requests: $request_count"

    # Extract and sum costs (example log: "Model=gpt-4o-mini; cost=5.1e-06")
    # Use awk to parse and sum costs
    local total_cost=$(echo "$logs" | \
        grep -o "cost=[0-9.e+-]*" | \
        cut -d= -f2 | \
        awk '{sum+=$1} END {printf "%.6f", sum}')

    echo "💰 Total cost: \$$total_cost"

    # Calculate average cost per request
    local avg_cost=$(echo "$total_cost $request_count" | awk '{printf "%.6f", $1/$2}')
    echo "📈 Average per request: \$$avg_cost"

    # Extrapolate to monthly if we have data
    if [ "$hours" == "24" ] && [ "$request_count" -gt 0 ]; then
        local monthly=$(echo "$total_cost 30" | awk '{printf "%.2f", $1*$2}')
        echo "🔮 Projected monthly (if today's usage continues): \$$monthly"

        if (( $(echo "$monthly > 30" | bc -l) )); then
            echo "⚠️  WARNING: Projected cost exceeds \$30/month budget!"
        elif (( $(echo "$monthly > 25" | bc -l) )); then
            echo "⚠️  CAUTION: Approaching \$30/month budget"
        else
            echo "✅ On track for budget"
        fi
    fi

    # Model breakdown
    echo
    echo "📋 Usage by model:"
    echo "$logs" | \
        grep -o "Model=[a-zA-Z0-9_.-]*" | \
        sort | uniq -c | sort -rn | \
        awk '{printf "  %3d requests: %s\n", $1, substr($2, 7)}'

    echo
}

# Analyze different time periods
analyze_period 1 "Last Hour"
analyze_period 24 "Last 24 Hours (Today)"
analyze_period 168 "Last 7 Days (This Week)"

# Redis cache effectiveness
echo "=== Redis Cache Status ==="
CACHE_SIZE=$(docker exec openwebui-redis redis-cli DBSIZE 2>/dev/null || echo "0")
echo "📦 Cached items: $CACHE_SIZE"

if [ "$CACHE_SIZE" -gt 0 ]; then
    echo "✅ Cache is working (repeat queries will be free!)"
else
    echo "⚠️  Cache is empty (make some API calls to test)"
fi

echo

# Provider dashboard links
echo "=== Check Provider Dashboards ==="
echo "🔗 OpenAI: https://platform.openai.com/usage"
echo "🔗 Anthropic: https://console.anthropic.com/"
echo "🔗 Google: https://console.cloud.google.com/"
echo "🔗 Groq: https://console.groq.com/"
echo

# Budget recommendations
echo "=== Budget Tips ==="
echo "💡 Default model: gpt-4o-mini (\$0.014/session) - BEST BUDGET"
echo "💡 Cheapest: llama-3.1-8b-instant (\$0.003/session) - 5x cheaper!"
echo "💡 Avoid: claude-sonnet-4-5 (\$0.15/session) - 10x more expensive"
echo "💡 Avoid: gemini-2.5-flash (\$0.04/session) - Use gemini-2.0-flash instead"
echo

# LiteLLM verbose logs (optional - shows detailed breakdown)
echo "=== Recent LiteLLM Activity (last 10 requests) ==="
docker logs openwebui-litellm --tail 100 2>&1 | \
    grep -E "Model=|Tokens=" | tail -10

echo
echo "✅ Cost analysis complete!"
echo
echo "Run this script:"
echo "  - Daily: Monitor spending"
echo "  - Weekly: Review model usage patterns"
echo "  - Before month-end: Ensure under \$30 budget"
