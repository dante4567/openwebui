# GTD Enhancements for OpenWebUI

**Date:** 2025-10-16
**Status:** Ready to apply
**Purpose:** Optimize OpenWebUI for GTD (Getting Things Done) workflows with prompts, budget controls, and productivity features

---

## 🎯 What's Included

### 1. Six New GTD-Specific Prompts

| Command | Purpose | Use Case |
|---------|---------|----------|
| `/weeklyreview` | GTD Weekly Review | End-of-week processing: collect, review, plan |
| `/projectplan` | Project Planning | Break projects into next actions with contexts |
| `/capture` | Quick Capture | Transform notes/voice into structured tasks |
| `/dailygtd` | Daily Standup | Generate daily plan with calendar + tasks |
| `/context` | Context Filter | Show tasks matching current context/energy |
| `/twominute` | 2-Minute Rule | Find and execute quick wins (≤2min tasks) |

### 2. Budget-Optimized Configuration

**Changes:**
- **Default model:** `claude-sonnet-4-5` → `gpt-4o-mini`
  - Cost: $0.15/session → $0.014/session
  - **Savings:** ~$10-15/month
- **Model list:** Removed 5 fake models, added 3 real ones
  - ❌ Removed: `gpt-5`, `gpt-5-mini`, `claude-opus-4-1`, `claude-sonnet-4`, `gemini-2.5-flash-lite`
  - ✅ Added: `gpt-4.1-mini`, `llama-3.3-70b-versatile`, `gemini-2.0-flash`
- **Image generation:** Disabled (not needed for GTD)
- **Signup:** Disabled (security)

### 3. Weather Tool Enabled

**Why:** Adds context for scheduling decisions
- "Will it rain Friday for outdoor meeting?"
- "Best weather day this week for errands?"
- **Cost:** Free (uses Open-Meteo API)
- **Registration:** Manual (see instructions below)

### 4. Cost Monitoring Script

**File:** `check-llm-costs.sh`
**Features:**
- Analyze LLM spending by hour/day/week
- Model usage breakdown
- Budget projection ($30/month target)
- Redis cache effectiveness
- Provider dashboard links

---

## 📦 Files Created

```
.
├── gtd-prompts.sql               # SQL to insert 6 GTD prompts
├── apply-gtd-enhancements.sh     # Main application script
├── check-llm-costs.sh            # Cost monitoring tool
├── /tmp/config-GTD-OPTIMIZED.json # Optimized OpenWebUI config
└── GTD-ENHANCEMENTS.md           # This file
```

**Modified:**
- `docker-compose.yml` - Disabled signup, enabled weather-tool

---

## 🚀 Installation

### Option 1: Apply Everything (Recommended)

```bash
cd ~/Documents/my-git/openwebui
./apply-gtd-enhancements.sh
```

This will:
1. Add 6 GTD prompts to database
2. Apply optimized config
3. Restart OpenWebUI
4. Show next steps

### Option 2: Manual Step-by-Step

#### Step 1: Add GTD Prompts

```bash
docker cp gtd-prompts.sql openwebui:/tmp/gtd-prompts.sql
docker exec openwebui sqlite3 /app/backend/data/webui.db < /tmp/gtd-prompts.sql
```

#### Step 2: Apply Config

```bash
docker cp /tmp/config-GTD-OPTIMIZED.json openwebui:/tmp/config.json
docker exec openwebui python3 << 'EOF'
import json, sqlite3
with open('/tmp/config.json') as f:
    config = json.load(f)
conn = sqlite3.connect('/app/backend/data/webui.db')
conn.execute('UPDATE config SET data=? WHERE id=1', (json.dumps(config),))
conn.commit()
EOF
```

#### Step 3: Restart Stack

```bash
docker-compose up -d --build
```

This builds weather-tool and applies docker-compose.yml changes.

---

## ✅ Verification

### 1. Test GTD Prompts

Open http://localhost:8080, start a new chat, type:

```
/weeklyreview
```

You should see the "GTD Weekly Review" prompt appear.

### 2. Verify Default Model

- Start new chat
- Check model selector (top right)
- Should default to **gpt-4o-mini**

### 3. Check Model List

Settings → Models → Should show 11 models:
- OpenAI: gpt-4o-mini, gpt-4.1-mini, gpt-4o
- Anthropic: claude-sonnet-4-5, claude-3-5-sonnet, claude-3-5-haiku
- Groq: llama-3.3-70b, llama-3.1-8b
- Google: gemini-2.5-pro, gemini-2.5-flash, gemini-2.0-flash

### 4. Register Weather Tool

- Settings → Admin → Tools → Add Tool Server
- **URL:** `http://weather-tool:8000`
- **Type:** OpenAPI
- **Auth:** Bearer (leave key blank)
- Save

