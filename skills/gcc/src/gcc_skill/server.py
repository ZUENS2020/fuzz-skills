from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from . import commands

app = FastAPI(title="GCC Context Controller", version="0.1.0")


class InitRequest(BaseModel):
    root: str = Field(..., description="Project root path")
    goal: Optional[str] = None
    todo: Optional[List[str]] = None
    session_id: Optional[str] = Field(None, description="Session identifier for isolation")


class BranchRequest(BaseModel):
    root: str
    branch: str
    purpose: str
    session_id: Optional[str] = None


class LogRequest(BaseModel):
    root: str
    branch: str
    entries: List[str]
    session_id: Optional[str] = None


class CommitRequest(BaseModel):
    root: str
    branch: str
    contribution: str
    purpose: Optional[str] = None
    log_entries: Optional[List[str]] = None
    metadata_updates: Optional[Dict[str, Any]] = None
    update_main: Optional[str] = None
    session_id: Optional[str] = None


class MergeRequest(BaseModel):
    root: str
    source_branch: str
    target_branch: Optional[str] = None
    summary: Optional[str] = None
    session_id: Optional[str] = None


class ContextRequest(BaseModel):
    root: str
    branch: Optional[str] = None
    commit_id: Optional[str] = None
    log_tail: Optional[int] = None
    metadata_segment: Optional[str] = None
    session_id: Optional[str] = None


class HistoryRequest(BaseModel):
    root: str
    limit: int = 20
    session_id: Optional[str] = None


class DiffRequest(BaseModel):
    root: str
    from_ref: str
    to_ref: Optional[str] = None
    session_id: Optional[str] = None


class ShowRequest(BaseModel):
    root: str
    ref: str
    path: Optional[str] = None
    session_id: Optional[str] = None


class ResetRequest(BaseModel):
    root: str
    ref: str
    mode: str = "soft"
    confirm: bool = False
    session_id: Optional[str] = None


def _path(root: str) -> Path:
    base = os.environ.get("GCC_DATA_ROOT")
    if base:
        # Extract project name from the path for cleaner volume structure
        # e.g., "J:\fuzz-skills" -> "fuzz-skills"
        # e.g., "/home/user/projects/my-app" -> "my-app"
        project_name = Path(root).name
        # Fallback to parent name if project_name is empty or just a drive letter
        if not project_name or project_name.endswith(":"):
            project_name = Path(root).parent.name
        if not project_name:
            project_name = "project"
        return (Path(base) / project_name).resolve()
    return Path(root).expanduser().resolve()


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/init")
def init(req: InitRequest) -> Dict[str, Any]:
    try:
        return commands.init(_path(req.root), req.goal, req.todo, req.session_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/branch")
def create_branch(req: BranchRequest) -> Dict[str, Any]:
    try:
        return commands.branch(_path(req.root), req.branch, req.purpose, req.session_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/log")
def append_log(req: LogRequest) -> Dict[str, Any]:
    try:
        return commands.log(_path(req.root), req.branch, req.entries, req.session_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/commit")
def commit(req: CommitRequest) -> Dict[str, Any]:
    try:
        return commands.commit(
            _path(req.root),
            req.branch,
            req.contribution,
            req.purpose,
            req.log_entries,
            req.metadata_updates,
            req.update_main,
            req.session_id,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/merge")
def merge(req: MergeRequest) -> Dict[str, Any]:
    try:
        return commands.merge(
            _path(req.root),
            req.source_branch,
            req.target_branch,
            req.summary,
            req.session_id,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/context")
def context(req: ContextRequest) -> Dict[str, Any]:
    try:
        return commands.context(
            _path(req.root),
            req.branch,
            req.commit_id,
            req.log_tail,
            req.metadata_segment,
            req.session_id,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/history")
def history(req: HistoryRequest) -> Dict[str, Any]:
    try:
        return commands.history(_path(req.root), req.limit, req.session_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/diff")
def diff(req: DiffRequest) -> Dict[str, Any]:
    try:
        return commands.diff(_path(req.root), req.from_ref, req.to_ref, req.session_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/show")
def show(req: ShowRequest) -> Dict[str, Any]:
    try:
        return commands.show(_path(req.root), req.ref, req.path, req.session_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/reset")
def reset(req: ResetRequest) -> Dict[str, Any]:
    try:
        return commands.reset(_path(req.root), req.ref, req.mode, req.confirm, req.session_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


def main() -> None:
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
