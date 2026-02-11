from pathlib import Path

from fastapi.testclient import TestClient

from gcc_skill.server import app


client = TestClient(app)


def test_init_branch_commit_context(tmp_path: Path) -> None:
    root = str(tmp_path)
    session_id = "session-a"
    res = client.post(
        "/init",
        json={"root": root, "goal": "Test", "todo": ["a"], "session_id": session_id},
    )
    assert res.status_code == 200

    res = client.post(
        "/branch",
        json={
            "root": root,
            "branch": "main",
            "purpose": "Main work",
            "session_id": session_id,
        },
    )
    assert res.status_code == 200

    res = client.post(
        "/commit",
        json={
            "root": root,
            "branch": "main",
            "contribution": "Did work",
            "session_id": session_id,
        },
    )
    assert res.status_code == 200
    commit_id = res.json()["commit_id"]

    res = client.post(
        "/context",
        json={
            "root": root,
            "branch": "main",
            "commit_id": commit_id,
            "log_tail": 5,
            "session_id": session_id,
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert "branches" in body
    assert body["branch"]["latest_commit"] == commit_id


def test_session_isolation(tmp_path: Path) -> None:
    root = str(tmp_path)
    res = client.post(
        "/branch",
        json={"root": root, "branch": "main", "purpose": "Main", "session_id": "one"},
    )
    assert res.status_code == 200

    res = client.post(
        "/context",
        json={"root": root, "session_id": "two"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["branches"] == []


def test_history_and_show(tmp_path: Path) -> None:
    root = str(tmp_path)
    session_id = "history"
    res = client.post(
        "/init",
        json={"root": root, "goal": "Test", "todo": [], "session_id": session_id},
    )
    assert res.status_code == 200

    res = client.post(
        "/branch",
        json={"root": root, "branch": "main", "purpose": "Main", "session_id": session_id},
    )
    assert res.status_code == 200

    res = client.post(
        "/history",
        json={"root": root, "limit": 5, "session_id": session_id},
    )
    assert res.status_code == 200
    commits = res.json().get("commits", [])
    assert commits

    res = client.post(
        "/show",
        json={"root": root, "ref": "HEAD", "path": "main.md", "session_id": session_id},
    )
    assert res.status_code == 200
    assert "GCC Roadmap" in res.json().get("content", "")
