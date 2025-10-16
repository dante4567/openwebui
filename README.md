# OpenWebUI Task/Calendar Management Stack

**OpenWebUI setup with tool servers for AI-assisted task and calendar management**

**⚠️ HONEST DISCLAIMER:**
- **Target use case**: Single-user local development
- **NOT production-ready**: No authentication, rate limiting, or monitoring
- **NOT minimal**: 10 containers (OpenWebUI + ChromaDB + LiteLLM + Redis + SearXNG + Tika + 4 tool servers)
- **NOT a complete GTD system**: Has tools that CAN support GTD, but no workflow automation
- **Security**: Use only on trusted local network, do NOT expose to internet

**📖 Read [HONEST-STATUS.md](HONEST-STATUS.md) for detailed no-BS assessment of what actually works vs what's theoretical.**

## Why This Setup?

This configuration is designed for **practical AI workflows** where you need the LLM to:
- ✅ **Read/analyze your documents** (RAG with local files)
- ✅ **Take actions** (file operations, git commits, API calls)
- ✅ **Remember context** (persistent memory across sessions)
- ✅ **Use multiple modalities** (voice input/output, image generation)

**What makes this different from ChatGPT/Claude web:**
- You control the data (local ChromaDB, no vendor lock-in)
- LLM can access your filesystem and git repos
- All conversations + documents stay on your machine
- Mix multiple LLM providers (use Groq for speed, GPT-4 for quality, Claude for writing)
- Extensible via tool servers (add any API/function)

## Use Cases This Setup Excels At

### ✅ Great For:
1. **Document Research & Analysis**
   - Drop PDFs into `~/input-rag/`, ask questions across all docs
   - Example: "Summarize all meeting notes from last quarter"

2. **Code Projects with Context**
   - LLM can read your codebase, make changes, commit to git
   - Example: "Refactor this function and commit with a descriptive message"

3. **Personal Knowledge Base**
   - Upload notes, research, articles → persistent RAG
   - Memory tool remembers entities/relations across chats

4. **Multi-step Workflows**
   - Combine tools: "Read requirements.txt, check outdated packages, update them, test, commit"
   - Weather + calendar: "Should I reschedule my outdoor meeting tomorrow?"

5. **Voice-First Workflows**
   - STT + TTS for hands-free operation
   - Example: Dictate notes → LLM organizes → saves to files

### ⚠️ Not Ideal For:
1. **Mobile access** - Desktop/laptop only (unless you set up VPN)
2. **Team collaboration** - Single user focus (no multi-user auth built-in)
3. **Real-time data** - Tool servers add latency vs. native integrations
4. **Production applications** - Great for personal use, needs hardening for production

## What's Included

This stack provides a complete "agentic" AI setup:
- ✅ **OpenWebUI** - AI chat interface with function calling
- ✅ **ChromaDB** - Vector database for RAG (document Q&A)
- ✅ **Cloud LLMs** - OpenAI, Groq, Anthropic, Google (primary)
- ✅ **Tool Servers** - OpenAPI tool servers for agentic workflows:
  - **Weather** - Real-time forecasts (Open-Meteo API)
  - **Filesystem** - Read/write files in `~/input-rag` directory
  - **Git** - Repository operations (clone, commit, push, pull)
  - **Memory** - Knowledge graph for persistent context (entities, relations, observations)
- ✅ **Extended Services** (New!):
  - **Pipelines** - OpenWebUI's native extension framework (modify LLM requests/responses)
  - **SearXNG** - Self-hosted metasearch (Google+Bing+DDG, no API keys, no rate limits)
  - **Apache Tika** - Advanced document parsing with OCR (100+ formats, scanned PDFs)
  - **LiteLLM** - Unified LLM gateway (caching, cost tracking, fallbacks)
  - **Redis** - Response caching for LiteLLM (save API costs)
- ✅ **Pre-configured Features**:
  - Text-to-Speech (OpenAI TTS, voice: alloy)
  - Speech-to-Text (OpenAI Whisper)
  - Image Generation (DALL-E 3)
  - Code Execution (Pyodide sandbox)
  - Web Search (SearXNG self-hosted)
  - Personas & Custom Functions

