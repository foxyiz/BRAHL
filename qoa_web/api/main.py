"""qoa_web — local BRAHL web API + static frontend."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import projects as project_store
from runner import (
    KK_ROOT,
    analyze_run,
    compare_verify_runs,
    capture_brahl_context,
    create_ypad_suite,
    create_fstart_config,
    default_fstart_for_suite,
    default_fstart_template,
    delete_fstart_config,
    ensure_brahl_report,
    get_job,
    get_suite_detail,
    list_fstart_configs,
    list_fstart_for_suite,
    list_suites,
    list_z_runs,
    load_errors_excerpt,
    load_failures,
    read_fstart_config,
    report_stats,
    start_run,
    suite_report_context,
    write_fstart_config,
    write_run_report,
)
import ypad as ypad_store
import waitlist as waitlist_store
import invites as invite_store
import nalanda as nalanda_store
import auth as auth_store
import brahl_plan as brahl_plan_store

WEB_DIR = Path(__file__).resolve().parent.parent / "web"
APP_VERSION = "1.3.0"

app = FastAPI(title="qoa_web", description="BRAHL web — FoXYiZ local API", version=APP_VERSION)


@app.on_event("startup")
def _startup() -> None:
    auth_store.init_db()


class AuthRegisterRequest(BaseModel):
    email: str
    password: str = ""
    name: str = ""
    role: str = "creator"
    first_name: str = ""
    last_name: str = ""
    country: str = ""
    phone: str = ""
    roles: list[str] | None = None
    app_url: str = ""
    profile_complete: bool = True


class AuthLoginRequest(BaseModel):
    email: str
    password: str


class AuthSocialRequest(BaseModel):
    provider: str
    email: str
    name: str = ""


class AuthProfileUpdate(BaseModel):
    first_name: str = ""
    last_name: str = ""
    country: str = ""
    phone: str = ""
    roles: list[str] | None = None
    app_url: str = ""
    profile_complete: bool = True


class BrahlPlanGenerateRequest(BaseModel):
    requirement: str
    budget_usd: float | None = None
    automation_pct: int | None = None


class BrahlPlanAcceptRequest(BaseModel):
    brahl_plan: dict[str, Any]


class AuthForgotRequest(BaseModel):
    email: str


class AuthResetRequest(BaseModel):
    token: str
    password: str


def _auth_user(request: Request) -> dict[str, Any] | None:
    return auth_store.user_from_request(request.headers.get("Authorization"))


def _require_project(project_id: str, request: Request) -> dict[str, Any]:
    project = project_store.get_project(project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    user = _auth_user(request)
    if not project_store.user_can_access_project(project, user):
        raise HTTPException(403, "Not allowed to access this project")
    return project


class RunRequest(BaseModel):
    config_path: str = Field(default="f/fStart_Math_smoke.json")
    step_label: str = Field(default="Run")


class ContextRequest(BaseModel):
    prompt: str
    config_path: str = Field(default="f/fStart_Math_smoke.json")
    documents: list[dict[str, str]] | None = None
    project_id: str | None = None


class YpadProjectCreate(BaseModel):
    name: str
    app_url: str = ""
    purpose: str = ""
    budget_usd: float = 0
    ai_enabled: bool = True
    context_items: list[dict[str, str]] | None = None


class PlannerChatRequest(BaseModel):
    message: str
    draft: dict[str, Any] | None = None
    history: list[dict[str, str]] | None = None


class PlannerCreateRequest(BaseModel):
    draft: dict[str, Any]
    brahl_plan: dict[str, Any] | None = None
    quick_brahl: bool = False


class ProjectCreate(BaseModel):
    name: str = ""
    app_url: str = ""
    purpose: str = ""
    suite_name: str = ""
    suite_config: str = ""
    budget_usd: float = 0
    budget_split: dict[str, int] | None = None
    ai_enabled: bool = True
    context_items: list[dict[str, str]] | None = None


class ProjectUpdate(BaseModel):
    name: str | None = None
    app_url: str | None = None
    purpose: str | None = None
    status: str | None = None
    budget_usd: float | None = None
    budget_split: dict[str, int] | None = None
    ai_enabled: bool | None = None
    brahl_context_path: str | None = None
    latest_run: str | None = None
    runtime_mode: str | None = None
    app_version: str | None = None
    baseline_version: str | None = None
    baseline_run: str | None = None


class VersionBaselineRequest(BaseModel):
    version_label: str = ""
    run_name: str | None = None


class ChatMessage(BaseModel):
    text: str


class HitlStoryCreate(BaseModel):
    title: str
    description: str = ""


class InviteHitlRequest(BaseModel):
    note: str = ""
    consultant_name: str = ""
    team_name: str = ""  # legacy alias
    email: str = ""
    consultant_tag: str = ""
    bug_bounty: bool = False


class ChangeAssistanceRequest(BaseModel):
    note: str = ""


class YpadSheetSave(BaseModel):
    headers: list[str] | None = None
    rows: list[dict[str, str]]


class ContextItem(BaseModel):
    kind: str = "connector"
    label: str = ""
    value: str = ""


class HitlReportSubmit(BaseModel):
    run_name: str
    report_path: str | None = None
    critical_issues: int = 0
    time_hours: float = 0.0
    features_found: int = 0
    hunt_report_path: str | None = None
    artifact_paths: list[str] | None = None


class BrahlReportRegister(BaseModel):
    run_name: str
    source: str = "automation"


class BrahlChatMessage(BaseModel):
    text: str
    run_name: str | None = None


class Atomic77ChatMessage(BaseModel):
    text: str
    faq_key: str | None = None
    avatar: str | None = None


class Atomic77PlatformChat(BaseModel):
    text: str
    faq_key: str | None = None
    avatar: str = "client"
    project_id: str | None = None


class YpadSuiteRequest(BaseModel):
    suite_config: str = Field(default="y/Math/Math.json")


class ShrinkRequest(BaseModel):
    run_name: str
    suite_config: str = Field(default="y/Math/Math.json")


class ReportGenerateRequest(BaseModel):
    run_name: str
    config_path: str = Field(default="f/fStart_Math_verify.json")
    step_label: str = Field(default="Verify")
    project_id: str | None = None


class CycleEventRequest(BaseModel):
    step: str
    detail: str = ""
    run_name: str | None = None


class WaitlistRequest(BaseModel):
    email: str
    role: str = Field(default="any", description="creator | consultant | networker | any")
    note: str = ""
    source: str = Field(default="signin")


class InviteRedeemRequest(BaseModel):
    code: str
    email: str = ""
    note: str = ""


class InviteBatchRequest(BaseModel):
    batch_type: str = Field(description="creator | consultant | nalanda")
    label: str = ""
    count: int = Field(default=50, ge=1, le=200)
    trial_days: int = Field(default=7, ge=1, le=30)


class NalandaLessonRequest(BaseModel):
    profile_id: str
    title: str
    blurb: str = ""
    url: str = ""
    tags: list[str] = Field(default_factory=list)
    author_name: str = ""


class NalandaThreadRequest(BaseModel):
    profile_id: str
    title: str
    body: str
    author_name: str = ""


class NalandaReplyRequest(BaseModel):
    profile_id: str
    body: str
    author_name: str = ""


def _admin_token_ok(request: Request) -> bool:
    expected = os.environ.get("QOA_ADMIN_TOKEN", "").strip()
    if expected:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            return auth[7:].strip() == expected
        return request.headers.get("X-Admin-Token", "").strip() == expected
    client = request.client.host if request.client else ""
    return client in ("127.0.0.1", "::1")


def _require_admin(request: Request) -> None:
    if not _admin_token_ok(request):
        raise HTTPException(403, "Admin token required (QOA_ADMIN_TOKEN)")


@app.get("/api/version")
def version() -> dict[str, str]:
    return {"version": APP_VERSION, "service": "qoa_web", "brahl_phases": "Build,Run,Analyze,Heal,Loop,BRAHL"}


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "qoa_web", "version": APP_VERSION, "root": str(KK_ROOT)}


@app.post("/api/auth/register")
def auth_register(body: AuthRegisterRequest) -> dict[str, Any]:
    try:
        user = auth_store.register_user(
            body.email,
            body.password or None,
            body.name,
            body.role,
            first_name=body.first_name,
            last_name=body.last_name,
            country=body.country,
            phone=body.phone,
            roles=body.roles,
            app_url=body.app_url,
            profile_complete=body.profile_complete,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    token = auth_store.create_token(user)
    return {"user": user, "token": token}


@app.post("/api/auth/login")
def auth_login(body: AuthLoginRequest) -> dict[str, Any]:
    user = auth_store.authenticate_user(body.email, body.password)
    if not user:
        raise HTTPException(401, "Invalid email or password")
    token = auth_store.create_token(user)
    return {"user": user, "token": token}


@app.post("/api/auth/social")
def auth_social(body: AuthSocialRequest) -> dict[str, Any]:
    """Social sign-in stub (wire real OAuth later). Continues to profile step when incomplete."""
    try:
        user = auth_store.social_login_or_register(body.provider, body.email, body.name)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    token = auth_store.create_token(user)
    return {"user": user, "token": token, "needs_profile": not user.get("profile_complete")}


@app.get("/api/auth/me")
def auth_me(request: Request) -> dict[str, Any]:
    user = auth_store.user_from_request(request.headers.get("Authorization"))
    if not user:
        raise HTTPException(401, "Not authenticated")
    return {"user": user}


@app.patch("/api/auth/me")
async def auth_me_update(request: Request, body: AuthProfileUpdate) -> dict[str, Any]:
    user = auth_store.user_from_request(request.headers.get("Authorization"))
    if not user:
        raise HTTPException(401, "Not authenticated")
    try:
        updated = auth_store.update_user_profile(
            user["id"],
            {
                "first_name": body.first_name,
                "last_name": body.last_name,
                "country": body.country,
                "phone": body.phone,
                "roles": body.roles,
                "app_url": body.app_url,
                "profile_complete": body.profile_complete,
            },
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    token = auth_store.create_token(updated)
    return {"user": updated, "token": token}


@app.post("/api/auth/me/profile-upload")
async def auth_profile_upload(request: Request, file: UploadFile = File(...)) -> dict[str, Any]:
    user = auth_store.user_from_request(request.headers.get("Authorization"))
    if not user:
        raise HTTPException(401, "Not authenticated")
    data = await file.read()
    if len(data) > 5_000_000:
        raise HTTPException(400, "Profile file too large (max 5MB)")
    try:
        rel = auth_store.save_profile_upload(user["id"], file.filename or "profile.bin", data)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    updated = auth_store.get_user(user["id"])
    return {"ok": True, "profile_path": rel, "user": updated}


@app.get("/api/config")
def public_config() -> dict[str, Any]:
    return {
        "allow_demo": auth_store.demo_allowed(),
        "auth_enabled": True,
        "version": APP_VERSION,
    }


@app.post("/api/auth/forgot-password")
def auth_forgot(body: AuthForgotRequest) -> dict[str, Any]:
    token = auth_store.create_password_reset(body.email)
    # Always return ok — do not leak whether email exists. Dev: include reset_token when demo.
    out: dict[str, Any] = {
        "ok": True,
        "message": "If that email is registered, a reset link is available.",
    }
    if token and auth_store.demo_allowed():
        out["reset_token"] = token
        out["reset_path"] = f"/forgot-password?token={token}"
    return out


@app.post("/api/auth/reset-password")
def auth_reset(body: AuthResetRequest) -> dict[str, Any]:
    try:
        auth_store.reset_password(body.token, body.password)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"ok": True, "message": "Password updated — log in with your new password."}


@app.post("/api/projects/{project_id}/brahl-plan/generate")
def brahl_plan_generate(project_id: str, body: BrahlPlanGenerateRequest, request: Request) -> dict[str, Any]:
    project = _require_project(project_id, request)
    if not project.get("ai_enabled", True):
        raise HTTPException(400, "AI is off for this project")
    try:
        result = brahl_plan_store.generate_brahl_plan(
            body.requirement,
            project_name=project.get("name") or "project",
            app_url=project.get("app_url") or "",
            budget_usd=float(body.budget_usd or project.get("budget_usd") or 0),
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return result


@app.post("/api/projects/{project_id}/brahl-plan/accept")
def brahl_plan_accept(project_id: str, body: BrahlPlanAcceptRequest, request: Request) -> dict[str, Any]:
    _require_project(project_id, request)
    try:
        project = project_store.apply_brahl_plan(project_id, body.brahl_plan)
    except KeyError:
        raise HTTPException(404, "Project not found") from None
    return {"project": project}


class FstartCreate(BaseModel):
    suite_name: str
    variant: str = Field(default="verify", description="verify | smoke | smoke_headless")


class FstartSave(BaseModel):
    path: str
    content: dict[str, Any]


@app.get("/api/configs")
def configs(suite: str | None = None) -> dict[str, Any]:
    if suite:
        items = list_fstart_for_suite(suite)
        default = items[0] if items else None
        if not default:
            suggested = f"f/fStart_{suite}_verify.json"
            return {
                "configs": [],
                "default": None,
                "suggested": suggested,
                "suite": suite,
                "template": default_fstart_template(suite),
            }
        return {"configs": items, "default": default, "suite": suite}
    all_cfgs = list_fstart_configs()
    return {"configs": all_cfgs}


@app.get("/api/configs/content")
def config_content(path: str) -> dict[str, Any]:
    try:
        data = read_fstart_config(path)
    except FileNotFoundError:
        raise HTTPException(404, f"Config not found: {path}") from None
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"path": path.replace("\\", "/"), "content": data}


@app.put("/api/configs/content")
def config_save(body: FstartSave) -> dict[str, Any]:
    try:
        rel = write_fstart_config(body.path, body.content)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"path": rel, "ok": True}


@app.post("/api/configs")
def config_create(body: FstartCreate) -> dict[str, Any]:
    if not get_suite_detail(body.suite_name):
        raise HTTPException(404, f"Suite not found: {body.suite_name}")
    try:
        rel = create_fstart_config(body.suite_name, body.variant)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    return {"path": rel, "content": read_fstart_config(rel)}


@app.delete("/api/configs/content")
def config_delete(path: str) -> dict[str, str]:
    try:
        delete_fstart_config(path)
    except FileNotFoundError:
        raise HTTPException(404, f"Config not found: {path}") from None
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"ok": True, "path": path}


@app.get("/api/ai/status")
def ai_status() -> dict[str, Any]:
    import ai_assist
    import ai_docs

    docs = ai_docs.list_ai_docs()
    in_prompt = [d for d in docs if d.get("in_prompt")]
    return {
        "available": ai_assist.is_ai_available(),
        "model": os.environ.get("OPENAI_MODEL", "gpt-4o-mini") if ai_assist.is_ai_available() else None,
        "docs_loaded": bool(ai_assist.brahl_doc_context(100)),
        "context_doc_count": len(in_prompt),
        "reference_doc_count": len(docs),
    }


@app.get("/api/ai/docs")
def ai_docs_list() -> dict[str, Any]:
    import ai_docs

    return {
        "docs": ai_docs.list_ai_docs(),
        "note": "Shared across all projects — not per-project. BRAHL + FoXYiZ are loaded into AI prompts when AI is on.",
    }


@app.get("/api/ai/docs/{doc_id}")
def ai_doc_content(doc_id: str) -> dict[str, Any]:
    import ai_docs

    doc = ai_docs.get_ai_doc(doc_id)
    if not doc:
        raise HTTPException(404, f"Document not found: {doc_id}")
    return {"doc": doc}


@app.get("/api/test-users")
def test_users_list() -> dict[str, Any]:
    import test_users as test_user_store

    idx = test_user_store.load_index()
    return {
        "fictional": True,
        "source": "Docs/test-user-data/",
        "version": idx.get("version"),
        "personas": test_user_store.list_personas(),
    }


@app.get("/api/test-users/{persona_id}")
def test_user_detail(persona_id: str) -> dict[str, Any]:
    import test_users as test_user_store

    try:
        persona = test_user_store.load_persona(persona_id)
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    return {
        "fictional": True,
        "persona": persona,
        "frontend": test_user_store.to_frontend_profile(persona),
    }


@app.get("/api/test-users/{persona_id}/tasks")
def test_user_tasks(persona_id: str, avatar: str = "client") -> dict[str, Any]:
    import test_users as test_user_store

    try:
        persona = test_user_store.load_persona(persona_id)
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    tasks = test_user_store.tasks_for_avatar(persona, avatar)
    return {
        "fictional": True,
        "persona_id": persona["id"],
        "avatar": avatar,
        "tasks": tasks,
    }


@app.get("/api/test-users/{persona_id}/fixture")
def test_user_fixture(persona_id: str) -> dict[str, Any]:
    import test_users as test_user_store

    try:
        bundle = test_user_store.fixture_bundle(persona_id)
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    return {"fictional": True, "fixture": bundle}


@app.get("/api/suites")
def suites() -> dict[str, Any]:
    return {"suites": list_suites()}


@app.get("/api/suites/{suite_name}")
def suite_detail(suite_name: str) -> dict[str, Any]:
    detail = get_suite_detail(suite_name)
    if not detail:
        raise HTTPException(404, f"Suite not found: {suite_name}")
    return {"suite": detail}


def _suite_config_for_name(suite_name: str) -> str:
    detail = get_suite_detail(suite_name)
    if not detail:
        raise HTTPException(404, f"Suite not found: {suite_name}")
    return detail.get("path") or f"y/{suite_name}/{suite_name}.json"


@app.get("/api/suites/{suite_name}/ypad/{sheet}")
def get_ypad_sheet(suite_name: str, sheet: str) -> dict[str, Any]:
    sheet = sheet.lower()
    if sheet not in ("plans", "actions", "designs", "env"):
        raise HTTPException(400, "sheet must be plans, actions, designs, or env")
    suite_config = _suite_config_for_name(suite_name)
    try:
        if sheet == "env":
            return ypad_store.read_env_example(suite_config)
        return ypad_store.read_ypad_sheet(suite_config, sheet)
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc


@app.put("/api/suites/{suite_name}/ypad/{sheet}")
def put_ypad_sheet(suite_name: str, sheet: str, body: YpadSheetSave) -> dict[str, Any]:
    sheet = sheet.lower()
    if sheet not in ("plans", "actions", "designs"):
        raise HTTPException(400, "Only plans, actions, and designs are editable")
    suite_config = _suite_config_for_name(suite_name)
    try:
        return ypad_store.write_ypad_sheet(suite_config, sheet, body.rows, body.headers)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(400, str(exc)) from exc


@app.get("/api/ypad-projects")
def ypad_projects() -> dict[str, Any]:
    return {"suites": list_suites()}


@app.get("/api/ypad-projects/{suite_name}")
def ypad_project_workspace(suite_name: str) -> dict[str, Any]:
    detail = get_suite_detail(suite_name)
    if not detail:
        raise HTTPException(404, f"Project not found: {suite_name}")
    project = project_store.get_or_create_for_suite(suite_name, detail)
    payout = project_store.compute_payout_preview(project)
    return {"suite": detail, "project": project, "payout_preview": payout}


@app.post("/api/ypad-projects")
def create_ypad_project(body: YpadProjectCreate, request: Request) -> dict[str, Any]:
    name = body.name.strip()
    if not name:
        raise HTTPException(400, "name required")
    try:
        detail = create_ypad_suite(name, body.app_url, body.purpose)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(500, f"Could not scaffold yPAD: {exc}") from exc
    safe = detail["name"]
    auth_user = auth_store.user_from_request(request.headers.get("Authorization"))
    project = project_store.create_project(
        {
            "name": safe,
            "app_url": body.app_url or detail.get("url") or "",
            "purpose": body.purpose or detail.get("description") or "",
            "suite_name": safe,
            "suite_config": detail.get("path") or f"y/{safe}/{safe}.json",
            "budget_usd": body.budget_usd,
            "ai_enabled": body.ai_enabled,
            "context_items": body.context_items,
            "owner_user_id": auth_user.get("id") if auth_user else None,
        }
    )
    payout = project_store.compute_payout_preview(project)
    return {"suite": detail, "project": project, "payout_preview": payout}


@app.post("/api/planner/chat")
def planner_chat(body: PlannerChatRequest) -> dict[str, Any]:
    import planner as planner_store

    msg = (body.message or "").strip()
    if not msg:
        raise HTTPException(400, "message required")
    return planner_store.planner_turn(msg, body.draft, body.history)


@app.post("/api/planner/create")
def planner_create(body: PlannerCreateRequest, request: Request) -> dict[str, Any]:
    import planner as planner_store

    auth_user = auth_store.user_from_request(request.headers.get("Authorization"))
    try:
        created = planner_store.create_from_planner(
            body.draft,
            brahl_plan=body.brahl_plan,
            owner_user_id=auth_user.get("id") if auth_user else None,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(500, f"Could not create project: {exc}") from exc

    job = None
    if body.quick_brahl:
        config_path = created.get("config_path") or default_fstart_for_suite(created["suite"]["name"])
        try:
            job = start_run(config_path, step_label="Verify")
            created["quick_brahl_job"] = {
                "job_id": job.job_id,
                "status": job.status,
                "config_path": config_path,
            }
        except Exception as exc:
            created["quick_brahl_error"] = str(exc)
    return created


@app.get("/api/suites/{suite_name}/brahl/reports")
def suite_brahl_reports(suite_name: str) -> dict[str, Any]:
    detail = get_suite_detail(suite_name)
    if not detail:
        raise HTTPException(404, f"Suite not found: {suite_name}")
    runs = list_z_runs(suite_name)
    for r in runs:
        r["has_file"] = bool(r.get("report"))
    latest = runs[0]["name"] if runs else detail.get("latest_run")
    return {"suite": detail, "runs": runs, "latest_run_name": latest}


@app.get("/api/suites/{suite_name}/brahl/reports/{run_name}/content")
def suite_brahl_report_content(
    suite_name: str,
    run_name: str,
    project_id: str | None = None,
) -> dict[str, Any]:
    if not get_suite_detail(suite_name):
        raise HTTPException(404, f"Suite not found: {suite_name}")
    project = project_store.get_project(project_id) if project_id else None
    ctx = suite_report_context(suite_name, project)
    config_path = default_fstart_for_suite(suite_name)
    try:
        ensure_brahl_report(run_name, config_path=config_path, project=ctx)
        markdown = project_store.load_report_markdown(run_name, ctx)
        stats = report_stats(run_name)
    except FileNotFoundError:
        raise HTTPException(404, f"No results for run: {run_name}") from None
    version_compare = None
    if project:
        baseline_run = (project.get("baseline_run") or "").strip()
        if baseline_run and baseline_run != run_name:
            try:
                version_compare = compare_verify_runs(baseline_run, run_name)
                if version_compare:
                    version_compare["baseline_version"] = project.get("baseline_version") or "baseline (old)"
                    version_compare["app_version"] = project.get("app_version") or "current (new)"
            except Exception:
                version_compare = None
    return {"run_name": run_name, "markdown": markdown, "stats": stats, "suite": get_suite_detail(suite_name), "version_compare": version_compare}


@app.get("/api/runs")
def runs(suite: str | None = None) -> dict[str, Any]:
    return {"runs": list_z_runs(suite)}


@app.get("/api/runs/{run_name}/stats")
def run_stats(run_name: str) -> dict[str, Any]:
    run_dir = KK_ROOT / "z" / run_name
    if not run_dir.is_dir():
        raise HTTPException(404, f"Run not found: {run_name}")
    stats = analyze_run(run_name)
    stats["health"] = "green" if stats.get("fails", 0) == 0 and stats.get("total_plans", 0) > 0 else (
        "amber" if stats.get("total_plans", 0) > 0 else "unknown"
    )
    return stats


@app.get("/api/runs/{run_name}/failures")
def run_failures(run_name: str) -> dict[str, Any]:
    run_dir = KK_ROOT / "z" / run_name
    if not run_dir.is_dir():
        raise HTTPException(404, f"Run not found: {run_name}")
    return {"run": run_name, "failures": load_failures(run_dir)}


@app.post("/api/projects/{project_id}/runs/{run_name}/analyze-ai")
def analyze_run_ai(project_id: str, run_name: str) -> dict[str, Any]:
    import ai_assist

    project = project_store.get_project(project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    if not project.get("ai_enabled", True):
        raise HTTPException(400, "AI is off for this project — enable AI toggle on Build")
    run_dir = KK_ROOT / "z" / run_name
    if not run_dir.is_dir():
        raise HTTPException(404, f"Run not found: {run_name}")
    failures = load_failures(run_dir)
    errors = load_errors_excerpt(run_dir)
    stats = analyze_run(run_name)
    if not ai_assist.is_ai_available():
        return {
            "ai": False,
            "fallback": True,
            "markdown": _fallback_analyze_markdown(failures, errors, stats),
            "failures": failures,
            "stats": stats,
        }
    md = ai_assist.analyze_run_rca(project, run_name, failures, errors)
    if not md:
        md = _fallback_analyze_markdown(failures, errors, stats)
        return {"ai": False, "fallback": True, "markdown": md, "failures": failures, "stats": stats}
    return {"ai": True, "markdown": md, "failures": failures, "stats": stats}


@app.post("/api/projects/{project_id}/runs/{run_name}/heal-suggest")
def heal_suggest_ai(project_id: str, run_name: str, body: dict[str, str] | None = None) -> dict[str, Any]:
    import ai_assist

    project = project_store.get_project(project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    if not project.get("ai_enabled", True):
        raise HTTPException(400, "AI is off for this project")
    run_dir = KK_ROOT / "z" / run_name
    if not run_dir.is_dir():
        raise HTTPException(404, f"Run not found: {run_name}")
    failures = load_failures(run_dir)
    rca = (body or {}).get("rca_markdown", "")
    suite_config = project.get("suite_config") or f"y/{project.get('suite_name', 'qoa_web')}/{project.get('suite_name', 'qoa_web')}.json"
    if not ai_assist.is_ai_available():
        return {
            "ai": False,
            "markdown": _fallback_heal_markdown(failures, suite_config),
            "failures": failures,
        }
    md = ai_assist.heal_suggestions(project, run_name, failures, rca, suite_config)
    if not md:
        md = _fallback_heal_markdown(failures, suite_config)
        return {"ai": False, "markdown": md, "failures": failures}
    return {"ai": True, "markdown": md, "failures": failures}


def _fallback_analyze_markdown(failures: list, errors: str, stats: dict) -> str:
    lines = [
        "## Analyze (manual — set OPENAI_API_KEY in f/.env for AI RCA)",
        "",
        f"**{stats.get('passes', 0)}/{stats.get('total_plans', 0)} pass** · "
        f"**{stats.get('fails', 0)} fail**",
        "",
        "Per BRAHL.md, classify each failure as **T1** (yPAD), **T2** (engine), **T3** (env), or **A1** (app defect).",
        "",
        "| Plan | Step | Output |",
        "|------|------|--------|",
    ]
    for f in failures[:20]:
        lines.append(f"| {f.get('planId', '')} | {f.get('stepId', '')} | {f.get('output', '')[:80]} |")
    if errors:
        lines.extend(["", "### _errors.csv", "```", errors[:1500], "```"])
    return "\n".join(lines)


def _fallback_heal_markdown(failures: list, suite_config: str) -> str:
    lines = [
        "## Heal (manual — AI off or no API key)",
        "",
        f"Suite: `{suite_config}`",
        "",
        "Per BRAHL.md heal priority:",
        "1. yD_Common — locators & URLs",
        "2. y2Actions — steps, Expected, xReuse",
        "3. y1Plans — Run, Tags",
        "",
        "Use **Shrink to failures** before Loop 2/3; **Restore all Run=Y** before Verify.",
    ]
    if failures:
        lines.append("\nFailing plans: " + ", ".join({f.get("planId", "") for f in failures}))
    return "\n".join(lines)


@app.post("/api/ypad/shrink")
def ypad_shrink(body: ShrinkRequest) -> dict[str, Any]:
    try:
        return ypad_store.shrink_to_failures(body.run_name, body.suite_config)
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc


@app.post("/api/ypad/restore")
def ypad_restore(body: YpadSuiteRequest) -> dict[str, Any]:
    try:
        return ypad_store.restore_all_run_y(body.suite_config)
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc


@app.post("/api/runs/{run_name}/report")
def generate_report(run_name: str, body: ReportGenerateRequest) -> dict[str, Any]:
    if run_name != body.run_name:
        run_name = body.run_name
    project = None
    if body.project_id:
        project = project_store.get_project(body.project_id)
    try:
        result = write_run_report(run_name, body.config_path, body.step_label, project)
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    return result


@app.post("/api/projects/{project_id}/cycle")
def add_cycle_event(project_id: str, body: CycleEventRequest) -> dict[str, Any]:
    try:
        entry = project_store.append_cycle_event(project_id, body.step, body.detail, body.run_name)
    except KeyError:
        raise HTTPException(404, "Project not found") from None
    project = project_store.get_project(project_id)
    return {"event": entry, "project": project}


@app.get("/api/projects/{project_id}/cycle")
def get_cycle_history(project_id: str) -> dict[str, Any]:
    project = project_store.get_project(project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    return {"cycle_history": project.get("cycle_history") or []}


@app.post("/api/jobs")
def create_job(body: RunRequest) -> dict[str, Any]:
    """Start FoXYiZ fEngine2.py — Run/Loop execution path (no AI)."""
    job = start_run(body.config_path, body.step_label)
    return job.to_dict()


@app.get("/api/jobs/{job_id}")
def job_status(job_id: str) -> dict[str, Any]:
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job.to_dict()


@app.post("/api/context")
def create_context(body: ContextRequest) -> dict[str, Any]:
    try:
        result = capture_brahl_context(body.prompt, body.config_path, body.documents)
        if body.project_id:
            try:
                project_store.update_project(
                    body.project_id,
                    {"brahl_context_path": result.get("context_path")},
                )
            except KeyError:
                pass
        return result
    except Exception as exc:
        raise HTTPException(500, str(exc)) from exc


@app.get("/api/projects")
def list_projects(request: Request, role: str = "client") -> dict[str, Any]:
    user = _auth_user(request)
    if role == "consultant":
        items = project_store.list_consultant_projects()
        if user and user.get("role") not in ("qa_hunter", "both", "admin"):
            items = [p for p in items if project_store.user_can_access_project(p, user)]
    else:
        owner_id = user.get("id") if user and user.get("role") in ("creator", "both", "admin") else None
        items = project_store.list_client_projects(owner_user_id=owner_id)
        if user:
            items = [p for p in items if project_store.user_can_access_project(p, user)]
    return {"projects": items, "role": role}


@app.get("/api/projects/{project_id}/cost-meter")
def project_cost_meter(project_id: str, request: Request, runtime: str | None = None) -> dict[str, Any]:
    project = _require_project(project_id, request)
    meter = project_store.compute_cost_meter(project, runtime)
    return {"cost_meter": meter, "project": project}


@app.get("/api/consultant/wallet")
def consultant_wallet() -> dict[str, Any]:
    wallet = project_store.consultant_wallet()
    from pricing import get_pricing_rules

    wallet["pricing"] = get_pricing_rules(wallet_balance_usd=float(wallet.get("total_earned_usd") or 0))
    return {"wallet": wallet}


@app.get("/api/pricing")
def pricing_rules(
    budget_usd: float = 0,
    automation_pct: int = 50,
    human_pct: int = 50,
    wallet_balance_usd: float = 0,
) -> dict[str, Any]:
    from pricing import get_pricing_rules

    return {
        "pricing": get_pricing_rules(
            budget_usd=budget_usd,
            automation_pct=automation_pct,
            human_pct=human_pct,
            wallet_balance_usd=wallet_balance_usd,
        )
    }


@app.get("/api/projects/{project_id}")
def get_project(project_id: str, request: Request) -> dict[str, Any]:
    project = _require_project(project_id, request)
    payout = project_store.compute_payout_preview(project)
    return {"project": project, "payout_preview": payout}


@app.get("/api/projects/{project_id}/build-board")
def build_board(project_id: str, request: Request) -> dict[str, Any]:
    project = _require_project(project_id, request)
    suite_name = project.get("suite_name") or "qoa_web"
    suite_config = project.get("suite_config") or f"y/{suite_name}/{suite_name}.json"
    try:
        automation = ypad_store.list_automation_plans(suite_config)
    except FileNotFoundError:
        automation = []
    suite = get_suite_detail(suite_name)
    latest_run = project.get("latest_run")
    report_stats_data = None
    if latest_run:
        try:
            report_stats_data = report_stats(latest_run)
        except Exception:
            report_stats_data = None
    version_compare = None
    baseline_run = (project.get("baseline_run") or "").strip()
    if baseline_run and latest_run and baseline_run != latest_run:
        try:
            version_compare = compare_verify_runs(baseline_run, latest_run)
            if version_compare:
                version_compare["baseline_version"] = project.get("baseline_version") or "baseline (old)"
                version_compare["app_version"] = project.get("app_version") or "current (new)"
        except Exception:
            version_compare = None
    user_msgs = [m for m in project.get("chat_messages") or [] if m.get("role") == "user"]
    requirement = (project.get("purpose") or project.get("prompt") or "").strip()
    if not requirement and user_msgs:
        requirement = (user_msgs[0].get("text") or "").strip()
    return {
        "requirement": requirement,
        "automation_plans": automation,
        "hitl_stories": project.get("hitl_stories") or [],
        "hitl_consultants": project.get("hitl_consultants") or [],
        "hitl_invites": project.get("hitl_invites") or [],
        "change_requests": project.get("change_requests") or [],
        "latest_run": latest_run,
        "report_stats": report_stats_data,
        "version_compare": version_compare,
        "suite": suite,
        "project": project,
    }


@app.post("/api/projects/{project_id}/hitl-stories")
def add_hitl_story(project_id: str, body: HitlStoryCreate) -> dict[str, Any]:
    if not body.title.strip():
        raise HTTPException(400, "title required")
    try:
        story = project_store.add_hitl_story(project_id, body.title, body.description)
    except KeyError:
        raise HTTPException(404, "Project not found") from None
    project = project_store.get_project(project_id)
    return {"story": story, "project": project}


@app.post("/api/projects/{project_id}/invite-hitl")
def invite_hitl(project_id: str, body: InviteHitlRequest) -> dict[str, Any]:
    try:
        invite = project_store.invite_hitl(
            project_id,
            body.note,
            body.consultant_name or body.team_name,
            body.email,
            body.bug_bounty,
            body.consultant_tag,
        )
    except KeyError:
        raise HTTPException(404, "Project not found") from None
    team = (body.consultant_name or body.team_name).strip() or "consultant"
    tag = body.consultant_tag.strip()
    tag_bit = f" [{tag}]" if tag else ""
    bounty = " (bug bounty welcome)" if body.bug_bounty else ""
    msg = project_store.add_chat_message(
        project_id,
        "assistant",
        f"Invitation sent to {team}{tag_bit}{bounty}. "
        "External QA Hunter teams can join this challenge to cover manual user stories and enrich BRAHL reports.",
    )
    project = project_store.get_project(project_id)
    return {"invite": invite, "project": project, "message": msg}


@app.post("/api/projects/{project_id}/request-change")
def request_change(project_id: str, body: ChangeAssistanceRequest) -> dict[str, Any]:
    try:
        entry = project_store.request_change_assistance(project_id, body.note)
    except KeyError:
        raise HTTPException(404, "Project not found") from None
    note = body.note.strip() or "Project has changed — need assistance again."
    user_text = f"[Change request] {note}"
    project_store.add_chat_message(project_id, "user", user_text)
    project = project_store.get_project(project_id)
    assert project
    reply_text = project_store.assistant_reply(project, user_text)
    project_store.add_chat_message(project_id, "assistant", reply_text)
    project = project_store.get_project(project_id)
    return {"change_request": entry, "project": project}


@app.post("/api/projects/{project_id}/version-baseline")
def snapshot_version_baseline(project_id: str, body: VersionBaselineRequest) -> dict[str, Any]:
    try:
        project = project_store.snapshot_version_baseline(
            project_id, body.version_label, body.run_name
        )
    except KeyError:
        raise HTTPException(404, "Project not found") from None
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from None
    return {"project": project}


@app.post("/api/projects")
def create_project(body: ProjectCreate, request: Request) -> dict[str, Any]:
    data = body.model_dump()
    user = _auth_user(request)
    if user:
        data["owner_user_id"] = user.get("id")
    project = project_store.create_project(data)
    welcome = project_store.add_chat_message(
        project["id"],
        "assistant",
        "Hi — I'm your BRAHL Build assistant. What are you trying to test or improve?",
    )
    project = project_store.get_project(project["id"])
    return {"project": project, "message": welcome}


@app.patch("/api/projects/{project_id}")
def patch_project(project_id: str, body: ProjectUpdate, request: Request) -> dict[str, Any]:
    _require_project(project_id, request)
    patch = {k: v for k, v in body.model_dump().items() if v is not None}
    try:
        project = project_store.update_project(project_id, patch)
    except KeyError:
        raise HTTPException(404, "Project not found") from None
    return {"project": project}


@app.post("/api/projects/{project_id}/chat")
def post_chat(project_id: str, body: ChatMessage, request: Request) -> dict[str, Any]:
    project = _require_project(project_id, request)
    if not project.get("ai_enabled", True):
        raise HTTPException(400, "AI is off — use manual purpose field on Build")
    user_msg = project_store.add_chat_message(project_id, "user", body.text)
    project = project_store.get_project(project_id)
    assert project
    reply_text = project_store.assistant_reply(project, body.text)
    assistant_msg = project_store.add_chat_message(project_id, "assistant", reply_text)
    project = project_store.get_project(project_id)
    return {"user_message": user_msg, "assistant_message": assistant_msg, "project": project}


@app.post("/api/projects/{project_id}/context")
def add_context(project_id: str, body: ContextItem) -> dict[str, Any]:
    try:
        item = project_store.add_context_item(project_id, body.kind, body.label, body.value)
    except KeyError:
        raise HTTPException(404, "Project not found") from None
    project = project_store.get_project(project_id)
    return {"item": item, "project": project}


@app.post("/api/projects/{project_id}/documents")
async def upload_document(project_id: str, file: UploadFile = File(...)) -> dict[str, Any]:
    if not project_store.get_project(project_id):
        raise HTTPException(404, "Project not found")
    content = await file.read()
    if not content:
        raise HTTPException(400, "Empty file")
    try:
        doc = project_store.add_document(project_id, file.filename or "upload.bin", content)
    except KeyError:
        raise HTTPException(404, "Project not found") from None
    return {"document": doc}


@app.post("/api/projects/{project_id}/join-hitl")
def join_hitl(project_id: str) -> dict[str, Any]:
    try:
        project = project_store.join_hitl(project_id)
    except KeyError:
        raise HTTPException(404, "Project not found") from None
    msg = project_store.add_chat_message(
        project_id,
        "assistant",
        "A QA Hunter joined this challenge. "
        "They can upload yPADs offline and enrich BRAHL reports.",
    )
    project = project_store.get_project(project_id)
    return {"project": project, "message": msg}


@app.post("/api/projects/{project_id}/submit-hitl-report")
def submit_hitl_report(project_id: str, body: HitlReportSubmit) -> dict[str, Any]:
    try:
        entry = project_store.submit_hitl_report(
            project_id,
            body.run_name,
            body.report_path,
            critical_issues=body.critical_issues,
            time_hours=body.time_hours,
            features_found=body.features_found,
            hunt_report_path=body.hunt_report_path,
            artifact_paths=body.artifact_paths,
        )
    except KeyError:
        raise HTTPException(404, "Project not found") from None
    project = project_store.get_project(project_id)
    payout = project_store.compute_payout_preview(project) if project else []
    return {"report": entry, "project": project, "payout_preview": payout}


@app.get("/api/projects/{project_id}/brahl/reports")
def list_brahl_reports(project_id: str) -> dict[str, Any]:
    try:
        reports = project_store.list_brahl_reports(project_id)
    except KeyError:
        raise HTTPException(404, "Project not found") from None
    project = project_store.get_project(project_id)
    latest = reports[0]["run_name"] if reports else None
    return {"reports": reports, "latest_run_name": latest, "project_name": project.get("name") if project else ""}


@app.get("/api/projects/{project_id}/brahl/reports/{run_name}/content")
def brahl_report_content(project_id: str, run_name: str, report_id: str | None = None) -> dict[str, Any]:
    project = project_store.get_project(project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    reports = list(project.get("reports") or [])
    report_entry = None
    if report_id:
        report_entry = next((r for r in reports if r.get("id") == report_id), None)
    if not report_entry:
        matches = [r for r in reports if r.get("run_name") == run_name]
        report_entry = matches[-1] if matches else None
    if report_entry and (report_entry.get("report_path") or "").strip():
        try:
            markdown = project_store.load_project_report_markdown(project_id, report_entry)
            artifacts = list(report_entry.get("artifacts") or [])
            return {
                "run_name": run_name,
                "markdown": markdown,
                "stats": {},
                "version_compare": None,
                "source": report_entry.get("source"),
                "artifacts": artifacts,
                "report_id": report_entry.get("id"),
            }
        except FileNotFoundError:
            pass
    suite_name = _suite_from_run_name(run_name)
    ctx = suite_report_context(suite_name, project) if suite_name else project
    try:
        ensure_brahl_report(run_name, project=ctx)
        markdown = project_store.load_report_markdown(run_name, ctx)
        stats = report_stats(run_name)
    except FileNotFoundError:
        raise HTTPException(404, f"No results for run: {run_name}") from None
    version_compare = None
    baseline_run = (project.get("baseline_run") or "").strip()
    if baseline_run and baseline_run != run_name:
        try:
            version_compare = compare_verify_runs(baseline_run, run_name)
            if version_compare:
                version_compare["baseline_version"] = project.get("baseline_version") or "baseline (old)"
                version_compare["app_version"] = project.get("app_version") or "current (new)"
        except Exception:
            version_compare = None
    return {"run_name": run_name, "markdown": markdown, "stats": stats, "version_compare": version_compare, "artifacts": []}


@app.get("/api/projects/{project_id}/uploads/{filename}")
def project_upload_file(project_id: str, filename: str):
    project = project_store.get_project(project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    path = project_store._resolve_upload_path(project_id, f"data/uploads/{project_id}/{filename}")
    if not path:
        raise HTTPException(404, "File not found")
    return FileResponse(path)


def _suite_from_run_name(run_name: str) -> str:
    parts = run_name.split("_")
    return "_".join(parts[2:]) if len(parts) >= 3 else ""


@app.post("/api/projects/{project_id}/brahl/reports/{run_name}/ensure")
def brahl_report_ensure(project_id: str, run_name: str) -> dict[str, Any]:
    project = project_store.get_project(project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    try:
        ensure_brahl_report(run_name, project=project)
        markdown = project_store.load_report_markdown(run_name, project)
        stats = report_stats(run_name)
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from None
    return {"run_name": run_name, "markdown": markdown, "stats": stats}


@app.post("/api/projects/{project_id}/brahl/reports")
def register_brahl_report(project_id: str, body: BrahlReportRegister) -> dict[str, Any]:
    try:
        entry = project_store.register_brahl_report(project_id, body.run_name, body.source)
    except KeyError:
        raise HTTPException(404, "Project not found") from None
    reports = project_store.list_brahl_reports(project_id)
    return {"report": entry, "reports": reports}


@app.post("/api/projects/{project_id}/brahl/chat")
def brahl_chat(project_id: str, body: BrahlChatMessage) -> dict[str, Any]:
    project = project_store.get_project(project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    user_msg = project_store.add_brahl_chat_message(project_id, "user", body.text)
    run_name = body.run_name or project.get("latest_run")
    report_md = None
    project = project_store.get_project(project_id)
    assert project
    if run_name:
        try:
            ensure_brahl_report(run_name, project=project)
            report_md = project_store.load_report_markdown(run_name, project)
        except FileNotFoundError:
            report_md = None
    reply_text = project_store.brahl_model_reply(project, report_md, body.text, run_name)
    assistant_msg = project_store.add_brahl_chat_message(project_id, "assistant", reply_text)
    project = project_store.get_project(project_id)
    return {"user_message": user_msg, "assistant_message": assistant_msg, "project": project, "run_name": run_name}


@app.post("/api/projects/{project_id}/atomic77/chat")
def atomic77_project_chat(project_id: str, body: Atomic77ChatMessage) -> dict[str, Any]:
    project = project_store.get_project(project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    ai_on = project.get("ai_enabled", True)
    if not ai_on and not body.faq_key:
        raise HTTPException(400, "AI is off — use FAQ chips or turn AI on")
    user_msg = project_store.add_atomic77_chat_message(project_id, "user", body.text)
    project = project_store.get_project(project_id)
    assert project
    history = [
        {"role": m.get("role"), "text": m.get("text", "")}
        for m in (project.get("atomic77_chat_messages") or [])[-10:]
        if m.get("role") in ("user", "assistant")
    ][:-1]
    avatar = body.avatar or project.get("owner_avatar") or "client"
    import ai_assist

    reply_text, tokens_est = ai_assist.atomic77_assistant_reply(
        project,
        body.text,
        avatar=avatar,
        faq_key=body.faq_key,
        history=history if ai_on else None,
    )
    project_store.record_atomic77_tokens(project_id, tokens_est)
    assistant_msg = project_store.add_atomic77_chat_message(project_id, "assistant", reply_text)
    project = project_store.get_project(project_id)
    return {
        "user_message": user_msg,
        "assistant_message": assistant_msg,
        "project": project,
        "tokens_est": tokens_est,
    }


@app.post("/api/atomic77/chat")
def atomic77_platform_chat(body: Atomic77PlatformChat) -> dict[str, Any]:
    """Platform Atomic 77 — works without a selected project (e.g. Networker)."""
    project = None
    if body.project_id:
        project = project_store.get_project(body.project_id)
    import ai_assist

    history: list[dict[str, str]] = []
    if project:
        history = [
            {"role": m.get("role"), "text": m.get("text", "")}
            for m in (project.get("atomic77_chat_messages") or [])[-10:]
            if m.get("role") in ("user", "assistant")
        ]
    reply_text, tokens_est = ai_assist.atomic77_assistant_reply(
        project,
        body.text,
        avatar=body.avatar,
        faq_key=body.faq_key,
        history=history if ai_assist.is_ai_available() else None,
    )
    if project and body.project_id:
        project_store.add_atomic77_chat_message(body.project_id, "user", body.text)
        project_store.record_atomic77_tokens(body.project_id, tokens_est)
        project_store.add_atomic77_chat_message(body.project_id, "assistant", reply_text)
        project = project_store.get_project(body.project_id)
    return {
        "assistant_message": {"role": "assistant", "text": reply_text},
        "tokens_est": tokens_est,
        "project": project,
    }


@app.get("/api/files/z/{run_name}/{filename:path}")
def z_artifact(run_name: str, filename: str):
    path = KK_ROOT / "z" / run_name / filename
    if not path.is_file():
        raise HTTPException(404, "File not found")
    return FileResponse(path)


if WEB_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=str(WEB_DIR)), name="assets")


@app.get("/api/about/ecosystem")
def about_ecosystem() -> dict[str, Any]:
    inv = invite_store.list_admin_summary()
    return {
        "ecosystem": project_store.ecosystem_stats(),
        "waitlist_count": waitlist_store.count_entries(),
        "gtm": {
            "batch_count": inv.get("batch_count", 0),
            "code_count": inv.get("code_count", 0),
            "redeemed_count": inv.get("redeemed_count", 0),
            "active_trials": inv.get("active_trials", 0),
        },
    }


@app.post("/api/waitlist")
def waitlist_join(body: WaitlistRequest, request: Request) -> dict[str, Any]:
    ip = request.client.host if request.client else None
    try:
        result = waitlist_store.add_entry(
            body.email,
            role=body.role,
            note=body.note,
            source=body.source,
            ip=ip,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    entry = result["entry"]
    return {
        "ok": True,
        "duplicate": result["duplicate"],
        "count": result["count"],
        "message": "Already on the list — try the demo below."
        if result["duplicate"]
        else "You're on the list — try the demo now.",
        "entry": {"id": entry["id"], "email": entry["email"], "role": entry["role"]},
    }


@app.get("/api/waitlist/count")
def waitlist_count() -> dict[str, int]:
    return {"count": waitlist_store.count_entries()}


@app.get("/api/admin/waitlist")
def admin_waitlist(request: Request) -> dict[str, Any]:
    _require_admin(request)
    return {"entries": waitlist_store.list_entries(), "count": waitlist_store.count_entries()}


@app.get("/api/admin/waitlist/export")
def admin_waitlist_export(request: Request):
    from fastapi.responses import Response

    _require_admin(request)
    csv_text = waitlist_store.export_csv()
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=brahl_waitlist.csv"},
    )


@app.get("/api/invites/validate")
def invites_validate(code: str) -> dict[str, Any]:
    return invite_store.validate_code(code)


@app.post("/api/invites/redeem")
def invites_redeem(body: InviteRedeemRequest) -> dict[str, Any]:
    try:
        return invite_store.redeem_code(body.code, body.email, body.note)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.get("/api/admin/invites")
def admin_invites(request: Request) -> dict[str, Any]:
    _require_admin(request)
    return invite_store.list_admin_summary()


@app.post("/api/admin/invites/batch")
def admin_invites_batch(request: Request, body: InviteBatchRequest) -> dict[str, Any]:
    _require_admin(request)
    try:
        return invite_store.generate_batch(body.batch_type, body.label, body.count, body.trial_days)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.get("/api/admin/invites/export")
def admin_invites_export(request: Request, batch_id: str):
    from fastapi.responses import Response

    _require_admin(request)
    try:
        csv_text = invite_store.export_batch_csv(batch_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=invites_{batch_id}.csv"},
    )


@app.get("/api/nalanda/lessons")
def nalanda_list_lessons(limit: int = 50) -> dict[str, Any]:
    return {"lessons": nalanda_store.list_lessons(limit)}


@app.post("/api/nalanda/lessons")
def nalanda_add_lesson(body: NalandaLessonRequest) -> dict[str, Any]:
    try:
        lesson = nalanda_store.add_lesson(
            body.profile_id,
            body.title,
            body.blurb,
            body.url,
            body.tags,
            body.author_name,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"lesson": lesson}


@app.get("/api/nalanda/threads")
def nalanda_list_threads(limit: int = 50) -> dict[str, Any]:
    return {"threads": nalanda_store.list_threads(limit)}


@app.get("/api/nalanda/threads/{thread_id}")
def nalanda_get_thread(thread_id: str) -> dict[str, Any]:
    try:
        thread = nalanda_store.get_thread(thread_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    return {"thread": thread}


@app.post("/api/nalanda/threads")
def nalanda_add_thread(body: NalandaThreadRequest) -> dict[str, Any]:
    try:
        thread = nalanda_store.add_thread(
            body.profile_id, body.title, body.body, body.author_name
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"thread": thread}


@app.post("/api/nalanda/threads/{thread_id}/replies")
def nalanda_add_reply(thread_id: str, body: NalandaReplyRequest) -> dict[str, Any]:
    try:
        result = nalanda_store.add_reply(
            thread_id, body.profile_id, body.body, body.author_name
        )
        thread = nalanda_store.get_thread(thread_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"reply": result["reply"], "thread": thread}


@app.get("/api/nalanda/invite")
def nalanda_profile_invite(profile_id: str, author_name: str = "") -> dict[str, Any]:
    try:
        invite = nalanda_store.get_or_create_profile_invite(profile_id, author_name)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return invite


@app.get("/api/nalanda/stats")
def nalanda_stats() -> dict[str, Any]:
    return nalanda_store.community_stats()


@app.get("/admin")
def admin_page():
    about_path = WEB_DIR / "about.html"
    if not about_path.is_file():
        raise HTTPException(404, "Admin page not found")
    return FileResponse(about_path, headers={"X-Admin-Section": "about-admin-title"})


@app.get("/about")
def about_page():
    about_path = WEB_DIR / "about.html"
    if not about_path.is_file():
        raise HTTPException(404, "About page not found")
    return FileResponse(about_path)


@app.get("/welcome")
def welcome_page():
    welcome_path = WEB_DIR / "welcome.html"
    if not welcome_path.is_file():
        raise HTTPException(404, "Welcome page not found")
    return FileResponse(welcome_path)


@app.get("/signin")
def signin_page():
    signin_path = WEB_DIR / "signin.html"
    if not signin_path.is_file():
        raise HTTPException(404, "Sign-in page not found")
    return FileResponse(signin_path)


@app.get("/login")
def login_page():
    login_path = WEB_DIR / "login.html"
    if not login_path.is_file():
        raise HTTPException(404, "Login page not found")
    return FileResponse(login_path)


@app.get("/signup")
def signup_page():
    signup_path = WEB_DIR / "signup.html"
    if not signup_path.is_file():
        raise HTTPException(404, "Signup page not found")
    return FileResponse(signup_path)


@app.get("/forgot-password")
def forgot_password_page():
    path = WEB_DIR / "forgot-password.html"
    if not path.is_file():
        raise HTTPException(404, "Forgot-password page not found")
    return FileResponse(path)


@app.get("/app")
def app_page():
    index_path = WEB_DIR / "index.html"
    if not index_path.is_file():
        raise HTTPException(404, "Frontend not built")
    return FileResponse(index_path)


@app.get("/")
def index():
    welcome_path = WEB_DIR / "welcome.html"
    if welcome_path.is_file():
        return FileResponse(welcome_path)
    index_path = WEB_DIR / "index.html"
    if not index_path.is_file():
        raise HTTPException(404, "Frontend not built")
    return FileResponse(index_path)
