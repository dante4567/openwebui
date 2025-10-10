# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a complete OpenWebUI stack with ChromaDB and multiple OpenAPI tool servers. It provides a self-hosted AI chat interface with RAG capabilities, cloud LLM support, and extended functionality through tool servers (weather, filesystem, git, memory).

**Note**: Ollama is currently DISABLED in this configuration. The stack uses cloud-based LLMs (OpenAI, Groq, Anthropic, Google) and OpenAI embeddings for RAG.

## Architecture

### Service Architecture
```
OpenWebUI (8080) → Main chat interface
├── Cloud LLMs: OpenAI, Groq, Anthropic, Google
├── ChromaDB (3000→8000): Vector database for RAG + memory
├── Tool Servers (OpenAPI):
│   ├── Weather (8005→8000): Open-Meteo API integration
│   ├── Filesystem (8006→8000): Sandboxed file operations in /workspace
│   ├── Git (8003→8000): Repository operations in /workspace
│   └── Memory (8004→8000): Knowledge graph storage
└── Extended Services:
    ├── Pipelines (9099): OpenWebUI extension framework
    ├── SearXNG (8081→8080): Metasearch engine for web search
    ├── Tika (9998): Document parsing with OCR (100+ formats)
    ├── LiteLLM (4000): Unified LLM gateway with caching
    └── Redis (6379): Caching backend for LiteLLM
```

**Note**: Port mappings show `host:container` format. Tool servers all run on port 8000 internally.

### Key Components
- **OpenWebUI**: Runs as `ghcr.io/open-webui/open-webui:latest` container
- **ChromaDB**: Vector store for RAG and persistent memory
- **Cloud LLM APIs**: OpenAI (GPT-4o, GPT-4o-mini), Groq (llama-3.1), Anthropic (Claude), Google (Gemini)
- **Tool Servers**: Built from `github.com/open-webui/openapi-servers` with custom Dockerfiles
- **Shared Workspace**: Host directory `~/input-rag` mounted to `/workspace` (enables RAG on local files)

### Docker Compose Services
All services run on `openwebui-net` bridge network:

**Core Services:**
- `chromadb`: Container name `openwebui-chromadb` (port 3000→8000)
- `openwebui`: Container name `openwebui` (port 8080)

**Tool Servers:**
- `weather-tool`: Container name `openwebui-weather` (port 8005→8000)
- `filesystem-tool`: Container name `openwebui-filesystem` (port 8006→8000)
- `git-tool`: Container name `openwebui-git` (port 8003→8000)
- `memory-tool`: Container name `openwebui-memory` (port 8004→8000)

**Extended Services:**
- `pipelines`: Container name `openwebui-pipelines` (port 9099)
- `searxng`: Container name `openwebui-searxng` (port 8081→8080)
- `tika`: Container name `openwebui-tika` (port 9998)
- `litellm`: Container name `openwebui-litellm` (port 4000)
- `redis`: Container name `openwebui-redis` (port 6379)

## Development Commands

### Stack Management
```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# View logs for all services
docker-compose logs -f

# View logs for specific service
docker-compose logs -f openwebui
docker-compose logs -f weather-tool

# Restart specific service
docker-compose restart openwebui

# Check service status
docker-compose ps
```

### Configuration Management
```bash
# Import configuration from JSON file (one-time setup)
# Places config.json in /tmp/config.json inside container, then runs import script
docker cp config-1759705898447.json openwebui:/tmp/config.json
docker exec openwebui python3 -c "$(cat import_config_v2.py)"

# This imports: models, personas, prompts, tools, etc. into SQLite database
# Location: /app/backend/data/webui.db
```

### Tool Server Management
```bash
# Rebuild tool server after changes
docker-compose build weather-tool
docker-compose up -d weather-tool

# Test tool servers directly (using external ports)
curl "http://localhost:8005/forecast?latitude=52.52&longitude=13.41"  # Weather
curl "http://localhost:8006/docs"  # Filesystem OpenAPI docs
curl "http://localhost:8003/docs"  # Git OpenAPI docs
curl "http://localhost:8004/docs"  # Memory OpenAPI docs

# Access workspace (mounted from ~/input-rag)
docker exec -it openwebui-filesystem ls -la /workspace
# Or access directly on host:
ls -la ~/input-rag

# Copy files to workspace for RAG processing
cp mydocument.pdf ~/input-rag/
```

