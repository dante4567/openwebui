# Chat Import Guide - ChatGPT, Claude, Gemini → OpenWebUI

**Last updated:** 2025-10-16

This guide shows you how to export chats from ChatGPT, Claude (Anthropic), and Gemini, then import them into OpenWebUI.

---

## 📊 Quick Comparison

| Provider | Export Format | Time to Export | Direct Import? | Best Method |
|----------|---------------|----------------|----------------|-------------|
| **ChatGPT** | JSON (structured) | 24-48 hours | No | RAG or Convert |
| **Claude** | JSON (conversations) | Few minutes | No | RAG or Convert |
| **Gemini** | JSON (via Takeout) | Hours-days | No | RAG or Convert |

**TL;DR:** No provider supports direct import to OpenWebUI. Best approach: **Convert to markdown → Upload as RAG documents**.

---

## 🔄 Export Process

### 1. ChatGPT Export

**Steps:**
```
1. Go to: https://chatgpt.com
2. Click profile icon (bottom left)
3. Settings → Data Controls
4. Click "Export data"
5. Confirm email
6. Wait 24-48 hours
7. Check email for download link
8. Download ZIP file
```

**What you get:**
```
chatgpt_export.zip
├── conversations.json       # All your chats
├── user.json               # Profile info
├── message_feedback.json   # Your ratings
└── model_comparisons.json  # A/B tests
```

**conversations.json format:**
```json
[
  {
    "id": "conv-abc123",
    "title": "Python debugging help",
    "create_time": 1697000000,
    "update_time": 1697000000,
    "mapping": {
      "msg-1": {
        "message": {
          "author": {"role": "user"},
          "content": {"parts": ["How do I debug Python?"]}
        }
      },
      "msg-2": {
        "message": {
          "author": {"role": "assistant"},
          "content": {"parts": ["Here's how to debug Python..."]}
        }
      }
    }
  }
]
```

---

### 2. Claude (Anthropic) Export

**Steps:**
```
1. Go to: https://claude.ai
2. Click profile/settings icon
3. Settings → Privacy
4. Click "Request Data Export"
5. Confirm email
6. Wait 5-30 minutes
7. Check email for download link
8. Download ZIP file
```

**What you get:**
```
claude_export.zip
├── conversations.json      # All your chats
└── metadata.json          # Account info
```

**conversations.json format:**
```json
[
  {
    "uuid": "conv-xyz789",
    "name": "Code review assistance",
    "created_at": "2025-10-01T10:00:00Z",
    "updated_at": "2025-10-01T11:00:00Z",
    "chat_messages": [
      {
        "uuid": "msg-1",
        "text": "Review this code...",
        "sender": "human",
        "created_at": "2025-10-01T10:00:00Z"
      },
      {
        "uuid": "msg-2",
        "text": "Here's my review...",
        "sender": "assistant",
        "created_at": "2025-10-01T10:01:00Z"
      }
    ]
  }
]
```

---

### 3. Gemini (Google) Export

**Steps:**
```
1. Go to: https://takeout.google.com
2. Click "Deselect all"
3. Find and select "Bard" or "Gemini"
4. Click "Next step"
5. Choose:
   - Frequency: Export once
   - File type: .zip
   - Size: 2GB (default)
6. Click "Create export"
7. Wait hours to days (depends on data size)
8. Check email for download link
9. Download ZIP file
```

**What you get:**
```
google_takeout.zip
└── Bard/
    └── conversations.json  # All your chats
```

**conversations.json format:**
```json
[
  {
    "id": "conversation-123",
    "title": "Travel planning",
    "createTime": "2025-10-01T10:00:00Z",
    "messages": [
      {
        "id": "msg-1",
        "author": "user",
        "text": "Plan a trip to Japan",
        "timestamp": "2025-10-01T10:00:00Z"
      },
      {
        "id": "msg-2",
        "author": "model",
        "text": "Here's a Japan itinerary...",
        "timestamp": "2025-10-01T10:01:00Z"
      }
    ]
  }
]
```

