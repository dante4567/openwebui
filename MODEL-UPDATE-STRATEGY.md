# Model Update Strategy & Currency

This document tracks LLM model versions and provides guidance on keeping them current.

---

## Current Model Status (October 2025)

### ✅ Models Updated - PRICING CHANGES DETECTED

| Provider | Model | Version/Date | Status | Cost (per 1M tokens) |
|----------|-------|--------------|--------|---------------------|
| **OpenAI** | gpt-4o-mini | 2024-07-18 | ✅ Best budget model | $0.15 / $0.60 |
| **OpenAI** | gpt-4.1-mini | 2025-04-14 | ✅ Current (1M context) | $0.40 / $1.60 |
| **OpenAI** | gpt-4o | 2024 release | ⚠️ GPT-5 released, 4o still good | $2.50 / $10.00 |
| **Anthropic** | claude-sonnet-4-5 | 20250929 | ✅ Latest (Sept 2025) | $3.00 / $15.00 |
| **Anthropic** | claude-3-5-sonnet | 20241022 | ✅ Still good (Oct 2024) | $3.00 / $15.00 |
| **Groq** | llama-3.3-70b-versatile | Dec 2024 release | ✅ Latest Meta model | $0.59 / $0.79 |
| **Google** | gemini-2.5-pro | Apr 2025 | ⚠️ PRICE INCREASED Jun 2025 | $1.25 / $10.00 |
| **Google** | gemini-2.5-flash | Apr 2025 | ⚠️ PRICE INCREASED Jun 2025 | $0.30 / $2.50 |
| **Google** | gemini-2.0-flash | 2024 release | ✅ Best Google budget | $0.10 / $0.40 |

**Last verified**: October 14, 2025 via web search

**CRITICAL CHANGES:**
- ⚠️ Gemini 2.5 Flash pricing increased 300% (input) and 733% (output) in June 2025
- ⚠️ GPT-4.1-mini is 2.6x more expensive than GPT-4o-mini despite "mini" name
- ✅ Use gpt-4o-mini or gemini-2.0-flash for budget workloads

---

## Automated Model Currency Checking

### Test Script Integration

The `test-gtd-stack.sh` script now includes **automated model currency checks** that:

1. **Query provider APIs** to verify current models exist
2. **Check version strings** match latest releases
3. **Warn about deprecations** if models are no longer available
4. **Provide update links** when manual verification needed

**Run check:**
```bash
./test-gtd-stack.sh
# Look for "Checking if models are up-to-date via API..." section
```

### Manual Verification Script

For deeper investigation, use `/tmp/check-models.sh`:

```bash
#!/bin/bash
set -a
source /path/to/.env
set +a

# OpenAI
curl -s "https://api.openai.com/v1/models" \
  -H "Authorization: Bearer $OPENAI_API_KEY" | \
  jq -r '.data[] | select(.id | contains("gpt-4o")) | .id'

# Anthropic (check via test request)
curl -s "https://api.anthropic.com/v1/messages" \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "Content-Type: application/json" \
  -d '{"model":"claude-3-5-sonnet-20241022","max_tokens":10,"messages":[{"role":"user","content":"test"}]}' | \
  jq -r '.model'

# Groq
curl -s "https://api.groq.com/openai/v1/models" \
  -H "Authorization: Bearer $GROQ_API_KEY" | \
  jq -r '.data[] | select(.id | contains("llama")) | .id'
```

---

## When to Update Models

### 1. Deprecation Warnings ⚠️

**Action**: Update immediately when providers announce deprecation.

**How to know:**
- OpenAI deprecation timeline: https://platform.openai.com/docs/deprecations
- Anthropic changelog: https://docs.anthropic.com/en/release-notes/overview
- Google updates: https://ai.google.dev/gemini-api/docs/models/gemini
- Groq models: https://console.groq.com/docs/models

**Example deprecations to watch:**
- `gpt-3.5-turbo` → Use `gpt-4o-mini` instead (cheaper and better)
- `claude-3-opus` → Use `claude-3-5-sonnet` instead (better performance)

### 2. New Major Releases 🚀

**Action**: Test new models in staging, migrate if better/cheaper.

**When new releases happen:**
- **Immediately test** with your typical workloads
- **Compare costs** (new models often cheaper for same quality)
- **Update docker-compose.yml** if migrating
- **Update test script** expected models

**Recent examples:**
- GPT-4o (May 2024): Replaced GPT-4-turbo, 2x faster, 50% cheaper
- Claude 3.5 Sonnet (Oct 2024): Replaced Claude 3 Opus, better quality, cheaper
- Llama 3.3 70B (Dec 2024): Matches Llama 3.1 405B quality at 1/6 the size

### 3. Monthly Review 📅

