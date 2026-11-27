---
description: Run the AIR AGENTS API test suite (optionally filtered) and summarize failures
argument-hint: "[pytest -k expression]"
allowed-tools: Bash(python:*), Bash(python3:*), Bash(pip:*), Bash(PYTHONPATH=. pytest:*)
---

Run the test suite from the repo root:

`PYTHONPATH=. pytest -q $ARGUMENTS`

If imports fail, run `python -m pip install -r requirements.txt` once and retry. Summarize any failures with file, test name, and likely cause; do not modify tests to make them pass without explaining why.
