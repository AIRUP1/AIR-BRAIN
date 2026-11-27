#!/usr/bin/env python3
"""PreToolUse hook: refuse edits to real .env files (allow .env.example)."""
import json
import os
import sys

data = json.load(sys.stdin)
path = (data.get("tool_input") or {}).get("file_path", "")
name = os.path.basename(path)
if name == ".env" or (name.startswith(".env.") and name != ".env.example"):
    print("Blocked: edit .env.example instead; real .env files hold secrets.", file=sys.stderr)
    sys.exit(2)
sys.exit(0)
