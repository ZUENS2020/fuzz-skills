from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, Optional

import httpx

SERVER_URL_ENV = "GCC_SERVER_URL"
SESSION_ID_ENV = "GCC_SESSION_ID"
DEFAULT_SERVER_URL = "http://localhost:8000"
DEFAULT_SESSION_ID = None

COMMIT_PROMPT_GUIDE = (
    "Commit guidance: every gcc_commit should include a clear contribution summary, "
    "key observations/actions in log_entries, and any file/module changes in metadata_updates. "
    "Update main milestones via update_main when needed."
)

TOOLS = [
    {
        "name": "gcc_init",
        "description": "Initialize a session memory store under .GCC/sessions/<session_id>/. Creates main.md (goal + todo) and prepares a git-backed workspace for memory commits.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "root": {"type": "string"},
                "goal": {"type": "string"},
                "todo": {"type": "array", "items": {"type": "string"}},
                "session_id": {"type": "string"},
            },
            "required": ["root"],
        },
    },
    {
        "name": "gcc_branch",
        "description": "Create a memory branch within the session. Writes commit.md/log.md/metadata.yaml and creates a git branch for isolated exploration.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "root": {"type": "string"},
                "branch": {"type": "string"},
                "purpose": {"type": "string"},
                "session_id": {"type": "string"},
            },
            "required": ["root", "branch", "purpose"],
        },
    },
    {
        "name": "gcc_commit",
        "description": "Record a structured memory checkpoint. Appends to commit.md, optionally adds OTA log entries and metadata updates, updates main.md, and creates a git commit. "
        + COMMIT_PROMPT_GUIDE,
        "inputSchema": {
            "type": "object",
            "properties": {
                "root": {"type": "string"},
                "branch": {"type": "string"},
                "contribution": {"type": "string"},
                "purpose": {"type": "string"},
                "log_entries": {"type": "array", "items": {"type": "string"}},
                "metadata_updates": {"type": "object"},
                "update_main": {"type": "string"},
                "session_id": {"type": "string"},
            },
            "required": ["root", "branch", "contribution"],
        },
    },
    {
        "name": "gcc_merge",
        "description": "Merge a source memory branch into a target branch (default main). Performs git merge and updates main.md plus merged commit/log/metadata content.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "root": {"type": "string"},
                "source_branch": {"type": "string"},
                "target_branch": {"type": "string"},
                "summary": {"type": "string"},
                "session_id": {"type": "string"},
            },
            "required": ["root", "source_branch"],
        },
    },
    {
        "name": "gcc_context",
        "description": "Retrieve structured context at multiple levels: project overview, branch summaries, commit entry, log tail, or a metadata segment.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "root": {"type": "string"},
                "branch": {"type": "string"},
                "commit_id": {"type": "string"},
                "log_tail": {"type": "integer"},
                "metadata_segment": {"type": "string"},
                "session_id": {"type": "string"},
            },
            "required": ["root"],
        },
    },
    {
        "name": "gcc_log",
        "description": "Append fine-grained OTA log entries to branch log.md and record a git commit for traceability.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "root": {"type": "string"},
                "branch": {"type": "string"},
                "entries": {"type": "array", "items": {"type": "string"}},
                "session_id": {"type": "string"},
            },
            "required": ["root", "branch", "entries"],
        },
    },
    {
        "name": "gcc_history",
        "description": "List git commit history for the session repository. Each entry reflects a memory change checkpoint.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "root": {"type": "string"},
                "limit": {"type": "integer"},
                "session_id": {"type": "string"},
            },
            "required": ["root"],
        },
    },
    {
        "name": "gcc_diff",
        "description": "Show git diff between two refs to compare memory changes (e.g., HEAD~1..HEAD).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "root": {"type": "string"},
                "from_ref": {"type": "string"},
                "to_ref": {"type": "string"},
                "session_id": {"type": "string"},
            },
            "required": ["root", "from_ref"],
        },
    },
    {
        "name": "gcc_show",
        "description": "Show file content at a git ref (e.g., main.md or branches/<branch>/commit.md) to inspect memory before/after changes.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "root": {"type": "string"},
                "ref": {"type": "string"},
                "path": {"type": "string"},
                "session_id": {"type": "string"},
            },
            "required": ["root", "ref"],
        },
    },
    {
        "name": "gcc_reset",
        "description": "Reset the session git repo to a ref. Use mode=soft or hard; hard reset requires confirm=true.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "root": {"type": "string"},
                "ref": {"type": "string"},
                "mode": {"type": "string"},
                "confirm": {"type": "boolean"},
                "session_id": {"type": "string"},
            },
            "required": ["root", "ref"],
        },
    },
]


