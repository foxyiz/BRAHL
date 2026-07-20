"""Cloud FoXYiZ worker client — Arena → remote EC2 HTTP worker.

Env:
  FOXYIZ_CLOUD_WORKER_URL  base URL of the worker (e.g. https://host:8770)
  FOXYIZ_CLOUD_TOKEN       shared bearer token (optional but recommended)
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any


def cloud_configured() -> bool:
    return bool((os.environ.get("FOXYIZ_CLOUD_WORKER_URL") or "").strip())


def cloud_status() -> dict[str, Any]:
    url = (os.environ.get("FOXYIZ_CLOUD_WORKER_URL") or "").strip().rstrip("/")
    token = (os.environ.get("FOXYIZ_CLOUD_TOKEN") or "").strip()
    out: dict[str, Any] = {
        "configured": bool(url),
        "worker_url_set": bool(url),
        "token_set": bool(token),
        "reachable": False,
        "detail": "",
    }
    if not url:
        out["detail"] = "Set FOXYIZ_CLOUD_WORKER_URL to enable cloud Run."
        return out
    try:
        req = urllib.request.Request(
            f"{url}/health",
            headers=_headers(token),
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            out["reachable"] = resp.status == 200
            out["detail"] = body[:200]
    except Exception as exc:  # noqa: BLE001 — status probe
        out["detail"] = str(exc)
    return out


def _headers(token: str | None = None) -> dict[str, str]:
    h = {"Content-Type": "application/json", "Accept": "application/json"}
    tok = (token if token is not None else os.environ.get("FOXYIZ_CLOUD_TOKEN") or "").strip()
    if tok:
        h["Authorization"] = f"Bearer {tok}"
    return h


def _worker_base() -> str:
    url = (os.environ.get("FOXYIZ_CLOUD_WORKER_URL") or "").strip().rstrip("/")
    if not url:
        raise RuntimeError("FOXYIZ_CLOUD_WORKER_URL is not set")
    return url


def submit_job(
    *,
    config_path: str,
    step_label: str = "Run",
    tags: list[str] | None = None,
    thread_count: int | None = None,
    profiles: list[str] | None = None,
) -> dict[str, Any]:
    """POST a new engine job to the cloud worker; returns worker job dict."""
    payload = {
        "config_path": config_path,
        "step_label": step_label,
        "tags": tags,
        "thread_count": thread_count,
        "profiles": profiles,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{_worker_base()}/v1/jobs",
        data=data,
        headers=_headers(),
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"cloud worker HTTP {exc.code}: {body}") from exc


def poll_job(remote_job_id: str) -> dict[str, Any]:
    req = urllib.request.Request(
        f"{_worker_base()}/v1/jobs/{remote_job_id}",
        headers=_headers(),
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"cloud worker poll HTTP {exc.code}: {body}") from exc
