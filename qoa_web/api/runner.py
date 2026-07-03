"""FoXYiZ engine subprocess runner for qoa_web API."""

from __future__ import annotations

import csv
import re
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

KK_ROOT = Path(__file__).resolve().parents[2]
F_DIR = KK_ROOT / "f"
Z_DIR = KK_ROOT / "z"
ENGINE = F_DIR / "fEngine2.py"

OUTPUT_DIR_RE = re.compile(r"Output Directory:\s*(.+)")


@dataclass
class Job:
    job_id: str
    config_path: str
    step_label: str
    status: str = "queued"
    return_code: int | None = None
    output_dir: str | None = None
    log_lines: list[str] = field(default_factory=list)
    started_at: float | None = None
    finished_at: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "config_path": self.config_path,
            "step_label": self.step_label,
            "status": self.status,
            "return_code": self.return_code,
            "output_dir": self.output_dir,
            "log_lines": self.log_lines[-200:],
            "started_at": self.started_at,
            "finished_at": self.finished_at,
        }


_jobs: dict[str, Job] = {}
_lock = threading.Lock()


def list_fstart_configs() -> list[str]:
    if not F_DIR.is_dir():
        return []
    return [f"f/{p.name}" for p in sorted(F_DIR.glob("fStart*.json"))]


def list_z_runs(suite_suffix: str | None = None) -> list[dict[str, Any]]:
    if not Z_DIR.is_dir():
        return []
    runs: list[dict[str, Any]] = []
    for path in sorted(Z_DIR.iterdir(), key=lambda p: p.name, reverse=True):
        if not path.is_dir():
            continue
        if suite_suffix and not path.name.endswith(f"_{suite_suffix}"):
            continue
        results = next(path.glob("*_zResults.csv"), None)
        if not results:
            continue
        passes = fails = 0
        with results.open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                if (row.get("Result") or "").lower() == "fail":
                    fails += 1
                else:
                    passes += 1
        dash = next(path.glob("*_zDash.html"), None)
        runs.append(
            {
                "name": path.name,
                "path": str(path.relative_to(KK_ROOT)).replace("\\", "/"),
                "passes": passes,
                "fails": fails,
                "dashboard": str(dash.relative_to(KK_ROOT)).replace("\\", "/") if dash else None,
                "report": str((path / "brahl_report.md").relative_to(KK_ROOT)).replace("\\", "/")
                if (path / "brahl_report.md").is_file()
                else None,
            }
        )
    return runs


def load_failures(run_dir: Path) -> list[dict[str, str]]:
    results = next(run_dir.glob("*_zResults.csv"), None)
    if not results:
        return []
    out: list[dict[str, str]] = []
    with results.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            if (row.get("Result") or "").lower() != "fail":
                continue
            out.append(
                {
                    "planId": row.get("PlanId", ""),
                    "stepId": row.get("StepId", ""),
                    "output": (row.get("Output") or "")[:300],
                }
            )
    return out


def get_job(job_id: str) -> Job | None:
    return _jobs.get(job_id)


def start_run(config_path: str, step_label: str = "Run") -> Job:
    job_id = uuid.uuid4().hex[:10]
    job = Job(job_id=job_id, config_path=config_path, step_label=step_label)
    with _lock:
        _jobs[job_id] = job

    def worker() -> None:
        job.status = "running"
        job.started_at = time.time()
        cfg = KK_ROOT / config_path.replace("/", "\\") if "\\" not in config_path else KK_ROOT / config_path
        if not cfg.is_file():
            job.status = "failed"
            job.log_lines.append(f"Config not found: {config_path}")
            job.finished_at = time.time()
            return
        try:
            proc = subprocess.Popen(
                [sys.executable, str(ENGINE), "--config", str(cfg.relative_to(KK_ROOT))],
                cwd=str(KK_ROOT),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            )
            assert proc.stdout is not None
            for line in proc.stdout:
                job.log_lines.append(line.rstrip("\n"))
                m = OUTPUT_DIR_RE.search(line)
                if m:
                    job.output_dir = m.group(1).strip()
            proc.wait()
            job.return_code = proc.returncode
            job.status = "completed" if proc.returncode == 0 else "failed"
        except Exception as exc:
            job.log_lines.append(f"[ERROR] {exc}")
            job.status = "failed"
        finally:
            job.finished_at = time.time()

    threading.Thread(target=worker, daemon=True).start()
    return job


def generate_brahl_report_md(run_name: str, config_path: str, step_label: str) -> str:
    run_dir = Z_DIR / run_name
    results = next(run_dir.glob("*_zResults.csv"), None) if run_dir.is_dir() else None
    passes = fails = 0
    if results and results.is_file():
        with results.open(encoding="utf-8-sig", newline="") as f:
            seen: set[tuple[str, str]] = set()
            for row in csv.DictReader(f):
                key = (row.get("PlanId", ""), row.get("StepId", ""))
                if key in seen:
                    continue
                seen.add(key)
                if (row.get("Result") or "").strip().lower() == "fail":
                    fails += 1
                else:
                    passes += 1
    total = passes + fails
    dash = next(run_dir.glob("*_zDash.html"), None) if run_dir.is_dir() else None
    dash_rel = dash.relative_to(KK_ROOT).as_posix() if dash else ""
    return f"""# BRAHL Report — qoa_web — {run_name}

**App:** http://127.0.0.1:8765/
**Step:** {step_label}
**Config:** {config_path}
**Verify:** z/{run_name}/ — **{passes}/{total} pass**

---

## Summary

Automated report generated by qoa_web v1.0.

| Metric | Value |
|--------|-------|
| Passed | {passes} |
| Failed | {fails} |
| Dashboard | {dash_rel or "n/a"} |

---

## Verdict

- [{"x" if fails == 0 else " "}] Verify run {"green" if fails == 0 else "has failures"}
- [x] Report linked to project

"""


def write_run_report(run_name: str, config_path: str, step_label: str) -> dict[str, Any]:
    md = generate_brahl_report_md(run_name, config_path, step_label)
    run_dir = Z_DIR / run_name
    if not run_dir.is_dir():
        raise FileNotFoundError(f"Run not found: {run_name}")
    report_path = run_dir / "brahl_report.md"
    report_path.write_text(md, encoding="utf-8")
    return {"run_name": run_name, "report_path": str(report_path.relative_to(KK_ROOT)).replace("\\", "/"), "markdown": md}


def capture_brahl_context(prompt: str, config_path: str, documents: list[dict] | None = None) -> dict[str, Any]:
    sys.path.insert(0, str(F_DIR))
    import fEngine2  # noqa: WPS433

    extra = {"documents": documents} if documents else None
    ctx_path, baseline = fEngine2.write_brahl_context(prompt, config_path, extra=extra)
    return {"context_path": ctx_path, "baseline": baseline}


def list_suites() -> list[dict[str, str]]:
    y_dir = KK_ROOT / "y"
    out: list[dict[str, str]] = []
    for path in sorted(y_dir.glob("*/*.json")):
        try:
            import json

            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, dict) and "input_files" in data:
            out.append(
                {
                    "path": path.relative_to(KK_ROOT).as_posix(),
                    "name": data.get("name") or path.stem,
                    "url": data.get("url", ""),
                }
            )
    return out
