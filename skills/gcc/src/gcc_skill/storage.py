from __future__ import annotations

import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from .lock import file_lock

COMMIT_SEPARATOR = "=== Commit ==="
DEFAULT_SESSION = "default"


def normalize_session_id(session_id: Optional[str]) -> str:
    if not session_id:
        return DEFAULT_SESSION
    if not re.match(r"^[A-Za-z0-9_-]+$", session_id):
        raise ValueError("session_id must be alphanumeric with optional '-' or '_' only")
    return session_id


def _now_iso() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def gcc_root(root: Path) -> Path:
    return root / ".GCC"


def session_root(root: Path, session_id: str) -> Path:
    return gcc_root(root) / "sessions" / session_id


def branches_root(root: Path, session_id: str) -> Path:
    return session_root(root, session_id) / "branches"


def branch_root(root: Path, session_id: str, branch: str) -> Path:
    return branches_root(root, session_id) / branch


def main_path(root: Path, session_id: str) -> Path:
    return session_root(root, session_id) / "main.md"


def commit_path(root: Path, session_id: str, branch: str) -> Path:
    return branch_root(root, session_id, branch) / "commit.md"


def log_path(root: Path, session_id: str, branch: str) -> Path:
    return branch_root(root, session_id, branch) / "log.md"


def metadata_path(root: Path, session_id: str, branch: str) -> Path:
    return branch_root(root, session_id, branch) / "metadata.yaml"


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)


def _append_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(content)


def ensure_gcc(root: Path, goal: Optional[str], todo: Optional[List[str]], session_id: str) -> None:
    gcc_root(root).mkdir(parents=True, exist_ok=True)
    session_root(root, session_id).mkdir(parents=True, exist_ok=True)
    branches_root(root, session_id).mkdir(parents=True, exist_ok=True)
    if not main_path(root, session_id).exists():
        lines = ["# GCC Roadmap", "", "## Goal", goal or "(unset)", "", "## Todo"]
        if todo:
            lines.extend([f"- {item}" for item in todo])
        else:
            lines.append("- (none)")
        _write_text(main_path(root, session_id), "\n".join(lines) + "\n")


def ensure_branch(root: Path, session_id: str, branch: str, purpose: str) -> None:
    b_root = branch_root(root, session_id, branch)
    b_root.mkdir(parents=True, exist_ok=True)
    if not commit_path(root, session_id, branch).exists():
        header = [f"# Branch: {branch}", f"# Purpose: {purpose}", ""]
        _write_text(commit_path(root, session_id, branch), "\n".join(header) + "\n")
    log_path(root, session_id, branch).touch(exist_ok=True)
    if not metadata_path(root, session_id, branch).exists():
        _write_text(
            metadata_path(root, session_id, branch),
            yaml.safe_dump({"file_structure": {}, "env_config": {}}),
        )


def list_branches(root: Path, session_id: str) -> List[str]:
    if not branches_root(root, session_id).exists():
        return []
    return sorted([p.name for p in branches_root(root, session_id).iterdir() if p.is_dir()])


def read_main(root: Path, session_id: str) -> str:
    if not main_path(root, session_id).exists():
        return ""
    return main_path(root, session_id).read_text(encoding="utf-8")


def update_main(root: Path, session_id: str, update_text: str) -> None:
    content = read_main(root, session_id)
    if content:
        content = content.rstrip() + "\n\n" + update_text.strip() + "\n"
    else:
        content = update_text.strip() + "\n"
    _write_text(main_path(root, session_id), content)


def append_log(root: Path, session_id: str, branch: str, entries: List[str]) -> None:
    if not entries:
        return
    timestamp = _now_iso()
    block = [f"[{timestamp}]"] + [f"- {item}" for item in entries] + [""]
    _append_text(log_path(root, session_id, branch), "\n".join(block))


