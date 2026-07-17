"""Lightweight local schedule model for BRAHL Loop — disabled by default.

Schedules only ever call the existing job runner (runner.start_run) with a plain
Run/Verify step — never an AI endpoint. Cloud runtime is estimated for cost
transparency; local runtime never carries a platform runtime charge.
"""

from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SCHEDULES_FILE = DATA_DIR / "schedules.json"

INTERVALS = ("hourly", "daily")
RUNTIMES = ("local", "cloud")

# Rough, intentionally conservative cloud compute estimate for cost transparency —
# not a billing source of truth. ~$0.08/min per worker thread on a small cloud runner.
CLOUD_USD_PER_MINUTE_PER_THREAD = 0.08
ESTIMATED_RUN_MINUTES = 6.0

_lock = threading.Lock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _ensure_file() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not SCHEDULES_FILE.is_file():
        SCHEDULES_FILE.write_text("[]", encoding="utf-8")


def load_schedules() -> list[dict[str, Any]]:
    _ensure_file()
    with _lock:
        try:
            data = json.loads(SCHEDULES_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            data = []
    return data if isinstance(data, list) else []


def save_schedules(schedules: list[dict[str, Any]]) -> None:
    _ensure_file()
    with _lock:
        SCHEDULES_FILE.write_text(json.dumps(schedules, indent=2), encoding="utf-8")


def _compute_next_run(interval: str, from_time: datetime | None = None) -> str:
    base = from_time or datetime.now(timezone.utc)
    delta = timedelta(hours=1) if interval == "hourly" else timedelta(days=1)
    return (base + delta).isoformat(timespec="seconds")


def _normalize(s: dict[str, Any]) -> dict[str, Any]:
    s.setdefault("id", uuid.uuid4().hex[:10])
    s.setdefault("profiles", [])
    s.setdefault("thread_count", 1)
    s.setdefault("runtime", "local")
    s.setdefault("enabled", False)
    s.setdefault("last_run_at", None)
    s.setdefault("last_job_id", None)
    s.setdefault("last_run_name", None)
    s.setdefault("created_at", _now())
    s.setdefault("updated_at", s.get("created_at"))
    if s.get("interval") not in INTERVALS:
        s["interval"] = "daily"
    if s.get("runtime") not in RUNTIMES:
        s["runtime"] = "local"
    if not s.get("next_run"):
        s["next_run"] = _compute_next_run(s["interval"])
    return s


def estimate_cloud_cost(profiles: list[str] | None, thread_count: int, interval: str) -> dict[str, Any]:
    """Best-effort estimate of cloud runtime cost per run and per month.

    Local runtime never bills platform runtime — this estimate only applies when
    the schedule's runtime is (or would be) "cloud".
    """
    threads = max(1, int(thread_count or 1), len([p for p in (profiles or []) if p]) or 1)
    per_run_usd = round(ESTIMATED_RUN_MINUTES * CLOUD_USD_PER_MINUTE_PER_THREAD * threads, 2)
    runs_per_month = 720 if interval == "hourly" else 30
    monthly_usd = round(per_run_usd * runs_per_month, 2)
    return {
        "per_run_usd": per_run_usd,
        "runs_per_month_est": runs_per_month,
        "monthly_usd_est": monthly_usd,
        "note": "Rough estimate — actual cloud compute billing may vary by provider/instance size.",
    }


def list_project_schedules(project_id: str) -> list[dict[str, Any]]:
    schedules = load_schedules()
    out = [_normalize(dict(s)) for s in schedules if s.get("project_id") == project_id]
    out.sort(key=lambda s: s.get("created_at") or "", reverse=True)
    return out


def create_schedule(
    project_id: str,
    suite: str,
    config_path: str,
    *,
    profiles: list[str] | None = None,
    thread_count: int = 1,
    interval: str = "daily",
    runtime: str = "local",
    step_label: str = "Verify",
    enabled: bool = False,
) -> dict[str, Any]:
    if interval not in INTERVALS:
        raise ValueError(f"interval must be one of {INTERVALS}")
    if runtime not in RUNTIMES:
        raise ValueError(f"runtime must be one of {RUNTIMES}")
    schedules = load_schedules()
    entry = _normalize(
        {
            "id": uuid.uuid4().hex[:10],
            "project_id": project_id,
            "suite": suite,
            "config_path": config_path,
            "profiles": list(profiles or []),
            "thread_count": max(1, int(thread_count or 1)),
            "interval": interval,
            "runtime": runtime,
            "step_label": step_label if step_label in ("Run", "Verify") else "Verify",
            "enabled": bool(enabled),
        }
    )
    schedules.append(entry)
    save_schedules(schedules)
    return entry


def update_schedule(schedule_id: str, patch: dict[str, Any]) -> dict[str, Any]:
    schedules = load_schedules()
    for i, s in enumerate(schedules):
        if s.get("id") != schedule_id:
            continue
        s = _normalize(dict(s))
        for key in ("suite", "config_path", "profiles", "thread_count", "interval", "runtime", "step_label"):
            if key in patch and patch[key] is not None:
                s[key] = patch[key]
        if s["interval"] not in INTERVALS:
            raise ValueError(f"interval must be one of {INTERVALS}")
        if s["runtime"] not in RUNTIMES:
            raise ValueError(f"runtime must be one of {RUNTIMES}")
        s["next_run"] = _compute_next_run(s["interval"])
        s["updated_at"] = _now()
        schedules[i] = s
        save_schedules(schedules)
        return s
    raise KeyError(schedule_id)


def toggle_schedule(schedule_id: str, enabled: bool) -> dict[str, Any]:
    schedules = load_schedules()
    for i, s in enumerate(schedules):
        if s.get("id") != schedule_id:
            continue
        s = _normalize(dict(s))
        s["enabled"] = bool(enabled)
        if s["enabled"] and not s.get("next_run"):
            s["next_run"] = _compute_next_run(s["interval"])
        s["updated_at"] = _now()
        schedules[i] = s
        save_schedules(schedules)
        return s
    raise KeyError(schedule_id)


def delete_schedule(schedule_id: str) -> None:
    schedules = load_schedules()
    remaining = [s for s in schedules if s.get("id") != schedule_id]
    if len(remaining) == len(schedules):
        raise KeyError(schedule_id)
    save_schedules(remaining)


def due_schedules(now: datetime | None = None) -> list[dict[str, Any]]:
    """Enabled schedules whose next_run has passed — used by the background runner."""
    now = now or datetime.now(timezone.utc)
    out = []
    for s in load_schedules():
        s = _normalize(dict(s))
        if not s.get("enabled"):
            continue
        try:
            next_run = datetime.fromisoformat(s["next_run"])
            if next_run.tzinfo is None:
                next_run = next_run.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            continue
        if next_run <= now:
            out.append(s)
    return out


def mark_schedule_ran(schedule_id: str, job_id: str | None, run_name: str | None) -> dict[str, Any] | None:
    schedules = load_schedules()
    for i, s in enumerate(schedules):
        if s.get("id") != schedule_id:
            continue
        s = _normalize(dict(s))
        s["last_run_at"] = _now()
        s["last_job_id"] = job_id
        s["last_run_name"] = run_name
        s["next_run"] = _compute_next_run(s["interval"])
        s["updated_at"] = _now()
        schedules[i] = s
        save_schedules(schedules)
        return s
    return None