## Exporting Your Configuration (For Backup/Transfer)

Once you've set up OpenWebUI the way you like it, export your configuration:

### 1. Export via GUI
```bash
# In OpenWebUI:
# 1. Go to: Admin Panel → Settings → General
# 2. Scroll down to "Import/Export Settings"
# 3. Click: "Export Settings" button
# 4. Save JSON file
```

### 2. Store Securely
```bash
# Store in password manager (Bitwarden, 1Password, etc.)
# DO NOT commit to git - contains API keys!
```

### 3. Use on New Machine
```bash
# Copy config to new machine
# Run import commands from "Method 2" above
```

**Pro tip:** Keep both in your password manager:
- **`.env`** file (as secure note) - for environment variables
- **`config.json`** (as secure note) - for OpenWebUI settings

This way you can spin up a fully-configured OpenWebUI on any machine in 2 minutes!

---

## Quick Start (5 Minutes)

### Method 1: Fresh Setup (Recommended)

```bash
# 1. Clone this repo
git clone <your-repo-url>
cd openwebui

# 2. Setup environment
cp .env.example .env
# Edit .env and add your API keys (at least WEBUI_SECRET_KEY + one LLM key)

# 3. Create data directory for RAG
mkdir -p ~/input-rag

# 4. Start the stack
docker-compose up -d

# 5. Wait ~30 seconds, then access
open http://localhost:8080

# 6. Create admin account (first user = admin)
```

**That's it!** You now have OpenWebUI with TTS, STT, image generation, RAG, and 4 tool servers running.

### Method 2: Import Pre-Configured Settings (Fast Setup)

If you have a saved config from a previous setup:

```bash
# 1-4. Same as Method 1 above

# 5. Copy your config JSON from secure storage (Bitwarden, 1Password, etc.)
# Replace YOUR_*_API_KEY placeholders with real keys
cp config.example.json config.json
# Edit config.json with real API keys

# 6. Import configuration
docker cp config.json openwebui:/tmp/config.json
docker exec openwebui python3 -c "$(cat import_config_v2.py)"

# 7. Restart to apply
docker-compose restart openwebui

# 8. Access and login
open http://localhost:8080
```

**What gets imported:**
- ✅ All API keys (OpenAI, Groq, Anthropic, Google)
- ✅ Tool server connections (weather, filesystem, git, memory)
- ✅ RAG settings (chunk size, embedding model, top-k)
- ✅ TTS/STT configuration
- ✅ Image generation settings
- ✅ Web search configuration
- ✅ UI preferences (signup disabled, message rating enabled)

### 3. Access OpenWebUI

Open http://localhost:8080

**First-time setup:**
1. Create admin account (first user = admin)
2. Place documents in `~/input-rag/` for RAG
3. Start chatting with agentic features!

---

## GUI Configuration Guide

### Required (5 minutes)

#### 1. Create Admin Account
- **URL**: http://localhost:8080
- **Action**: Fill signup form (first user = admin automatically)
- **Save**: Username + password securely!

#### 2. Verify Connections
- **Go to**: Profile Icon → Admin Panel → Settings → Connections
- **Check**:
  - ✅ Ollama: Connected (green)
  - ✅ OpenAI: API key loaded
  - ✅ Other APIs: Keys loaded from .env

#### 3. Verify ChromaDB
- **Go to**: Admin Panel → Settings → Documents
- **Check**:
  - ✅ ChromaDB: Connected
  - ✅ Embedding model: nomic-embed-text

### Optional (Configure as needed)

#### Model Visibility
- **Go to**: Admin Panel → Settings → Models
- **Configure**: Which models appear in chat dropdown
- **Recommendation**:
  - Enable: Groq models (fast, free)
  - Enable: GPT-4o-mini (fast, cheap)
  - Enable: Claude (excellent writing)
  - Enable: Ollama models you pulled

