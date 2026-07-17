"""Focused tests for the evidence library, batch report registration, and schedules."""

from __future__ import annotations

from pathlib import Path

import projects as project_store
import schedules as schedules_store


def _isolate_projects(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(project_store, "DATA_DIR", tmp_path)
    monkeypatch.setattr(project_store, "PROJECTS_FILE", tmp_path / "projects.json")
    monkeypatch.setattr(project_store, "UPLOADS_DIR", tmp_path / "uploads")


def _isolate_schedules(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(schedules_store, "DATA_DIR", tmp_path)
    monkeypatch.setattr(schedules_store, "SCHEDULES_FILE", tmp_path / "schedules.json")


def _new_project(name: str = "EvidenceTestProject") -> dict:
    return project_store.create_project({"name": name})


def test_add_and_list_evidence(tmp_path: Path, monkeypatch) -> None:
    _isolate_projects(tmp_path, monkeypatch)
    project = _new_project()
    pid = project["id"]

    item = project_store.add_evidence_item(
        pid,
        "screenshot",
        author="qa1",
        path="uploads/shot.png",
        title="Landing page glitch",
    )
    assert item["kind"] == "screenshot"
    assert item["author"] == "qa1"
    assert item["created_at"]

    items = project_store.list_evidence(pid)
    assert any(i["id"] == item["id"] for i in items)

    found = project_store.list_evidence(pid, query="glitch")
    assert any(i["id"] == item["id"] for i in found)

    filtered_out = project_store.list_evidence(pid, query="nonexistent-term-xyz")
    assert all(i["id"] != item["id"] for i in filtered_out)

    by_kind = project_store.list_evidence(pid, kind="screenshot")
    assert all(i["kind"] == "screenshot" for i in by_kind)


def test_add_evidence_normalizes_unknown_kind(tmp_path: Path, monkeypatch) -> None:
    _isolate_projects(tmp_path, monkeypatch)
    project = _new_project()
    item = project_store.add_evidence_item(project["id"], "not-a-real-kind", title="x")
    assert item["kind"] == "note"


def test_link_evidence_to_report(tmp_path: Path, monkeypatch) -> None:
    _isolate_projects(tmp_path, monkeypatch)
    project = _new_project()
    pid = project["id"]

    item = project_store.add_evidence_item(pid, "note", note="Repro steps for bug")
    report = project_store.register_brahl_report(pid, "20260101_000000_TestSuite", source="automation")

    linked = project_store.link_evidence(pid, [item["id"]], report_id=report["id"])
    assert linked and linked[0]["report_id"] == report["id"]

    by_report = project_store.list_evidence(pid, report_id=report["id"])
    assert any(i["id"] == item["id"] for i in by_report)


def test_submit_hitl_report_links_evidence_ids(tmp_path: Path, monkeypatch) -> None:
    _isolate_projects(tmp_path, monkeypatch)
    project = _new_project()
    pid = project["id"]

    item = project_store.add_evidence_item(pid, "audio_note", title="Voice memo")
    entry = project_store.submit_hitl_report(
        pid,
        "20260101_000000_TestSuite",
        evidence_ids=[item["id"]],
    )

    updated_items = project_store.list_evidence(pid, report_id=entry["id"])
    assert any(i["id"] == item["id"] for i in updated_items)


def test_register_brahl_report_batch_shares_batch_id(tmp_path: Path, monkeypatch) -> None:
    _isolate_projects(tmp_path, monkeypatch)
    project = _new_project()
    pid = project["id"]

    run_names = [
        "20260101_000001_TestSuite",
        "20260101_000002_TestSuite",
        "20260101_000003_TestSuite",
    ]
    result = project_store.register_brahl_report_batch(
        pid, run_names, source="automation", batch_dashboard="z/zDash_batch_1/index.html"
    )
    entries = result["entries"]
    assert len(entries) == len(run_names)
    batch_id = result["batch_id"]
    assert batch_id
    assert all(e["batch_id"] == batch_id for e in entries)
    assert all(e["batch_dashboard"] == "z/zDash_batch_1/index.html" for e in entries)
    # Each run gets its own report row — not just the first.
    assert {e["run_name"] for e in entries} == set(run_names)

    reports = project_store.list_brahl_reports(pid)
    assert len(reports) == len(run_names)


def test_register_brahl_report_batch_empty_run_names(tmp_path: Path, monkeypatch) -> None:
    _isolate_projects(tmp_path, monkeypatch)
    project = _new_project()
    result = project_store.register_brahl_report_batch(project["id"], [], source="automation")
    assert result == {"entries": [], "batch_id": None}


def test_report_archive_toggle(tmp_path: Path, monkeypatch) -> None:
    _isolate_projects(tmp_path, monkeypatch)
    project = _new_project()
    pid = project["id"]
    report = project_store.register_brahl_report(pid, "20260101_000000_TestSuite")
    assert report["archived"] is False

    archived = project_store.set_report_archived(pid, report["id"], True)
    assert archived["archived"] is True

    reports = project_store.list_brahl_reports(pid)
    match = next(r for r in reports if r["id"] == report["id"])
    assert match["archived"] is True


# --- Schedules ---------------------------------------------------------------


def test_create_and_list_schedule_disabled_by_default(tmp_path: Path, monkeypatch) -> None:
    _isolate_schedules(tmp_path, monkeypatch)
    entry = schedules_store.create_schedule(
        "proj-1", "Math", "f/fStart/Math.json", profiles=["Smoke"], interval="daily"
    )
    assert entry["enabled"] is False
    assert entry["runtime"] == "local"
    assert entry["next_run"]

    listed = schedules_store.list_project_schedules("proj-1")
    assert len(listed) == 1
    assert listed[0]["id"] == entry["id"]


def test_create_schedule_rejects_bad_interval(tmp_path: Path, monkeypatch) -> None:
    _isolate_schedules(tmp_path, monkeypatch)
    try:
        schedules_store.create_schedule("proj-1", "Math", "f/fStart/Math.json", interval="weekly")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_toggle_schedule(tmp_path: Path, monkeypatch) -> None:
    _isolate_schedules(tmp_path, monkeypatch)
    entry = schedules_store.create_schedule("proj-1", "Math", "f/fStart/Math.json")
    toggled = schedules_store.toggle_schedule(entry["id"], True)
    assert toggled["enabled"] is True
    toggled_off = schedules_store.toggle_schedule(entry["id"], False)
    assert toggled_off["enabled"] is False


def test_update_schedule_recomputes_next_run(tmp_path: Path, monkeypatch) -> None:
    _isolate_schedules(tmp_path, monkeypatch)
    entry = schedules_store.create_schedule("proj-1", "Math", "f/fStart/Math.json", interval="daily")
    updated = schedules_store.update_schedule(entry["id"], {"interval": "hourly"})
    assert updated["interval"] == "hourly"
    assert updated["next_run"]


def test_delete_schedule(tmp_path: Path, monkeypatch) -> None:
    _isolate_schedules(tmp_path, monkeypatch)
    entry = schedules_store.create_schedule("proj-1", "Math", "f/fStart/Math.json")
    schedules_store.delete_schedule(entry["id"])
    assert schedules_store.list_project_schedules("proj-1") == []


def test_due_schedules_only_enabled_and_past_next_run(tmp_path: Path, monkeypatch) -> None:
    _isolate_schedules(tmp_path, monkeypatch)
    from datetime import datetime, timedelta, timezone

    entry = schedules_store.create_schedule("proj-1", "Math", "f/fStart/Math.json", enabled=True)
    # Not due yet — next_run defaults to the future.
    assert schedules_store.due_schedules() == []

    past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(timespec="seconds")
    all_sched = schedules_store.load_schedules()
    for s in all_sched:
        if s["id"] == entry["id"]:
            s["next_run"] = past
    schedules_store.save_schedules(all_sched)

    due = schedules_store.due_schedules()
    assert len(due) == 1
    assert due[0]["id"] == entry["id"]

    disabled = schedules_store.toggle_schedule(entry["id"], False)
    assert disabled["enabled"] is False
    assert schedules_store.due_schedules() == []


def test_mark_schedule_ran_advances_next_run(tmp_path: Path, monkeypatch) -> None:
    from datetime import datetime, timezone

    _isolate_schedules(tmp_path, monkeypatch)
    entry = schedules_store.create_schedule("proj-1", "Math", "f/fStart/Math.json", interval="hourly")
    updated = schedules_store.mark_schedule_ran(entry["id"], "job-123", "20260101_000000_Math")
    assert updated is not None
    assert updated["last_job_id"] == "job-123"
    assert updated["last_run_name"] == "20260101_000000_Math"
    assert updated["last_run_at"]
    next_run = datetime.fromisoformat(updated["next_run"])
    now = datetime.now(timezone.utc)
    assert next_run > now
    assert (next_run - now).total_seconds() <= 3605


def test_estimate_cloud_cost_scales_with_threads_and_interval() -> None:
    hourly = schedules_store.estimate_cloud_cost(["Smoke"], 1, "hourly")
    daily = schedules_store.estimate_cloud_cost(["Smoke"], 1, "daily")
    assert hourly["runs_per_month_est"] > daily["runs_per_month_est"]
    assert hourly["monthly_usd_est"] > daily["monthly_usd_est"]

    single_thread = schedules_store.estimate_cloud_cost(["Smoke"], 1, "daily")
    multi_thread = schedules_store.estimate_cloud_cost(["Smoke", "API"], 4, "daily")
    assert multi_thread["per_run_usd"] > single_thread["per_run_usd"]
