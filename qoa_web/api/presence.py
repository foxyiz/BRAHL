"""Arena presence / live activity — heartbeat + coarse geo."""

from __future__ import annotations

import hashlib
import json
import threading
import time
import urllib.request
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
PRESENCE_PATH = DATA_DIR / "presence.json"
_lock = threading.Lock()
ONLINE_TTL_SEC = 45
GEO_CACHE: dict[str, dict[str, Any]] = {}


def _now() -> float:
    return time.time()


def _load() -> dict[str, Any]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not PRESENCE_PATH.is_file():
        return {"sessions": {}, "time_spent": {}}
    try:
        data = json.loads(PRESENCE_PATH.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {"sessions": {}, "time_spent": {}}
        sessions = data.get("sessions")
        if isinstance(sessions, list):
            data["sessions"] = {
                (s.get("session_key") or str(i)): s for i, s in enumerate(sessions) if isinstance(s, dict)
            }
        else:
            data.setdefault("sessions", {})
            if not isinstance(data["sessions"], dict):
                data["sessions"] = {}
        spent = data.get("time_spent")
        if not isinstance(spent, dict):
            data["time_spent"] = {}
        else:
            data.setdefault("time_spent", {})
        return data
    except (OSError, json.JSONDecodeError):
        return {"sessions": {}, "time_spent": {}}


def _save(data: dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    PRESENCE_PATH.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _ip_hash(ip: str) -> str:
    return hashlib.sha256((ip or "unknown").encode("utf-8")).hexdigest()[:16]


def _is_private_ip(ip: str) -> bool:
    if not ip:
        return True
    if ip in ("127.0.0.1", "::1", "localhost"):
        return True
    if ip.startswith("10.") or ip.startswith("192.168.") or ip.startswith("172."):
        return True
    return False


def resolve_geo(
    ip: str,
    *,
    client_lat: float | None = None,
    client_lng: float | None = None,
    client_city: str | None = None,
    client_country: str | None = None,
) -> dict[str, Any]:
    """Coarse location: prefer browser consent coords, else IP lookup, else local stub."""
    if client_lat is not None and client_lng is not None:
        return {
            "city": (client_city or "").strip() or "Approx",
            "country": (client_country or "").strip() or "",
            "lat": float(client_lat),
            "lng": float(client_lng),
            "source": "browser",
        }
    if _is_private_ip(ip):
        return {
            "city": "Local",
            "country": "Local",
            "lat": 37.77,
            "lng": -122.42,
            "source": "local",
        }
    cached = GEO_CACHE.get(ip)
    if cached:
        return dict(cached)
    # Free IP geolocation (best-effort; fail soft)
    try:
        url = f"http://ip-api.com/json/{ip}?fields=status,city,country,lat,lon"
        req = urllib.request.Request(url, headers={"User-Agent": "qoa_web-presence/1.0"})
        with urllib.request.urlopen(req, timeout=2.5) as resp:
            payload = json.loads(resp.read().decode("utf-8", errors="replace"))
        if payload.get("status") == "success":
            geo = {
                "city": payload.get("city") or "",
                "country": payload.get("country") or "",
                "lat": float(payload.get("lat") or 0) or None,
                "lng": float(payload.get("lon") or 0) or None,
                "source": "ip",
            }
            GEO_CACHE[ip] = geo
            return dict(geo)
    except Exception:
        pass
    return {"city": "Unknown", "country": "", "lat": None, "lng": None, "source": "none"}


def record_heartbeat(
    *,
    session_key: str,
    user_id: str | None,
    display_name: str,
    email: str = "",
    project_id: str | None,
    path: str,
    avatar: str,
    ip: str,
    roles: list[str] | None = None,
    client_lat: float | None = None,
    client_lng: float | None = None,
    client_city: str | None = None,
    client_country: str | None = None,
) -> dict[str, Any]:
    geo = resolve_geo(
        ip,
        client_lat=client_lat,
        client_lng=client_lng,
        client_city=client_city,
        client_country=client_country,
    )
    now = _now()
    with _lock:
        data = _load()
        sessions = data["sessions"]
        prev = sessions.get(session_key) or {}
        last_ts = float(prev.get("ts") or 0)
        delta = now - last_ts if last_ts else 0
        # Cap idle gaps so overnight leave doesn't count as time spent
        if 0 < delta <= 120 and project_id:
            spend_key = f"{user_id or session_key}:{project_id}"
            spent = data["time_spent"]
            spent[spend_key] = float(spent.get(spend_key) or 0) + delta
        loc_label = ", ".join(x for x in [geo.get("city"), geo.get("country")] if x) or "Unknown"
        entry = {
            "session_key": session_key,
            "user_id": user_id,
            "display_name": display_name or "Guest",
            "email": email,
            "project_id": project_id,
            "path": (path or "/")[:200],
            "avatar": avatar or "creator",
            "roles": list(roles or []),
            "ts": now,
            "started_at": float(prev.get("started_at") or now),
            "ip_hash": _ip_hash(ip),
            "city": geo.get("city") or "",
            "country": geo.get("country") or "",
            "lat": geo.get("lat"),
            "lng": geo.get("lng"),
            "location_label": loc_label,
            "geo_source": geo.get("source"),
        }
        sessions[session_key] = entry
        # prune stale
        cutoff = now - 86400
        data["sessions"] = {k: v for k, v in sessions.items() if float(v.get("ts") or 0) >= cutoff}
        _save(data)
        return entry


def _is_online(entry: dict[str, Any], now: float | None = None) -> bool:
    now = now if now is not None else _now()
    return (now - float(entry.get("ts") or 0)) <= ONLINE_TTL_SEC


def list_live(
    *,
    project_id: str | None = None,
    redact: bool = False,
) -> dict[str, Any]:
    now = _now()
    with _lock:
        data = _load()
        raw = data.get("sessions") or {}
        if isinstance(raw, dict):
            sessions = list(raw.values())
        else:
            sessions = list(raw)
    if project_id:
        sessions = [s for s in sessions if s.get("project_id") == project_id]
    online = [s for s in sessions if _is_online(s, now)]
    countries = {s.get("country") for s in sessions if s.get("country")}
    mapped = [s for s in sessions if s.get("lat") is not None and s.get("lng") is not None]

    def _public(s: dict[str, Any]) -> dict[str, Any]:
        dur = max(0, now - float(s.get("started_at") or s.get("ts") or now))
        out = {
            "session_key": s.get("session_key"),
            "user_id": s.get("user_id"),
            "display_name": s.get("display_name"),
            "avatar": s.get("avatar"),
            "path": s.get("path"),
            "project_id": s.get("project_id"),
            "city": s.get("city"),
            "country": s.get("country"),
            "location_label": s.get("location_label") or "Unknown",
            "lat": s.get("lat"),
            "lng": s.get("lng"),
            "online": _is_online(s, now),
            "duration_sec": int(dur),
            "ago_sec": int(max(0, now - float(s.get("ts") or now))),
            "roles": s.get("roles") or [],
        }
        if redact:
            out["display_name"] = (out["display_name"] or "User")[:1] + "…"
            out["email"] = ""
            # Hide confidential app paths for non-members
            path = out.get("path") or "/"
            if any(x in path for x in ("/heal", "/analyze", "chat", "ypad")):
                out["path"] = "/app"
        return out

    recent = sorted(sessions, key=lambda s: float(s.get("ts") or 0), reverse=True)[:40]
    return {
        "online_now": len(online),
        "total_sessions": len(sessions),
        "mapped_locations": len(mapped),
        "countries": len(countries),
        "markers": [
            {
                "lat": s["lat"],
                "lng": s["lng"],
                "avatar": s.get("avatar"),
                "online": _is_online(s, now),
                "label": s.get("city") or s.get("country") or "Unknown",
            }
            for s in mapped
            if s.get("lat") is not None
        ],
        "recent": [_public(s) for s in recent],
    }


def time_spent_seconds(user_id: str | None, project_id: str) -> float:
    if not project_id:
        return 0.0
    with _lock:
        data = _load()
        key = f"{user_id}:{project_id}"
        return float((data.get("time_spent") or {}).get(key) or 0)


def time_spent_for_project(project_id: str) -> list[dict[str, Any]]:
    prefix = f":{project_id}"
    with _lock:
        data = _load()
        spent = data.get("time_spent") or {}
    out = []
    for k, sec in spent.items():
        if not k.endswith(prefix) and not k.endswith(f":{project_id}"):
            continue
        uid = k.rsplit(":", 1)[0]
        out.append({"user_id": uid, "seconds": float(sec)})
    return sorted(out, key=lambda x: -x["seconds"])
