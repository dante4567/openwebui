# GTD Workflow Prompts for OpenWebUI

Professional-grade GTD (Getting Things Done) prompts that integrate with Todoist and CalDAV tools to create a complete productivity system.

## ⚠️ HONEST ASSESSMENT - READ THIS FIRST

**Status**: These prompts are **UNTESTED in real usage**.

**What this means:**
- ❌ **Never imported to OpenWebUI** - Installation instructions are theoretical
- ❌ **Never run with actual LLM** - Example outputs are fabricated
- ❌ **Never tested with tools** - Don't know if tool calling will work inside prompts
- ❌ **No user feedback** - Designed based on GTD principles, not real usage
- ❌ **Unknown token limits** - Some prompts might be too long for certain models
- ❌ **Time estimates are guesses** - Never actually timed in practice

**What IS true:**
- ✅ Prompts follow proper GTD methodology
- ✅ JSON format is correct for OpenWebUI
- ✅ Instructions are detailed and comprehensive
- ✅ Designed by someone who understands GTD

**Should you use these?**
- **YES** - As starting templates to customize
- **NO** - Expecting them to work perfectly out of the box
- **EXPECT** - To need significant tweaking based on your actual usage

**Recommendation**: Import one prompt at a time, test it, modify it based on results, then move to the next.

**Report issues**: If you actually use these and find problems, please document what doesn't work. This is currently a theoretical system that needs real-world validation.

---

## Available Prompts

| Prompt | Command | Purpose | Time Required |
|--------|---------|---------|---------------|
| **GTD Weekly Review** | `/weeklyreview` | Complete weekly review to achieve mind-like-water clarity | 60-90 min |
| **GTD Daily Planning** | `/dailygtd` | Start your day with focused intention | 10-15 min |
| **GTD Inbox Processing** | `/processinbox` | Process inbox to zero using decision workflow | 30-45 min |
| **GTD Context Lists** | `/context [@context]` | Show tasks by context (location, tool, energy) | 2-5 min |
| **GTD Project Planning** | `/projectplan` | Plan projects from vision to action | 15-45 min |

## Installation

### Option 1: Import via OpenWebUI GUI (Recommended)

1. **Navigate to Workspace**:
   ```
   OpenWebUI → Workspace → Prompts
   ```

2. **Import Prompts**:
   - Click "+" (Create New Prompt)
   - Click "Import" button
   - Select JSON file from `prompts/` directory
   - Repeat for each prompt

3. **Verify Installation**:
   - Go to Workspace → Prompts
   - You should see all 5 GTD prompts listed

### Option 2: Bulk Import via API

```bash
# Set your OpenWebUI URL and API key
OPENWEBUI_URL="http://localhost:8080"
OPENWEBUI_API_KEY="your-api-key"

# Import all prompts
for file in prompts/*.json; do
  curl -X POST "$OPENWEBUI_URL/api/v1/prompts/import" \
    -H "Authorization: Bearer $OPENWEBUI_API_KEY" \
    -H "Content-Type: application/json" \
    -d @"$file"
done
```

### Option 3: Manual Creation

1. Open each JSON file
2. Copy the "content" field
3. In OpenWebUI:
   - Workspace → Prompts → + (Create)
   - Name: [from JSON "name" field]
   - Command: [from JSON "command" field]
   - Description: [from JSON "description" field]
   - Content: [paste from JSON "content" field]
   - Tags: [from JSON "tags" field]
   - Save

## Usage Guide

### 1. Weekly Review (`/weeklyreview`)

**When to use**: Every Friday or Sunday
**Duration**: 60-90 minutes

**What it does**:
- Guides you through 5 phases of GTD weekly review
- Uses CalDAV tool to review calendar
- Uses Todoist tool to review tasks
- Helps you plan next week
- Generates summary report

**Example**:
```
You: /weeklyreview
AI: Let's begin your weekly review. Phase 1: Getting Clear.
    What's been on your mind this week that we should capture?

[AI guides you through all 5 phases]

AI: 📊 Weekly Review Summary
    ✅ This Week:
    - 47 tasks completed
    - Q4 presentation finished

    🎯 Next Week:
    - Client meeting prep (Priority)
    - Code review sprint
    - Start marketing campaign

    🧠 Insights:
    - You're crushing work tasks but health goals need attention
    - Consider blocking morning time for exercise
```