Test: In chat, ask "What's the weather in Berlin?"

### 5. Monitor Costs

```bash
./check-llm-costs.sh
```

Should show request count, costs, model breakdown.

---

## 📖 Using GTD Prompts

### `/weeklyreview` - Weekly Review

**When:** End of week (Friday afternoon or Sunday evening)
**Time:** 30-45 minutes
**Process:**
1. Tell the prompt what's on your mind
2. Review active projects
3. Identify stalled projects (no next action)
4. Review waiting-for items
5. Plan next week priorities

**Example:**
```
/weeklyreview

This week I finished the Q4 report, started the website redesign,
and had 3 client meetings. I'm feeling overwhelmed with the CRM migration
project - it's been stuck for 2 weeks. Next week I have 2 conference calls
and need to prepare a presentation.
```

**Output:** Structured markdown review with completed items, active projects, priorities.

---

### `/projectplan` - Project Planning

**When:** Starting a new project or when stuck
**Time:** 15-30 minutes
**Process:**
1. Describe desired outcome
2. Brainstorm all steps
3. Organize into sequence
4. Identify very next physical action

**Example:**
```
/projectplan

Project: Migrate CRM to new platform
Outcome: All customer data in new system, team trained, old system decommissioned
Deadline: End of Q1 2026
Stakeholders: Sales team (5 people), IT, customers
```

**Output:** Structured project plan with next actions, contexts, effort estimates.

---

### `/capture` - Quick Capture

**When:** Anytime you have a thought/idea/task
**Time:** <2 minutes
**Process:**
1. Paste rough notes (voice transcript, email, thought)
2. Get structured output (task, project, reference, or trash)

**Example:**
```
/capture

need to call john about the meeting next week
also remind sarah about the budget approval
and that idea about automating the weekly reports with python
oh and buy milk
```

**Output:** JSON for Todoist or structured markdown for each item.

---

### `/dailygtd` - Daily Standup

**When:** Every morning
**Time:** 10-15 minutes
**Process:**
1. Let it fetch your calendar (CalDAV tool)
2. Let it fetch your tasks (Todoist tool)
3. Tell it your context (energy, time available)

**Example:**
```
/dailygtd

Context: At office, high energy morning, have 3 hours before first meeting at 11am.
After meetings, medium energy afternoon. Need to leave by 5pm today.
```

**Output:** Prioritized daily plan with must-do, should-do, quick wins.

---

### `/context` - Context Filter

**When:** When deciding what to work on next
**Time:** 2-5 minutes
**Process:**
1. Tell it your current context
2. Get filtered list of relevant tasks

**Example:**
```
/context

I'm at home, have my laptop, high energy, 2 hours free before dinner.
```

**Output:** Tasks matching @home + @computer + high energy + 2hr window.

---

### `/twominute` - 2-Minute Rule

**When:** During transitions (between meetings, end of day)
**Time:** 5-10 minutes
**Process:**
1. Run the prompt
2. Get list of quick wins (≤2min each)
3. Do them immediately

**Example:**
```
/twominute

Show me quick wins I can do right now. I'm at my computer.
```

**Output:** Batched list of 2-minute tasks, grouped by context.

---

## 💰 Cost Analysis

### Before Enhancements

| Item | Cost |
|------|------|
| Default model | claude-sonnet-4-5 ($0.15/session) |
| 50 sessions/month | $7.50/month |
| 100 sessions/month | $15.00/month |
| 200 sessions/month | **$30.00/month (BUDGET LIMIT)** |

### After Enhancements

| Item | Cost | Savings |
|------|------|---------|
| Default model | gpt-4o-mini ($0.014/session) | -91% |
| 50 sessions/month | $0.70/month | **-$6.80** |
| 100 sessions/month | $1.40/month | **-$13.60** |
| 200 sessions/month | $2.80/month | **-$27.20** |
| **2100 sessions/month** | **$29.40/month** | Budget fits! |

**Impact:** You can now do **10x more sessions** within the same $30/month budget.

---

## 🎯 Recommended Workflow

### Daily Routine

**Morning (10 minutes):**
1. Run `/dailygtd` to plan your day
2. Check weather if needed for scheduling
3. Process any overnight emails/messages with `/capture`

**During Day:**
- Use `/context` when switching contexts (@home → @office)
- Use `/twominute` during transitions (between meetings)
- Use existing prompts like `//gtd2` for ad-hoc task management

**Evening (5 minutes):**
- Quick review of completed tasks
- Capture any outstanding items with `/capture`
- Update Todoist with tomorrow's priorities

### Weekly Routine

**Friday or Sunday (45 minutes):**
1. Run `/weeklyreview` for full GTD review
2. Process inbox items with `/capture`
3. Update projects with `/projectplan` if needed
4. Check costs: `./check-llm-costs.sh`

---

## 🔧 Customization