#### Personas
- **Go to**: Workspace → Personas
- **Create**: Custom AI personas
- **Examples**:
  - "Python Expert" - for coding help
  - "Academic Writer" - for research papers
  - "Data Analyst" - for data questions

#### Functions/Tools (Agentic Capabilities)
- **Go to**: Admin Panel → Settings → Functions
- **Built-in tools** (already available):
  - Code execution
  - Web browsing (if enabled)
  - Image generation (if enabled)

- **Custom tools** (you can create):
  - **Filesystem access**: Read/write files
  - **Git operations**: Commit, push, pull
  - **Todoist integration**: Create/manage tasks
  - **CalDAV**: Calendar management
  - **Custom APIs**: Any REST API

**To create custom function:**
1. Click "+" → "Create Function"
2. Define function name, description, parameters
3. Write Python code or API call
4. Test and enable

**Example Function** (Todoist task creator):
```python
# Name: create_todoist_task
# Description: Creates a task in Todoist

import requests
import os

def create_task(content: str, project: str = "Inbox"):
    api_key = os.environ.get("TODOIST_API_KEY")
    url = "https://api.todoist.com/rest/v2/tasks"
    headers = {"Authorization": f"Bearer {api_key}"}
    data = {"content": content, "project_id": project}

    response = requests.post(url, headers=headers, json=data)
    return response.json()
```

#### System Prompts (Optional)
- **Go to**: Admin Panel → Workspace → Prompts
- **Create**: Reusable system prompts
- **Examples**:
  - "Code Helper" - Always output clean, documented code
  - "Academic Tone" - Formal academic writing style
  - "Concise Responses" - Keep answers brief

#### Tool Servers (OpenAPI Integration)
- **Go to**: Admin Panel → Settings → Tools
- **What it does**: Connect external tool servers to extend LLM capabilities

**Included Tool: Weather Server**
- **URL**: http://weather-tool:8000 (internal) or http://localhost:8001 (external)
- **Provider**: Open-Meteo API (free, no key required)
- **Capabilities**: Get weather forecast by location (lat/lon)
- **OpenAPI Docs**: http://localhost:8001/docs

**To add weather tool:**
1. Go to: Admin Panel → Settings → Tools
2. Click: "Add Tool Server"
3. Enter: `http://weather-tool:8000`
4. Save and test