### Extended Services Management
```bash
# Test Pipelines service
curl http://localhost:9099/
# Expected: {"status":true}

# Test SearXNG search
curl "http://localhost:8081/search?q=test&format=json"
# Returns JSON search results from multiple search engines

# Test Tika document parsing
curl http://localhost:9998/tika
# Expected: "This is Tika Server (Apache Tika X.X.X)"

# Test with document parsing
curl -X PUT --data-binary @mydocument.pdf http://localhost:9998/tika --header "Accept: text/plain"

# Test LiteLLM health
curl http://localhost:4000/health
# Expected: {"status":"healthy"}

# Test Redis
docker exec openwebui-redis redis-cli ping
# Expected: PONG

# View LiteLLM logs (caching info, cost tracking)
docker-compose logs -f litellm

# View SearXNG search configuration
docker-compose logs -f searxng
```

### Data Management
```bash
# List Docker volumes first to get exact names
docker volume ls | grep openwebui

# Backup OpenWebUI data (get exact volume name from 'docker volume ls')
docker run --rm \
  -v openwebui_openwebui-data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/openwebui-backup-$(date +%Y%m%d).tar.gz -C /data .

# Backup ChromaDB
docker run --rm \
  -v openwebui_chromadb-data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/chromadb-backup-$(date +%Y%m%d).tar.gz -C /data .

# Backup workspace (directly from host mount)
tar czf workspace-backup-$(date +%Y%m%d).tar.gz -C ~/input-rag .

# Backup memory knowledge graph
docker run --rm \
  -v openwebui_memory-data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/memory-backup-$(date +%Y%m%d).tar.gz -C /data .

# Backup pipelines data
docker run --rm \
  -v openwebui_pipelines-data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/pipelines-backup-$(date +%Y%m%d).tar.gz -C /data .

# Backup Redis cache (optional - can be regenerated)
docker run --rm \
  -v openwebui_redis-data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/redis-backup-$(date +%Y%m%d).tar.gz -C /data .
```

## Configuration

### Environment Variables
- `.env` contains all API keys and secrets (NOT committed to git)
- Required: `WEBUI_SECRET_KEY` (generate with `openssl rand -hex 32`)
- Cloud LLM keys: `OPENAI_API_KEY`, `GROQ_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`
- Optional: `TODOIST_API_KEY`, `BRAVE_SEARCH_API_KEY`, etc.

**Note on GitHub Secrets**: This is a local Docker deployment, not a GitHub Actions workflow. GitHub Secrets are designed for CI/CD pipelines. For local development:
- Keep `.env` file locally (never commit it)
- Use `.env.example` as a template (commit this)
- For production deployments, use Docker Swarm secrets, Kubernetes secrets, or a secrets manager (Vault, AWS Secrets Manager, etc.)

### Docker Compose Environment
Key environment variables in `docker-compose.yml`:
- `ENABLE_SIGNUP=false`: Admin-only mode (set to `true` temporarily for first user)
- `RAG_EMBEDDING_ENGINE=openai`: Uses OpenAI for embeddings (Ollama disabled)
- `RAG_EMBEDDING_MODEL=text-embedding-3-small`: OpenAI embedding model
- `ENABLE_CODE_EXECUTION=true`: Pyodide sandbox enabled
- `ENABLE_FUNCTION_CALLING=true`: Tool/function calling enabled
- `ENABLE_MEMORY=true`: Persistent memory in ChromaDB
- `TASK_MODEL=gpt-4o-mini`: Cloud model for background tasks
- `ENABLE_OLLAMA_API=false`: Local Ollama is disabled

### Inter-Container Communication
Tool servers communicate using internal Docker network:
- OpenWebUI → Tool Servers: Use `http://weather-tool:8000` (NOT `localhost:8005`)
- OpenWebUI → ChromaDB: `http://chromadb:8000` (external: `localhost:3000`)
- External access uses mapped ports: `localhost:8005` (weather), `localhost:8006` (filesystem), `localhost:8003` (git), `localhost:8004` (memory)

## Tool Server Implementation