**Action**: Check for updates monthly (first Sunday).

**Checklist:**
```bash
# 1. Run automated test
./test-gtd-stack.sh

# 2. Check provider announcements
- OpenAI blog: https://openai.com/news
- Anthropic blog: https://www.anthropic.com/news
- Google AI blog: https://developers.googleblog.com/
- Groq updates: https://wow.groq.com/news/

# 3. Review pricing
- Costs may decrease for same models
- New budget tiers may be available

# 4. Update documentation
- Update MODEL-UPDATE-STRATEGY.md
- Update test script expected models
- Update CLAUDE.md if architecture changes
```

---

## How to Update Models

### Step 1: Update Configuration

**OpenWebUI GUI** (Settings → Connections):
1. Navigate to Settings → Connections
2. Find the provider (OpenAI, Anthropic, etc.)
3. Update model name if changed
4. Test with a simple query

**Or update docker-compose.yml** (for defaults):
```yaml
environment:
  - DEFAULT_MODELS=gpt-4o-mini,claude-3-5-sonnet-20241022
  - TASK_MODEL=gpt-4o-mini
```

### Step 2: Update Test Script

Edit `test-gtd-stack.sh`:

```bash
# Update EXPECTED_MODELS array
EXPECTED_MODELS=(
    "gpt-4o-mini:OpenAI:0.15:0.60"
    "NEW-MODEL-NAME:Provider:input:output"
)

# Update OUTDATED_MODELS array
OUTDATED_MODELS=(
    "old-model-to-warn-about"
)

# Update API test sections if model names changed
```

### Step 3: Update Documentation

Update in these files:
- `MODEL-UPDATE-STRATEGY.md` (this file) → Update "Current Model Status" table
- `CLAUDE.md` → Update budget controls section if pricing changed
- `.env.example` → Update comments about model versions
- `CI-CD-RECOMMENDATIONS.md` → Update pricing references

### Step 4: Test Everything

```bash
# Run full test suite
./test-gtd-stack.sh

# Expected results:
# - All API keys working with new models
# - Model currency checks pass
# - No outdated model warnings
# - Cost projections updated
```

---

## Monitoring for Updates

### Option 1: RSS Feeds (Recommended)

Subscribe to provider blogs in your RSS reader:
- OpenAI: `https://openai.com/blog/rss.xml`
- Anthropic: `https://www.anthropic.com/news.rss`
- Google AI: Check https://developers.googleblog.com/feeds/posts/default
- Groq: https://wow.groq.com/feed/

### Option 2: Email Notifications

Sign up for provider newsletters:
- OpenAI: https://platform.openai.com/ → Account → Email preferences
- Anthropic: https://www.anthropic.com/newsletter
- Google: https://developers.google.com/profile/u/me/notifications
- Groq: https://console.groq.com/settings

### Option 3: GitHub Actions (Automated)

Add to `.github/workflows/check-models.yml`:

```yaml
name: Check Model Updates

on:
  schedule:
    - cron: '0 9 * * 0'  # Every Sunday at 9am UTC
  workflow_dispatch:

jobs:
  check-models:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run model currency check
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          GROQ_API_KEY: ${{ secrets.GROQ_API_KEY }}
        run: |
          # Create temp script from check-models.sh
          ./test-gtd-stack.sh 2>&1 | grep -A20 "Checking if models are up-to-date"

      - name: Create issue if outdated
        if: failure()
        uses: actions/github-script@v7
        with:
          script: |
            github.rest.issues.create({
              owner: context.repo.owner,
              repo: context.repo.repo,
              title: '⚠️ Model Update Available',
              body: 'Automated check detected model updates. Review logs and update configuration.',
              labels: ['maintenance', 'models']
            })
```

---

## Model Migration Examples

### Example 1: Migrate from GPT-4 Turbo to GPT-4o

**Why**: GPT-4o is 2x faster, 50% cheaper, and better quality.

```bash
# 1. Update OpenWebUI
# Settings → Connections → OpenAI → Change "gpt-4-turbo" to "gpt-4o"

# 2. Update test script
sed -i '' 's/gpt-4-turbo/gpt-4o/g' test-gtd-stack.sh

# 3. Update OUTDATED_MODELS
# Add "gpt-4-turbo" to the array

# 4. Test
./test-gtd-stack.sh
```

### Example 2: Add New Budget Model

**Scenario**: Google releases `gemini-2.0-flash-lite` at $0.01/$0.05 per 1M tokens.

