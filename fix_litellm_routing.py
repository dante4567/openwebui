#!/usr/bin/env python3
"""
Fix OpenWebUI to route all LLM traffic through LiteLLM proxy.

This script modifies the OpenWebUI SQLite database to:
1. Replace all direct provider API URLs with http://litellm:4000
2. Replace all provider API keys with LiteLLM master key (sk-1234)
3. Keep only ONE connection endpoint (LiteLLM)

Before: 4 connections (OpenAI, Groq, Google, Anthropic) - bypassing LiteLLM
After:  1 connection (LiteLLM) - all traffic goes through proxy
"""

import sqlite3
import json
import sys
from datetime import datetime

DB_PATH = "/tmp/webui.db"
LITELLM_URL = "http://litellm:4000"
LITELLM_KEY = "sk-1234"

def fix_config():
    """Fix OpenWebUI config to use LiteLLM proxy."""

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get current config
    cursor.execute("SELECT id, data FROM config WHERE id = 1")
    row = cursor.fetchone()

    if not row:
        print("❌ No config found in database")
        return False

    config_id, config_json = row
    config = json.loads(config_json)

    # Show current state
    print("📊 Current Configuration:")
    print(f"   API Base URLs: {len(config['openai']['api_base_urls'])} connections")
    for i, url in enumerate(config['openai']['api_base_urls']):
        print(f"   [{i}] {url}")

    # Backup original
    backup = json.dumps(config, indent=2)
    with open("/tmp/webui_config_backup.json", "w") as f:
        f.write(backup)
    print(f"\n💾 Backup saved to /tmp/webui_config_backup.json")

    # Fix configuration
    print(f"\n🔧 Fixing configuration...")

    # Replace with single LiteLLM endpoint
    config['openai']['api_base_urls'] = [LITELLM_URL]
    config['openai']['api_keys'] = [LITELLM_KEY]

    # Update api_configs - keep only connection 0
    config['openai']['api_configs'] = {
        "0": {
            "enable": True,
            "tags": [],
            "prefix_id": "",
            "model_ids": [],
            "connection_type": "external",
            "auth_type": "bearer"
        }
    }

    # Update embedding to use LiteLLM
    if 'rag' in config:
        # Keep Google embedding model but route through LiteLLM
        config['rag']['openai_api_base_url'] = LITELLM_URL
        config['rag']['openai_api_key'] = LITELLM_KEY
        print(f"   ✓ RAG embeddings now route through LiteLLM")

    # Update TTS/STT to use LiteLLM
    if 'audio' in config:
        if 'tts' in config['audio'] and 'openai' in config['audio']['tts']:
            config['audio']['tts']['openai']['api_base_url'] = LITELLM_URL
            config['audio']['tts']['openai']['api_key'] = LITELLM_KEY
            print(f"   ✓ TTS now routes through LiteLLM")

        if 'stt' in config['audio'] and 'openai' in config['audio']['stt']:
            config['audio']['stt']['openai']['api_base_url'] = LITELLM_URL
            config['audio']['stt']['openai']['api_key'] = LITELLM_KEY
            print(f"   ✓ STT now routes through LiteLLM")

    # Update image generation to use LiteLLM
    if 'image_generation' in config and 'openai' in config['image_generation']:
        config['image_generation']['openai']['api_base_url'] = LITELLM_URL
        config['image_generation']['openai']['api_key'] = LITELLM_KEY
        print(f"   ✓ Image generation now routes through LiteLLM")

    # Update timestamp
    config['version'] = config.get('version', 0) + 1

    # Save fixed config
    new_config_json = json.dumps(config)
    timestamp = datetime.now().isoformat()

    cursor.execute(
        "UPDATE config SET data = ?, updated_at = ? WHERE id = ?",
        (new_config_json, timestamp, config_id)
    )

    conn.commit()
    conn.close()

    print(f"\n✅ Configuration fixed!")
    print(f"   API Base URLs: {len(config['openai']['api_base_urls'])} connection (LiteLLM)")
    print(f"   URL: {config['openai']['api_base_urls'][0]}")
    print(f"\n🎯 All LLM traffic will now route through LiteLLM proxy")
    print(f"   Benefits: Redis caching, fallback chains, cost tracking (in-memory)")

    return True

if __name__ == "__main__":
    try:
        success = fix_config()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
