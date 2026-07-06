"""GTM invite codes — batch launches (50 Creators / 50 QA Hunters) with 7-day trial."""

from __future__ import annotations

import json
import secrets
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
INVITES_PATH = DATA_DIR / "invites.json"
SEED_PATH = DATA_DIR / "invites.seed.json"

TRIAL_DAYS = 7
BATCH_SIZE_DEFAULT = 50
VALID_BATCH_TYPES = frozenset({"creator", "consultant", "nalanda"})


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _trial_end_iso(days: int = TRIAL_DAYS) -> str:
    end = datetime.now(timezone.utc) + timedelta(days=days)
    return end.replace(microsecond=0).isoformat()


def _empty_store() -> dict[str, Any]:
    return {"batches": [], "codes": [], "redemptions": []}


def _load() -> dict[str, Any]:
    if INVITES_PATH.is_file():
        try:
            data = json.loads(INVITES_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                data.setdefault("batches", [])
                data.setdefault("codes", [])
                data.setdefault("redemptions", [])
                return data
        except (json.JSONDecodeError, OSError):
            pass
    if SEED_PATH.is_file():
        try:
            data = json.loads(SEED_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                _save(data)
                return data
        except (json.JSONDecodeError, OSError):
            pass
    store = _empty_store()
    _save(store)
    return store


def _save(store: dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    INVITES_PATH.write_text(json.dumps(store, indent=2), encoding="utf-8")


def _normalize_code(code: str) -> str:
    return (code or "").strip().upper().replace(" ", "")


def _code_prefix(batch_type: str) -> str:
    if batch_type == "creator":
        return "CR"
    if batch_type == "consultant":
        return "QH"
    return "NA"


def find_code(store: dict[str, Any], code: str) -> dict[str, Any] | None:
    norm = _normalize_code(code)
    if not norm:
        return None
    for row in store.get("codes") or []:
        if _normalize_code(row.get("code", "")) == norm:
            return row
    return None


def validate_code(code: str) -> dict[str, Any]:
    store = _load()
    row = find_code(store, code)
    if not row:
        return {"valid": False, "reason": "Invite code not found"}
    if row.get("revoked"):
        return {"valid": False, "reason": "This invite was revoked"}
    max_uses = int(row.get("max_uses") or 1)
    uses = int(row.get("uses") or 0)
    if uses >= max_uses:
        return {"valid": False, "reason": "This invite has already been used"}
    batch = next((b for b in store.get("batches") or [] if b.get("id") == row.get("batch_id")), None)
    suggested = "client"
    if row.get("batch_type") == "consultant":
        suggested = "consultant"
    elif row.get("batch_type") == "nalanda":
        suggested = "networker"
    return {
        "valid": True,
        "code": row.get("code"),
        "batch_type": row.get("batch_type"),
        "batch_id": row.get("batch_id"),
        "batch_label": batch.get("label") if batch else row.get("batch_id"),
        "trial_days": int(row.get("trial_days") or TRIAL_DAYS),
        "suggested_avatar": suggested,
    }


def redeem_code(code: str, email: str = "", note: str = "") -> dict[str, Any]:
    store = _load()
    check = validate_code(code)
    if not check.get("valid"):
        raise ValueError(check.get("reason") or "Invalid invite")
    row = find_code(store, code)
    if not row:
        raise ValueError("Invite code not found")

    trial_days = int(row.get("trial_days") or TRIAL_DAYS)
    trial_ends_at = _trial_end_iso(trial_days)
    row["uses"] = int(row.get("uses") or 0) + 1
    row["last_redeemed_at"] = _now_iso()

    redemption = {
        "id": f"rd_{int(time.time())}_{len(store.get('redemptions') or []) + 1}",
        "code": row.get("code"),
        "batch_id": row.get("batch_id"),
        "batch_type": row.get("batch_type"),
        "email": (email or "").strip()[:200],
        "note": (note or "").strip()[:500],
        "redeemed_at": _now_iso(),
        "trial_ends_at": trial_ends_at,
        "trial_days": trial_days,
    }
    store.setdefault("redemptions", []).append(redemption)
    _save(store)

    batch = next((b for b in store.get("batches") or [] if b.get("id") == row.get("batch_id")), {})
    msg = f"Welcome — {trial_days}-day trial started. Pick your profile and BRAHL it."
    if row.get("batch_type") == "nalanda":
        msg = (
            f"Welcome to Nalanda — {trial_days}-day community trial started. "
            "Pick a profile, switch to Nalanda, and join the discussion."
        )
    suggested = "client"
    if row.get("batch_type") == "consultant":
        suggested = "consultant"
    elif row.get("batch_type") == "nalanda":
        suggested = "networker"
    return {
        "ok": True,
        "message": msg,
        "trial": {
            "code": row.get("code"),
            "batch_type": row.get("batch_type"),
            "batch_label": batch.get("label") or row.get("batch_id"),
            "trial_days": trial_days,
            "trial_ends_at": trial_ends_at,
            "suggested_avatar": suggested,
            "nalanda_community": row.get("batch_type") == "nalanda",
        },
        "redemption": redemption,
    }


def generate_batch(
    batch_type: str,
    label: str = "",
    count: int = BATCH_SIZE_DEFAULT,
    trial_days: int = TRIAL_DAYS,
) -> dict[str, Any]:
    batch_type = (batch_type or "creator").strip().lower()
    if batch_type not in VALID_BATCH_TYPES:
        raise ValueError("batch_type must be creator, consultant, or nalanda")
    count = max(1, min(int(count), 200))
    trial_days = max(1, min(int(trial_days), 30))

    store = _load()
    batch_num = len(store.get("batches") or []) + 1
    batch_id = f"batch_{batch_num:03d}_{batch_type}"
    type_label = "Creators" if batch_type == "creator" else "QA Hunters"
    if batch_type == "nalanda":
        type_label = "Nalanda community"
    batch_label = (label or f"Launch {batch_num} — {count} {type_label}").strip()[:120]
    prefix = _code_prefix(batch_type)

    batch = {
        "id": batch_id,
        "label": batch_label,
        "batch_type": batch_type,
        "size": count,
        "trial_days": trial_days,
        "created_at": _now_iso(),
    }
    codes: list[dict[str, Any]] = []
    for i in range(1, count + 1):
        token = secrets.token_hex(2).upper()
        code = f"QOA-{prefix}{count}-{batch_num:03d}-{i:03d}-{token}"
        entry = {
            "code": code,
            "batch_id": batch_id,
            "batch_type": batch_type,
            "trial_days": trial_days,
            "max_uses": 1,
            "uses": 0,
            "created_at": _now_iso(),
            "revoked": False,
        }
        codes.append(entry)

    store.setdefault("batches", []).append(batch)
    store.setdefault("codes", []).extend(codes)
    _save(store)

    return {
        "batch": batch,
        "codes": [c["code"] for c in codes],
        "sample_link": f"/welcome?code={codes[0]['code']}" if codes else "",
    }


def list_admin_summary() -> dict[str, Any]:
    store = _load()
    batches = store.get("batches") or []
    codes = store.get("codes") or []
    redemptions = store.get("redemptions") or []
    redeemed = sum(1 for c in codes if int(c.get("uses") or 0) > 0)
    active_trials = 0
    now = datetime.now(timezone.utc)
    for r in redemptions:
        try:
            end = datetime.fromisoformat(r.get("trial_ends_at", "").replace("Z", "+00:00"))
            if end.tzinfo is None:
                end = end.replace(tzinfo=timezone.utc)
            if end > now:
                active_trials += 1
        except (TypeError, ValueError):
            pass
    return {
        "batch_count": len(batches),
        "code_count": len(codes),
        "redeemed_count": redeemed,
        "redemption_count": len(redemptions),
        "active_trials": active_trials,
        "batches": batches,
        "recent_redemptions": list(reversed(redemptions[-20:])),
    }


def export_batch_csv(batch_id: str) -> str:
    import csv
    import io

    store = _load()
    rows = [c for c in store.get("codes") or [] if c.get("batch_id") == batch_id]
    if not rows:
        raise ValueError("Batch not found")
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["code", "batch_type", "invite_link", "uses", "max_uses", "trial_days"])
    for c in rows:
        w.writerow([
            c.get("code"),
            c.get("batch_type"),
            f"/welcome?code={c.get('code')}",
            c.get("uses", 0),
            c.get("max_uses", 1),
            c.get("trial_days", TRIAL_DAYS),
        ])
    return buf.getvalue()


def register_nalanda_personal_code(code: str, owner_profile_id: str, owner_name: str = "") -> dict[str, Any]:
    """Register a personal Nalanda community invite (multi-use, synced from nalanda.py)."""
    norm = _normalize_code(code)
    if not norm:
        raise ValueError("Invalid code")
    store = _load()
    if find_code(store, norm):
        return find_code(store, norm) or {}

    batch_id = f"nalanda_personal_{owner_profile_id.lower()}"
    batches = store.get("batches") or []
    batch = next((b for b in batches if b.get("id") == batch_id), None)
    if not batch:
        label = f"Nalanda — {owner_name or owner_profile_id.upper()}"
        batch = {
            "id": batch_id,
            "label": label[:120],
            "batch_type": "nalanda",
            "size": 1,
            "trial_days": TRIAL_DAYS,
            "created_at": _now_iso(),
            "owner_profile_id": owner_profile_id.lower(),
        }
        batches.append(batch)
        store["batches"] = batches

    entry = {
        "code": norm,
        "batch_id": batch_id,
        "batch_type": "nalanda",
        "trial_days": TRIAL_DAYS,
        "max_uses": 50,
        "uses": 0,
        "created_at": _now_iso(),
        "revoked": False,
        "owner_profile_id": owner_profile_id.lower(),
    }
    store.setdefault("codes", []).append(entry)
    _save(store)
    return entry
