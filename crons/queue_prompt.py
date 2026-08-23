#!/usr/bin/env python3
import sys
import os

if len(sys.argv) < 2:
    print("Usage: queue_prompt.py <prompt_text>")
    sys.exit(1)

prompt_text = sys.argv[1]

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
plugins_dir = os.path.join(parent_dir, "plugins")

sys.path.insert(0, plugins_dir)
sys.path.insert(0, os.path.expanduser('~/.hermes/plugins'))
if os.path.exists("/opt/data/plugins"):
    sys.path.insert(0, "/opt/data/plugins")

try:
    from core import db
    db.add_notification(prompt_text)
    print(f"Successfully queued alert: '{prompt_text[:50]}...'")
except Exception as e:
    print(f"Error queuing prompt in SQLite: {e}")
    sys.exit(1)
