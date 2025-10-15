#!/bin/bash
# Apply GTD Enhancements to OpenWebUI
# This script:
# 1. Adds 6 GTD-specific prompts
# 2. Updates config to budget-friendly defaults
# 3. Shows before/after comparison

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "============================================"
echo "Apply GTD Enhancements to OpenWebUI"
echo "============================================"
echo

# Check if OpenWebUI container is running
if ! docker ps --format '{{.Names}}' | grep -q "openwebui"; then
    echo "❌ OpenWebUI container not running"
    echo "   Start it with: docker-compose up -d"
    exit 1
fi

# Check if required files exist
if [ ! -f "$SCRIPT_DIR/gtd-prompts.sql" ]; then
    echo "❌ gtd-prompts.sql not found"
    exit 1
fi

if [ ! -f "/tmp/config-GTD-OPTIMIZED.json" ]; then
    echo "❌ /tmp/config-GTD-OPTIMIZED.json not found"
    echo "   Run this from the repo root: cd $SCRIPT_DIR && ./apply-gtd-enhancements.sh"
    exit 1
fi

echo "📋 Changes to be applied:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo
echo "✨ NEW GTD PROMPTS (6 total):"
echo "  1. /weeklyreview  - GTD Weekly Review assistant"
echo "  2. /projectplan   - Project Planning with next actions"
echo "  3. /capture       - Quick Capture inbox processing"
echo "  4. /dailygtd      - Daily Standup with context"
echo "  5. /context       - Context-based task filtering"
echo "  6. /twominute     - 2-Minute Rule quick wins"
echo
echo "🔧 CONFIG CHANGES:"
echo "  • Default model: claude-sonnet-4-5 → gpt-4o-mini (\$0.014/session vs \$0.15)"
echo "  • Model list: Removed fake models (gpt-5, claude-opus-4-1, gemini-2.5-flash-lite)"
echo "  • Model list: Added real models (gpt-4.1-mini, llama-3.3-70b, gemini-2.0-flash)"
echo "  • Image generation: Disabled (not needed for GTD)"
echo "  • Signup: Already disabled ✅"
echo "  • Notes: Already enabled ✅"
echo
echo "🛠️  DOCKER CHANGES (manual restart required):"
echo "  • ENABLE_SIGNUP: true → false (security)"
echo "  • Weather tool: Uncommented (useful for scheduling)"
echo
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo

read -p "Apply these changes? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

echo
echo "🔄 Step 1: Backing up current config..."
docker exec openwebui python3 -c "
import sqlite3, json
conn = sqlite3.connect('/app/backend/data/webui.db')
cursor = conn.cursor()
cursor.execute('SELECT data FROM config WHERE id=1')
config = json.loads(cursor.fetchone()[0])
print(json.dumps(config, indent=2))
" > /tmp/config-backup-$(date +%Y%m%d-%H%M%S).json
echo "✅ Backup saved to /tmp/config-backup-*.json"

echo
echo "🔄 Step 2: Adding GTD prompts to database..."
docker cp "$SCRIPT_DIR/gtd-prompts.sql" openwebui:/tmp/gtd-prompts.sql
docker exec openwebui sqlite3 /app/backend/data/webui.db < /tmp/gtd-prompts.sql
echo "✅ 6 GTD prompts added"

echo
echo "🔄 Step 3: Applying optimized config..."
docker cp /tmp/config-GTD-OPTIMIZED.json openwebui:/tmp/config-optimized.json
docker exec openwebui python3 << 'PYEOF'
import json
import sqlite3

# Load optimized config
with open('/tmp/config-optimized.json', 'r') as f:
    config = json.load(f)

# Update database
conn = sqlite3.connect('/app/backend/data/webui.db')
conn.execute('UPDATE config SET data=? WHERE id=1', (json.dumps(config),))
conn.commit()
conn.close()

print("✅ Config updated successfully")
PYEOF

echo
echo "🔄 Step 4: Restarting OpenWebUI to apply changes..."
docker-compose restart openwebui

echo
echo "⏳ Waiting for OpenWebUI to start (15 seconds)..."
sleep 15

echo
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ GTD Enhancements Applied Successfully!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo
echo "📝 WHAT CHANGED:"
echo
echo "1. NEW PROMPTS (Use in Chat):"
echo "   Type these commands in any chat:"
echo "   • /weeklyreview  - Conduct GTD weekly review"
echo "   • /projectplan   - Plan projects with next actions"
echo "   • /capture       - Quick capture inbox items"
echo "   • /dailygtd      - Generate daily plan"
echo "   • /context       - Filter tasks by context"
echo "   • /twominute     - Find quick wins (≤2min tasks)"
echo
echo "2. BUDGET-OPTIMIZED DEFAULT:"
echo "   • New chats default to gpt-4o-mini (\$0.014/session)"
echo "   • Previous: claude-sonnet-4-5 (\$0.15/session)"
echo "   • Monthly savings: ~\$10-15 if used as primary model"
echo
echo "3. MODEL LIST CLEANED:"
echo "   • Removed 5 fake/non-existent models"
echo "   • Added 3 real models (gpt-4.1-mini, llama-3.3-70b, gemini-2.0-flash)"
echo "   • Total: 11 working models"
echo
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo
echo "🚀 NEXT STEPS:"
echo
echo "1. REBUILD STACK (for docker-compose changes):"
echo "   cd $SCRIPT_DIR"
echo "   docker-compose up -d --build"
echo "   # This will:"
echo "   #  - Build weather-tool container"
echo "   #  - Apply ENABLE_SIGNUP=false"
echo
echo "2. VERIFY CHANGES:"
echo "   - Open http://localhost:8080"
echo "   - Start a new chat"
echo "   - Type /weeklyreview (should see GTD Weekly Review prompt)"
echo "   - Check model list (should show gpt-4o-mini as default)"
echo
echo "3. REGISTER WEATHER TOOL:"
echo "   - Settings → Admin → Tools → Add Tool Server"
echo "   - URL: http://weather-tool:8000"
echo "   - Type: OpenAPI"
echo "   - Save"
echo
echo "4. MONITOR COSTS:"
echo "   ./check-llm-costs.sh"
echo
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo
echo "📖 DOCUMENTATION:"
echo "   - GTD prompts: gtd-prompts.sql (can edit and re-apply)"
echo "   - Config backup: /tmp/config-backup-*.json"
echo "   - Cost monitoring: ./check-llm-costs.sh"
echo
echo "💡 TIP: Use /capture to quickly process inbox items into Todoist!"
echo