### Dockerfiles Pattern
All tool server Dockerfiles follow this pattern:
1. Use `python:3.10.12-slim` base image
2. Create non-privileged `appuser` (UID 10001)
3. Clone `github.com/open-webui/openapi-servers` repo
4. Install dependencies from tool-specific `requirements.txt`
5. Copy application to `/app` and cleanup temp files
6. Switch to `appuser`
7. Run with `uvicorn main:app --host 0.0.0.0 --port 8000`

### Filesystem Tool Specifics
- Modified `config.py` to use `/workspace` instead of `~/tmp` (line 26 in Dockerfile.filesystem)
- Sandboxed to `/workspace` directory only - cannot access files outside this path
- Mounts host directory `~/input-rag` to `/workspace` (shared with git-tool)
- All file operations validated against `/workspace` allowlist

**Security Trade-offs:**
- ✅ **Benefit**: LLM can read/process your local documents for RAG
- ⚠️ **Risk**: LLM has write access - could modify/delete files in `~/input-rag`
- 💡 **Best Practice**: Use dedicated directory, keep backups, avoid mounting sensitive locations like `~/Documents`

### Security Considerations
- All tool servers run as non-root user (`appuser`)
- Filesystem/Git tools restricted to `/workspace` directory only
- Weather tool has no sensitive data (public API)
- Memory tool stores data in isolated volume

**Host Mount Security:**
- LLM has **read/write access** to `~/input-rag` via filesystem and git tools
- Change mount path in `docker-compose.yml` to customize (lines 86, 111)
- **Recommendations:**
  - Use dedicated directory for RAG data only (e.g., `~/input-rag`)
  - Never mount `~/Documents`, `~/Desktop`, or other sensitive locations
  - Keep regular backups of mounted directory
  - Consider read-only mount for sensitive data: `~/data:/workspace:ro`
  - Monitor LLM interactions when working with important files

## Troubleshooting

### Service Connection Issues
```bash
# Check ChromaDB connectivity
docker exec openwebui curl http://chromadb:8000/api/v1/heartbeat

# Check tool server connectivity
docker exec openwebui curl http://weather-tool:8000/docs
docker exec openwebui curl http://filesystem-tool:8000/docs
docker exec openwebui curl http://git-tool:8000/docs
docker exec openwebui curl http://memory-tool:8000/docs

# Check extended services connectivity
docker exec openwebui curl http://pipelines:9099/
docker exec openwebui curl http://searxng:8080/
docker exec openwebui curl http://tika:9998/tika
docker exec openwebui curl http://litellm:4000/health
docker exec openwebui-redis redis-cli ping
```

### Common Issues
- **OpenAI API errors**: Verify `OPENAI_API_KEY` in `.env` is valid (required for embeddings)
- **Tool not working in chat**: Use GPT-4o-mini or Claude 3.5 (small models lack tool support)
- **First login**: Temporarily set `ENABLE_SIGNUP=true` in docker-compose.yml
- **Tool server URLs in GUI**: Use internal names (`http://weather-tool:8000`) NOT external ports
- **ChromaDB connection failed**: Ensure ChromaDB container is running and healthy

## Important Notes

### RAG Configuration
- Default chunk size: 1500 with 100 overlap
- Top-K: 5 results
- Embedding model: `text-embedding-3-small` (OpenAI)
- **Note**: Requires valid `OPENAI_API_KEY` in `.env`
- Cost: ~$0.02 per 1M tokens (very affordable for embeddings)

### Model Recommendations
- **Best for tools**: GPT-4o-mini, Claude 3.5 Sonnet, Gemini 1.5 Pro
- **Fast + free**: Groq llama-3.1-70b/8b (limited quota)
- **Embeddings**: OpenAI text-embedding-3-small (required for RAG in current setup)

### Volumes
- `chromadb-data`: Vector database + memory storage
- `openwebui-data`: User data, conversations, settings (includes SQLite database)
- `memory-data`: Knowledge graph persistence
- `pipelines-data`: Custom pipelines and extensions
- `redis-data`: Redis persistence for LiteLLM caching
- **Host mount**: `~/input-rag` → `/workspace` (filesystem/git tools - change in docker-compose.yml lines 86, 111)

### Port Mapping

**Core Services:**
- 8080: OpenWebUI web interface
- 3000: ChromaDB (mapped from internal 8000)