---

## 🎯 Import Methods (Ranked by Ease)

### Method 1: RAG Documents (Easiest) ⭐ **RECOMMENDED**

**Pros:**
- ✅ Easiest (no coding)
- ✅ Works with any format
- ✅ Searchable across all chats
- ✅ Works with all LLM models

**Cons:**
- ⚠️ Loses conversation structure
- ⚠️ Not interactive (read-only)

**How to:**

1. **Convert JSON to Markdown** (manual or script)
2. **Upload to OpenWebUI:**
   ```
   Workspace → Documents → Upload
   Or: Copy to ~/input-rag/ (if configured)
   ```
3. **Ask questions:**
   ```
   "Search my imported chats for Python debugging tips"
   "What did I learn about React in my old conversations?"
   ```

---

### Method 2: Convert to OpenWebUI Format (Medium)

**Pros:**
- ✅ Preserves conversation structure
- ✅ Can continue conversations
- ✅ Shows up in chat history

**Cons:**
- ⚠️ Requires scripting
- ⚠️ Must match OpenWebUI schema
- ⚠️ Time-consuming

**OpenWebUI Chat Schema:**
```json
{
  "id": "unique-chat-id",
  "user_id": "user-uuid",
  "title": "Chat title",
  "chat": {
    "messages": [
      {
        "id": "msg-id",
        "role": "user",
        "content": "Message text",
        "timestamp": 1697000000
      }
    ]
  },
  "created_at": 1697000000,
  "updated_at": 1697000000
}
```

---

### Method 3: Database Direct Import (Advanced)

**Pros:**
- ✅ Most control
- ✅ Fastest for bulk import

**Cons:**
- ⚠️ Requires SQL knowledge
- ⚠️ Risk of database corruption
- ⚠️ Must stop OpenWebUI

**Not recommended unless you're comfortable with SQLite.**

---

## 🛠️ Conversion Scripts

I'll create scripts for each provider:

### Script 1: ChatGPT JSON → Markdown

```python
#!/usr/bin/env python3
"""Convert ChatGPT export to markdown files."""

import json
from pathlib import Path
from datetime import datetime

def convert_chatgpt_to_markdown(json_path, output_dir):
    """Convert ChatGPT conversations.json to markdown files."""

    with open(json_path) as f:
        conversations = json.load(f)

    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)

    for conv in conversations:
        # Skip empty conversations
        if not conv.get('mapping'):
            continue

        title = conv.get('title', 'Untitled')
        create_time = datetime.fromtimestamp(conv.get('create_time', 0))

        # Safe filename
        filename = f"{create_time.strftime('%Y%m%d')}_{title[:50]}.md"
        filename = "".join(c for c in filename if c.isalnum() or c in ' -_.')

        # Build markdown
        md_content = [
            f"# {title}",
            f"",
            f"**Date:** {create_time.strftime('%Y-%m-%d %H:%M')}",
            f"**Source:** ChatGPT",
            f"",
            "---",
            ""
        ]

        # Extract messages from mapping
        messages = []
        for node_id, node in conv['mapping'].items():
            if 'message' in node and node['message']:
                msg = node['message']
                if msg.get('content') and msg['content'].get('parts'):
                    role = msg['author']['role']
                    content = '\n'.join(msg['content']['parts'])
                    messages.append((role, content))

        # Write messages
        for role, content in messages:
            if role == 'user':
                md_content.append(f"## 👤 You")
            elif role == 'assistant':
                md_content.append(f"## 🤖 ChatGPT")
            else:
                md_content.append(f"## {role.title()}")

            md_content.append("")
            md_content.append(content)
            md_content.append("")

        # Write file
        output_path = output_dir / filename
        output_path.write_text('\n'.join(md_content), encoding='utf-8')
        print(f"✓ Created: {output_path.name}")

    print(f"\n✅ Converted {len(conversations)} conversations")

if __name__ == '__main__':
    import sys
    if len(sys.argv) != 3:
        print("Usage: python3 convert_chatgpt.py conversations.json output_dir/")
        sys.exit(1)

    convert_chatgpt_to_markdown(sys.argv[1], sys.argv[2])
```

