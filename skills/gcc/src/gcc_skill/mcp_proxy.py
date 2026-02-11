from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, Optional

import httpx

SERVER_URL_ENV = "GCC_SERVER_URL"
DEFAULT_SERVER_URL = "http://localhost:8000"

TOOLS = [
    {
        "name": "gcc_init",
        "description": "Initialize a .GCC/ session store",
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
        "description": "Create a branch for a session",
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
        "description": "Record a structured commit entry",
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
        "description": "Merge one branch into another",
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
        "description": "Retrieve structured context",
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
        "description": "Append OTA log entries",
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
        "description": "List git history for a session",
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
        "description": "Show diff between two git refs",
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
        "description": "Show a file or commit content at a git ref",
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
        "description": "Reset the session git repo to a ref",
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
    return _post(mapping[tool_name], arguments)


def _write_response(payload: Dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(payload) + "\n")
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
                _write_response(
                    {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {
                            "serverInfo": {"name": "gcc-mcp", "version": "0.1.0"},
                            "capabilities": {"tools": {}},
                        },
                    }
                )
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

            if method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments") or {}
                result = _handle_tools_call(tool_name, arguments)
                _write_response(
                    {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {"content": [{"type": "text", "text": json.dumps(result)}]},
                    }
                )
                continue

            if method in ("shutdown", "exit"):
                _write_response({"jsonrpc": "2.0", "id": request_id, "result": {}})
                break

            _write_response(_error_response(request_id, f"Unsupported method: {method}"))
        except Exception as exc:
            _write_response(_error_response(None, str(exc)))


if __name__ == "__main__":
    main()
