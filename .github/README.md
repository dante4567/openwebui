# GitHub Actions CI/CD

This directory contains automated workflows for continuous integration and delivery.

## Workflows

### 1. Unit Tests (`workflows/unit-tests.yml`)

**Triggers:**
- Every push to `main` or `develop` branches
- Every pull request targeting these branches
- Only runs if tool code changes

**What it does:**
- Runs pytest for both todoist-tool and caldav-tool
- Generates coverage reports (target: >85%)
- Uploads coverage to Codecov
- Fails build if tests fail

**Runtime:** ~2-3 minutes

### 2. Integration Tests (`workflows/integration-tests.yml`)

**Triggers:**
- Push to `main` branch
- Pull requests to `main`
- Manual dispatch (workflow_dispatch)

**What it does:**
- **Integration tests:**
  - Builds Docker images for GTD tools
  - Starts containers
  - Tests health endpoints
  - Checks logs for errors

- **OpenWebUI configuration validation:**
  - Starts full OpenWebUI stack (OpenWebUI + all 4 tool servers)
  - Validates OpenWebUI API is responding
  - Checks configuration endpoint accessibility
  - Verifies tool server connectivity from OpenWebUI container
  - **Queries OpenWebUI database:**
    - Lists all database tables
    - Checks configuration settings
    - Verifies user accounts
    - Lists tool/function registrations
    - Shows model configuration
    - Displays configured prompts
  - Checks logs for critical errors

- **Configuration validation:**
  - Validates docker-compose.yml syntax
  - Checks for hardcoded API keys
  - Verifies .env.example exists
  - Validates Python syntax

- **Documentation checks:**
  - Verifies required docs exist
  - Checks for broken markdown links

**Runtime:** ~10-15 minutes (longer due to full stack startup)

### 3. Dependency Updates (`dependabot.yml`)

**Schedule:** Weekly on Mondays

**What it tracks:**
- GitHub Actions versions (`actions/*@v4` → `actions/*@v5`)
- Python packages in `todoist-tool/requirements.txt`
- Python packages in `caldav-tool/requirements.txt`
- Docker base images in Dockerfiles

**Behavior:**
- Creates individual PRs for major updates
- Groups minor/patch updates together
- Auto-labels PRs by component
- Includes changelog links

## Configuration Files

- `workflows/unit-tests.yml` - Unit test automation
- `workflows/integration-tests.yml` - Integration test automation
- `dependabot.yml` - Dependency update configuration
- `markdown-link-check-config.json` - Link checker settings

## Local Testing

Run CI checks locally before pushing:

```bash
# Unit tests (same as CI)
./run-tests.sh

# Validate docker-compose syntax
docker-compose config > /dev/null

# Check for hardcoded secrets
grep -r "sk-proj-" --exclude-dir=.git .
grep -r "gsk_" --exclude-dir=.git .
grep -r "sk-ant-api" --exclude-dir=.git .

# Validate Python syntax
python3 -m py_compile todoist-tool/main.py
python3 -m py_compile caldav-tool/main.py
```

## CI Status Badges

Add these to your README.md for visibility:

```markdown
![Unit Tests](https://github.com/YOUR_USERNAME/YOUR_REPO/workflows/Unit%20Tests/badge.svg)
![Integration Tests](https://github.com/YOUR_USERNAME/YOUR_REPO/workflows/Integration%20Tests/badge.svg)
```

## Troubleshooting

**Tests fail in CI but pass locally:**
- Check Python version (CI uses 3.10)
- Verify environment variables are set correctly
- Check for missing dependencies in requirements.txt

**Docker builds fail:**
- Ensure base image `python:3.10.12-slim` is available
- Check for network issues pulling dependencies
- Verify requirements.txt syntax

**Dependabot PRs fail:**
- Review breaking changes in dependency changelogs
- Update test mocks if API changes
- Check for incompatible version combinations

## Best Practices

1. **Keep CI fast:** ~5 minutes total is ideal
2. **Fix broken builds immediately:** Don't accumulate technical debt
3. **Review dependabot PRs weekly:** Security updates are important
4. **Update workflows annually:** Keep GitHub Actions versions current
5. **Monitor CI costs:** GitHub provides 2000 free minutes/month for private repos