---

### Script 2: Claude JSON → Markdown

```python
#!/usr/bin/env python3
"""Convert Claude export to markdown files."""

import json
from pathlib import Path
from datetime import datetime

def convert_claude_to_markdown(json_path, output_dir):
    """Convert Claude conversations.json to markdown files."""

    with open(json_path) as f:
        conversations = json.load(f)

    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)

    for conv in conversations:
        title = conv.get('name', 'Untitled')
        created = datetime.fromisoformat(conv['created_at'].replace('Z', '+00:00'))

        # Safe filename
        filename = f"{created.strftime('%Y%m%d')}_{title[:50]}.md"
        filename = "".join(c for c in filename if c.isalnum() or c in ' -_.')

        # Build markdown
        md_content = [
            f"# {title}",
            f"",
            f"**Date:** {created.strftime('%Y-%m-%d %H:%M')}",
            f"**Source:** Claude",
            f"",
            "---",
            ""
        ]

        # Write messages
        for msg in conv.get('chat_messages', []):
            sender = msg.get('sender', 'unknown')
            text = msg.get('text', '')

            if sender == 'human':
                md_content.append(f"## 👤 You")
            elif sender == 'assistant':
                md_content.append(f"## 🤖 Claude")
            else:
                md_content.append(f"## {sender.title()}")

            md_content.append("")
            md_content.append(text)
            md_content.append("")

        # Write file
        output_path = output_dir / filename
        output_path.write_text('\n'.join(md_content), encoding='utf-8')
        print(f"✓ Created: {output_path.name}")

    print(f"\n✅ Converted {len(conversations)} conversations")

if __name__ == '__main__':
    import sys
    if len(sys.argv) != 3:
        print("Usage: python3 convert_claude.py conversations.json output_dir/")
        sys.exit(1)

    convert_claude_to_markdown(sys.argv[1], sys.argv[2])
```

---

### Script 3: Gemini JSON → Markdown

```python
#!/usr/bin/env python3
"""Convert Gemini export to markdown files."""

import json
from pathlib import Path
from datetime import datetime

def convert_gemini_to_markdown(json_path, output_dir):
    """Convert Gemini conversations.json to markdown files."""

    with open(json_path) as f:
        conversations = json.load(f)

    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)

    for conv in conversations:
        title = conv.get('title', 'Untitled')
        created = datetime.fromisoformat(conv['createTime'].replace('Z', '+00:00'))

        # Safe filename
        filename = f"{created.strftime('%Y%m%d')}_{title[:50]}.md"
        filename = "".join(c for c in filename if c.isalnum() or c in ' -_.')

        # Build markdown
        md_content = [
            f"# {title}",
            f"",
            f"**Date:** {created.strftime('%Y-%m-%d %H:%M')}",
            f"**Source:** Gemini",
            f"",
            "---",
            ""
        ]

        # Write messages
        for msg in conv.get('messages', []):
            author = msg.get('author', 'unknown')
            text = msg.get('text', '')

            if author == 'user':
                md_content.append(f"## 👤 You")
            elif author == 'model':
                md_content.append(f"## 🤖 Gemini")
            else:
                md_content.append(f"## {author.title()}")

            md_content.append("")
            md_content.append(text)
            md_content.append("")

        # Write file
        output_path = output_dir / filename
        output_path.write_text('\n'.join(md_content), encoding='utf-8')
        print(f"✓ Created: {output_path.name}")

    print(f"\n✅ Converted {len(conversations)} conversations")

if __name__ == '__main__':
    import sys
    if len(sys.argv) != 3:
        print("Usage: python3 convert_gemini.py conversations.json output_dir/")
        sys.exit(1)

    convert_gemini_to_markdown(sys.argv[1], sys.argv[2])
```