**Tool Servers:**
- 8005: Weather tool (mapped from internal 8000)
- 8006: Filesystem tool (mapped from internal 8000)
- 8003: Git tool (mapped from internal 8000)
- 8004: Memory tool (mapped from internal 8000)

**Extended Services:**
- 9099: Pipelines extension framework
- 8081: SearXNG metasearch (mapped from internal 8080)
- 9998: Apache Tika document parsing
- 4000: LiteLLM unified gateway
- 6379: Redis caching

## Extended Services

### Pipelines (Port 9099)
OpenWebUI's native extension framework for modifying LLM requests/responses before/after processing.

**Capabilities:**
- Custom pre-processing of user messages
- Post-processing of LLM responses
- Adding custom logic/integrations
- More powerful than tool servers (can modify request flow)

**Enable in OpenWebUI:**
```yaml
# In docker-compose.yml openwebui environment:
- ENABLE_PIPELINES=true
- PIPELINES_URLS=http://pipelines:9099
```

**Documentation:** https://docs.openwebui.com/pipelines

### SearXNG (Port 8081)
Self-hosted metasearch engine aggregating results from Google, Bing, DuckDuckGo, and 70+ other search engines.

**Why Better Than DuckDuckGo API:**
- No rate limits
- No API key needed
- Aggregates multiple sources
- Privacy-focused (no tracking)

**Already Configured:**
- `RAG_WEB_SEARCH_ENGINE=searxng`
- `SEARXNG_QUERY_URL=http://searxng:8080/search?q=<query>`

**Configuration:** `searxng/settings.yml`

### Apache Tika (Port 9998)
Mature document parsing engine supporting 100+ file formats with OCR capabilities.

**Supported Formats:**
- PDFs (including scanned with OCR)
- Microsoft Office (Word, Excel, PowerPoint)
- Images, HTML, XML, CSV, and more

**Already Configured:**
- `CONTENT_EXTRACTION_ENGINE=tika`
- `TIKA_SERVER_URL=http://tika:9998`

**Use Case:** Upload documents to OpenWebUI → Tika extracts text → Embedded in ChromaDB for RAG

### LiteLLM Proxy (Port 4000)
Unified gateway for all LLM providers with advanced features.

**Features:**
- **Caching**: Reduces API costs by caching responses in Redis
- **Cost Tracking**: Real-time spend monitoring across all providers
- **Fallback Logic**: Auto-retry with cheaper models if primary fails
- **Rate Limiting**: Prevent runaway costs
- **Unified API**: OpenAI-compatible endpoint for all providers

**Configuration:** `litellm_config.yaml`

**Models Available:**
- OpenAI: gpt-4o, gpt-4o-mini
- Anthropic: claude-3-5-sonnet, claude-3-5-haiku
- Groq: llama-3.1-70b, llama-3.1-8b
- Google: gemini-1.5-pro, gemini-1.5-flash

**Fallback Chain:**
```yaml
gpt-4o → gpt-4o-mini (if fails)
claude-3-5-sonnet → gpt-4o (if fails)
llama-3.1-70b → llama-3.1-8b (if fails)
```

**Enable in OpenWebUI:**
Point OpenWebUI to `http://litellm:4000/v1` as an OpenAI-compatible endpoint.

**UI Access:** http://localhost:4000 (admin/admin - change in litellm_config.yaml)

### Redis (Port 6379)
Caching backend for LiteLLM to reduce API costs.

**Configuration:**
- Persistence enabled (appendonly mode)
- Stores in `redis-data` volume
- Used automatically by LiteLLM

**Cost Savings Example:**
- Same question asked twice → Second request served from cache (free)
- Typical savings: 20-40% on API costs for repeated queries

## Re-enabling Ollama (Optional)

If you want to use local models and local embeddings instead of cloud APIs:

1. **Uncomment Ollama service** in `docker-compose.yml` (lines 3-22)
2. **Update OpenWebUI environment** in `docker-compose.yml`:
   ```yaml
   - ENABLE_OLLAMA_API=true
   - OLLAMA_BASE_URL=http://ollama:11434
   - RAG_EMBEDDING_ENGINE=ollama
   - RAG_EMBEDDING_MODEL=nomic-embed-text
   ```