def _server_url() -> str:
    return os.environ.get(SERVER_URL_ENV, DEFAULT_SERVER_URL).rstrip("/")


def _default_session_id() -> str:
    # Priority 1: Explicit environment variable (GCC_SESSION_ID)
    env_value = os.environ.get(SESSION_ID_ENV)
    if env_value:
        return env_value

    # Priority 2: Try to get container ID from Docker environment
    # Docker sets hostname to container ID
    try:
        hostname = os.environ.get("HOSTNAME", "")
        if hostname and len(hostname) >= 12:
            # Container IDs are typically 64 hex chars, use first 12
            global DEFAULT_SESSION_ID
            if DEFAULT_SESSION_ID is None:
                DEFAULT_SESSION_ID = f"container-{hostname[:12]}"
            return DEFAULT_SESSION_ID
    except Exception:
        pass

    # Priority 3: Fallback to process ID
    global DEFAULT_SESSION_ID
    if DEFAULT_SESSION_ID is None:
        DEFAULT_SESSION_ID = f"mcp-{os.getpid()}"
    return DEFAULT_SESSION_ID


def _ensure_session_id(arguments: Dict[str, Any]) -> Dict[str, Any]:
    if "session_id" not in arguments or not arguments.get("session_id"):
        arguments = dict(arguments)
        arguments["session_id"] = _default_session_id()
    return arguments


def _post(path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    url = f"{_server_url()}{path}"
    with httpx.Client(timeout=30.0) as client:
        response = client.post(url, json=payload)
        response.raise_for_status()
        return response.json()


def _handle_tools_call(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    mapping = {
        "gcc_init": "/init",
        "gcc_branch": "/branch",
        "gcc_commit": "/commit",
        "gcc_merge": "/merge",
        "gcc_context": "/context",
        "gcc_log": "/log",
        "gcc_history": "/history",
        "gcc_diff": "/diff",
        "gcc_show": "/show",
        "gcc_reset": "/reset",
    }
    if tool_name not in mapping:
        raise ValueError(f"Unknown tool: {tool_name}")
    payload = _ensure_session_id(arguments)
    return _post(mapping[tool_name], payload)


def _write_response(payload: Dict[str, Any]) -> None:
    # Use ensure_ascii=False to properly handle Unicode characters (e.g., Chinese)
    sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def _error_response(request_id: Optional[Any], message: str) -> Dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": -32000, "message": message},
    }


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
            request_id = request.get("id")
            method = request.get("method")
            params = request.get("params") or {}

            if method == "initialize":
                protocol = params.get("protocolVersion") if isinstance(params, dict) else None
                protocol = protocol or "2024-11-05"
                _write_response(
                    {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {
                            "protocolVersion": protocol,
                            "serverInfo": {"name": "gcc-mcp", "version": "0.1.0"},
                            "capabilities": {"tools": {}},
                        },
                    }
                )
                continue

            if method in ("initialized", "notifications/initialized") or (
                isinstance(method, str) and method.startswith("notifications/")
            ):
                # Notifications do not expect a response.
                continue

            if method == "tools/list":
                _write_response(
                    {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {"tools": TOOLS},
                    }
                )
                continue

            if method == "ping":
                _write_response({"jsonrpc": "2.0", "id": request_id, "result": {}})
                continue

            if method == "resources/list":
                _write_response({"jsonrpc": "2.0", "id": request_id, "result": {"resources": []}})
                continue

            if method == "prompts/list":
                _write_response({"jsonrpc": "2.0", "id": request_id, "result": {"prompts": []}})
                continue

            if method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments") or {}
                result = _handle_tools_call(tool_name, arguments)
                _write_response(
                    {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}]},
                    }
                )
                continue

            if method in ("shutdown", "exit"):
                _write_response({"jsonrpc": "2.0", "id": request_id, "result": {}})
                break

            if request_id is not None:
                _write_response(_error_response(request_id, f"Unsupported method: {method}"))
        except Exception as exc:
            if "request_id" in locals() and request_id is not None:
                _write_response(_error_response(request_id, str(exc)))


if __name__ == "__main__":
    main()
