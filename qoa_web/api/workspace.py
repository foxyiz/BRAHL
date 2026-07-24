"""Desktop workspace bind — GitHub clone or local folder for the app under test."""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from paths import KK_ROOT

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
WORKSPACE_FILE = DATA_DIR / "workspace.json"
CLONES_DIR = KK_ROOT / "workspaces"

_SLUG_RE = re.compile(r"[^a-zA-Z0-9._-]+")


def _ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CLONES_DIR.mkdir(parents=True, exist_ok=True)


def load_workspace() -> dict[str, Any] | None:
    _ensure_dirs()
    if not WORKSPACE_FILE.is_file():
        return None
    try:
        data = json.loads(WORKSPACE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    path = (data.get("local_path") or "").strip()
    if not path or not Path(path).is_dir():
        return None
    return data


def save_workspace(data: dict[str, Any]) -> dict[str, Any]:
    _ensure_dirs()
    payload = {
        "source": data.get("source") or "local",
        "repo_url": (data.get("repo_url") or "").strip() or None,
        "local_path": str(Path(data["local_path"]).resolve()),
        "default_branch": (data.get("default_branch") or "").strip() or None,
        "slug": data.get("slug") or Path(data["local_path"]).name,
        "bound_at": data.get("bound_at") or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    WORKSPACE_FILE.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def clear_workspace() -> None:
    if WORKSPACE_FILE.is_file():
        WORKSPACE_FILE.unlink()


def _slug_from_url(url: str) -> str:
    parsed = urlparse(url.strip())
    path = (parsed.path or "").rstrip("/")
    name = path.split("/")[-1] if path else "repo"
    if name.endswith(".git"):
        name = name[:-4]
    slug = _SLUG_RE.sub("-", name).strip("-._") or "repo"
    return slug[:80]


def bind_local(path: str) -> dict[str, Any]:
    p = Path(path).expanduser().resolve()
    if not p.is_dir():
        raise ValueError(f"Folder not found: {p}")
    return save_workspace(
        {
            "source": "local",
            "repo_url": None,
            "local_path": str(p),
            "slug": p.name,
        }
    )


def clone_github(repo_url: str, branch: str | None = None) -> dict[str, Any]:
    url = (repo_url or "").strip()
    if not url:
        raise ValueError("repo_url required")
    if not (url.startswith("http://") or url.startswith("https://") or url.startswith("git@")):
        raise ValueError("Use an https:// or git@ GitHub URL")
    _ensure_dirs()
    slug = _slug_from_url(url)
    dest = CLONES_DIR / slug
    if dest.is_dir() and any(dest.iterdir()):
        # Already cloned — bind existing
        return save_workspace(
            {
                "source": "github",
                "repo_url": url,
                "local_path": str(dest.resolve()),
                "default_branch": branch,
                "slug": slug,
            }
        )
    cmd = ["git", "clone", "--depth", "1"]
    if branch:
        cmd.extend(["--branch", branch])
    cmd.extend([url, str(dest)])
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(CLONES_DIR),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=180,
            env=os.environ.copy(),
        )
    except FileNotFoundError as exc:
        raise ValueError("git not found on PATH — install Git or bind a local folder") from exc
    except subprocess.TimeoutExpired as exc:
        raise ValueError("git clone timed out") from exc
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "clone failed").strip()
        raise ValueError(err[:500])
    return save_workspace(
        {
            "source": "github",
            "repo_url": url,
            "local_path": str(dest.resolve()),
            "default_branch": branch,
            "slug": slug,
        }
    )


def workspace_summary() -> dict[str, Any]:
    ws = load_workspace()
    if not ws:
        return {"bound": False, "workspace": None}
    path = ws.get("local_path") or ""
    short = path
    try:
        short = str(Path(path).name)
        parent = Path(path).parent.name
        if parent:
            short = f"{parent}/{Path(path).name}"
    except Exception:
        pass
    return {"bound": True, "workspace": ws, "short_label": short}
