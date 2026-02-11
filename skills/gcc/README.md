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
docker volume create gcc_data
docker run --rm -p 8000:8000 -e GCC_DATA_ROOT=/data -v gcc_data:/data gcc-skill:latest
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

# GCC Context Controller (HTTP + MCP)

本项目实现论文中的 Git-Context-Controller (GCC) 记忆系统，并提供 HTTP API 与 MCP stdio 代理两种使用方式。系统会把记忆写入 .GCC/ 目录，并在每次记忆变更时写入 git 提交，便于回溯、对比和回滚。

每个会话由 session_id 隔离，路径为 .GCC/sessions/<session_id>/。每个会话内部是一个独立的 git 仓库，COMMIT/BRANCH/MERGE 等操作会映射为真实的 git 提交或合并。

## 功能概览

- 结构化记忆：main.md、commit.md、log.md、metadata.yaml
- 分支隔离与合并：BRANCH/MERGE 对应 git 分支与合并
- 记忆变更追踪：每次记忆变更产生 git commit
- 变更回看：history/diff/show/reset
- 多会话隔离：session_id 互不干扰

## 目录结构

```
.GCC/
  sessions/
    <session_id>/
      main.md
      branches/
        <branch>/
          commit.md
          log.md
          metadata.yaml
      .git/
      git.log
```

## 运行方式（本地）

```bash
pip install -e .
uvicorn gcc_skill.server:app --host 0.0.0.0 --port 8000
```

## 运行方式（Docker）

```bash
docker build -t gcc-skill:latest .
docker run --rm -p 8000:8000 gcc-skill:latest
```

或使用 compose：

```bash
docker compose up --build
```

## MCP 代理

本项目包含 stdio MCP 代理（gcc-mcp），负责把 MCP 工具调用转发到 HTTP 服务器。

代理会在未提供 session_id 时自动生成并复用一个会话标识。你也可以通过 GCC_SESSION_ID 手动指定。

启动 HTTP 服务后：

```bash
set GCC_SERVER_URL=http://localhost:8000
gcc-mcp
```

指定会话 ID：

```bash
set GCC_SESSION_ID=claude-1
gcc-mcp
```

如果你使用 Claude Code：

```bash
claude mcp add --scope user --transport stdio gcc -- gcc-mcp
```

## AI 提交要求（Prompt 建议）

为了让记忆提交内容结构化、可追溯，建议在提示词中明确要求 AI 每次调用提交工具时给出以下信息：

- 必填：本次完成了什么（contribution）
- 必填：关联的分支（branch）与会话（session_id，MCP 默认自动填）
- 建议：关键决策与原因（写入 log_entries）
- 建议：重要文件/模块变化（写入 metadata_updates）
- 可选：是否更新全局里程碑（update_main）

你可以在提示词里直接要求：

"每次完成一个里程碑都要调用 gcc_commit，且提供：contribution（本次完成点）、log_entries（关键观察/行动）、metadata_updates（文件结构变化）、必要时 update_main（更新计划）。"

## HTTP API

### POST /init
初始化会话与 .GCC 结构。

请求：
```json
{
  "root": "workspace/demo",
  "goal": "项目目标",
  "todo": ["任务1", "任务2"],
  "session_id": "claude-1"
}
```

### POST /branch
创建分支并生成 commit/log/metadata 文件。

请求：
```json
{
  "root": "workspace/demo",
  "branch": "experiment-a",
  "purpose": "探索一个替代方案",
  "session_id": "claude-1"
}
```

### POST /commit
提交一次结构化记忆检查点。

请求：
```json
{
  "root": "workspace/demo",
  "branch": "experiment-a",
  "contribution": "实现解析器并添加测试",
  "purpose": "如果分支尚不存在才需要",
  "log_entries": ["Observation A", "Action B"],
  "metadata_updates": {"file_structure": {"src/": "core"}},
  "update_main": "更新里程碑",
  "session_id": "claude-1"
}
```

### POST /merge
合并一个分支到目标分支（默认 main）。

请求：
```json
{
  "root": "workspace/demo",
  "source_branch": "experiment-a",
  "target_branch": "main",
  "summary": "合并解析器实现",
  "session_id": "claude-1"
}
```

### POST /context
读取结构化上下文。

请求：
```json
{
  "root": "workspace/demo",
  "branch": "experiment-a",
  "commit_id": "可选",
  "log_tail": 20,
  "metadata_segment": "file_structure",
  "session_id": "claude-1"
}
```

### POST /log
追加 OTA 日志。

请求：
```json
{
  "root": "workspace/demo",
  "branch": "experiment-a",
  "entries": ["Observation", "Thought", "Action"],
  "session_id": "claude-1"
}
```

### POST /history
查看会话 git 提交历史。

请求：
```json
{
  "root": "workspace/demo",
  "limit": 20,
  "session_id": "claude-1"
}
```

### POST /diff
对比两次记忆变更的差异。

请求：
```json
{
  "root": "workspace/demo",
  "from_ref": "HEAD~1",
  "to_ref": "HEAD",
  "session_id": "claude-1"
}
```

### POST /show
查看某个版本的文件内容（记忆回看）。

请求：
```json
{
  "root": "workspace/demo",
  "ref": "HEAD~1",
  "path": "main.md",
  "session_id": "claude-1"
}
```

### POST /reset
回滚到指定版本（soft 或 hard）。

请求：
```json
{
  "root": "workspace/demo",
  "ref": "HEAD~1",
  "mode": "hard",
  "confirm": true,
  "session_id": "claude-1"
}
```

## MCP 工具（对应 HTTP）

```
gcc_init      -> /init
gcc_branch    -> /branch
gcc_commit    -> /commit
gcc_merge     -> /merge
gcc_context   -> /context
gcc_log       -> /log
gcc_history   -> /history
gcc_diff      -> /diff
gcc_show      -> /show
gcc_reset     -> /reset
```

## 注意事项

- 容器模式推荐使用持久卷并设置 GCC_DATA_ROOT=/data，防止数据丢失。
- root 建议使用相对路径（例如 workspace/demo），会映射到容器数据根目录。
- 必须安装 git 并确保在 PATH 中可用。
- session_id 为空时默认使用 "default"。
- git 操作日志会写入 .GCC/sessions/<session_id>/git.log。
- 所有文件均为纯文本；metadata 使用 YAML。
