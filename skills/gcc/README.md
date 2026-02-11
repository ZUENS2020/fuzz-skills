# GCC Context Controller (HTTP Skill)

This server implements the Git-Context-Controller (GCC) memory system as described in the paper. It exposes an HTTP API that manages a .GCC/ folder inside a project root.
Each session is backed by a git repository under .GCC/sessions/<session_id>/, so COMMIT/BRANCH/MERGE map to git operations within that repo.
Multiple sessions are isolated by session_id under .GCC/sessions/<session_id>/. If omitted, session_id defaults to "default".

## Run

```bash
pip install -e .
uvicorn gcc_skill.server:app --host 0.0.0.0 --port 8000
```

## Docker

Build and run:

```bash
docker build -t gcc-skill:latest .
docker run --rm -p 8000:8000 gcc-skill:latest
```

Or with compose:

```bash
docker compose up --build
```

## MCP Proxy

This project includes a stdio MCP proxy that forwards tool calls to the HTTP server.

Start the HTTP server (local or container), then in the MCP environment:

```bash
set GCC_SERVER_URL=http://localhost:8000
gcc-mcp
```

If you use Claude Code, add the proxy as a stdio MCP server:

```bash
claude mcp add --scope user --transport stdio gcc -- gcc-mcp
```

## API

### POST /init
Create the .GCC/ structure and main.md.

Request:
```json
{
  "root": "C:/path/to/project",
  "goal": "High-level project goal",
  "todo": ["task 1", "task 2"],
  "session_id": "claude-1"
}
```

### POST /branch
Create a branch and its files.

Request:
```json
{
  "root": "C:/path/to/project",
  "branch": "experiment-a",
  "purpose": "Explore an alternative approach",
  "session_id": "claude-1"
}
```

### POST /commit
Record a milestone with a structured commit entry.

Request:
```json
{
  "root": "C:/path/to/project",
  "branch": "experiment-a",
  "contribution": "Implemented parser and added tests",
  "purpose": "Optional if branch already exists",
  "log_entries": ["Observed X", "Action Y"],
  "metadata_updates": {"file_structure": {"src/": "core"}},
  "update_main": "Updated milestone list",
  "session_id": "claude-1"
}
```

### POST /merge
Merge one branch into another (default target is main).

Request:
```json
{
  "root": "C:/path/to/project",
  "source_branch": "experiment-a",
  "target_branch": "main",
  "summary": "Merged parser implementation",
  "session_id": "claude-1"
}
```

### POST /context
Retrieve structured context.

Request:
```json
{
  "root": "C:/path/to/project",
  "branch": "experiment-a",
  "commit_id": "optional",
  "log_tail": 20,
  "metadata_segment": "file_structure",
  "session_id": "claude-1"
}
```

### POST /log
Append OTA log entries to a branch log.

Request:
```json
{
  "root": "C:/path/to/project",
  "branch": "experiment-a",
  "entries": ["Observation", "Thought", "Action"],
  "session_id": "claude-1"
}

### POST /history
List git history for the session repository.

Request:
```json
{
  "root": "C:/path/to/project",
  "limit": 20,
  "session_id": "claude-1"
}
```

### POST /diff
Show git diff between two refs (memory changes).

Request:
```json
{
  "root": "C:/path/to/project",
  "from_ref": "HEAD~1",
  "to_ref": "HEAD",
  "session_id": "claude-1"
}
```

### POST /show
Show file content at a git ref (view memory before changes).

Request:
```json
{
  "root": "C:/path/to/project",
  "ref": "HEAD~1",
  "path": "main.md",
  "session_id": "claude-1"
}
```

### POST /reset
Reset the session git repo to a ref.

Request:
```json
{
  "root": "C:/path/to/project",
  "ref": "HEAD~1",
  "mode": "hard",
  "confirm": true,
  "session_id": "claude-1"
}
```
```

## Notes
- The .GCC/ layout matches the paper specification.
- session_id isolates multiple agent sessions under one server.
- Git must be installed and available on PATH.
- All files are plain text; metadata is YAML.
