from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from . import storage
from .git_ops import (
    add_and_commit,
    checkout_branch,
    ensure_repo,
    git_diff,
    git_log,
    git_reset,
    git_show,
    merge_branch,
)


class GCCError(ValueError):
    pass


def init(
    root: Path,
    goal: Optional[str],
    todo: Optional[List[str]],
    session_id: Optional[str],
) -> Dict[str, Any]:
    session = storage.normalize_session_id(session_id)
    def _run() -> Dict[str, Any]:
        storage.ensure_gcc(root, goal, todo, session)
        ensure_repo(storage.session_root(root, session))
        return {
            "gcc_root": str(storage.gcc_root(root)),
            "session": session,
            "main": str(storage.main_path(root, session)),
        }

    return storage.with_lock(root, session, _run)


def branch(
    root: Path,
    branch_name: str,
    purpose: str,
    session_id: Optional[str],
) -> Dict[str, Any]:
    if not branch_name:
        raise GCCError("branch name is required")
    if not purpose:
        raise GCCError("branch purpose is required")
    session = storage.normalize_session_id(session_id)
    def _run() -> Dict[str, Any]:
        storage.ensure_gcc(root, None, None, session)
        repo_root = storage.session_root(root, session)
        ensure_repo(repo_root)
        checkout_branch(repo_root, branch_name)
        storage.ensure_branch(root, session, branch_name, purpose)
        add_and_commit(
            repo_root,
            [
                storage.commit_path(root, session, branch_name),
                storage.log_path(root, session, branch_name),
                storage.metadata_path(root, session, branch_name),
            ],
            f"GCC branch {branch_name}",
        )
        return {"branch": branch_name, "purpose": purpose, "session": session}

    return storage.with_lock(root, session, _run)


def log(
    root: Path,
    branch_name: str,
    entries: List[str],
    session_id: Optional[str],
) -> Dict[str, Any]:
    if not branch_name:
        raise GCCError("branch name is required")
    session = storage.normalize_session_id(session_id)
    def _run() -> Dict[str, Any]:
        storage.ensure_gcc(root, None, None, session)
        repo_root = storage.session_root(root, session)
        ensure_repo(repo_root)
        if branch_name not in storage.list_branches(root, session):
            raise GCCError(f"branch not found: {branch_name}")
        checkout_branch(repo_root, branch_name)
        storage.append_log(root, session, branch_name, entries)
        add_and_commit(
            repo_root,
            [storage.log_path(root, session, branch_name)],
            f"GCC log {branch_name}",
        )
        return {"branch": branch_name, "entries": len(entries), "session": session}

    return storage.with_lock(root, session, _run)


def commit(
    root: Path,
    branch_name: str,
    contribution: str,
    purpose: Optional[str],
    log_entries: Optional[List[str]],
    metadata_updates: Optional[Dict[str, Any]],
    update_main_text: Optional[str],
    session_id: Optional[str],
) -> Dict[str, Any]:
    if not branch_name:
        raise GCCError("branch name is required")
    if not contribution:
        raise GCCError("contribution is required")
    session = storage.normalize_session_id(session_id)

    def _run() -> Dict[str, Any]:
        storage.ensure_gcc(root, None, None, session)
        repo_root = storage.session_root(root, session)
        ensure_repo(repo_root)
        if branch_name not in storage.list_branches(root, session):
            if not purpose:
                raise GCCError("branch does not exist; purpose is required to create it")
            storage.ensure_branch(root, session, branch_name, purpose)
        checkout_branch(repo_root, branch_name)
        branch_purpose = storage.get_branch_purpose(root, session, branch_name) or (purpose or "")

        if log_entries:
            storage.append_log(root, session, branch_name, log_entries)
        if metadata_updates:
            storage.update_metadata(root, session, branch_name, metadata_updates)

        commit_id = storage.append_commit(root, session, branch_name, branch_purpose, contribution)

        if update_main_text:
            storage.update_main(root, session, update_main_text)

        add_and_commit(
            repo_root,
            [
                storage.commit_path(root, session, branch_name),
                storage.log_path(root, session, branch_name),
                storage.metadata_path(root, session, branch_name),
                storage.main_path(root, session),
            ],
            f"GCC commit {branch_name}: {contribution[:60]}",
        )

        return {"branch": branch_name, "commit_id": commit_id, "session": session}

    return storage.with_lock(root, session, _run)