### 2. Daily Planning (`/dailygtd`)

**When to use**: Every morning
**Duration**: 10-15 minutes

**What it does**:
- Shows today's calendar
- Identifies must-do tasks
- Creates time blocks
- Sets top 3 priorities
- Suggests quick wins

**Example**:
```
You: /dailygtd
AI: Good morning! Let me check your calendar...

    📅 Today's Schedule:
    09:00-10:00 - Team standup
    14:00-15:00 - Client call

    🎯 Top 3 Priorities:
    1. Finish presentation (Due today, P4)
    2. Review Sarah's code (P3)
    3. Update project timeline (P2)

    ⚡ Quick Wins (Do Now):
    - Respond to John's email (2 min)
    - File expense report (5 min)

    Shall I block 10:00-12:00 for deep work on the presentation?
```

### 3. Inbox Processing (`/processinbox`)

**When to use**: When inbox has > 10 items
**Duration**: 30-45 minutes

**What it does**:
- Guides through GTD decision workflow
- Applies 2-minute rule
- Creates tasks/projects in Todoist
- Achieves inbox zero

**Example**:
```
You: /processinbox
AI: Let's process your inbox! How many items do you have?

You: About 15

AI: Perfect. Let's tackle them one by one.

    Item 1: Describe it briefly

You: Email from boss about Q1 planning

AI: Is this actionable?

You: Yes

AI: What's the very next physical action?

You: Schedule 30-minute meeting with boss

AI: Will this take less than 2 minutes?

You: No, probably 5-10 minutes

AI: Is it a project (multiple steps)?

You: No, just one task

AI: ✅ Created task: "Schedule Q1 planning meeting with boss"
    Context: @computer
    Priority: 3 (high)

    Item 2: What is it?

[Continue until inbox empty]

AI: ✅ Inbox Processing Complete!

    📊 Stats:
    - Items processed: 15
    - Tasks created: 8
    - Projects created: 1
    - Items trashed: 4
    - 2-minute actions completed: 2

    ✨ Result: Inbox Zero! Great work!
```

### 4. Context Lists (`/context`)

**When to use**: Anytime you want filtered task list
**Duration**: 2-5 minutes

**What it does**:
- Filters tasks by context
- Suggests what to do next
- Batches similar tasks
- Tracks progress

**Examples**:
```
You: /context @phone
AI: 📍 Context: @phone

    ⚡ Quick Wins (< 5 min):
    - [ ] Call dentist to confirm appointment
    - [ ] Check voicemail

    🎯 Priority Calls:
    1. [P4] Call client re: contract - Due: Today
    2. [P3] Schedule meeting with team lead

    💡 Suggestion:
    You have 3 phone calls queued. Want to batch them now?
    Estimated time: 15 minutes

You: /context low energy
AI: 📍 Context: Low Energy

    Easy tasks for when you're tired:
    - [ ] Organize desktop files (10 min)
    - [ ] Read industry newsletter (15 min)
    - [ ] Clear email subscriptions (5 min)

    💡 Suggestion:
    Start with "Organize desktop files" - it's satisfying
    and will give you a quick win to build momentum.
```

### 5. Project Planning (`/projectplan`)

**When to use**: Starting a new project
**Duration**: 15-45 minutes (depending on size)

**What it does**:
- Clarifies purpose and outcome
- Brainstorms all components
- Organizes into structure
- Creates next actions in Todoist
- Schedules milestones in CalDAV

**Example**:
```
You: /projectplan Launch company blog

AI: Great! Let's plan this project.

    First, what's the purpose? Why launch a blog?

You: Generate leads and establish thought leadership

AI: Perfect. Now imagine it's 3 months from now and the
    blog is successfully launched. What does that look like?

You: We have 10 published articles, getting 500 visitors/month,
     3 lead signups per week

AI: Excellent vision! Let's brainstorm everything that needs
    to happen...

    [Continues through planning process]

    🎯 Project Plan: Launch Company Blog

    📝 Purpose:
    Generate leads and establish thought leadership

    ✨ Success Looks Like:
    10 published articles, 500 visitors/month, 3 leads/week

    🏗️ Major Components:
    1. Content Strategy (4 tasks)
    2. Platform Setup (6 tasks)
    3. Initial Content (8 tasks)
    4. Promotion (5 tasks)

    ⚡ Immediate Next Actions:
    1. ✅ Research blog platforms @computer - Due: This week
    2. Draft content calendar @computer - Due: Next week

    📆 Calendar Blocks Created:
    - Friday 2pm: Platform decision meeting
    - Next Monday: First article writing session

    I've created this project in Todoist with 23 tasks.
    Ready to start with researching platforms?
```

