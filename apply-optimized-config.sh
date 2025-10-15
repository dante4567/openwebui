#!/bin/bash
# Apply optimized config to OpenWebUI
# This sets budget-friendly defaults: gpt-4o-mini, only working models, etc.

set -e

echo "============================================"
echo "Applying Optimized Budget Configuration"
echo "============================================"
echo

if [ ! -f "config-OPTIMIZED-BUDGET.json" ]; then
    echo "❌ config-OPTIMIZED-BUDGET.json not found"
    echo "   Run this script from the repo root directory"
    exit 1
fi

echo "📋 Configuration changes:"
echo "  • default_models: gpt-4o-mini (budget-friendly)"
echo "  • model_filter_list: 11 working models only"
echo "  • Removed: gpt-5, gpt-5-mini, claude-opus-4-1 (not in LiteLLM)"
echo "  • embedding_model: text-embedding-3-small"
echo "  • enable_signup: false"
echo

read -p "Apply this configuration? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

echo
echo "🔄 Copying config to container..."
docker cp config-OPTIMIZED-BUDGET.json openwebui:/tmp/config.json

echo "💾 Updating database..."
docker exec openwebui python3 << 'PYEOF'
import json
import sqlite3

# Load config
with open('/tmp/config.json', 'r') as f:
    config = json.load(f)

# Update database
conn = sqlite3.connect('/app/backend/data/webui.db')
conn.execute('UPDATE config SET data=? WHERE id=1', (json.dumps(config),))
conn.commit()
conn.close()

print("✅ Database updated successfully")
PYEOF

echo "🔄 Restarting OpenWebUI..."
docker-compose restart openwebui

echo
echo "✅ Configuration applied!"
echo
echo "Changes:"
echo "  • Default model is now: gpt-4o-mini"
echo "  • Only 11 working models visible in GUI"
echo "  • Budget-optimized for $30/month (~2100 sessions)"
echo
echo "🌐 OpenWebUI will be ready in ~10 seconds:"
echo "   http://localhost:8080"
echo