3. **Update depends_on** in openwebui service:
   ```yaml
   depends_on:
     ollama:
       condition: service_healthy
     chromadb:
       condition: service_started
   ```
4. **Restart stack**:
   ```bash
   docker-compose down
   docker-compose up -d
   ```
5. **Pull models**:
   ```bash
   docker exec openwebui-ollama ollama pull nomic-embed-text
   docker exec openwebui-ollama ollama pull llama3.2:1b
   ```

## Configuration Import/Export

The repository includes utilities for importing/exporting OpenWebUI configuration:

### Files
- `config-1759705898447.json`: Example exported configuration (models, personas, prompts, tools)
- `import_config_v2.py`: Python script to import JSON config into SQLite database

### Import Configuration
```bash
# Copy config to container
docker cp config-1759705898447.json openwebui:/tmp/config.json

# Import into database
docker exec openwebui python3 -c "
import sqlite3
import json
import time

with open('/tmp/config.json', 'r') as f:
    json_content = f.read()

conn = sqlite3.connect('/app/backend/data/webui.db')
cursor = conn.cursor()
now = int(time.time())
version = json.loads(json_content).get('version', 0)

cursor.execute('INSERT INTO config (id, data, version, created_at, updated_at) VALUES (?, ?, ?, ?, ?)',
               (1, json_content, version, now, now))

conn.commit()
conn.close()
print('Config imported successfully.')
"
```

### Export Configuration
```bash
# Export from GUI: Admin Panel → Settings → Export
# Or query database directly:
docker exec openwebui sqlite3 /app/backend/data/webui.db \
  "SELECT data FROM config WHERE id=1" > exported_config.json
```

## Key Architectural Decisions

### Current Setup (Cloud-First)
- **LLMs**: Cloud APIs only (OpenAI, Groq, Anthropic, Google)
- **Embeddings**: OpenAI `text-embedding-3-small` (requires API key)
- **Ollama**: Disabled (commented out in docker-compose.yml)
- **Benefits**: Minimal resource usage, best model quality, no large downloads
- **Drawbacks**: Requires internet connection and API keys

### Alternative Setup (Local-First)
To run fully offline with local models:
1. Enable Ollama service (see "Re-enabling Ollama" section)
2. Pull local models: `llama3.2:1b`, `nomic-embed-text`
3. Switch embedding engine to Ollama
4. Trade-off: Higher resource usage (~2-3GB RAM), lower model quality, fully offline

### Tool Server Architecture Notes
- All tool servers run on **internal port 8000** within containers
- External access via mapped ports (8003-8006)
- **Internal URLs** for OpenWebUI configuration: `http://weather-tool:8000`, etc.
- **External URLs** for testing: `http://localhost:8005`, etc.
- Filesystem and Git tools share `/workspace` directory (mounted from host `~/input-rag`)
- Memory tool uses JSON storage in dedicated volume

### Database Storage
- **OpenWebUI data**: SQLite database at `/app/backend/data/webui.db` (in openwebui-data volume)
- **ChromaDB**: Vector storage at `/chroma/chroma` (in chromadb-data volume)
- **Memory graph**: JSON file at `/data/memory.json` (in memory-data volume)
- **Workspace**: Files at `/workspace` (mounted from host `~/input-rag`)

## Using Local Data with RAG

### Setup Your Data Directory
```bash
# Create dedicated directory for RAG data
mkdir -p ~/input-rag

# Copy documents you want to process
cp ~/Documents/myreport.pdf ~/input-rag/
cp -r ~/Projects/documentation ~/input-rag/

# Restart services to mount the directory
docker-compose restart filesystem-tool git-tool
```

### Customizing Mount Location
Edit `docker-compose.yml` lines 86 and 111 to change the mount path:
```yaml
volumes:
  - /path/to/your/data:/workspace  # Change this path
```

### Read-Only Access (More Secure)
For sensitive data you only want to read (not modify):
```yaml
volumes:
  - ~/sensitive-docs:/workspace:ro  # :ro = read-only
```

### Using RAG with Local Files
1. Place documents in `~/input-rag/`
2. In OpenWebUI chat, use filesystem tool to read files
3. Or upload documents via UI for automatic embedding in ChromaDB
4. LLM can now search and reference your local documents
