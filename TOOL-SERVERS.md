# OpenWebUI Tool Servers - Quick Reference

## 🎯 What Are Tool Servers?

Tool servers extend LLM capabilities by providing external functions that models can call. They use the OpenAPI standard to define their capabilities.

## ✅ Installed Tool Servers

### 1. Weather Tool 🌤️
- **URL**: `http://weather-tool:8000`
- **External Access**: http://localhost:8001/docs
- **Capabilities**: Real-time weather forecasts for any location
- **API Provider**: Open-Meteo (free, no key required)
- **Example**: "What's the weather in Berlin?"

### 2. Filesystem Tool 📁
- **URL**: `http://filesystem-tool:8000`
- **External Access**: http://localhost:8002/docs
- **Capabilities**: Read/write files, search, list directories
- **Security**: Restricted to `/workspace` directory only
- **Example**: "Create a file called notes.txt with some content"

### 3. Git Tool 🔧
- **URL**: `http://git-tool:8000`
- **External Access**: http://localhost:8003/docs
- **Capabilities**: Git operations (clone, commit, push, pull, status)
- **Workspace**: Shares `/workspace` with filesystem tool
- **Example**: "Initialize a git repo in /workspace/my-project"

### 4. Memory Tool 🧠
- **URL**: `http://memory-tool:8000`
- **External Access**: http://localhost:8004/docs
- **Capabilities**: Knowledge graph for persistent LLM memory
- **Storage**: Entities, relations, and observations
- **Example**: "Remember that John works at Acme Corp as a software engineer"

## 🚀 Setup in OpenWebUI

### Step 1: Enable Tools Globally

1. Go to: **Admin Panel → Settings → Interface**
2. Find: **"Enable Function Calling"** or **"Enable Tools"**
3. Toggle: **ON**

### Step 2: Add Tool Servers

1. Go to: **Admin Panel → Settings → Tools**
2. Click: **"Add Tool Server"**
3. Add each server:

```
Weather Tool:    http://weather-tool:8000
Filesystem Tool: http://filesystem-tool:8000
Git Tool:        http://git-tool:8000
Memory Tool:     http://memory-tool:8000
```

4. Toggle each tool **ON**

### Step 3: Enable for Models

1. Go to: **Admin Panel → Settings → Models**
2. For each model (GPT-4o, Claude, Gemini):
   - Click **Edit** icon
   - Find: **"Capabilities"** section
   - Enable: **"Function Calling"** or **"Tool Use"**
   - Click **Save**

## 💡 Usage Examples

### Weather Tool
```
User: "What's the weather in Tokyo?"
LLM: *calls weather tool with Tokyo coordinates*
LLM: "In Tokyo, it's currently 15°C with clear skies..."
```

### Filesystem Tool
```
User: "Create a Python script in /workspace called hello.py that prints Hello World"
LLM: *calls filesystem tool to write file*
LLM: "I've created /workspace/hello.py with the Hello World script."
```

**Important**: All file paths must be within `/workspace` directory for security.

### Git Tool
```
User: "Initialize a git repository in /workspace/my-app"
LLM: *calls git tool to run git init*
LLM: "Repository initialized successfully."
```

### Memory Tool
```
User: "Remember that Sarah is a data scientist at TechCorp, specializing in ML"
LLM: *creates entity for Sarah with observations and relations*
LLM: "I've saved this information. Sarah is now in my knowledge graph."

User: "What do you know about Sarah?"
LLM: *queries knowledge graph for Sarah*
LLM: "Sarah is a data scientist who works at TechCorp and specializes in machine learning."
```

## 🔧 Testing Tool Servers

### Check if Services are Running
```bash
docker-compose ps
```

### Test Individual Tools
```bash
# Weather tool
curl "http://localhost:8001/docs"

# Filesystem tool
curl "http://localhost:8002/docs"

# Git tool
curl "http://localhost:8003/docs"

# Memory tool
curl "http://localhost:8004/docs"
```

