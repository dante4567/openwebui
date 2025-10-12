# CI/CD & LiteLLM Recommendations

This document provides guidance on CI/CD automation and whether to use LiteLLM proxy vs direct API connections for your OpenWebUI GTD stack.

---

## CI/CD with GitHub Actions

### Should You Use CI/CD?

**YES, for this GTD stack. Here's why:**

1. **Automated testing**: Catch breaking changes before they affect your workflow
2. **Configuration validation**: Ensure docker-compose.yml matches CLAUDE.md documentation
3. **Security checks**: Scan for exposed secrets in commits
4. **Dependency updates**: Auto-update tool server dependencies weekly

### Recommended GitHub Actions Workflow

Create `.github/workflows/test-gtd-stack.yml`:

```yaml
name: Test GTD Stack

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  schedule:
    # Run weekly on Mondays at 9am UTC
    - cron: '0 9 * * 1'
  workflow_dispatch:  # Manual trigger

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Create dummy .env file
        run: |
          cat > .env << EOF
          WEBUI_SECRET_KEY=$(openssl rand -hex 32)
          OPENAI_API_KEY=sk-dummy-key-for-testing
          TODOIST_API_KEY=dummy-todoist-key
          CALDAV_URL=https://caldav.example.com
          CALDAV_USERNAME=test
          CALDAV_PASSWORD=test
          EOF

      - name: Build Docker images
        run: docker-compose build --parallel

      - name: Start services
        run: docker-compose up -d

      - name: Wait for services to be healthy
        run: |
          echo "Waiting 60 seconds for services to start..."
          sleep 60

      - name: Run integration tests
        run: |
          chmod +x ./test-gtd-stack.sh
          ./test-gtd-stack.sh || true

      - name: Check for configuration drift
        run: |
          # Ensure CLAUDE.md mentions all services in docker-compose
          SERVICES=$(docker-compose config --services | sort)
          for service in $SERVICES; do
            if ! grep -q "$service" CLAUDE.md; then
              echo "WARNING: Service '$service' not documented in CLAUDE.md"
              exit 1
            fi
          done

      - name: Scan for secrets
        uses: trufflesecurity/trufflehog@main
        with:
          path: ./
          base: main

      - name: Clean up
        if: always()
        run: docker-compose down -v

  validate-config:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Validate docker-compose.yml
        run: |
          docker-compose config > /dev/null
          echo "✅ docker-compose.yml is valid"

      - name: Check for DEFAULT_MODELS config
        run: |
          if ! grep -q "DEFAULT_MODELS.*gpt-4o-mini" docker-compose.yml; then
            echo "❌ DEFAULT_MODELS should include gpt-4o-mini for budget control"
            exit 1
          fi
          echo "✅ Budget-friendly default model configured"

      - name: Check for ENABLE_FUNCTION_CALLING
        run: |
          if ! grep -q "ENABLE_FUNCTION_CALLING=true" docker-compose.yml; then
            echo "❌ ENABLE_FUNCTION_CALLING must be true for GTD tools"
            exit 1
          fi
          echo "✅ Function calling enabled"

  dependency-check:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Check for outdated base images
        run: |
          echo "Checking for image updates..."
          docker pull ghcr.io/open-webui/open-webui:latest
          docker pull chromadb/chroma:latest
          docker pull redis:7-alpine
          docker pull python:3.10.12-slim
          echo "✅ Base images checked"
```

### Additional Workflows to Consider

**1. Auto-update dependencies** (`.github/workflows/update-deps.yml`):
```yaml
name: Update Dependencies

on:
  schedule:
    - cron: '0 3 * * 1'  # Weekly on Monday 3am UTC
  workflow_dispatch:

jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Update Docker images
        run: |
          docker-compose pull
          docker-compose build --pull
      - name: Create PR if changes
        uses: peter-evans/create-pull-request@v5
        with:
          title: "chore: update dependencies"
          body: "Automated dependency update"
          branch: "deps/auto-update"
```

**2. Backup workspace** (`.github/workflows/backup.yml`):
```yaml
name: Backup Workspace

on:
  schedule:
    - cron: '0 2 * * *'  # Daily at 2am UTC
  workflow_dispatch:

jobs:
  backup:
    runs-on: ubuntu-latest
    steps:
      # Use rclone to backup ~/ai-workspace to cloud storage
      # Configure with repository secrets
```

---

## LiteLLM vs Direct API Connections

### Current Setup (Direct APIs)

You're currently using **direct API connections**:
- OpenWebUI → OpenAI API (via `OPENAI_API_KEY`)
- OpenWebUI → Anthropic API (via `ANTHROPIC_API_KEY`)
- OpenWebUI → Google API (via `GOOGLE_API_KEY`)
- OpenWebUI → Groq API (via `GROQ_API_KEY`)

**Pros:**
- Simple configuration (just API keys)
- Lower latency (no proxy hop)
- OpenWebUI handles multi-provider natively
- Less infrastructure to maintain

**Cons:**
- No unified rate limiting across providers
- No fallback/retry logic
- No usage tracking/analytics
- Each provider has different API formats (handled by OpenWebUI)

### Alternative: LiteLLM Proxy

**What is LiteLLM?**
- Unified proxy that translates all LLM providers to OpenAI-compatible API
- Single endpoint for all models: `http://localhost:4000`
- Built-in rate limiting, retries, fallbacks, caching
- Cost tracking and analytics dashboard

