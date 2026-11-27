# air-agents-helper

Claude Code plugin for developing the AIR AGENTS API.

| Component | Name |
|---|---|
| Skills | `lending-desk-compliance`, `add-v1-route` |
| Commands | `/air-agents-helper:test`, `:new-route`, `:compliance-check` |
| Agent | `api-reviewer` |
| Hook | PreToolUse guard blocking edits to real `.env` files |

## Try it

```bash
claude --plugin-dir ./plugins/air-agents-helper
# or via marketplace:
/plugin marketplace add ./ && /plugin install air-agents-helper@air-brain-plugins
```

No MCP server is bundled; add a `.mcp.json` here if you want one.
