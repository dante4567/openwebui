# GTD Prompts Quick Reference Card

**Quick access to your GTD workflow commands in OpenWebUI**

---

## 📅 Daily Routine

### `/dailygtd` - Start Your Day
**When:** Every morning (10 min)
**What:** Generates focused daily plan from calendar + tasks
**Input:** Tell it your context (energy level, time available)
**Output:** Prioritized plan with must-do, should-do, quick wins

**Example:**
```
/dailygtd

Context: At office, high energy morning, 3 hours before first meeting.
Medium energy afternoon with 2 client calls.
```

---

### `/twominute` - Fill Transitions
**When:** Between meetings, end of day (5-10 min)
**What:** Find tasks completable in ≤2 minutes
**Input:** Current context (@computer, @phone, etc.)
**Output:** Batched quick wins for immediate execution

**Example:**
```
/twominute

Show me quick wins. I'm at my computer with 10 minutes free.
```

---

### `/context` - Choose Next Task
**When:** When deciding what to work on
**What:** Filters tasks by location, tool, energy, time
**Input:** Your current situation
**Output:** Relevant tasks matching ALL criteria

**Example:**
```
/context

I'm at home, have my laptop, low energy, 45 minutes before dinner.
```

---

## 📋 Project Management

### `/projectplan` - Break Down Projects
**When:** Starting new project or feeling stuck (15-30 min)
**What:** Transforms project into actionable next actions
**Input:** Desired outcome + context
**Output:** Structured plan with next actions, contexts, effort estimates

**Example:**
```
/projectplan

Project: Migrate customer database to new CRM
Outcome: All data migrated, team trained, old system retired
Deadline: End Q1 2026
Stakeholders: Sales team (5 people), IT
```

---

### `/capture` - Process Inbox
**When:** Anytime you have thoughts/notes/ideas (<2 min)
**What:** Transforms messy input into structured GTD items
**Input:** Voice transcripts, notes, email summaries, ideas
**Output:** JSON for Todoist or structured markdown

**Example:**
```
/capture

need to call john about next week's meeting
remind sarah about budget approval
idea: automate weekly reports with python
buy milk
```

---

## 🔄 Weekly Ritual

### `/weeklyreview` - End of Week
**When:** Friday afternoon or Sunday evening (30-45 min)
**What:** Comprehensive GTD weekly review
**Input:** What's on your mind, what happened this week
**Output:** Structured review with completed items, active projects, priorities

**Example:**
```
/weeklyreview

This week: Finished Q4 report, started website redesign, 3 client meetings.
Feeling: Overwhelmed with CRM migration (stuck 2 weeks).
Next week: 2 conference calls, need to prepare presentation.
```

---

## 🎯 Quick Comparison

| Prompt | Time | When to Use | Output |
|--------|------|-------------|--------|
| `/dailygtd` | 10 min | Every morning | Today's prioritized plan |
| `/twominute` | 5 min | Between tasks | Quick wins (≤2min) |
| `/context` | 2 min | Choosing next task | Filtered task list |
| `/projectplan` | 20 min | New/stuck project | Action plan |
| `/capture` | 1 min | Random thoughts | Structured items |
| `/weeklyreview` | 40 min | End of week | Full GTD review |

---

## 💡 Pro Tips

### Prompt Stacking
Combine prompts for powerful workflows:

**Morning Routine:**
```
1. /weeklyreview (if Friday/Sunday)
2. /dailygtd (plan today)
3. /twominute (clear quick wins)
4. Start deep work
```

**Mid-Day:**
```
1. /context (what matches my current situation?)
2. /twominute (5 min before next meeting)
```

**Project Kickoff:**
```
1. /projectplan (break down project)
2. /capture (process related notes)
3. Add tasks to Todoist via GUI
```

---

## 🔤 Prompt Shortcuts

Typing the full command? Too slow!

OpenWebUI auto-completes after `/`:
- Type `/wee` → `/weeklyreview`
- Type `/dai` → `/dailygtd`
- Type `/cap` → `/capture`
- Type `/two` → `/twominute`
- Type `/con` → `/context`
- Type `/pro` → `/projectplan`

---

## 🌍 Language Support

**All prompts support German + English!**

The prompts will:
- Respond in the language you use
- Understand mixed German/English input
- Adapt formatting to your preference

**Example (German):**
```
/dailygtd

Kontext: Im Büro, hohe Energie am Morgen, 3 Stunden vor erstem Meeting.
```

---

## 🛠️ Integration with GTD Tools

These prompts work best with your tool servers:

### Filesystem Tool (`http://filesystem-tool:8000`)
- Save `/weeklyreview` output as markdown
- Store project plans in `~/ai-workspace`

### Git Tool (`http://git-tool:8000`)
- Commit weekly reviews to version control
- Track project evolution over time

