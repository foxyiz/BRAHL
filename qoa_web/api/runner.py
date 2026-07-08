"""FoXYiZ engine subprocess runner for qoa_web API."""

from __future__ import annotations

import csv
import json
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
Y_DIR = KK_ROOT / "y"
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


def list_fstart_for_suite(suite_name: str) -> list[str]:
    """fStart configs that reference this y/ suite."""
    cfg_path = f"y/{suite_name}/{suite_name}.json"
    matches: list[str] = []
    for rel in list_fstart_configs():
        try:
            data = json.loads((KK_ROOT / rel.replace("/", "\\")).read_text(encoding="utf-8"))
            configs = data.get("configs") or []
            if cfg_path in configs or any(suite_name in c for c in configs):
                matches.append(rel)
        except (OSError, json.JSONDecodeError):
            continue
    if matches:
        for pref in ("verify", "smoke"):
            for m in matches:
                if pref in m.lower():
                    return [m] + [x for x in matches if x != m]
        return matches
    named = [c for c in list_fstart_configs() if suite_name in c.lower()]
    if named:
        return named
    fallback = f"f/fStart_{suite_name}_verify.json"
    if (F_DIR / f"fStart_{suite_name}_verify.json").is_file():
        return [fallback]
    return []


def _validate_fstart_path(rel_path: str) -> Path:
    rel = rel_path.replace("\\", "/").strip()
    if not rel.startswith("f/fStart") or not rel.endswith(".json"):
        raise ValueError("Invalid fStart path")
    path = KK_ROOT / rel.replace("/", "\\")
    if not path.resolve().is_relative_to(F_DIR.resolve()):
        raise ValueError("Path must be under f/")
    return path


def read_fstart_config(rel_path: str) -> dict[str, Any]:
    path = _validate_fstart_path(rel_path)
    if not path.is_file():
        raise FileNotFoundError(rel_path)
    return json.loads(path.read_text(encoding="utf-8"))