## Integration with GTD Tools

### Todoist Tool
All prompts can:
- ✅ Create tasks
- ✅ List tasks
- ✅ Update priorities
- ✅ Add labels/contexts
- ✅ Set due dates
- ✅ Create projects

### CalDAV Tool
All prompts can:
- ✅ Show calendar
- ✅ Create events
- ✅ Block time
- ✅ Set reminders

### Combined Power
Example workflow:
1. `/dailygtd` - Reviews calendar (CalDAV) + tasks (Todoist)
2. Identifies priority tasks
3. Creates calendar blocks for deep work
4. Updates task priorities
5. All in one conversational flow

## Tips for Best Results

### 1. Be Consistent
- Run `/weeklyreview` every week (same day/time)
- Run `/dailygtd` every morning
- Process inbox 3x per week

### 2. Be Honest
- If AI suggests too much, say "That's too much"
- If you're tired, say "I'm low energy today"
- AI will adjust recommendations

### 3. Use Contexts Religiously
Add contexts to every task:
- `@work`, `@home`, `@errands`
- `@computer`, `@phone`, `@online`
- `@high-energy`, `@low-energy`

### 4. Trust the Process
GTD works when you:
- Capture everything
- Process regularly
- Review weekly
- Do the next action

### 5. Customize Prompts
Feel free to edit prompts to match your workflow:
- Add your specific contexts
- Adjust time estimates
- Include your role/responsibilities

## Keyboard Shortcuts

If OpenWebUI supports custom shortcuts, set these:
- `Cmd+Shift+W` → `/weeklyreview`
- `Cmd+Shift+D` → `/dailygtd`
- `Cmd+Shift+I` → `/processinbox`
- `Cmd+Shift+C` → `/context`

## Troubleshooting

### Prompts don't appear in menu
- Check: Workspace → Prompts → Verify they're imported
- Restart OpenWebUI if needed

### Commands don't work (`/weeklyreview` not recognized)
- Make sure "command" field is set in each prompt
- Check for typos in command name

### Tools not being called
- Verify tool servers are running: `docker-compose ps`
- Check tool registration: `./test-gtd-stack.sh`
- Ensure model supports function calling (gpt-4o-mini, claude-sonnet)

### AI doesn't follow prompt structure
- Try starting message with: "Follow the prompt exactly"
- Use a more capable model (gpt-4o instead of gpt-4o-mini)
- Check if prompt was imported correctly

## Advanced Usage

### Chaining Prompts
```
You: /dailygtd
AI: [Completes daily planning]

You: /context @work high-energy
AI: [Shows filtered tasks]

You: Start the first task
AI: [Guides you through task execution]
```

### Custom Contexts
Edit `/context` prompt to add your specific contexts:
```json
{
  "content": "... \n### Custom Contexts:\n- **@client-site** - At client office\n- **@airplane** - Offline, mobile work\n..."
}
```

### Integration with Other Tools
These prompts work great with:
- Time tracking: "Start timer for this task"
- Note-taking: "Create meeting notes for this"
- File management: "Save to project folder"

## Future Enhancements

Planned additions:
- [ ] `/gtd-monthly` - Monthly review
- [ ] `/gtd-quarterly` - Quarterly goals review
- [ ] `/gtd-energy` - Energy level assessment
- [ ] `/gtd-focus` - Deep work session guide
- [ ] `/gtd-retrospective` - Project post-mortem

## Support

Questions or issues? Check:
1. Main README.md for tool setup
2. TESTING.md for verification
3. CLAUDE.md for architecture details
4. Open an issue on GitHub

## Credits

Based on David Allen's "Getting Things Done" methodology.
Adapted for OpenWebUI with tool integration by Claude Code.

## License

Same as parent project - see root LICENSE file.