### View Tool Server Logs
```bash
docker-compose logs weather-tool
docker-compose logs filesystem-tool
docker-compose logs git-tool
docker-compose logs memory-tool
```

## 📊 Compatible Models

### ✅ Full Tool Support
- **GPT-4 Turbo** / **GPT-4o** / **GPT-4o-mini** (best for tools)
- **Claude 3.5 Sonnet** / **Claude 3 Opus/Haiku**
- **Google Gemini 1.5 Pro/Flash**
- **Groq llama-3.1-70b/8b** (function calling support)

### ❌ Limited/No Support
- llama3.2:1b (too small)
- Most small Ollama models

**Recommendation**: Use **GPT-4o-mini** for best balance of speed, cost, and tool support.

## 🔒 Security Considerations

### Filesystem Tool
- **Sandboxed**: Only accesses `/workspace` directory (configured in Dockerfile)
- **Isolated**: Cannot access host filesystem or other container directories
- **Shared Volume**: Data persists in Docker volume `filesystem-workspace`
- **Path Validation**: All file operations validated against `/workspace` allowlist

### Git Tool
- **Same Sandbox**: Uses same `/workspace` as filesystem tool
- **No Credentials**: Git credentials not configured by default
- **Local Only**: Cannot push without SSH/HTTPS credentials

### Weather Tool
- **No Sensitive Data**: Only queries public weather API
- **No API Key**: Uses free Open-Meteo service

## 🛠️ Advanced Configuration

### Access Workspace from Host

```bash
# Copy file from workspace to host
docker cp openwebui-filesystem:/workspace/myfile.txt ./myfile.txt

# Copy file from host to workspace
docker cp ./myfile.txt openwebui-filesystem:/workspace/myfile.txt

# Execute command in workspace
docker exec -it openwebui-filesystem ls -la /workspace
```

### Configure Git Credentials (Optional)

```bash
# Enter filesystem container
docker exec -it openwebui-filesystem sh

# Configure git
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
```

## 📝 Workspace Management

### List Files in Workspace
```bash
docker exec openwebui-filesystem ls -la /workspace
```

### Backup Workspace
```bash
docker run --rm \
  -v openwebui-complete_filesystem-workspace:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/workspace-backup-$(date +%Y%m%d).tar.gz -C /data .
```

### Restore Workspace
```bash
docker run --rm \
  -v openwebui-complete_filesystem-workspace:/data \
  -v $(pwd):/backup \
  alpine tar xzf /backup/workspace-backup-YYYYMMDD.tar.gz -C /data
```

## 🚫 Troubleshooting

### Tool not appearing in chat
1. **Check tool is enabled**: Admin Panel → Settings → Tools
2. **Verify model supports tools**: Use GPT-4o-mini or Claude 3.5
3. **Enable function calling**: Model settings → Capabilities → Function Calling

### Tool server not responding
```bash
# Check if running
docker ps | grep openwebui

# Restart tool server
docker-compose restart weather-tool filesystem-tool git-tool

# Check logs for errors
docker-compose logs weather-tool
```

### Permission denied in workspace
```bash
# Fix permissions
docker exec -it openwebui-filesystem chown -R appuser:appuser /workspace
```

## 📚 Resources

- **OpenWebUI Tools Docs**: https://docs.openwebui.com/features/plugin
- **OpenAPI Servers Repo**: https://github.com/open-webui/openapi-servers
- **OpenAPI Spec**: https://swagger.io/specification/

## 🎯 Next Steps

1. **Enable tools** in OpenWebUI settings
2. **Test with GPT-4o-mini** - ask about weather
3. **Try filesystem operations** - create/read files
4. **Experiment with git** - initialize repos, commit changes
5. **Build custom tools** - create your own OpenAPI servers!

---

**Last Updated**: 2025-10-06
**Stack Version**: Weather + Filesystem + Git Tools
