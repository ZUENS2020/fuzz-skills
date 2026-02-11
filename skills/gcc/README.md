# GCC Context Controller

Git-Context-Controller (GCC) memory system with MCP integration. Manages structured memory with git-backed version control.

## Quick Start

### Docker Compose (Recommended)

```bash
docker compose up -d --build
```

The service will be available at `http://localhost:8000`.

### Docker Run

```bash
docker build -t gcc-skill:latest .
docker volume create gcc_data
docker run -d --name gcc -p 8000:8000 \
  -v gcc_data:/data \
  gcc-skill:latest
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GCC_DATA_ROOT` | Base path for data storage | `/data` |
| `GCC_SESSION_ID` | Custom session ID for container isolation | Auto-detected from hostname |
| `GCC_SERVER_URL` | HTTP server URL for MCP proxy | `http://localhost:8000` |

### Session ID Priority

1. `GCC_SESSION_ID` environment variable (highest priority)
2. Container hostname (Docker auto-detects, uses first 12 chars)
3. Fallback to `default`

### Examples

Set a custom session ID:

```bash
docker run -d --name gcc -p 8000:8000 \
  -v gcc_data:/data \
  -e GCC_SESSION_ID=my-custom-session \
  gcc-skill:latest
```

Data will be stored under `/data/my-custom-session/.GCC/`.

## MCP Integration

Install the MCP proxy:

```bash
pip install -e skills/gcc
```

Set the server URL and start the proxy:

```bash
export GCC_SERVER_URL=http://localhost:8000
gcc-mcp
```

Add to Claude Code:

```bash
claude mcp add --scope user --transport stdio gcc -- gcc-mcp
```

## API

### POST /init
Initialize a session.

```json
{
  "root": "project-path",
  "goal": "Project goal",
  "todo": ["task1", "task2"],
  "session_id": "my-session"
}
```

### POST /branch
Create a memory branch.

```json
{
  "root": "project-path",
  "branch": "feature-branch",
  "purpose": "Branch purpose",
  "session_id": "my-session"
}
```

### POST /commit
Create a memory checkpoint.

```json
{
  "root": "project-path",
  "branch": "feature-branch",
  "contribution": "What was accomplished",
  "log_entries": ["Observation 1", "Action 1"],
  "metadata_updates": {"key": "value"},
  "session_id": "my-session"
}
```

### POST /context
Retrieve structured context.

```json
{
  "root": "project-path",
  "branch": "feature-branch",
  "session_id": "my-session"
}
```

## Data Structure

```
/data/
└── <session_id>/
    └── .GCC/
        └── sessions/
            └── <session_id>/
                ├── main.md              # Project goal and todos
                └── branches/
                    └── <branch>/
                        ├── commit.md   # Commit history
                        ├── log.md      # Detailed logs
                        └── metadata.yaml  # Structured metadata
```

## License

MIT
