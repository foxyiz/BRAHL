"""qoa_web — local BRAHL web API + static frontend."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import projects as project_store
from runner import (
    KK_ROOT,
    capture_brahl_context,
    get_job,
    list_fstart_configs,
    list_suites,
    list_z_runs,
    load_failures,
    start_run,
    write_run_report,
)
import ypad as ypad_store

WEB_DIR = Path(__file__).resolve().parent.parent / "web"
APP_VERSION = "1.0.0"

app = FastAPI(title="qoa_web", description="BRAHL web — FoXYiZ local API", version=APP_VERSION)


class RunRequest(BaseModel):
    config_path: str = Field(default="f/fStart_qoa_web_smoke.json")
    step_label: str = Field(default="Run")


class ContextRequest(BaseModel):
    prompt: str
    config_path: str = Field(default="f/fStart_qoa_web_smoke.json")
    documents: list[dict[str, str]] | None = None
    project_id: str | None = None


class ProjectCreate(BaseModel):
    name: str = ""
    app_url: str = ""
    purpose: str = ""


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


class ChatMessage(BaseModel):
    text: str


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


class BrahlReportRegister(BaseModel):
    run_name: str
    source: str = "automation"


class BrahlChatMessage(BaseModel):
    text: str
    run_name: str | None = None


class YpadSuiteRequest(BaseModel):
    suite_config: str = Field(default="y/qoa_web/qoa_web.json")


class ShrinkRequest(BaseModel):
    run_name: str
    suite_config: str = Field(default="y/qoa_web/qoa_web.json")


class ReportGenerateRequest(BaseModel):
    run_name: str
    config_path: str = Field(default="f/fStart_qoa_web_verify.json")
    step_label: str = Field(default="Verify")


class CycleEventRequest(BaseModel):
    step: str
    detail: str = ""
    run_name: str | None = None


@app.get("/api/version")
def version() -> dict[str, str]:
    return {"version": APP_VERSION, "service": "qoa_web", "brahl_phases": "Build,Run,Analyze,Heal,Loop,BRAHL"}


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "qoa_web", "version": APP_VERSION, "root": str(KK_ROOT)}


@app.get("/api/configs")
def configs() -> dict[str, list[str]]:
    return {"configs": list_fstart_configs()}


@app.get("/api/suites")
def suites() -> dict[str, list[dict[str, str]]]:
    return {"suites": list_suites()}


@app.get("/api/runs")
def runs(suite: str | None = None) -> dict[str, Any]:
    return {"runs": list_z_runs(suite)}


@app.get("/api/runs/{run_name}/failures")
def run_failures(run_name: str) -> dict[str, Any]:
    run_dir = KK_ROOT / "z" / run_name
    if not run_dir.is_dir():
        raise HTTPException(404, f"Run not found: {run_name}")
    return {"run": run_name, "failures": load_failures(run_dir)}


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
    try:
        result = write_run_report(run_name, body.config_path, body.step_label)
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
def list_projects(role: str = "client") -> dict[str, Any]:
    if role == "consultant":
        items = project_store.list_consultant_projects()
    else:
        items = project_store.list_client_projects()
    return {"projects": items, "role": role}


@app.get("/api/projects/{project_id}")
def get_project(project_id: str) -> dict[str, Any]:
    project = project_store.get_project(project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    payout = project_store.compute_payout_preview(project)
    return {"project": project, "payout_preview": payout}


@app.post("/api/projects")
def create_project(body: ProjectCreate) -> dict[str, Any]:
    project = project_store.create_project(body.model_dump())
    welcome = project_store.add_chat_message(
        project["id"],
        "assistant",
        "Hi — I'm your BRAHL Build assistant. What are you trying to test or improve?",
    )
    project = project_store.get_project(project["id"])
    return {"project": project, "message": welcome}


@app.patch("/api/projects/{project_id}")
def patch_project(project_id: str, body: ProjectUpdate) -> dict[str, Any]:
    patch = {k: v for k, v in body.model_dump().items() if v is not None}
    try:
        project = project_store.update_project(project_id, patch)
    except KeyError:
        raise HTTPException(404, "Project not found") from None
    return {"project": project}


@app.post("/api/projects/{project_id}/chat")
def post_chat(project_id: str, body: ChatMessage) -> dict[str, Any]:
    project = project_store.get_project(project_id)
    if not project:
        raise HTTPException(404, "Project not found")
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
        "A Human in the Loop consultant joined this project. "
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
def brahl_report_content(project_id: str, run_name: str) -> dict[str, Any]:
    if not project_store.get_project(project_id):
        raise HTTPException(404, "Project not found")
    try:
        markdown = project_store.load_report_markdown(run_name)
    except FileNotFoundError:
        raise HTTPException(404, f"Report not found for run: {run_name}") from None
    return {"run_name": run_name, "markdown": markdown}


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
    if run_name:
        try:
            report_md = project_store.load_report_markdown(run_name)
        except FileNotFoundError:
            report_md = None
    project = project_store.get_project(project_id)
    assert project
    reply_text = project_store.brahl_model_reply(project, report_md, body.text)
    assistant_msg = project_store.add_brahl_chat_message(project_id, "assistant", reply_text)
    project = project_store.get_project(project_id)
    return {"user_message": user_msg, "assistant_message": assistant_msg, "project": project, "run_name": run_name}


@app.get("/api/files/z/{run_name}/{filename:path}")
def z_artifact(run_name: str, filename: str):
    path = KK_ROOT / "z" / run_name / filename
    if not path.is_file():
        raise HTTPException(404, "File not found")
    return FileResponse(path)


if WEB_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=str(WEB_DIR)), name="assets")


@app.get("/")
def index():
    index_path = WEB_DIR / "index.html"
    if not index_path.is_file():
        raise HTTPException(404, "Frontend not built")
    return FileResponse(index_path)
