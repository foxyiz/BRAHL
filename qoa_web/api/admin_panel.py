"""Scoped Admin panel — Super Admin / Admin / Client Project Admin."""

from __future__ import annotations

from typing import Any

import auth as auth_store
import presence as presence_store
import projects as project_store


CONFIDENTIAL_PROJECT_KEYS = (
    "chat_messages",
    "documents",
    "context_items",
    "brahl_plan_draft",
    "hunt_artifacts",
    "manual_purpose",
)


def is_project_member(project: dict[str, Any], user: dict[str, Any] | None) -> bool:
    if not project or not user:
        return False
    uid = user.get("id")
    if not uid:
        return False
    if project.get("owner_user_id") == uid:
        return True
    for c in project.get("hitl_consultants") or []:
        if c.get("user_id") == uid or c.get("email") == user.get("email"):
            return True
    return False


def can_project_admin(project: dict[str, Any], user: dict[str, Any] | None) -> bool:
    """Creator/owner of the project (or platform admin who is a member)."""
    if not user or not project:
        return False
    if project.get("owner_user_id") and project.get("owner_user_id") == user.get("id"):
        return True
    # Demo/legacy unowned projects: allow any creator role for local ops
    if not project.get("owner_user_id"):
        roles = set(user.get("roles") or [])
        if "creator" in roles or user.get("role") in ("creator", "both", "admin", "super_admin"):
            return True
    if auth_store.is_platform_admin(user) and is_project_member(project, user):
        return True
    return False


def redact_project(project: dict[str, Any], *, member: bool) -> dict[str, Any]:
    """Strip confidential fields for non-members (super admin browse)."""
    p = dict(project)
    if member:
        return p
    for k in CONFIDENTIAL_PROJECT_KEYS:
        p.pop(k, None)
    # Keep lightweight metadata
    ai_u = p.get("ai_usage") or {}
    p["ai_usage"] = {
        "total_tokens": ai_u.get("total_tokens"),
        "usd_est": ai_u.get("usd_est"),
    }
    p["chat_messages"] = []
    p["redacted"] = True
    p["hitl_consultants"] = [
        {
            "id": c.get("id"),
            "consultant_name": (c.get("consultant_name") or "Hunter")[:1] + "…",
            "status": c.get("status"),
        }
        for c in (project.get("hitl_consultants") or [])
    ]
    return p


def admin_me(user: dict[str, Any] | None, *, token_bootstrap: bool = False) -> dict[str, Any]:
    roles = list((user or {}).get("roles") or [])
    platform = auth_store.is_platform_admin(user) or token_bootstrap
    super_a = auth_store.is_super_admin(user) or (
        token_bootstrap and not user
    )  # bare token => treat as super for local bootstrap
    if token_bootstrap and user is None:
        roles = ["super_admin"]
        super_a = True
        platform = True
    projects = project_store.load_projects()
    owned = []
    for p in projects:
        if can_project_admin(p, user) or (not user and token_bootstrap and not p.get("owner_user_id")):
            owned.append(
                {
                    "id": p.get("id"),
                    "name": p.get("name"),
                    "suite_name": p.get("suite_name"),
                    "status": p.get("status"),
                }
            )
    # Local demo: any client projects without ownership if bootstrap or creator
    if user and "creator" in roles:
        for p in projects:
            if p.get("owner_avatar") == "client" and not any(o["id"] == p.get("id") for o in owned):
                if not p.get("owner_user_id") or p.get("owner_user_id") == user.get("id"):
                    owned.append(
                        {
                            "id": p.get("id"),
                            "name": p.get("name"),
                            "suite_name": p.get("suite_name"),
                            "status": p.get("status"),
                        }
                    )
    return {
        "user": user,
        "roles": roles,
        "is_super_admin": super_a,
        "is_platform_admin": platform,
        "can_platform": platform,
        "project_scopes": owned,
        "tabs": _tabs_for(platform=platform, has_projects=bool(owned)),
    }


def _tabs_for(*, platform: bool, has_projects: bool) -> list[str]:
    if platform:
        return ["users", "clients", "projects", "consultants", "xp", "live", "gtm"]
    if has_projects:
        return ["users", "projects", "consultants", "xp", "live"]
    return []


def list_platform_users() -> list[dict[str, Any]]:
    users = auth_store.list_users()
    return [
        {
            "id": u["id"],
            "email": u.get("email"),
            "name": u.get("name"),
            "roles": u.get("roles") or [],
            "role": u.get("role"),
            "country": u.get("country"),
            "created_at": u.get("created_at"),
            "profile_complete": u.get("profile_complete"),
        }
        for u in users
    ]


def list_clients_summary() -> dict[str, Any]:
    projects = [p for p in project_store.load_projects() if p.get("owner_avatar") == "client"]
    by_owner: dict[str, dict[str, Any]] = {}
    for p in projects:
        oid = p.get("owner_user_id") or "unowned"
        entry = by_owner.setdefault(
            oid,
            {"owner_user_id": p.get("owner_user_id"), "name": "", "email": "", "project_count": 0, "roles": ["creator"]},
        )
        entry["project_count"] += 1
        if p.get("owner_user_id"):
            u = auth_store.get_user(p["owner_user_id"])
            if u:
                entry["name"] = u.get("name") or u.get("email")
                entry["email"] = u.get("email")
                entry["roles"] = u.get("roles") or ["creator"]
        else:
            entry["name"] = entry["name"] or f"Demo · {p.get('name')}"
    return {
        "total_clients": len(by_owner),
        "projects_posted": len(projects),
        "active_clients": sum(1 for p in projects if p.get("status") in ("open", "in_progress")),
        "clients": list(by_owner.values()),
    }