### Todoist Tool (`http://todoist-tool:8000`)
- `/capture` formats tasks for Todoist
- `/dailygtd` pulls from Todoist
- Auto-create tasks from prompts

### CalDAV Tool (`http://caldav-tool:8000`)
- `/dailygtd` uses calendar events
- Schedule time blocks for projects
- See hard landscape (time-specific commitments)

### Weather Tool (`http://weather-tool:8000`)
- `/context` can consider weather
- "Will it rain Friday for outdoor meeting?"
- Schedule errands on good weather days

---

## 📊 Example Workflow

**Monday Morning (15 minutes):**

1. **Open OpenWebUI:** http://localhost:8080
2. **Start chat:** New conversation
3. **Run daily plan:**
   ```
   /dailygtd

   Context: Office, high energy, 4 hours until lunch.
   Afternoon: 2 meetings, then medium energy.
   ```
4. **Execute quick wins:**
   ```
   /twominute

   At computer, show me quick wins.
   ```
5. **Check context for deep work:**
   ```
   /context

   2 hours free, high energy, @computer, need deep focus.
   ```

**Result:** Clear plan, quick wins done, ready for deep work.

---

**Friday Evening (45 minutes):**

1. **Weekly review:**
   ```
   /weeklyreview

   This week I completed [list], worked on [projects].
   Feeling [emotion] about [situation].
   Next week priorities: [top 3].
   ```
2. **Process inbox:**
   ```
   /capture

   [Paste all random notes from week]
   ```
3. **Plan next week's project:**
   ```
   /projectplan

   Project: [next week's big focus]
   Outcome: [desired result]
   ```

**Result:** Week wrapped up, mind clear, next week planned.

---

## 🎨 Customization

### Editing Prompts

Prompts stored in database. To customize:

**Method 1 (GUI):**
- Settings → Workspace → Prompts
- Find prompt by command name
- Edit content
- Save

**Method 2 (Script):**
```bash
# Edit add-gtd-prompts.py
# Change prompt content
docker cp add-gtd-prompts.py openwebui:/tmp/
docker exec openwebui python3 /tmp/add-gtd-prompts.py
```

### Common Customizations

**Change output format:**
- Prefer bullet points over markdown tables
- Add emoji more/less
- Change section headers

**Adjust German/English:**
- Default to one language
- Remove bilingual instructions

**Add your contexts:**
- Add `@home_office` or `@coworking`
- Add energy levels (focused, scattered, tired)
- Add people contexts `@agenda_boss`

---

## 🔍 Troubleshooting

### Prompt doesn't show up
**Symptom:** Type `/weeklyreview` and nothing happens

**Fix:**
```bash
docker cp add-gtd-prompts.py openwebui:/tmp/
docker exec openwebui python3 /tmp/add-gtd-prompts.py
```

### Wrong output format
**Symptom:** Prompt gives generic response, not GTD format

**Cause:** Using small model without prompt support

**Fix:** Use model with prompt support:
- ✅ gpt-4o-mini (recommended)
- ✅ claude-sonnet-4-5
- ✅ gemini-2.0-flash
- ❌ llama-3.1-8b-instant (too small)

### Prompt is too verbose
**Symptom:** Output too long/detailed

**Fix:** Add to your message:
```
/weeklyreview

[Your input]

Please keep it concise, bullet points only.
```

---

## 📚 Further Reading

- **GTD Methodology:** "Getting Things Done" by David Allen
- **Full Documentation:** `GTD-ENHANCEMENTS.md` in repo
- **Tool Setup:** `CLAUDE.md` sections on Todoist, CalDAV
- **Cost Monitoring:** `./check-llm-costs.sh`

---

## 🎯 Success Metrics

Track these to measure GTD effectiveness:

**Daily:**
- ✅ Used `/dailygtd` in morning?
- ✅ Cleared 2-minute tasks?
- ✅ Checked context before task switching?

**Weekly:**
- ✅ Completed `/weeklyreview`?
- ✅ All projects have next action?
- ✅ Inbox processed (0 items)?

**Monthly:**
- ✅ Projects completed vs started?
- ✅ Prompt usage frequency?
- ✅ System adjustments needed?

---

**Version:** 1.0
**Last Updated:** 2025-10-16
**Compatibility:** OpenWebUI (latest)
**Languages:** English, German

---

## 🚀 Quick Start Checklist

- [ ] Import config via GUI (sets gpt-4o-mini default)
- [ ] Register weather tool (Settings → Admin → Tools)
- [ ] Run `/dailygtd` to test prompts
- [ ] Save this reference card
- [ ] Schedule Friday `/weeklyreview` reminder
- [ ] Bookmark http://localhost:8080

**Ready to start your GTD journey!** 🎯
