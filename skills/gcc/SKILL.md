# GCC Context Controller Skill

## Summary
HTTP API server that implements the Git-Context-Controller (GCC) memory system from the paper, providing structured context management via COMMIT, BRANCH, MERGE, and CONTEXT operations with per-session isolation. Each session is backed by a git repo. Includes a stdio MCP proxy that forwards tool calls to the HTTP server.

## When to use
- You need long-horizon agent memory with checkpoints, branches, and merges.
- You want a project-level, inspectable context log stored in a .GCC/ folder.

## Tools
- HTTP endpoints: /init, /branch, /commit, /merge, /context, /log, /history, /diff, /show, /reset (all accept optional session_id; default is "default")
- MCP proxy tools: gcc_init, gcc_branch, gcc_commit, gcc_merge, gcc_context, gcc_log, gcc_history, gcc_diff, gcc_show, gcc_reset

## Install
- Python: pip install -e .
- Run: uvicorn gcc_skill.server:app --host 0.0.0.0 --port 8000
- MCP: set GCC_SERVER_URL=http://localhost:8000 && gcc-mcp

## Notes
- All operations write to a .GCC/ folder under the provided project root.
- Sessions are isolated under .GCC/sessions/<session_id>/.
- File structure follows the paper: main.md, branches/<branch>/commit.md, log.md, metadata.yaml.
- Requires git on PATH.