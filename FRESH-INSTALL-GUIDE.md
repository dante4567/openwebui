# Fresh Install Guide - OpenWebUI GTD Stack

**Time required:** 5-10 minutes
**Prerequisites:** Docker Desktop installed and running

---

## What You Need (Files)

### Required Files (in this repo):
```
.
├── docker-compose.yml           # Main stack definition (10 containers)
├── litellm_config.yaml          # LLM model routing config
├── .env.example                 # Template for API keys
├── Dockerfile.todoist           # Todoist tool server
├── Dockerfile.caldav            # CalDAV tool server
├── Dockerfile.filesystem        # Filesystem tool server
├── Dockerfile.git               # Git tool server
├── todoist-tool/                # Todoist tool code
│   ├── main.py
│   └── requirements.txt
├── caldav-tool/                 # CalDAV tool code
│   ├── main.py
│   └── requirements.txt
└── config-OPTIMIZED-BUDGET.json # Optional: Pre-configured settings
```

### API Keys You'll Need:

**Minimum (to start):**
- OpenAI API key (for gpt-4o-mini - budget default)
- Todoist API key (for task management)

**Optional (add later):**
- Anthropic API key (for Claude models)
- Google API key (for Gemini models)
- Groq API key (for Llama models - free tier available)
- CalDAV credentials (for calendar/contacts)

---

## Fresh Install Steps

### Step 1: Get the Files

```bash
# Option A: Clone the repo (if you have it on GitHub)
git clone <your-repo-url>
cd openwebui

# Option B: Copy files to new machine
# Use rsync, scp, or cloud storage to copy the entire directory
```

### Step 2: Create `.env` File with API Keys

```bash
# Copy the example
cp .env.example .env

# Edit with your favorite editor
nano .env  # or vim, code, etc.
```

**Minimal `.env` file:**
```bash
# Required
WEBUI_SECRET_KEY=<generate with: openssl rand -hex 32>
OPENAI_API_KEY=sk-proj-...your-key...

# Todoist (for task management)
TODOIST_API_KEY=your-todoist-key-here

# Optional - add if you have them
ANTHROPIC_API_KEY=your-key-here
GOOGLE_API_KEY=your-key-here
GROQ_API_KEY=your-key-here

# CalDAV (optional - for calendar/contacts)
CALDAV_URL=https://caldav.example.com
CALDAV_USERNAME=your-username
CALDAV_PASSWORD=your-password
```

**Get API keys:**
- OpenAI: https://platform.openai.com/api-keys
- Todoist: https://todoist.com/prefs/integrations/developer
- Anthropic: https://console.anthropic.com/
- Google: https://ai.google.dev/
- Groq: https://console.groq.com/

### Step 3: Create Workspace Directory

```bash
# Create directory for LLM file operations
mkdir -p ~/ai-workspace

# Initialize as git repo (optional but recommended)
cd ~/ai-workspace
git init
echo "# AI Workspace" > README.md
git add README.md
git commit -m "Initial commit"
cd -
```

### Step 4: Start the Stack

```bash
# From the repo directory
docker-compose up -d

# Wait ~30 seconds for everything to start
# Watch logs if you want:
docker-compose logs -f
```

This will:
- Pull Docker images (~2GB download first time)
- Build tool servers (todoist, caldav, filesystem, git)
- Start 10 containers
- Initialize databases

### Step 5A: Quick Setup (Using Pre-configured Settings)

**Recommended for fresh installs:**

```bash
# Wait for OpenWebUI to be ready
sleep 30

# Create first admin account via GUI
open http://localhost:8080
# Sign up with email/password (first user = admin)

# Apply optimized config (sets gpt-4o-mini default, clean model list)
./apply-optimized-config.sh

# Restart to apply
docker-compose restart openwebui
```

**Done!** You now have:
- Default model: gpt-4o-mini (budget-friendly)
- 11 working models available
- All 4 GTD tools enabled
- Budget optimized for ~70 sessions/day at $30/month

### Step 5B: Manual Setup (If You Want Control)

```bash
# 1. Open OpenWebUI
open http://localhost:8080

# 2. Create admin account
#    First user to sign up = admin automatically

# 3. After login, disable signups
#    Settings → Admin Panel → General → Enable Signup → OFF

# 4. Configure default model
#    Settings → General → Default Model → gpt-4o-mini

# 5. Verify tools are registered
#    Settings → Admin Panel → Tools
#    Should see: filesystem-tool, git-tool, todoist, caldav

# 6. Test a chat
#    Start new chat, ask: "List my Todoist tasks"
```

---

## Verification Checklist

Run the test script to verify everything works:

```bash
./test-gtd-stack.sh
```

**Expected results:**
- ✅ All 10 containers healthy
- ✅ All 4 tool servers responding
- ✅ Todoist API connected (shows task count)
- ✅ CalDAV API connected (shows calendar count)
- ✅ Filesystem operations working
- ✅ Git operations working
- ✅ OpenAI API working (gpt-4o-mini)
- ✅ LiteLLM proxy active

---

## What You Get

After installation, you have:

**OpenWebUI Interface:** http://localhost:8080
- Multi-LLM chat (OpenAI, Anthropic, Google, Groq)
- Function calling / agentic capabilities
- TTS/STT (voice input/output)
- Web search (SearXNG)
- RAG with ChromaDB

**GTD Tools Available:**
1. **Filesystem Tool** - Read/write files in ~/ai-workspace
2. **Git Tool** - Commit, push, pull in ~/ai-workspace
3. **Todoist Tool** - Manage tasks via Todoist API
4. **CalDAV Tool** - Manage calendar events and contacts

**Budget Controls:**
- Default: gpt-4o-mini ($0.15/$0.60 per 1M tokens)
- LiteLLM caching enabled (saves 50-80% on repeated queries)
- ~2100 sessions/month at $30 budget

---

## File Storage on New Machine

After installation, important data is stored in:

**Docker Volumes (automatic):**
- OpenWebUI database: `openwebui-data` volume
- ChromaDB vectors: `chromadb-data` volume
- Redis cache: `redis-data` volume

**Host Directories:**
- Workspace: `~/ai-workspace` (LLM can read/write here)

**To backup everything:**
```bash
# Export OpenWebUI config (includes all settings)
# Settings → Admin → Database → Export Settings

# Backup volumes
docker run --rm -v openwebui-data:/data -v $(pwd):/backup alpine \
  tar czf /backup/openwebui-backup-$(date +%Y%m%d).tar.gz -C /data .

# Backup workspace
tar czf ai-workspace-backup-$(date +%Y%m%d).tar.gz ~/ai-workspace
```

---

## Troubleshooting Fresh Install

**Port conflicts:**
```bash
# Check if ports are in use
lsof -i :8080  # OpenWebUI
lsof -i :4000  # LiteLLM
lsof -i :3000  # ChromaDB

# Stop conflicting services or change ports in docker-compose.yml
```

**Containers not starting:**
```bash
# Check logs
docker-compose logs openwebui
docker-compose logs todoist-tool

# Check .env file has valid keys
cat .env

# Restart specific service
docker-compose restart openwebui
```

**Tools not working in chat:**
```bash
# Verify tools are registered
docker exec openwebui sqlite3 /app/backend/data/webui.db \
  "SELECT data FROM config WHERE id=1" | \
  python3 -m json.tool | grep -A20 tool_server

# Should show all 4 tools with URLs like http://todoist-tool:8000
```

**"No models available":**
```bash
# Check if LiteLLM is running
curl http://localhost:4000/health

# Check API keys are loaded
docker exec openwebui printenv OPENAI_API_KEY

# Verify models in LiteLLM config
grep "model_name:" litellm_config.yaml
```

---

## Migration to New Machine

**On old machine:**
```bash
# 1. Export config from GUI
#    Settings → Admin → Database → Export Settings → Save as config.json

# 2. Copy files to new machine
rsync -av ~/Documents/my-git/openwebui/ newmachine:~/openwebui/
rsync -av ~/ai-workspace/ newmachine:~/ai-workspace/

# 3. Copy .env separately (it's gitignored)
scp .env newmachine:~/openwebui/.env
```

**On new machine:**
```bash
# 1. Install Docker Desktop

# 2. Run steps 1-4 from Fresh Install

# 3. Import config
docker cp config.json openwebui:/tmp/config.json
docker exec openwebui python3 << 'EOF'
import json, sqlite3
with open('/tmp/config.json') as f:
    config = json.load(f)
conn = sqlite3.connect('/app/backend/data/webui.db')
conn.execute('UPDATE config SET data=? WHERE id=1', (json.dumps(config),))
conn.commit()
EOF

# 4. Restart
docker-compose restart openwebui
```

**Done!** Exact same setup on new machine in ~5 minutes.

---

## Next Steps

1. **Test the GTD workflow:**
   - "Create a file called test.md in workspace with my todo list"
   - "Add a Todoist task: Review this setup"
   - "Commit the file to git with message 'Testing workspace'"

2. **Explore models:**
   - Try gpt-4o-mini (cheap, fast)
   - Try claude-sonnet-4-5 when you need quality
   - Try llama-3.3-70b on Groq (very fast, cheap)

3. **Customize:**
   - Add more prompts (Settings → Workspace → Prompts)
   - Create personas for different tasks
   - Adjust model visibility (Settings → Models)

4. **Monitor costs:**
   - OpenAI: https://platform.openai.com/usage
   - Groq: https://console.groq.com/
   - LiteLLM logs: `docker logs openwebui-litellm | grep -i cost`

---

## Quick Reference Commands

```bash
# Start/stop
docker-compose up -d
docker-compose down

# View logs
docker-compose logs -f openwebui
docker-compose logs -f todoist-tool

# Restart after config changes
docker-compose restart openwebui

# Check status
docker-compose ps
./test-gtd-stack.sh

# Backup
docker exec openwebui sqlite3 /app/backend/data/webui.db ".backup /tmp/backup.db"
docker cp openwebui:/tmp/backup.db ./backup-$(date +%Y%m%d).db

# Update to latest
git pull
docker-compose pull
docker-compose up -d
```

---

**Last Updated:** October 14, 2025