def list_projects_for_admin(user: dict[str, Any] | None, *, platform: bool) -> list[dict[str, Any]]:
    out = []
    for p in project_store.load_projects():
        if p.get("owner_avatar") != "client":
            continue
        member = is_project_member(p, user) or can_project_admin(p, user)
        if platform and not user and not p.get("owner_user_id"):
            member = True
        if not platform and not member and not can_project_admin(p, user):
            continue
        view = redact_project(p, member=member)
        # Platform non-member: metadata only
        if platform and not member:
            view = redact_project(p, member=False)
        out.append(
            {
                "id": view.get("id"),
                "name": view.get("name"),
                "status": view.get("status"),
                "suite_name": view.get("suite_name"),
                "budget_usd": view.get("budget_usd"),
                "ai_enabled": view.get("ai_enabled", True),
                "latest_run": view.get("latest_run"),
                "redacted": bool(view.get("redacted")),
                "is_member": member,
                "hunter_count": len(p.get("hitl_consultants") or []),
                "purpose": (view.get("purpose") or view.get("prompt") or "")[:180]
                if member
                else "",
            }
        )
    return out


def list_consultants_for_scope(
    user: dict[str, Any] | None,
    *,
    platform: bool,
    project_id: str | None,
) -> dict[str, Any]:
    hunters: list[dict[str, Any]] = []
    if project_id:
        p = project_store.get_project(project_id)
        if not p or not can_project_admin(p, user):
            if not (platform and p and is_project_member(p, user)):
                if not (platform and p):
                    return {"total": 0, "consultants": []}
                # platform non-member: anonymized
                for c in p.get("hitl_consultants") or []:
                    hunters.append(
                        {
                            "name": (c.get("consultant_name") or "H")[:1] + "…",
                            "status": c.get("status"),
                            "project_id": project_id,
                            "redacted": True,
                        }
                    )
                return {"total": len(hunters), "consultants": hunters}
        for c in (p or {}).get("hitl_consultants") or []:
            uid = c.get("user_id")
            spent = presence_store.time_spent_seconds(uid, project_id) if uid else 0
            hunters.append(
                {
                    "id": c.get("id"),
                    "name": c.get("consultant_name") or c.get("team_name") or "Hunter",
                    "email": c.get("email"),
                    "status": c.get("status"),
                    "tier": c.get("tier"),
                    "project_id": project_id,
                    "time_spent_sec": spent,
                }
            )
        return {"total": len(hunters), "consultants": hunters}

    # Platform-wide: aggregate hunters from projects + users with qa_hunter
    if platform:
        for u in auth_store.list_users():
            roles = u.get("roles") or []
            if "qa_hunter" in roles:
                hunters.append(
                    {
                        "id": u["id"],
                        "name": u.get("name") or u.get("email"),
                        "email": u.get("email"),
                        "roles": roles,
                        "status": "registered",
                    }
                )
        return {"total": len(hunters), "consultants": hunters}
    return {"total": 0, "consultants": []}


def project_overview(project_id: str, user: dict[str, Any] | None, *, platform: bool) -> dict[str, Any]:
    p = project_store.get_project(project_id)
    if not p:
        raise KeyError(project_id)
    member = is_project_member(p, user) or can_project_admin(p, user)
    # Localhost / token bootstrap: treat unowned demo projects as operable (full Project Admin)
    if platform and not user and not p.get("owner_user_id"):
        member = True
    if not member and not platform:
        raise PermissionError("Not allowed")
    if not member and platform:
        # Aggregates only
        meter = None
        try:
            meter = project_store.compute_cost_meter(p)
            meter = {
                "budget_usd": meter.get("budget_usd"),
                "ai_usd_est": meter.get("ai_usd_est") or (meter.get("ai_usage") or {}).get("usd_est"),
                "runtime_mode": meter.get("runtime_mode"),
            }
        except Exception:
            meter = None
        live = presence_store.list_live(project_id=project_id, redact=True)
        return {
            "project": redact_project(p, member=False),
            "ai_enabled": p.get("ai_enabled", True),
            "cost_meter": meter,
            "hitl": [],
            "invites_pending": len([i for i in (p.get("hitl_invites") or []) if i.get("status") == "pending"]),
            "live": live,
            "time_spent": [],
            "access": "redacted",
        }

    meter = project_store.compute_cost_meter(p)
    live = presence_store.list_live(project_id=project_id, redact=False)
    spent = presence_store.time_spent_for_project(project_id)
    # attach names
    for row in spent:
        u = auth_store.get_user(row["user_id"]) if row.get("user_id") else None
        row["name"] = (u or {}).get("name") or row.get("user_id")
    return {
        "project": redact_project(p, member=True),
        "ai_enabled": p.get("ai_enabled", True),
        "cost_meter": meter,
        "hitl": p.get("hitl_consultants") or [],
        "invites_pending": [i for i in (p.get("hitl_invites") or []) if i.get("status") == "pending"],
        "live": live,
        "time_spent": spent,
        "access": "full",
    }


def set_project_ai(
    project_id: str,
    enabled: bool,
    user: dict[str, Any] | None,
    *,
    platform_bootstrap: bool = False,
) -> dict[str, Any]:
    p = project_store.get_project(project_id)
    if not p:
        raise KeyError(project_id)
    allowed = can_project_admin(p, user)
    if not allowed and platform_bootstrap and not p.get("owner_user_id"):
        allowed = True
    if not allowed:
        raise PermissionError("Project admin required")
    return project_store.update_project(project_id, {"ai_enabled": bool(enabled)})