def _parse_commits(text: str) -> List[Dict[str, str]]:
    commits: List[Dict[str, str]] = []
    if COMMIT_SEPARATOR not in text:
        return commits
    parts = text.split(COMMIT_SEPARATOR)
    for part in parts[1:]:
        entry = {}
        lines = [line.rstrip() for line in part.strip().splitlines()]
        current_key = None
        buffer: List[str] = []
        for line in lines:
            if line.startswith("Commit ID:"):
                entry["commit_id"] = line.split(":", 1)[1].strip()
            elif line.startswith("Timestamp:"):
                entry["timestamp"] = line.split(":", 1)[1].strip()
            elif line.endswith(":"):
                if current_key and buffer:
                    entry[current_key] = "\n".join(buffer).strip()
                current_key = line[:-1]
                buffer = []
            else:
                buffer.append(line)
        if current_key and buffer:
            entry[current_key] = "\n".join(buffer).strip()
        commits.append(entry)
    return commits


def get_branch_purpose(root: Path, session_id: str, branch: str) -> str:
    if not commit_path(root, session_id, branch).exists():
        return ""
    text = commit_path(root, session_id, branch).read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.startswith("# Purpose:"):
            return line.split(":", 1)[1].strip()
    return ""


def get_commit_entry(root: Path, session_id: str, branch: str, commit_id: str) -> Optional[str]:
    if not commit_path(root, session_id, branch).exists():
        return None
    text = commit_path(root, session_id, branch).read_text(encoding="utf-8")
    if COMMIT_SEPARATOR not in text:
        return None
    parts = text.split(COMMIT_SEPARATOR)
    for part in parts[1:]:
        if f"Commit ID: {commit_id}" in part:
            return COMMIT_SEPARATOR + part
    return None


def append_commit(
    root: Path,
    session_id: str,
    branch: str,
    purpose: str,
    contribution: str,
) -> str:
    commit_id = uuid.uuid4().hex[:8]
    existing = commit_path(root, session_id, branch).read_text(encoding="utf-8")
    commits = _parse_commits(existing)
    if commits:
        prev_summary = commits[-1].get("Previous Progress Summary", "")
        last_contrib = commits[-1].get("This Commit's Contribution", "")
        combined = "\n".join([line for line in [prev_summary, last_contrib] if line]).strip()
    else:
        combined = ""
    prev_block = combined if combined else "(none)"

    entry_lines = [
        COMMIT_SEPARATOR,
        f"Commit ID: {commit_id}",
        f"Timestamp: {_now_iso()}",
        "Branch Purpose:",
        purpose,
        "Previous Progress Summary:",
        prev_block,
        "This Commit's Contribution:",
        contribution,
        "",
    ]
    _append_text(commit_path(root, session_id, branch), "\n".join(entry_lines))
    return commit_id


def read_log_tail(root: Path, session_id: str, branch: str, tail: int) -> List[str]:
    if not log_path(root, session_id, branch).exists():
        return []
    lines = log_path(root, session_id, branch).read_text(encoding="utf-8").splitlines()
    if tail <= 0:
        return []
    return lines[-tail:]


def read_metadata(root: Path, session_id: str, branch: str) -> Dict[str, Any]:
    if not metadata_path(root, session_id, branch).exists():
        return {}
    data = yaml.safe_load(metadata_path(root, session_id, branch).read_text(encoding="utf-8"))
    return data or {}


def update_metadata(root: Path, session_id: str, branch: str, updates: Dict[str, Any]) -> None:
    data = read_metadata(root, session_id, branch)
    for key, value in updates.items():
        if value is None:
            data.pop(key, None)
        else:
            data[key] = value
    _write_text(metadata_path(root, session_id, branch), yaml.safe_dump(data, sort_keys=False))


def with_lock(root: Path, session_id: str, func, *args, **kwargs):
    lock_path = session_root(root, session_id) / ".lock"
    with file_lock(lock_path):
        return func(*args, **kwargs)
