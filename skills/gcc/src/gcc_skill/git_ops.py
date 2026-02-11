from __future__ import annotations

import os
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Iterable, List, Optional

DEFAULT_NAME = "gcc-skill"
DEFAULT_EMAIL = "gcc-skill@localhost"


def _log_path(repo_root: Path) -> Path:
    return repo_root / "git.log"


def _append_git_log(repo_root: Path, args: List[str], result: subprocess.CompletedProcess) -> None:
    timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [
        f"[{timestamp}] git {' '.join(args)}",
        f"exit={result.returncode}",
    ]
    if result.stdout:
        lines.append("stdout:")
        lines.append(result.stdout.rstrip())
    if result.stderr:
        lines.append("stderr:")
        lines.append(result.stderr.rstrip())
    lines.append("")
    _log_path(repo_root).parent.mkdir(parents=True, exist_ok=True)
    with _log_path(repo_root).open("a", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def _run_git(args: List[str], cwd: Path) -> subprocess.CompletedProcess:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=str(cwd),
            check=True,
            capture_output=True,
            text=True,
        )
        _append_git_log(cwd, args, result)
        return result
    except subprocess.CalledProcessError as exc:
        _append_git_log(cwd, args, exc)
        raise


def _try_git(args: List[str], cwd: Path) -> Optional[str]:
    try:
        result = _run_git(args, cwd)
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return None


def ensure_repo(repo_root: Path) -> None:
    repo_root.mkdir(parents=True, exist_ok=True)
    if not (repo_root / ".git").exists():
        _run_git(["init", "-b", "main"], repo_root)
    _ensure_identity(repo_root)
    _ensure_initial_commit(repo_root)


def _ensure_identity(repo_root: Path) -> None:
    name = _try_git(["config", "--get", "user.name"], repo_root)
    email = _try_git(["config", "--get", "user.email"], repo_root)
    if not name:
        _run_git(["config", "user.name", DEFAULT_NAME], repo_root)
    if not email:
        _run_git(["config", "user.email", DEFAULT_EMAIL], repo_root)


def _ensure_initial_commit(repo_root: Path) -> None:
    head = _try_git(["rev-parse", "--verify", "HEAD"], repo_root)
    if head:
        return
    _run_git(["add", "-A"], repo_root)
    _run_git(["commit", "--allow-empty", "-m", "GCC init"], repo_root)


def current_branch(repo_root: Path) -> str:
    name = _run_git(["rev-parse", "--abbrev-ref", "HEAD"], repo_root).stdout.strip()
    return name or "main"


def checkout_branch(repo_root: Path, branch: str) -> None:
    _run_git(["checkout", "-B", branch], repo_root)


def add_and_commit(repo_root: Path, paths: Iterable[Path], message: str) -> None:
    rel_paths = [str(p.relative_to(repo_root)) for p in paths]
    if not rel_paths:
        return
    _run_git(["add", *rel_paths], repo_root)
    if _try_git(["diff", "--cached", "--quiet"], repo_root) is None:
        _run_git(["commit", "-m", message], repo_root)


def merge_branch(repo_root: Path, source: str, message: str) -> None:
    _run_git(["merge", "--no-ff", source, "-m", message], repo_root)


def git_log(repo_root: Path, limit: int = 20) -> List[dict]:
    result = _run_git(
        ["log", f"-n{max(1, limit)}", "--pretty=format:%H|%ct|%s"],
        repo_root,
    )
    entries = []
    for line in result.stdout.splitlines():
        parts = line.split("|", 2)
        if len(parts) != 3:
            continue
        entries.append({"hash": parts[0], "timestamp": int(parts[1]), "subject": parts[2]})
    return entries


def git_diff(repo_root: Path, from_ref: str, to_ref: Optional[str]) -> str:
    if to_ref:
        args = ["diff", f"{from_ref}..{to_ref}"]
    else:
        args = ["diff", from_ref]
    return _run_git(args, repo_root).stdout


def git_show(repo_root: Path, ref: str, path: Optional[str]) -> str:
    if path:
        return _run_git(["show", f"{ref}:{path}"], repo_root).stdout
    return _run_git(["show", ref], repo_root).stdout


def git_reset(repo_root: Path, ref: str, mode: str) -> None:
    if mode not in {"soft", "hard"}:
        raise ValueError("reset mode must be 'soft' or 'hard'")
    _run_git(["reset", f"--{mode}", ref], repo_root)