---

## 🚀 Step-by-Step Import Process

### Complete Workflow:

```bash
# 1. Export from each provider (follow steps above)
# 2. Extract ZIP files
unzip chatgpt_export.zip -d chatgpt/
unzip claude_export.zip -d claude/
unzip google_takeout.zip -d gemini/

# 3. Create output directory
mkdir -p ~/imported-chats

# 4. Convert each export
python3 convert_chatgpt.py chatgpt/conversations.json ~/imported-chats/
python3 convert_claude.py claude/conversations.json ~/imported-chats/
python3 convert_gemini.py gemini/Bard/conversations.json ~/imported-chats/

# 5. Upload to OpenWebUI
# Option A: Copy to RAG directory (if configured)
cp ~/imported-chats/*.md ~/input-rag/

# Option B: Upload via GUI
# Go to OpenWebUI → Workspace → Documents → Upload
# Select all markdown files from ~/imported-chats/

# 6. Wait for indexing (ChromaDB)
# Give it 5-10 minutes to index all documents

# 7. Test search
# In OpenWebUI chat: "Search my imported chats for Python tips"
```

---

## 📝 Best Practices

### Selective Import (Recommended)

**Don't import everything!** Filter to valuable conversations:

```bash
# Import only chats from last 3 months
find ~/imported-chats/ -name "2025*.md" -mtime -90 -exec cp {} ~/input-rag/ \;

# Import only chats with specific keywords
grep -l "Python\|React\|Docker" ~/imported-chats/*.md | xargs cp -t ~/input-rag/

# Import only long conversations (>5KB)
find ~/imported-chats/ -name "*.md" -size +5k -exec cp {} ~/input-rag/ \;
```

### Organize by Topic

```bash
# Create topic folders
mkdir -p ~/input-rag/coding
mkdir -p ~/input-rag/projects
mkdir -p ~/input-rag/personal

# Sort by content
grep -l "code\|python\|javascript" ~/imported-chats/*.md | xargs cp -t ~/input-rag/coding/
grep -l "project\|plan\|design" ~/imported-chats/*.md | xargs cp -t ~/input-rag/projects/
```

### Privacy Filtering

```bash
# Remove chats with sensitive keywords
grep -l "password\|secret\|api.key\|credit.card" ~/imported-chats/*.md
# Review and delete manually

# Or use a script to redact
sed -i 's/sk-[a-zA-Z0-9]\{48\}/[API_KEY_REDACTED]/g' ~/imported-chats/*.md
```

---

## 🧪 Testing

After import, test that everything works:

```
Test Query 1: "What programming languages did I ask about in my old chats?"
Test Query 2: "Find conversations where I discussed project architecture"
Test Query 3: "Show me any React tips from my chat history"
```

If RAG is working, you'll get answers referencing your imported chats.

---

## ⚠️ Limitations

**What doesn't work:**

1. **Function calls** - Old chats with tool usage won't be executable
2. **Images** - Most exports don't include images
3. **Code interpreter results** - Only the code, not outputs
4. **Conversation continuity** - Can't continue old chats interactively
5. **Threading** - Loses conversation tree structure

**Workaround:** Use imported chats as **reference material** via RAG, not as interactive history.

---

## 🎯 Summary: Best Method

**For most users:**

1. ✅ Export from all 3 providers
2. ✅ Use conversion scripts → Markdown
3. ✅ Upload to OpenWebUI as RAG documents
4. ✅ Use RAG search to query old chats

**Time:** 2-3 hours total (mostly waiting for exports)

**Result:** Searchable knowledge base of all past conversations

---

## 📂 Next Steps

After import:

1. **Test RAG search** with queries
2. **Create topic collections** in OpenWebUI
3. **Set up GTD workflows** (see docs/GTD.md)
4. **Let memory tool learn** from new conversations

Your imported chats become a personal knowledge base! 🎉