def merge(
    root: Path,
    source_branch: str,
    target_branch: Optional[str],
    summary: Optional[str],
    session_id: Optional[str],
) -> Dict[str, Any]:
    if not source_branch:
        raise GCCError("source_branch is required")
    session = storage.normalize_session_id(session_id)

    def _run() -> Dict[str, Any]:
        storage.ensure_gcc(root, None, None, session)
        repo_root = storage.session_root(root, session)
        ensure_repo(repo_root)
        if source_branch not in storage.list_branches(root, session):
            raise GCCError(f"branch not found: {source_branch}")

        target = target_branch or "main"
        if target not in storage.list_branches(root, session):
            storage.ensure_branch(root, session, target, f"Main branch (merged from {source_branch})")
        checkout_branch(repo_root, target)

        source_commit = storage.commit_path(root, session, source_branch).read_text(encoding="utf-8")
        storage._append_text(storage.commit_path(root, session, target), "\n" + source_commit)

        source_log = storage.log_path(root, session, source_branch).read_text(encoding="utf-8")
        log_block = f"\n== Merge from {source_branch} ==\n" + source_log + "\n"
        storage._append_text(storage.log_path(root, session, target), log_block)

        source_meta = storage.read_metadata(root, session, source_branch)
        if source_meta:
            target_meta = storage.read_metadata(root, session, target)
            merged_from = target_meta.get("merged_from", {})
            merged_from[source_branch] = source_meta
            target_meta["merged_from"] = merged_from
            storage.update_metadata(root, session, target, target_meta)

        merge_note = summary or f"Merged branch {source_branch} into {target}"
        merge_branch(repo_root, source_branch, merge_note)
        storage.update_main(root, session, merge_note)

        add_and_commit(
            repo_root,
            [
                storage.commit_path(root, session, target),
                storage.log_path(root, session, target),
                storage.metadata_path(root, session, target),
                storage.main_path(root, session),
            ],
            f"GCC merge {source_branch} -> {target}",
        )

        return {"source_branch": source_branch, "target_branch": target, "session": session}

    return storage.with_lock(root, session, _run)


def context(
    root: Path,
    branch_name: Optional[str],
    commit_id: Optional[str],
    log_tail: Optional[int],
    metadata_segment: Optional[str],
    session_id: Optional[str],
) -> Dict[str, Any]:
    session = storage.normalize_session_id(session_id)
    storage.ensure_gcc(root, None, None, session)
    result: Dict[str, Any] = {
        "main": storage.read_main(root, session),
        "branches": storage.list_branches(root, session),
        "session": session,
    }

    if branch_name:
        if branch_name not in storage.list_branches(root, session):
            raise GCCError(f"branch not found: {branch_name}")
        commit_text = storage.commit_path(root, session, branch_name).read_text(encoding="utf-8")
        commits = storage._parse_commits(commit_text)
        last_commit = commits[-1] if commits else {}
        result["branch"] = {
            "name": branch_name,
            "purpose": storage.get_branch_purpose(root, session, branch_name),
            "latest_commit": last_commit.get("commit_id"),
            "latest_summary": last_commit.get("This Commit's Contribution"),
            "recent_commits": [c.get("commit_id") for c in commits[-10:]],
        }

    if commit_id and branch_name:
        result["commit_entry"] = storage.get_commit_entry(root, session, branch_name, commit_id)

    if log_tail and branch_name:
        result["log_tail"] = storage.read_log_tail(root, session, branch_name, log_tail)

    if metadata_segment and branch_name:
        metadata = storage.read_metadata(root, session, branch_name)
        result["metadata"] = metadata.get(metadata_segment)

    return result


def history(
    root: Path,
    limit: int,
    session_id: Optional[str],
) -> Dict[str, Any]:
    session = storage.normalize_session_id(session_id)

    def _run() -> Dict[str, Any]:
        storage.ensure_gcc(root, None, None, session)
        repo_root = storage.session_root(root, session)
        ensure_repo(repo_root)
        return {"session": session, "commits": git_log(repo_root, limit)}

    return storage.with_lock(root, session, _run)


def diff(
    root: Path,
    from_ref: str,
    to_ref: Optional[str],
    session_id: Optional[str],
) -> Dict[str, Any]:
    if not from_ref:
        raise GCCError("from_ref is required")
    session = storage.normalize_session_id(session_id)

    def _run() -> Dict[str, Any]:
        storage.ensure_gcc(root, None, None, session)
        repo_root = storage.session_root(root, session)
        ensure_repo(repo_root)
        return {"session": session, "diff": git_diff(repo_root, from_ref, to_ref)}

    return storage.with_lock(root, session, _run)


def show(
    root: Path,
    ref: str,
    path: Optional[str],
    session_id: Optional[str],
) -> Dict[str, Any]:
    if not ref:
        raise GCCError("ref is required")
    session = storage.normalize_session_id(session_id)

    def _run() -> Dict[str, Any]:
        storage.ensure_gcc(root, None, None, session)
        repo_root = storage.session_root(root, session)
        ensure_repo(repo_root)
        return {"session": session, "content": git_show(repo_root, ref, path)}

    return storage.with_lock(root, session, _run)


def reset(
    root: Path,
    ref: str,
    mode: str,
    confirm: bool,
    session_id: Optional[str],
) -> Dict[str, Any]:
    if not ref:
        raise GCCError("ref is required")
    if mode == "hard" and not confirm:
        raise GCCError("hard reset requires confirm=true")
    session = storage.normalize_session_id(session_id)

    def _run() -> Dict[str, Any]:
        storage.ensure_gcc(root, None, None, session)
        repo_root = storage.session_root(root, session)
        ensure_repo(repo_root)
        git_reset(repo_root, ref, mode)
        return {"session": session, "ref": ref, "mode": mode}

    return storage.with_lock(root, session, _run)