```bash
# 1. Test it works
curl -s -X POST "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-lite:generateContent?key=$GOOGLE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"contents":[{"parts":[{"text":"test"}]}]}'

# 2. Add to test script EXPECTED_MODELS
# "gemini-2.0-flash-lite:Google:0.01:0.05"

# 3. Update DEFAULT_MODELS in docker-compose.yml
# DEFAULT_MODELS=gpt-4o-mini,gemini-2.0-flash-lite

# 4. Document in CLAUDE.md budget section
```

---

## Quick Reference: Provider Update Patterns

| Provider | Typical Update Frequency | Naming Convention | Notes |
|----------|-------------------------|-------------------|-------|
| **OpenAI** | Every 3-6 months | `gpt-4o`, `gpt-4o-mini`, `gpt-4.1-mini` | GPT-5 released Oct 2025 |
| **Anthropic** | Every 6-9 months | `claude-3-5-sonnet-YYYYMMDD`, `claude-sonnet-4-5-YYYYMMDD` | 4.5 released Sept 2025 |
| **Google** | Every 3-4 months | `gemini-2.0-flash`, `gemini-2.5-pro` | Pricing changes Jun 2025 |
| **Groq** | Follows Meta releases | `llama-X.Y-NNb-variant` | Llama 3.3 70B latest |

**Model lifetimes**: Typically 12-18 months before deprecation announced, 6 months notice period.

---

## Troubleshooting

### Test Script Shows "Model not found"

**Cause**: Provider deprecated the model.

**Fix**:
1. Check provider's current models: Run `/tmp/check-models.sh`
2. Update to latest equivalent model
3. Update test script expected models

### New Model Returns Different Response Format

**Cause**: Provider changed API response schema.

**Fix**:
1. Check provider's API changelog
2. Update test script jq filters
3. Report issue if breaking change

### Pricing Changed But Still Shows Old Price

**Cause**: Test script has hardcoded pricing.

**Fix**:
1. Update `EXPECTED_MODELS` array in test-gtd-stack.sh
2. Update documentation in this file
3. Re-run budget calculations in CLAUDE.md

---

## Cost Impact of Model Updates

### Typical Scenarios

**Scenario 1: Provider lowers prices** (common)
- ✅ No action needed (automatic savings)
- Update documentation for accuracy

**Scenario 2: New cheaper model available** (quarterly)
- Test new model with your workloads
- Migrate if quality acceptable
- Potential 50-70% cost reduction

**Scenario 3: Model deprecated, forced upgrade** (rare)
- Usually moved to better model at similar/lower price
- Follow provider migration guide
- Test thoroughly before deploying

### Historical Price Trends (Reference)

- **2023**: GPT-4 at $30/$60 per 1M tokens
- **2024**: GPT-4o at $2.50/$10 per 1M tokens (83% reduction!)
- **2024**: GPT-4o-mini at $0.15/$0.60 per 1M tokens (99% reduction from GPT-4!)

**Trend**: Prices decrease 50-90% every 12-18 months for equivalent quality.

---

## Summary

### Current Status: ✅ All Models Current (Jan 2025)

### Action Items:

1. **Monthly**: Run `./test-gtd-stack.sh` to verify model currency
2. **Quarterly**: Check provider blogs for new releases
3. **On deprecation notice**: Update immediately (6 month window usually given)
4. **On new major release**: Test and consider migrating if better value

### Automation:

- ✅ Test script checks model currency automatically
- ✅ CI/CD can run weekly checks (see CI-CD-RECOMMENDATIONS.md)
- ✅ RSS feeds available for all major providers

**Next review due**: November 2025

---

## October 2025 Update Summary

**What Changed:**
1. **Gemini 2.5 pricing shock**: Google increased pricing significantly in June 2025
   - gemini-2.5-flash: $0.075→$0.30 input (300%), $0.30→$2.50 output (733%)
   - gemini-2.5-pro: Output increased from $5.00→$10.00 (100%)
2. **GPT-5 released**: OpenAI's new flagship (Oct 2025), but GPT-4o still available
3. **Claude Sonnet 4.5**: Released Sept 2025, best for coding
4. **GPT-4.1-mini confusion**: Despite "mini" name, it's more expensive than GPT-4o-mini

**Budget Recommendations Updated:**
- OLD: "Use gemini-2.5-flash for budget Google ($0.007/session)"
- NEW: "Use gemini-2.0-flash for budget Google ($0.009/session) - 2.5 is expensive!"
- OLD: "Use gpt-4.1-mini for budget OpenAI"
- NEW: "Use gpt-4o-mini for budget OpenAI - 4.1-mini is 2.6x more expensive"

**Action Taken:**
- ✅ Updated CLAUDE.md with correct October 2025 pricing
- ✅ Updated MODEL-UPDATE-STRATEGY.md
- ✅ Verified all pricing via web search (Oct 14, 2025)
- ⚠️ Need to update test-gtd-stack.sh EXPECTED_MODELS array