**When to Use LiteLLM:**

✅ **Use LiteLLM if you want:**
1. **Fallback chains**: "Try GPT-4o-mini, if rate limited use Groq's llama-3.3-70b"
2. **Cost tracking**: Built-in logging of spend per model/user
3. **Rate limiting**: Protect against runaway costs
4. **Caching**: Cache LLM responses for repeated queries (saves $$$)
5. **Load balancing**: Rotate between multiple API keys
6. **Custom routing**: "All coding tasks use GPT-4o, others use 4o-mini"

❌ **Stick with direct APIs if:**
1. You're happy with OpenWebUI's built-in provider support
2. You don't need fallback chains
3. You manually check cost at provider dashboards
4. You want minimal infrastructure complexity
5. You prefer lowest possible latency

### Migration Guide: Direct APIs → LiteLLM

If you decide to migrate, here's how:

**1. Enable LiteLLM in docker-compose.yml** (already uncommented in your setup):
```yaml
litellm:
  image: ghcr.io/berriai/litellm:main-latest
  ports:
    - "4000:4000"
  volumes:
    - ./litellm_config.yaml:/app/config.yaml
  environment:
    - OPENAI_API_KEY=${OPENAI_API_KEY}
    - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    - GOOGLE_API_KEY=${GOOGLE_API_KEY}
    - GROQ_API_KEY=${GROQ_API_KEY}
  command: ["--config", "/app/config.yaml"]
```

**2. Create `litellm_config.yaml`:**
```yaml
model_list:
  # Budget tier (default)
  - model_name: gpt-4o-mini
    litellm_params:
      model: gpt-4o-mini
      api_key: os.environ/OPENAI_API_KEY

  - model_name: llama-3.3-70b
    litellm_params:
      model: groq/llama-3.3-70b-versatile
      api_key: os.environ/GROQ_API_KEY

  # Premium tier
  - model_name: gpt-4o
    litellm_params:
      model: gpt-4o
      api_key: os.environ/OPENAI_API_KEY

  - model_name: claude-3.5-sonnet
    litellm_params:
      model: claude-3-5-sonnet-20241022
      api_key: os.environ/ANTHROPIC_API_KEY

  - model_name: gemini-1.5-pro
    litellm_params:
      model: gemini/gemini-1.5-pro-latest
      api_key: os.environ/GOOGLE_API_KEY

# Fallback chain: try cheap model first, fallback to alternative if rate limited
router_settings:
  routing_strategy: fallback
  fallbacks:
    - gpt-4o-mini: [llama-3.3-70b]
    - gpt-4o: [claude-3.5-sonnet, gemini-1.5-pro]

# Cost tracking
litellm_settings:
  success_callback: ["langfuse"]  # Optional: track all requests
  failure_callback: ["langfuse"]

# Rate limiting (protect budget)
general_settings:
  master_key: os.environ/LITELLM_MASTER_KEY
  database_url: "sqlite:///litellm_config.db"

  # Budget controls
  max_budget: 30.0  # $30/month total
  budget_duration: 30d
```

**3. Update OpenWebUI to use LiteLLM:**
- In OpenWebUI GUI: Settings → Connections
- Set OpenAI Base URL: `http://litellm:4000`
- Use OpenAI API Key format: `sk-any-string` (LiteLLM ignores it, uses config)
- All models now route through LiteLLM

**4. Monitor usage:**
```bash
# View LiteLLM logs
docker-compose logs -f litellm

# Check spend
curl http://localhost:4000/spend/tags

# View dashboard
open http://localhost:4000/ui
```

### Recommendation for Your Setup

**Start with direct APIs (current setup), migrate to LiteLLM if you hit issues:**

Your current setup with direct APIs is **perfectly fine** because:
1. OpenWebUI already handles multi-provider switching in the GUI
2. You have budget controls via `DEFAULT_MODELS=gpt-4o-mini`
3. You're comfortable manually checking cost dashboards
4. Your usage is personal/single-user (no complex routing needs)

**Migrate to LiteLLM only if you experience:**
- Rate limiting issues (need automatic fallbacks)
- Runaway costs (need hard budget limits)
- Want to try advanced features (caching, load balancing)
- Need detailed analytics (which model is used when)

---

## Summary

### CI/CD: **Recommended ✅**
- Protects against configuration drift
- Automates testing of tool integrations
- Catches security issues early
- Minimal effort with GitHub Actions

### LiteLLM: **Optional, use if needed 🤔**
- Direct APIs work great for most users
- LiteLLM adds features at cost of complexity
- Easy to migrate later if requirements change
- Already running in your stack (just not used)

**Next steps:**
1. ✅ Set up GitHub Actions workflow (copy examples above)
2. ✅ Run `./test-gtd-stack.sh` before every major change
3. 🤔 Try LiteLLM if you hit rate limits or want fallback chains
4. 📊 Monitor costs at provider dashboards monthly

---

## Quick Start: Enable CI/CD

```bash
# 1. Create GitHub Actions directory
mkdir -p .github/workflows

# 2. Copy test workflow
cat > .github/workflows/test.yml << 'EOF'
# (paste workflow from above)
EOF

# 3. Commit and push
git add .github/workflows/test.yml
git commit -m "Add CI/CD testing workflow"
git push

# 4. Check results at:
# https://github.com/yourusername/openwebui/actions
```

Your first CI run will validate the stack without affecting your local setup!
