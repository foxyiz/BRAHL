"""Auth + project ownership smoke tests."""
from __future__ import annotations

import os
from pathlib import Path

import auth as auth_store
import projects as project_store


def test_register_login_and_reset(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(auth_store, "DATA_DIR", tmp_path)
    monkeypatch.setattr(auth_store, "DB_PATH", tmp_path / "users.db")
    auth_store.init_db()
    user = auth_store.register_user("mvp@example.com", "password123", "MVP", "creator")
    assert user["email"] == "mvp@example.com"
    assert auth_store.authenticate_user("mvp@example.com", "password123")
    token = auth_store.create_password_reset("mvp@example.com")
    assert token
    auth_store.reset_password(token, "newpass456")
    assert auth_store.authenticate_user("mvp@example.com", "newpass456")
    assert auth_store.authenticate_user("mvp@example.com", "password123") is None


def test_multi_role_profile_and_social(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(auth_store, "DATA_DIR", tmp_path)
    monkeypatch.setattr(auth_store, "DB_PATH", tmp_path / "users.db")
    monkeypatch.setattr(auth_store, "UPLOADS_DIR", tmp_path / "profiles")
    auth_store.init_db()
    user = auth_store.register_user(
        "hunt@example.com",
        "password123",
        first_name="Ada",
        last_name="Hunter",
        country="US",
        phone="+15551212",
        roles=["creator", "qa_hunter"],
        app_url="https://app.example.com",
        profile_complete=True,
    )
    assert user["roles"] == ["creator", "qa_hunter"]
    assert user["role"] == "both"
    assert user["first_name"] == "Ada"
    social = auth_store.social_login_or_register("google", "social@example.com", "Sam Social")
    assert social["social_provider"] == "google"
    assert social["profile_complete"] is False
    done = auth_store.update_user_profile(
        social["id"],
        {"first_name": "Sam", "last_name": "Social", "roles": ["nalanda"], "profile_complete": True},
    )
    assert done["roles"] == ["nalanda"]
    assert done["profile_complete"] is True
    rel = auth_store.save_profile_upload(user["id"], "cv.pdf", b"%PDF-demo")
    assert rel.endswith("cv.pdf")
    assert (tmp_path / "profiles" / Path(rel).name).is_file()

def test_owned_project_access(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(project_store, "DATA_DIR", tmp_path)
    monkeypatch.setattr(project_store, "PROJECTS_FILE", tmp_path / "projects.json")
    monkeypatch.setattr(project_store, "UPLOADS_DIR", tmp_path / "uploads")
    a = project_store.create_project({"name": "A", "owner_user_id": "u1"})
    b = project_store.create_project({"name": "B", "owner_user_id": "u2"})
    c = project_store.create_project({"name": "C"})  # legacy / shared
    user1 = {"id": "u1", "role": "creator"}
    assert project_store.user_can_access_project(a, user1)
    assert not project_store.user_can_access_project(b, user1)
    assert project_store.user_can_access_project(c, user1)
    owned = project_store.list_client_projects(owner_user_id="u1")
    ids = {p["id"] for p in owned}
    assert a["id"] in ids
    assert c["id"] in ids  # unowned still listed for migration
    assert b["id"] not in ids


def test_demo_flag() -> None:
    prev = os.environ.get("QOA_ALLOW_DEMO")
    try:
        os.environ["QOA_ALLOW_DEMO"] = "0"
        assert auth_store.demo_allowed() is False
        os.environ["QOA_ALLOW_DEMO"] = "1"
        assert auth_store.demo_allowed() is True
    finally:
        if prev is None:
            os.environ.pop("QOA_ALLOW_DEMO", None)
        else:
            os.environ["QOA_ALLOW_DEMO"] = prev