**To add more tool servers** (from [openapi-servers repo](https://github.com/open-webui/openapi-servers)):
1. Add service to `docker-compose.yml` (similar to weather-tool)
2. Configure in OpenWebUI Tools settings
3. Available tools: Filesystem, Git, Web scraping, Database queries, etc.

---

## Configuration Overview

### What's in docker-compose.yml
```yaml
✅ Service definitions (Ollama, ChromaDB, OpenWebUI)
✅ Network configuration
✅ Volume mounts
✅ Health checks
✅ Feature flags (code execution, memory, functions enabled)
✅ Default settings (chunk size, top-k, etc.)
```

### What's in .env
```bash
✅ WEBUI_SECRET_KEY (security)
✅ API keys (OpenAI, Groq, Anthropic, Google, Todoist)
✅ Optional integrations (web search, image gen)
```

### What's in GUI (one-time)
```
✅ Admin account
✅ Model visibility
✅ Personas (optional)
✅ Custom functions/tools (optional)
✅ System prompts (optional)
✅ User preferences (theme, etc.)
```

---

## Architecture

### How It Works

```
┌─────────────────────────────────────────┐
│  OpenWebUI (Port 8080)                  │
│  - User interface                       │
│  - Manages conversations                │
│  - Executes functions/tools             │
└───────┬─────────────────────────────────┘
        │
        ├──→ Cloud LLMs (Primary)
        │    ├── Groq (fast, free)
        │    ├── OpenAI (GPT-4, GPT-3.5)
        │    ├── Anthropic (Claude)
        │    └── Google (Gemini)
        │
        ├──→ Ollama (Fallback)
        │    ├── llama3.2:1b (chat)
        │    └── nomic-embed-text (embeddings)
        │
        ├──→ ChromaDB (RAG + Memory)
        │    └── Vector storage for documents
        │
        └──→ Tool Servers (OpenAPI)
             └── Weather Tool (Open-Meteo API)
```

### Resource Usage

| Component | RAM | Disk | Notes |
|-----------|-----|------|-------|
| OpenWebUI | ~500MB | ~200MB | Base application |
| ChromaDB | ~300MB | Variable | +documents size |
| Ollama | ~200MB | ~500MB | Base only |
| Weather Tool | ~50MB | ~20MB | Minimal overhead |
| + nomic-embed-text | ~300MB | ~274MB | When loaded |
| + llama3.2:1b | ~1.3GB | ~1.3GB | When loaded |
| **Total Idle** | **~1.1GB** | **~2.1GB** | Minimal |
| **Total Active** | **~2.4GB** | **~2.1GB** | With models loaded |

---

## Management Commands

### Stack Management
```bash
# Start
docker-compose up -d

# Stop
docker-compose down

# Restart
docker-compose restart

# View logs
docker-compose logs -f
docker-compose logs -f openwebui  # Just OpenWebUI
```

### Model Management
```bash
# List installed models
docker exec openwebui-ollama ollama list

# Pull new model
docker exec openwebui-ollama ollama pull <model-name>

# Remove model
docker exec openwebui-ollama ollama rm <model-name>

# Check model info
docker exec openwebui-ollama ollama show <model-name>
```

### Tool Server Management
```bash
# Check weather tool status
docker ps | grep weather

# View weather tool logs
docker-compose logs -f weather-tool

# Access OpenAPI documentation
open http://localhost:8001/docs

# Test weather tool directly
curl "http://localhost:8001/forecast?latitude=52.52&longitude=13.41"

# Rebuild weather tool (after updates)
docker-compose build weather-tool
docker-compose up -d weather-tool
```

### Data Backup
```bash
# Backup all volumes
docker run --rm \
  -v openwebui-complete_openwebui-data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/openwebui-backup-$(date +%Y%m%d).tar.gz -C /data .

# Backup ChromaDB
docker run --rm \
  -v openwebui-complete_chromadb-data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/chromadb-backup-$(date +%Y%m%d).tar.gz -C /data .

# Backup Ollama models
docker run --rm \
  -v openwebui-complete_ollama-data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/ollama-backup-$(date +%Y%m%d).tar.gz -C /data .
```

---

## Advanced Configuration

### Use External ChromaDB

Edit `docker-compose.yml`:
```yaml
# Comment out internal chromadb service
# services:
#   chromadb:
#     ...

# Update OpenWebUI environment
openwebui:
  environment:
    - CHROMA_HTTP_HOST=external-server.local
    - CHROMA_HTTP_PORT=8000
```

### Connect to Home Network ChromaDB

If you have a ChromaDB server running on your home network:

Edit `docker-compose.yml`:
```yaml
openwebui:
  environment:
    # Replace with your ChromaDB server IP/hostname
    - CHROMA_HTTP_HOST=192.168.1.100  # or chromadb.local
    - CHROMA_HTTP_PORT=8000

# Optional: Comment out local chromadb service to save resources
# services:
#   chromadb:
#     ...
```

**Use case:** Share RAG documents across multiple OpenWebUI instances

### Enable Web Search

Edit `.env`:
```bash
# Add API key
BRAVE_SEARCH_API_KEY=your_key_here
# or SERPER_API_KEY, TAVILY_API_KEY, etc.
```

Edit `docker-compose.yml`:
```yaml
openwebui:
  environment:
    - ENABLE_WEB_SEARCH=true
```

### Enable Image Generation

Edit `docker-compose.yml`:
```yaml
openwebui:
  environment:
    - ENABLE_IMAGE_GENERATION=true
    - IMAGE_GENERATION_ENGINE=openai
    # OPENAI_API_KEY in .env
```

---

## Troubleshooting

### Ollama not connecting
```bash
# Check Ollama is running
docker ps | grep ollama

# Test Ollama directly
docker exec openwebui-ollama ollama list

# Check from OpenWebUI container
docker exec openwebui curl http://ollama:11434/api/tags
```

### ChromaDB not connecting
```bash
# Check ChromaDB is running
docker ps | grep chromadb

# Test ChromaDB directly
curl http://localhost:8000/api/v1/heartbeat

# Check from OpenWebUI container
docker exec openwebui curl http://chromadb:8000/api/v1/heartbeat
```

### Models not appearing
```bash
# Pull embedding model first
docker exec openwebui-ollama ollama pull nomic-embed-text

# Pull chat model
docker exec openwebui-ollama ollama pull llama3.2:1b

# Restart OpenWebUI
docker-compose restart openwebui
```

### Can't create admin account
Check `ENABLE_SIGNUP` in docker-compose.yml:
```yaml
- ENABLE_SIGNUP=true  # Temporarily enable for first account
```

After creating account, change back to `false`:
```yaml
- ENABLE_SIGNUP=false  # Disable signup (admin-only)
```

### Weather tool not working
```bash
# Check if weather-tool container is running
docker ps | grep weather

# Test weather tool directly
curl "http://localhost:8001/forecast?latitude=52.52&longitude=13.41"

# Check logs
docker-compose logs weather-tool

# Rebuild if needed
docker-compose build weather-tool
docker-compose up -d weather-tool
```

**In OpenWebUI:**
- Go to: Admin Panel → Settings → Tools
- Verify: `http://weather-tool:8000` is added (not localhost:8001)
- Use internal Docker network address for inter-container communication

---

## Security Best Practices

### ✅ Secrets Management
- Never commit `.env` to git
- Use strong `WEBUI_SECRET_KEY` (32+ chars)
- Rotate API keys periodically

### ✅ Network Security
- Keep on private network or use VPN
- Use reverse proxy (nginx) for HTTPS if exposing
- Change default ports if needed

### ✅ Regular Updates
```bash
# Pull latest images
docker-compose pull

# Restart with new images
docker-compose up -d
```

---

## What's Next

After setup, explore:
1. **Copy documents to `~/input-rag/`** → Test RAG (document Q&A)
2. **Try tool servers** → Ask "What's the weather in Berlin?" or "Read files in workspace"
3. **Create personas** → Customize AI behavior for specific tasks
4. **Try TTS/STT** → Voice chat with AI (works in browser)
5. **Generate images** → Ask "Create an image of a sunset over mountains"
6. **Try different models** → Compare Groq vs GPT-4o-mini vs Claude
7. **Export config** → Keep backup in password manager for quick deployment

## How This Setup Actually Works (No BS)

### Architecture Overview
```
Your request → OpenWebUI → Picks LLM → LLM response
                    ↓
            Tool servers (if LLM decides to use them)
            - Read file? → Filesystem tool
            - Git commit? → Git tool
            - Weather? → Weather tool
                    ↓
            ChromaDB (for RAG)
            - Embeds your documents
            - Retrieves relevant chunks
```

### Current Configuration Choices

**✅ What's working well:**
- **Cloud-first LLMs**: Better quality than local models, minimal cost
- **Host mount (`~/input-rag`)**: Direct access to files (practical > theoretical security)
- **OpenAI embeddings**: Better than Ollama's nomic-embed-text, costs ~$0.02/month
- **4 tool servers**: Cover 80% of agentic use cases
- **Config import**: Deploy to new machine in 2 minutes

**⚠️ Trade-offs made:**
- **LLM has write access to `~/input-rag`**: Convenient but risky - could delete files
  - *Mitigation*: Keep backups, don't mount sensitive directories
- **API keys in config JSON**: Easier to deploy but less secure than env vars only
  - *Mitigation*: Store config in password manager, never commit it
- **No authentication on tool servers**: Anyone with container access can use them
  - *Mitigation*: For personal use only, not exposed to network
- **ChromaDB not encrypted**: Vector data is plaintext in Docker volume
  - *Mitigation*: Don't store ultra-sensitive docs, or use disk encryption

### Known Limitations

1. **Tool calling reliability**: ~70% success rate
   - Small models (llama 3.2) often fail to use tools correctly
   - GPT-4o-mini and Claude 3.5 Sonnet work well
   - Workaround: Explicitly say "use the weather tool" instead of hoping LLM figures it out

2. **RAG quality depends on documents**:
   - Works great: Text PDFs, markdown, code files
   - Mediocre: Scanned PDFs (OCR needed), tables, images
   - Fails: Handwriting, complex layouts

3. **Memory tool is basic**:
   - Stores entities/relations but doesn't auto-recall across sessions
   - You need to explicitly ask "What do you remember about X?"
   - Better than nothing, not as good as native long-term memory

4. **Docker resource usage**:
   - ChromaDB + 4 tool servers + OpenWebUI = ~2GB RAM idle
   - Adding Ollama with models = +3-4GB RAM
   - Not suitable for 8GB RAM machines if you want to do anything else

## Real-Life Usage Tips

### Security Best Practices
- ✅ **Config JSON**: Store in Bitwarden/1Password (contains API keys)
- ✅ **`.env` file**: Also store in password manager (backup)
- ✅ **Workspace**: Only mount `~/input-rag` - never `~/Documents` or `~/Desktop`
- ✅ **Read-only mode**: For sensitive docs, use `:ro` mount in docker-compose.yml
- ✅ **Rotate keys**: If config is ever exposed, rotate all API keys immediately
- ✅ **Monitor usage**: Check LLM API bills monthly - tool calls can add up

### Deployment Workflow
```bash
# New machine setup (2 minutes):
1. Clone repo
2. Copy .env from password manager
3. Copy config.json from password manager (optional)
4. docker-compose up -d
5. Import config (if using)
6. Done!
```

### Cost Optimization (Real Numbers)
- **Free tier**: Groq (llama 3.1 70B, 6000 tokens/min free)
  - Good for: Quick tasks, experimentation
  - Reality: Rate limits hit quickly with heavy use

- **Budget (~$5-10/month)**: GPT-4o-mini + OpenAI embeddings
  - Good for: Daily use, RAG with moderate docs
  - Reality: $0.15/1M input tokens, $0.60/1M output - goes fast with long contexts

- **Premium (~$20-50/month)**: GPT-4o + Claude 3.5 Sonnet
  - Good for: Production-quality work, complex tasks
  - Reality: GPT-4o is $2.50/1M input - one big document dump = $0.50+

- **Offline**: Enable Ollama with local models
  - Good for: Privacy, no API costs
  - Reality: llama 3.2 3B is usable, larger models need 16GB+ RAM

### What Would Actually Improve This Setup

**High priority (worth doing):**
1. **Add authentication to tool servers**: Basic API key would prevent accidents
2. **Implement request approval**: Human-in-the-loop for file writes/git commits
3. **Better RAG chunking**: Current 1500 char chunks lose context across page breaks
4. **Structured output parsing**: Force tool responses into JSON for reliability
5. **Volume backups automation**: Cron job to backup ChromaDB + workspace weekly

**Medium priority (nice to have):**
1. **Add more tool servers**: Todoist, Notion, Gmail, Calendar
2. **Implement RAG reranking**: Currently just top-5, reranker would improve relevance
3. **Multi-user support**: Separate workspaces per user
4. **Mobile-friendly deployment**: Tailscale VPN for secure remote access
5. **Cost tracking**: Dashboard showing API usage per conversation

**Low priority (diminishing returns):**
1. **Custom embeddings model**: OpenAI's is good enough
2. **Streaming tool responses**: Adds complexity for marginal UX gain
3. **Voice wake word**: "Hey OpenWebUI..." - cool but gimmicky
4. **Auto-save conversations**: Already in database, export is easy enough

---

**Last Updated**: 2025-10-10
**Components**: OpenWebUI latest, ChromaDB latest, 4 Tool Servers (Weather, Filesystem, Git, Memory)
