# OpenWebUI Complete Stack

**Self-contained OpenWebUI with Ollama, ChromaDB, and cloud LLM support**

## What's Included

This stack provides:
- ✅ **OpenWebUI** - AI chat interface
- ✅ **Ollama** - Local LLM server (fallback + embeddings)
- ✅ **ChromaDB** - Vector database for RAG
- ✅ **Tool Servers** - OpenAPI tool servers for extended capabilities:
  - **Weather** - Real-time forecasts (Open-Meteo API)
  - **Filesystem** - File operations (sandboxed to `/workspace` directory)
  - **Git** - Repository management (clone, commit, push in `/workspace`)
  - **Memory** - Knowledge graph for persistent LLM memory (entities, relations, observations)

## Pre-Configured Features

### ✅ Already Configured (docker-compose + .env)
- **Cloud LLMs**: OpenAI, Groq, Anthropic, Google (primary)
- **Local LLM**: Ollama (fallback)
- **RAG**: ChromaDB + embeddings
- **Audio**: Whisper STT, OpenAI TTS
- **Memory**: Enabled (stores in ChromaDB)
- **Functions**: Enabled (configure tools in GUI)
- **Code Execution**: Enabled (Pyodide sandbox)

### 🔧 Needs GUI Configuration (one-time setup)
- Admin account creation
- Model visibility settings
- Personas (optional)
- Custom functions/tools (filesystem, git, todoist, etc.)
- System prompts (optional)

---

## Quick Start

### 1. Setup Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env file
nano .env

# REQUIRED: Set these values
# - WEBUI_SECRET_KEY (generate with: openssl rand -hex 32)
# - At least one LLM API key (GROQ_API_KEY recommended for free tier)
```

### 2. Start the Stack

```bash
# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f openwebui
```

### 3. Pull Models (First Time)

```bash
# Essential: Embedding model for RAG
docker exec openwebui-ollama ollama pull nomic-embed-text

# Recommended: Small chat model (fallback)
docker exec openwebui-ollama ollama pull llama3.2:1b

# Optional: Larger models
docker exec openwebui-ollama ollama pull llama3.2:3b
docker exec openwebui-ollama ollama pull deepseek-r1:1.5b
```

### 4. Access OpenWebUI

Open http://localhost:8080

**First-time setup:**
1. Create admin account (first user = admin)
2. Configure settings (see GUI Configuration below)

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

### Use OpenAI Embeddings (Instead of Ollama)

Edit `docker-compose.yml`:
```yaml
openwebui:
  environment:
    - RAG_EMBEDDING_ENGINE=openai
    - RAG_EMBEDDING_MODEL=text-embedding-3-small
    # OPENAI_API_KEY in .env
```

**Pros**: Better quality, minimal cost (~$0.02/month)
**Cons**: Requires internet, not fully offline

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
1. **Upload documents** → Test RAG (document Q&A)
2. **Connect weather tool** → Enable weather forecasts in chat
3. **Create personas** → Customize AI behavior
4. **Build functions** → Integrate with your tools (git, todoist, etc.)
5. **Try different models** → Compare Groq vs GPT-4 vs Claude
6. **Add more tool servers** → Filesystem, Git, Web scraping, etc.
7. **Export golden copy** → Deploy to other machines

---

**Last Updated**: 2025-10-06
**Components**: OpenWebUI v0.6.32+, Ollama latest, ChromaDB latest, Weather Tool (Open-Meteo)
