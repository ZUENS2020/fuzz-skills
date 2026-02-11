# GCC Context Controller Skill

## Summary
HTTP API server that implements the Git-Context-Controller (GCC) memory system from the paper, providing structured context management via COMMIT, BRANCH, MERGE, and CONTEXT operations with per-session isolation. Each session is backed by a git repo. Includes a stdio MCP proxy that forwards tool calls to the HTTP server.

## When to use
- You need long-horizon agent memory with checkpoints, branches, and merges.
- You want a project-level, inspectable context log stored in a .GCC/ folder.

## Tools
- HTTP endpoints: /init, /branch, /commit, /merge, /context, /log, /history, /diff, /show, /reset (all accept optional session_id; default is "default")
- MCP proxy tools (detailed): gcc_init initializes .GCC/sessions/<session_id>/, creates main.md and git repo
- gcc_branch creates branch files and a git branch for isolated memory work
- gcc_commit writes structured commit.md, updates log/metadata/main, and git commits
- gcc_merge merges memory branches and updates main.md plus git merge
- gcc_context reads project/branch/commit/log/metadata views
- gcc_log appends OTA logs and commits them
- gcc_history lists git history for memory checkpoints
- gcc_diff diffs memory changes between refs
- gcc_show shows memory files at a ref
- gcc_reset resets memory to a ref (soft/hard)

## Install
- Python: pip install -e .
- Run: uvicorn gcc_skill.server:app --host 0.0.0.0 --port 8000
- Docker: docker volume create gcc_data && docker run --rm -p 8000:8000 -e GCC_DATA_ROOT=/data -v gcc_data:/data gcc-skill:latest
- MCP: set GCC_SERVER_URL=http://localhost:8000 && gcc-mcp (auto session_id; override with GCC_SESSION_ID)

## Notes
- All operations write to a .GCC/ folder under the provided project root.
- Sessions are isolated under .GCC/sessions/<session_id>/.
- File structure follows the paper: main.md, branches/<branch>/commit.md, log.md, metadata.yaml.
- Requires git on PATH.
- Container mode should mount a volume and set GCC_DATA_ROOT to keep memory data.