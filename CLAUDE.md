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
└── Tool Servers (OpenAPI):
    ├── Weather (8005→8000): Open-Meteo API integration
    ├── Filesystem (8006→8000): Sandboxed file operations in /workspace
    ├── Git (8003→8000): Repository operations in /workspace
    └── Memory (8004→8000): Knowledge graph storage
```

**Note**: Port mappings show `host:container` format. Tool servers all run on port 8000 internally.

### Key Components
- **OpenWebUI**: Runs as `ghcr.io/open-webui/open-webui:latest` container
- **ChromaDB**: Vector store for RAG and persistent memory
- **Cloud LLM APIs**: OpenAI (GPT-4o, GPT-4o-mini), Groq (llama-3.1), Anthropic (Claude), Google (Gemini)
- **Tool Servers**: Built from `github.com/open-webui/openapi-servers` with custom Dockerfiles
- **Shared Workspace**: `filesystem-workspace` volume shared between filesystem and git tools

### Docker Compose Services
All services run on `openwebui-net` bridge network:
- `chromadb`: Container name `openwebui-chromadb` (port 3000→8000)
- `openwebui`: Container name `openwebui` (port 8080)
- `weather-tool`: Container name `openwebui-weather` (port 8005→8000)
- `filesystem-tool`: Container name `openwebui-filesystem` (port 8006→8000)
- `git-tool`: Container name `openwebui-git` (port 8003→8000)
- `memory-tool`: Container name `openwebui-memory` (port 8004→8000)

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

# Access workspace
docker exec -it openwebui-filesystem ls -la /workspace
docker cp openwebui-filesystem:/workspace/myfile.txt ./myfile.txt
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

# Backup workspace
docker run --rm \
  -v openwebui_filesystem-workspace:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/workspace-backup-$(date +%Y%m%d).tar.gz -C /data .

# Backup memory knowledge graph
docker run --rm \
  -v openwebui_memory-data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/memory-backup-$(date +%Y%m%d).tar.gz -C /data .
```

## Configuration

### Environment Variables
- `.env` contains all API keys and secrets (NOT committed to git)
- Required: `WEBUI_SECRET_KEY` (generate with `openssl rand -hex 32`)
- Cloud LLM keys: `OPENAI_API_KEY`, `GROQ_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`
- Optional: `TODOIST_API_KEY`, `BRAVE_SEARCH_API_KEY`, etc.

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
- Sandboxed to `/workspace` directory only for security
- Shares `filesystem-workspace` volume with git-tool
- All file operations validated against `/workspace` allowlist

### Security Considerations
- All tool servers run as non-root user (`appuser`)
- Filesystem/Git tools restricted to `/workspace` volume
- No host filesystem access
- Weather tool has no sensitive data (public API)
- Memory tool stores data in isolated volume

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
- `filesystem-workspace`: Shared workspace for filesystem/git tools
- `memory-data`: Knowledge graph persistence
- `ollama-data`: Defined but unused (Ollama disabled)

### Port Mapping
- 8080: OpenWebUI web interface
- 3000: ChromaDB (mapped from internal 8000)
- 8005: Weather tool (mapped from internal 8000)
- 8006: Filesystem tool (mapped from internal 8000)
- 8003: Git tool (mapped from internal 8000)
- 8004: Memory tool (mapped from internal 8000)

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
- Filesystem and Git tools share `/workspace` volume for seamless integration
- Memory tool uses JSON storage in dedicated volume

### Database Storage
- **OpenWebUI data**: SQLite database at `/app/backend/data/webui.db` (in openwebui-data volume)
- **ChromaDB**: Vector storage at `/chroma/chroma` (in chromadb-data volume)
- **Memory graph**: JSON file at `/data/memory.json` (in memory-data volume)
- **Workspace**: Files at `/workspace` (in filesystem-workspace volume)