### Editing Prompts

Prompts are in `gtd-prompts.sql`. To modify:

1. Edit the SQL file
2. Re-apply:
   ```bash
   docker cp gtd-prompts.sql openwebui:/tmp/gtd-prompts.sql
   docker exec openwebui sqlite3 /app/backend/data/webui.db < /tmp/gtd-prompts.sql
   ```
3. Restart: `docker-compose restart openwebui`

### Changing Default Model

Edit `/tmp/config-GTD-OPTIMIZED.json`, find:
```json
"default_models": "gpt-4o-mini"
```

Change to:
- `"llama-3.1-8b-instant"` - Cheapest ($0.003/session)
- `"gemini-2.0-flash"` - Fast & cheap ($0.009/session)
- `"gpt-4.1-mini"` - More expensive but 1M context ($0.036/session)

Then re-apply config with `./apply-gtd-enhancements.sh`.

---

## 🐛 Troubleshooting

### Prompts Not Showing

**Symptom:** Typing `/weeklyreview` doesn't show the prompt

**Fix:**
```bash
# Check if prompts were added
docker exec openwebui sqlite3 /app/backend/data/webui.db \
  "SELECT command, title FROM prompt WHERE command LIKE '%review%'"

# If empty, re-apply
docker cp gtd-prompts.sql openwebui:/tmp/gtd-prompts.sql
docker exec openwebui sqlite3 /app/backend/data/webui.db < /tmp/gtd-prompts.sql
docker-compose restart openwebui
```

### Model Still Defaults to Claude

**Symptom:** New chats default to claude-sonnet-4-5, not gpt-4o-mini

**Check:**
```bash
docker exec openwebui python3 -c "
import sqlite3, json
conn = sqlite3.connect('/app/backend/data/webui.db')
cursor = conn.cursor()
cursor.execute('SELECT data FROM config WHERE id=1')
config = json.loads(cursor.fetchone()[0])
print('Default model:', config['ui']['default_models'])
"
```

**Fix:** Re-run `./apply-gtd-enhancements.sh`

### Weather Tool Not Working

**Symptom:** Asking about weather gives "tool not available" error

**Fix:** Register manually:
1. Settings → Admin → Tools → Add Tool Server
2. URL: `http://weather-tool:8000`
3. Type: OpenAPI
4. Save
5. Test: "What's the weather in Berlin?"

### Cost Script Shows No Data

**Symptom:** `./check-llm-costs.sh` shows 0 requests

**Cause:** No API calls made yet, or LiteLLM logging disabled

**Fix:** Make a test API call:
```bash
curl -s -X POST http://localhost:4000/v1/chat/completions \
  -H "Authorization: Bearer sk-1234" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-4o-mini","messages":[{"role":"user","content":"test"}],"max_tokens":5}' \
  | jq .
```

Then re-run cost script.

---

## 📊 Success Metrics

Track these to measure GTD effectiveness:

### Weekly
- **Tasks completed:** Aim for 20-30/week
- **Projects with next action:** Should be 100%
- **2-minute wins:** Track with `/twominute` prompt
- **Weekly review consistency:** Every Friday or Sunday

### Monthly
- **LLM costs:** Stay under $30/month (check with `./check-llm-costs.sh`)
- **Active projects:** Review if >15 (too many balls in air)
- **Overdue tasks:** Should be <5 (everything else deferred intentionally)
- **Someday/Maybe reviews:** Once per month

### Quarterly
- **Completed projects:** How many outcomes achieved?
- **System refinement:** Adjust prompts, contexts, workflows
- **Cost optimization:** Review model usage, consider cheaper alternatives

---

## 🤝 Contributing

Found a better GTD prompt? Improved cost monitoring? Share it!

**File structure:**
- `gtd-prompts.sql` - Add your prompts here
- `apply-gtd-enhancements.sh` - Update if adding new features
- `GTD-ENHANCEMENTS.md` - Document new workflows

**Testing:**
1. Test on your setup first
2. Ensure backward compatibility
3. Update documentation
4. Commit with clear message

---

## 📚 Resources

### GTD Methodology
- Book: *Getting Things Done* by David Allen
- Website: https://gettingthingsdone.com/
- Community: /r/gtd on Reddit

### OpenWebUI Docs
- Main: https://docs.openwebui.com/
- Prompts: https://docs.openwebui.com/features/plugin/
- Tools: https://docs.openwebui.com/features/plugin/

### LLM Pricing
- OpenAI: https://openai.com/pricing
- Anthropic: https://www.anthropic.com/pricing
- Google: https://ai.google.dev/pricing
- Groq: https://console.groq.com/

---

**Generated:** 2025-10-16
**Version:** 1.0
**Maintainer:** OpenWebUI GTD Stack
**License:** Same as OpenWebUI (MIT)