def write_fstart_config(rel_path: str, data: dict[str, Any]) -> str:
    path = _validate_fstart_path(rel_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return rel_path.replace("\\", "/")


def default_fstart_template(suite_name: str, variant: str = "verify") -> dict[str, Any]:
    cfg_path = f"y/{suite_name}/{suite_name}.json"
    tags: list[str] = ["Smoke"] if variant == "smoke" else []
    return {
        "configs": [cfg_path],
        "thread_count": 1,
        "timeout": 10 if variant != "smoke" else 6,
        "headless": variant == "smoke_headless",
        "debug": False,
        "tags": tags,
    }


def create_fstart_config(suite_name: str, variant: str = "verify") -> str:
    """Create f/fStart_{suite}_{variant}.json for a y/ suite."""
    suffix = variant if variant != "verify" else "verify"
    filename = f"fStart_{suite_name}_{suffix}.json"
    rel = f"f/{filename}"
    path = F_DIR / filename
    if path.is_file():
        raise ValueError(f"Config already exists: {rel}")
    write_fstart_config(rel, default_fstart_template(suite_name, variant))
    return rel


def delete_fstart_config(rel_path: str) -> None:
    path = _validate_fstart_path(rel_path)
    if not path.is_file():
        raise FileNotFoundError(rel_path)
    path.unlink()


def plan_stats_from_zresults(results_path: Path) -> dict[str, Any]:
    """Aggregate zResults.csv at plan level (not action row level)."""
    plan_results: dict[str, str] = {}
    failures: list[dict[str, str]] = []
    duration = 0.0
    if not results_path.is_file():
        return {
            "passes": 0,
            "fails": 0,
            "total_plans": 0,
            "plan_results": plan_results,
            "failures": failures,
            "duration_sec": 0.0,
            "has_results": False,
        }
    with results_path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            plan_id = (row.get("PlanId") or "").strip()
            try:
                duration += float(row.get("TimeTaken") or 0)
            except (TypeError, ValueError):
                pass
            result = (row.get("Result") or "").strip().lower()
            if plan_id:
                if result == "fail":
                    plan_results[plan_id] = "fail"
                elif plan_id not in plan_results or plan_results[plan_id] != "fail":
                    plan_results[plan_id] = "pass"
            if result == "fail":
                failures.append(
                    {
                        "planId": plan_id,
                        "stepId": row.get("StepId", ""),
                        "output": (row.get("Output") or "")[:200],
                    }
                )
    passes = sum(1 for v in plan_results.values() if v == "pass")
    fails = sum(1 for v in plan_results.values() if v == "fail")
    return {
        "passes": passes,
        "fails": fails,
        "total_plans": passes + fails,
        "plan_results": plan_results,
        "failures": failures,
        "duration_sec": round(duration, 1),
        "has_results": True,
    }


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
        agg = plan_stats_from_zresults(results)
        dash = next(path.glob("*_zDash.html"), None)
        runs.append(
            {
                "name": path.name,
                "path": str(path.relative_to(KK_ROOT)).replace("\\", "/"),
                "passes": agg["passes"],
                "fails": agg["fails"],
                "total_plans": agg["total_plans"],
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
                    "stepInfo": row.get("StepInfo", ""),
                    "actionName": row.get("ActionName", ""),
                    "input": (row.get("Input") or "")[:200],
                    "output": (row.get("Output") or "")[:300],
                    "expected": (row.get("Expected") or "")[:200],
                }
            )
    return out


def load_errors_excerpt(run_dir: Path, max_lines: int = 40) -> str:
    err = run_dir / "_errors.csv"
    if not err.is_file():
        return ""
    lines = err.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    return "\n".join(lines[: max_lines + 1])


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


def analyze_run(run_name: str) -> dict[str, Any]:
    """Parse zResults for pass/fail counts, failures, and timing."""
    run_dir = Z_DIR / run_name
    out: dict[str, Any] = {
        "run_name": run_name,
        "passes": 0,
        "fails": 0,
        "total_plans": 0,
        "failures": [],
        "duration_sec": 0.0,
        "suite": _suite_from_run(run_name),
        "dashboard": None,
        "has_results": False,
    }
    if not run_dir.is_dir():
        return out
    results = next(run_dir.glob("*_zResults.csv"), None)
    dash = next(run_dir.glob("*_zDash.html"), None)
    if dash:
        out["dashboard"] = dash.relative_to(KK_ROOT).as_posix()
    if not results or not results.is_file():
        return out
    agg = plan_stats_from_zresults(results)
    out["has_results"] = agg["has_results"]
    out["passes"] = agg["passes"]
    out["fails"] = agg["fails"]
    out["total_plans"] = agg["total_plans"]
    out["failures"] = agg["failures"][:25]
    out["duration_sec"] = agg["duration_sec"]
    return out


def plan_result_map(run_name: str) -> dict[str, str]:
    """PlanId → pass|fail for the latest result row per plan."""
    run_dir = Z_DIR / run_name
    if not run_dir.is_dir():
        return {}
    results = next(run_dir.glob("*_zResults.csv"), None)
    if not results or not results.is_file():
        return {}
    return plan_stats_from_zresults(results)["plan_results"]


def compare_verify_runs(baseline_run: str, current_run: str) -> dict[str, Any]:
    """Compare two verify runs for version launch readiness (regressions, fixes, stable failures)."""
    if not baseline_run or not current_run or baseline_run == current_run:
        return {}
    base_map = plan_result_map(baseline_run)
    curr_map = plan_result_map(current_run)
    if not base_map or not curr_map:
        return {}
    base_stats = report_stats(baseline_run)
    curr_stats = report_stats(current_run)
    all_plans = sorted(set(base_map) | set(curr_map))
    regressions: list[str] = []
    fixed: list[str] = []
    still_failing: list[str] = []
    new_failures: list[str] = []
    for plan_id in all_plans:
        b = base_map.get(plan_id)
        c = curr_map.get(plan_id)
        if b == "pass" and c == "fail":
            regressions.append(plan_id)
        elif b == "fail" and c == "pass":
            fixed.append(plan_id)
        elif b == "fail" and c == "fail":
            still_failing.append(plan_id)
        elif b is None and c == "fail":
            new_failures.append(plan_id)
    launch_ok = len(regressions) == 0 and curr_stats.get("fails", 0) == 0
    return {
        "baseline_run": baseline_run,
        "current_run": current_run,
        "baseline_stats": base_stats,
        "current_stats": curr_stats,
        "regressions": regressions,
        "fixed": fixed,
        "still_failing": still_failing,
        "new_failures": new_failures,
        "regression_count": len(regressions),
        "fixed_count": len(fixed),
        "launch_regression_free": len(regressions) == 0,
        "launch_ready_vs_baseline": launch_ok,
    }


def _version_compare_report_section(
    project: dict[str, Any],
    current_run: str,
    baseline_version: str = "",
    app_version: str = "",
) -> str:
    baseline_run = (project.get("baseline_run") or "").strip()
    if not baseline_run or baseline_run == current_run:
        return ""
    cmp = compare_verify_runs(baseline_run, current_run)
    if not cmp:
        return ""
    b_label = baseline_version or project.get("baseline_version") or "baseline (old)"
    n_label = app_version or project.get("app_version") or "current (new)"
    bs = cmp["baseline_stats"]
    cs = cmp["current_stats"]
    b_health = bs.get("health", "unknown")
    c_health = cs.get("health", "unknown")

    def _plan_lines(plans: list[str], limit: int = 15) -> str:
        if not plans:
            return "*None.*"
        lines = [f"- `{p}`" for p in plans[:limit]]
        if len(plans) > limit:
            lines.append(f"- … and {len(plans) - limit} more")
        return "\n".join(lines)

    verdict = (
        "**No regressions** — safe to compare UX/launch metrics."
        if cmp["launch_regression_free"] and cs.get("fails", 0) == 0
        else "**Regressions detected** — fix before launch."
        if cmp["regression_count"]
        else "**Known failures remain** — review still-failing plans before launch."
        if cs.get("fails")
        else "**Compared** — review deltas below."
    )

    return f"""## Version compare — launch readiness

Creators: verify the **old** app first (save baseline), deploy the **new** version, then verify again. This section compares both.

| | **Old — {b_label}** | **New — {n_label}** |
|--|---------------------|---------------------|
| Verify run | `{baseline_run}` | `{current_run}` |
| Plans | {bs.get('passes', 0)}/{bs.get('total_plans', 0)} pass · **{bs.get('fails', 0)} fail** | {cs.get('passes', 0)}/{cs.get('total_plans', 0)} pass · **{cs.get('fails', 0)} fail** |
| Health | **{b_health}** | **{c_health}** |
| Engine time | ~{bs.get('duration_sec', 0)}s | ~{cs.get('duration_sec', 0)}s |

{verdict}

### Regressions (passed on old, fail on new) — **{cmp['regression_count']}**

{_plan_lines(cmp['regressions'])}

### Fixed since baseline — **{cmp['fixed_count']}**

{_plan_lines(cmp['fixed'])}

### Still failing (known on both versions) — **{len(cmp['still_failing'])}**

{_plan_lines(cmp['still_failing'])}

### New failures (only on new version scope) — **{len(cmp['new_failures'])}**

{_plan_lines(cmp['new_failures'])}

"""


def _suite_from_run(run_name: str) -> str:
    parts = run_name.split("_")
    if len(parts) >= 3:
        return "_".join(parts[2:])
    return parts[-1] if parts else "unknown"


def _load_brahl_context(context_path: str | None) -> dict[str, Any] | None:
    if not context_path:
        return None
    path = Path(context_path)
    if not path.is_file():
        rel = KK_ROOT / context_path.replace("\\", "/")
        path = rel if rel.is_file() else path
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _cycle_table_rows(cycle_history: list[dict[str, Any]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for entry in reversed(cycle_history):
        step = entry.get("step") or ""
        run = entry.get("run_name") or ""
        detail = entry.get("detail") or ""
        snap = entry.get("stats") if isinstance(entry.get("stats"), dict) else None
        stats = snap if snap else (analyze_run(run) if run else {})
        pf = stats.get("passes", "—")
        ff = stats.get("fails", "—")
        total = stats.get("total_plans", "—")
        rows.append(
            {
                "step": step,
                "run": run or "—",
                "pass": str(pf),
                "fail": str(ff),
                "total": str(total),
                "detail": detail,
            }
        )
    return rows


def _recovery_trace_section(cycle_history: list[dict[str, Any]]) -> str:
    """Summarize shrink/loop/verify recovery when failures drop to zero."""
    if not cycle_history:
        return ""
    ordered = list(reversed(cycle_history))
    lines: list[str] = []
    peak_fails = 0
    recovered = False
    for entry in ordered:
        step = entry.get("step") or ""
        snap = entry.get("stats") if isinstance(entry.get("stats"), dict) else None
        run = entry.get("run_name") or ""
        stats = snap if snap else (analyze_run(run) if run else {})
        fails = int(stats.get("fails") or 0) if stats else 0
        if fails > peak_fails:
            peak_fails = fails
        if peak_fails > 0 and fails == 0 and step.lower().startswith(("verify", "loop")):
            recovered = True
        if step in ("Shrink", "Restore") or step.startswith("Loop") or step == "Verify":
            pf = stats.get("passes", "—")
            tf = stats.get("total_plans", "—")
            lines.append(f"- **{step}** — {pf}/{tf} pass · {fails} fail · {entry.get('detail') or ''}")
    if not lines:
        return ""
    header = "## Recovery trace\n\n"
    if recovered:
        header += f"Failures recovered from **{peak_fails}** to **0** across the BRAHL loop.\n\n"
    else:
        header += "Cycle steps recorded during heal/loop (see table above).\n\n"
    return header + "\n".join(lines) + "\n\n"


def generate_brahl_report_md(
    run_name: str,
    config_path: str = "f/fStart_qoa_web_verify.json",
    step_label: str = "Verify",
    project: dict[str, Any] | None = None,
) -> str:
    """Standard BRAHL report — aligned with desktop BRAHL.md template."""
    project = project or {}
    stats = analyze_run(run_name)
    suite = _suite_from_run(run_name)
    app_url = project.get("app_url") or "http://127.0.0.1:8765/"
    purpose = (project.get("purpose") or project.get("prompt") or "").strip()
    passes = stats["passes"]
    fails = stats["fails"]
    total = stats["total_plans"]
    duration = stats["duration_sec"]
    dash = stats.get("dashboard") or f"z/{run_name}/{suite}_zDash.html"
    ctx = _load_brahl_context(project.get("brahl_context_path"))
    ctx_prompt = (ctx or {}).get("initialPrompt") or purpose
    cycle_rows = _cycle_table_rows(list(project.get("cycle_history") or []))
    recovery_block = _recovery_trace_section(list(project.get("cycle_history") or []))

    health = "green" if fails == 0 and total > 0 else ("amber" if total > 0 else "unknown")
    verdict_checks = [
        f"- [{'x' if total > 0 else ' '}] Tests executed ({total} plans)" if total else "- [ ] Tests executed",
        f"- [{'x' if fails == 0 and total > 0 else ' '}] Verify {'green' if fails == 0 and total > 0 else 'has failures'} ({passes}/{total} pass)",
        f"- [{'x' if stats['has_results'] else ' '}] Results on disk (`z/{run_name}/`)",
    ]

    exec_summary = (
        f"**{passes}/{total} plans passed**"
        + (f" · **{fails} failure(s)**" if fails else " · **all green**")
        + (f" · engine time ~{duration}s" if duration else "")
        + f". Overall app health for this verify run: **{health}**."
    )
    if fails:
        exec_summary += f" Review failures below and heal yPAD before the next cycle."

    failure_lines = ""
    if stats["failures"]:
        failure_lines = "\n".join(
            f"- **{f['planId']}** step {f['stepId']}: {f['output'][:120]}"
            for f in stats["failures"]
        )
    else:
        failure_lines = "*No failures in this run.*"

    cycle_table = ""
    if cycle_rows:
        cycle_table = "| Step | Run folder | Pass | Fail | Total | Detail |\n|------|------------|------|------|-------|--------|\n"
        cycle_table += "\n".join(
            f"| {r['step']} | `{r['run']}` | {r['pass']} | {r['fail']} | {r['total']} | {r['detail']} |"
            for r in cycle_rows
        )
    else:
        cycle_table = f"| {step_label} | `{run_name}` | {passes} | {fails} | {total} | verify run |"

    version_block = _version_compare_report_section(project, run_name)

    context_items = project.get("context_items") or []
    ctx_lines = ""
    if context_items:
        ctx_lines = "\n".join(
            f"- **{c.get('label', c.get('kind', 'context'))}** — {c.get('value', '')}"
            for c in context_items
        )
    else:
        ctx_lines = "*No connectors added in Build.*"

    suite_meta = project.get("suite_meta") or {}
    ypad_block = ""
    if suite_meta:
        ypaths = suite_meta.get("yplans_paths") or []
        ypad_block = f"""## yPAD baseline (y/ folder)

- **Suite config:** `{suite_meta.get('path', '')}`
- **Description:** {suite_meta.get('description') or '—'}
- **Version:** {suite_meta.get('version') or '—'}
- **Plans in y1Plans:** {suite_meta.get('plan_total', 0)} total · **Run=Y:** {suite_meta.get('plan_run_y', 0)} · **Run=N:** {suite_meta.get('plan_run_n', 0)}
- **yPlans:** {', '.join(f'`{p}`' for p in ypaths) or '—'}

"""

    return f"""# BRAHL Report — {suite} — {run_name}

**App:** {app_url}
**Scope:** Verify · **Config:** `{config_path}`
**Step:** {step_label}
**Verify folder:** `z/{run_name}/`

## Origin — user prompt

> {ctx_prompt or "No purpose captured — add in Build chat or project settings."}

**Reference context (Build):**

{ctx_lines}

{ypad_block}## Executive summary (for customer / product owner)

{exec_summary}

{version_block}
| Metric | Value |
|--------|-------|
| Plans run | {total} |
| Passed | {passes} |
| Failed | {fails} |
| Engine time | {duration}s |
| Health | {health} |
| Dashboard | `{dash}` |

## Cycle summary

{cycle_table}

{recovery_block}## Loop detail — {step_label}

- **Plans executed:** {total} ({passes} pass · {fails} fail)
- **Failures:**

{failure_lines}

- **Heals applied:** See Heal tab / yPAD change log for this cycle.

## Failures (detail)

{failure_lines}

## Customer action plan — next BRAHL run

1. {"Review and heal failing plans listed above." if fails else "No failures — proceed to next feature scope or publish."}
2. Re-run BRAHL: Step 0 (purpose + context) → Loop 1 → Verify with same fStart config.
3. Expected: Verify green; do not weaken assertions to force green.

## Verdict

{chr(10).join(verdict_checks)}

**Dashboard:** `{dash}`
**BRAHL report:** `z/{run_name}/brahl_report.md`
"""


def write_brahl_report_files(
    run_name: str,
    markdown: str,
    suite_name: str | None = None,
) -> dict[str, str]:
    """Write in-run and flat-index report files."""
    run_dir = Z_DIR / run_name
    if not run_dir.is_dir():
        raise FileNotFoundError(f"Run not found: {run_name}")
    suite = suite_name or _suite_from_run(run_name)
    in_run = run_dir / "brahl_report.md"
    in_run.write_text(markdown, encoding="utf-8")
    flat_path = Z_DIR / f"brahl_report_{run_name}.md"
    flat_path.write_text(markdown, encoding="utf-8")
    try:
        sys.path.insert(0, str(F_DIR))
        import fEngine2  # noqa: WPS433

        fEngine2.write_brahl_report(markdown, suite_name=suite, verify_output_dir=str(run_dir))
    except Exception:
        pass
    return {
        "in_run": in_run.relative_to(KK_ROOT).as_posix(),
        "flat": flat_path.relative_to(KK_ROOT).as_posix(),
    }


def ensure_brahl_report(
    run_name: str,
    config_path: str = "f/fStart_qoa_web_verify.json",
    step_label: str = "Verify",
    project: dict[str, Any] | None = None,
) -> Path:
    """Return report path, generating from zResults if missing."""
    in_run = Z_DIR / run_name / "brahl_report.md"
    flat = Z_DIR / f"brahl_report_{run_name}.md"
    if in_run.is_file():
        return in_run
    if flat.is_file():
        return flat
    stats = analyze_run(run_name)
    if not stats["has_results"]:
        raise FileNotFoundError(f"No results for run: {run_name}")
    md = generate_brahl_report_md(run_name, config_path, step_label, project)
    write_brahl_report_files(run_name, md)
    return in_run


def report_stats(run_name: str) -> dict[str, Any]:
    stats = analyze_run(run_name)
    total = stats["total_plans"]
    fails = stats["fails"]
    health = "green" if fails == 0 and total > 0 else ("amber" if total > 0 else "unknown")
    return {**stats, "health": health}


def write_run_report(
    run_name: str,
    config_path: str,
    step_label: str,
    project: dict[str, Any] | None = None,
) -> dict[str, Any]:
    md = generate_brahl_report_md(run_name, config_path, step_label, project)
    paths = write_brahl_report_files(run_name, md)
    return {
        "run_name": run_name,
        "report_path": paths["in_run"],
        "markdown": md,
        "stats": report_stats(run_name),
    }


def capture_brahl_context(prompt: str, config_path: str, documents: list[dict] | None = None) -> dict[str, Any]:
    sys.path.insert(0, str(F_DIR))
    import fEngine2  # noqa: WPS433

    extra = {"documents": documents} if documents else None
    ctx_path, baseline = fEngine2.write_brahl_context(prompt, config_path, extra=extra)
    return {"context_path": ctx_path, "baseline": baseline}


def list_suites() -> list[dict[str, Any]]:
    y_dir = KK_ROOT / "y"
    out: list[dict[str, Any]] = []
    for path in sorted(y_dir.glob("*/*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict) or "input_files" not in data:
            continue
        name = data.get("name") or path.parent.name
        rel = path.relative_to(KK_ROOT).as_posix()
        entry: dict[str, Any] = {
            "path": rel,
            "name": name,
            "url": data.get("url", ""),
            "description": data.get("description", ""),
            "version": data.get("version", ""),
        }
        try:
            import ypad as ypad_store

            entry.update(ypad_store.plan_stats(rel))
        except (FileNotFoundError, OSError):
            entry.update({"plan_total": 0, "plan_run_y": 0, "plan_run_n": 0, "plan_reuse": 0, "yplans_paths": []})
        runs = list_z_runs(name)
        entry["latest_run"] = runs[0]["name"] if runs else None
        entry["run_count"] = len(runs)
        out.append(entry)
    return out


def get_suite_detail(suite_name: str) -> dict[str, Any] | None:
    for s in list_suites():
        if s["name"] == suite_name:
            return s
    return None


def suite_report_context(suite_name: str, project: dict[str, Any] | None = None) -> dict[str, Any]:
    """Merge y/ suite metadata with optional client project for BRAHL report generation."""
    detail = get_suite_detail(suite_name) or {"name": suite_name}
    ctx: dict[str, Any] = {
        "name": suite_name,
        "app_url": detail.get("url") or "",
        "purpose": detail.get("description") or "",
        "prompt": detail.get("description") or "",
        "suite_meta": detail,
    }
    if project:
        for key in (
            "cycle_history",
            "context_items",
            "brahl_context_path",
            "purpose",
            "prompt",
            "app_url",
            "chat_messages",
        ):
            if project.get(key):
                ctx[key] = project[key]
        if project.get("purpose") or project.get("prompt"):
            ctx["purpose"] = project.get("purpose") or project.get("prompt")
        if project.get("app_url"):
            ctx["app_url"] = project["app_url"]
    return ctx


def default_fstart_for_suite(suite_name: str) -> str:
    """Best-match fStart config for a suite."""
    cfg_path = f"y/{suite_name}/{suite_name}.json"
    matches: list[str] = []
    for rel in list_fstart_configs():
        try:
            data = json.loads((KK_ROOT / rel.replace("/", "\\")).read_text(encoding="utf-8"))
            configs = data.get("configs") or []
            if cfg_path in configs or any(suite_name in c for c in configs):
                matches.append(rel)
        except (OSError, json.JSONDecodeError):
            continue
    if not matches:
        return f"f/fStart_{suite_name}_verify.json" if (F_DIR / f"fStart_{suite_name}_verify.json").is_file() else "f/fStart_qoa_web_verify.json"
    for pref in ("verify", "smoke"):
        for m in matches:
            if pref in m.lower():
                return m
    return matches[0]


def slug_suite_name(name: str) -> str:
    slug = re.sub(r"[^\w\-]", "_", name.strip().lower())
    slug = re.sub(r"_+", "_", slug).strip("_")
    return slug or "project"


def create_ypad_suite(name: str, app_url: str = "", description: str = "") -> dict[str, Any]:
    """Scaffold y/<name>/ with D1–D9 persona y3Designs and starter smoke plans."""
    import sys

    u_dir = KK_ROOT / "u"
    if str(u_dir) not in sys.path:
        sys.path.insert(0, str(u_dir))
    from scaffold_app_ypad import write_app_ypad_suite

    try:
        result = write_app_ypad_suite(name, app_url, description)
    except ValueError:
        raise
    safe = result["name"]
    detail = get_suite_detail(safe)
    return detail or result
