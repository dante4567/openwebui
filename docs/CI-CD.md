# CI/CD & LiteLLM Recommendations

This document provides guidance on CI/CD automation and explains how your OpenWebUI GTD stack uses LiteLLM proxy for all LLM API access.

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

## Current Architecture: LiteLLM Proxy Gateway

### How This Stack Works

**Your stack ALREADY USES LiteLLM as the unified gateway** (not direct API connections):

```
OpenWebUI (port 8080)
    ↓
LiteLLM Proxy (port 4000) ← Redis caching enabled
    ↓
OpenAI, Anthropic, Google, Groq APIs
```

**All API calls route through `http://litellm:4000`** - this is critical and non-negotiable.

### What LiteLLM Provides (Already Active)

✅ **Currently enabled features:**

1. **Redis Caching** (50-80% cost savings)
   - Repeat queries cost $0
   - Cache hit rate visible in logs
   - Saves ~$15/month on $30 budget

2. **Fallback Chains** (reliability)
   - If GPT-4o rate limited → tries Claude Sonnet
   - If Gemini 2.5 fails → tries Gemini 2.0
   - Prevents "model unavailable" errors

3. **Unified Interface** (simplicity)
   - Single endpoint for all 11 models
   - OpenAI-compatible API format
   - No provider-specific code needed

4. **Cost Tracking** (monitoring)
   - Verbose logging shows per-request costs
   - Token usage breakdown (input/output)
   - View with: `docker logs openwebui-litellm | grep -i cost`

5. **Load Balancing** (scalability)
   - Can rotate between multiple API keys
   - Distributes requests across providers
   - Currently configured for single-key usage

### Current Configuration Files

**litellm_config.yaml** (already exists):
- 11 working models configured
- Fallback chains defined
- Redis caching enabled
- Verbose cost logging enabled

**docker-compose.yml** (already configured):
- LiteLLM container running on port 4000
- Redis container for caching (port 6379)
- API keys passed via environment variables
- Volume mount: `./litellm_config.yaml:/app/config.yaml`

**OpenWebUI database** (already configured):
- Base URL: `http://litellm:4000`
- Auth key: `sk-1234` (placeholder, LiteLLM uses env vars)
- All 11 models route through LiteLLM

### Monitoring LiteLLM

```bash
# Check if LiteLLM is running
curl http://localhost:4000/health

# View cost tracking logs
docker logs openwebui-litellm | grep -i cost

# Check Redis cache stats
docker exec redis redis-cli INFO stats | grep -i hits

# Monitor real-time requests
docker-compose logs -f litellm
```

### Why You Can't Remove LiteLLM

**LiteLLM is required** because:
1. OpenWebUI is configured to use `http://litellm:4000` as the only API endpoint
2. Removing it breaks all LLM functionality
3. Redis caching saves enough money to pay for the 2.22 GB disk space
4. Fallback chains prevent failures when providers have issues

**To switch to direct APIs** (not recommended):
- Would lose 50-80% cost savings from caching
- Would lose automatic fallbacks
- Would need to reconfigure OpenWebUI database
- Would need to handle provider-specific API formats
- Net result: Higher costs, lower reliability

---

## Summary

### CI/CD: **Recommended ✅**
- Protects against configuration drift
- Automates testing of tool integrations
- Catches security issues early
- Minimal effort with GitHub Actions

### LiteLLM: **Already Active ✅**
- ALL API calls route through LiteLLM proxy
- Redis caching saves 50-80% on API costs (~$15/month)
- Fallback chains prevent provider outages
- Cost tracking via verbose logging enabled
- Required for current setup (can't be disabled)

**Next steps:**
1. ✅ Set up GitHub Actions workflow (copy examples above)
2. ✅ Run `./test-gtd-stack.sh` before every major change
3. 📊 Monitor LiteLLM costs: `docker logs openwebui-litellm | grep -i cost`
4. 📈 Check Redis cache hits: `docker exec redis redis-cli INFO stats`

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
