"""
Aggregate parallel FoXYiZ batch runs into one batch dashboard HTML.

Run from KK/ after parallel terminals finish:

  python u/zBatchDash.py --name parallel_demo --logs z/parallel_demo_*.log
  python u/zBatchDash.py --name journey_wave1 --runs z/20260705_111807_qoa_web z/20260705_111809_qoa_web
  python u/zBatchDash.py --name journey_wave1 --since 20260705_1118

Writes: z/zDash_batch_<name>.html
"""
from __future__ import annotations

import argparse
import csv
import glob
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from _paths import FOXYIZ_ROOT, Z_DIR


@dataclass
class BatchJob:
    label: str
    tag: str = ""
    config: str = ""
    run_dir: Path | None = None
    run_name: str = ""
    total_plans: int = 0
    passed: int = 0
    failed: int = 0
    wall_seconds: float = 0.0
    step_seconds: float = 0.0
    dashboard: str = ""
    log_path: Path | None = None
    started_at: str = ""
    finished_at: str = ""

    @property
    def pass_rate(self) -> float:
        if self.total_plans <= 0:
            return 0.0
        return round(100.0 * self.passed / self.total_plans, 1)


def escape_html(value: object) -> str:
    if value is None:
        return ""
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def format_duration(seconds: float) -> str:
    if seconds <= 0:
        return "—"
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes, secs = divmod(int(round(seconds)), 60)
    if minutes < 60:
        return f"{minutes}m {secs}s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes}m {secs}s"


def parse_zresults(run_dir: Path) -> tuple[int, int, int, float]:
    """Return total_plans, passed, failed, step_seconds from zResults CSV."""
    results_files = sorted(run_dir.glob("*_zResults.csv"))
    if not results_files:
        return 0, 0, 0, 0.0

    plan_results: dict[str, str] = {}
    step_seconds = 0.0
    for results_path in results_files:
        with results_path.open(encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                plan_id = (row.get("PlanId") or "").strip()
                result = (row.get("Result") or "").strip().lower()
                try:
                    step_seconds += float(row.get("TimeTaken") or 0)
                except (TypeError, ValueError):
                    pass
                if not plan_id:
                    continue
                if result == "fail":
                    plan_results[plan_id] = "fail"
                elif plan_id not in plan_results or plan_results[plan_id] != "fail":
                    plan_results[plan_id] = "pass"

    passed = sum(1 for value in plan_results.values() if value == "pass")
    failed = sum(1 for value in plan_results.values() if value == "fail")
    total = len(plan_results)
    return total, passed, failed, round(step_seconds, 2)


def parse_zdash_meta(run_dir: Path) -> dict:
    dash_files = sorted(run_dir.glob("*_zDash.html"))
    if not dash_files:
        return {}
    try:
        text = dash_files[0].read_text(encoding="utf-8")
    except OSError:
        return {}
    match = re.search(r"const runMeta\s*=\s*(\{.*?\});", text, re.DOTALL)
    if not match:
        return {}
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return {}


def read_text_auto(path: Path) -> str:
    raw = path.read_bytes()
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        return raw.decode("utf-16")
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw.decode("utf-8-sig")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("utf-16", errors="replace")


def parse_parallel_log(log_path: Path) -> BatchJob:
    text = read_text_auto(log_path)
    label = log_path.stem
    if label.startswith("parallel_demo_"):
        label = label.replace("parallel_demo_", "", 1)
    elif label.startswith("parallel_"):
        label = label.replace("parallel_", "", 1)

    config_match = re.search(r"fStart_qoa_web[^\s\"']+\.json", text)
    config = config_match.group(0) if config_match else ""

    tag_match = re.search(r"Tag filter: Running plans with tags:\s*(.+)", text)
    tag = tag_match.group(1).strip() if tag_match else label

    run_dir = None
    run_name = ""
    run_match = re.search(r"Results saved to:\s*(.+)", text)
    if run_match:
        raw = run_match.group(1).strip()
        run_dir = Path(raw)
        if not run_dir.is_absolute():
            run_dir = FOXYIZ_ROOT / run_dir
        run_name = run_dir.name

    total = passed = failed = 0
    for line in text.splitlines():
        if "? Total Plans:" in line or "Total Plans:" in line:
            m = re.search(r"Total Plans:\s*(\d+)", line)
            if m:
                total = int(m.group(1))
        if "? Passed:" in line or "Passed:" in line:
            m = re.search(r"Passed:\s*(\d+)", line)
            if m:
                passed = int(m.group(1))
        if "? Failed:" in line or "Failed:" in line:
            m = re.search(r"Failed:\s*(\d+)", line)
            if m:
                failed = int(m.group(1))

    wall_seconds = 0.0
    wall_match = re.search(r"Total Time:\s*([\d.]+)\s*seconds", text)
    if wall_match:
        wall_seconds = float(wall_match.group(1))

    ts_matches = re.findall(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", text)
    started_at = ts_matches[0] if ts_matches else ""
    finished_at = ts_matches[-1] if ts_matches else ""

    dashboard = ""
    dash_match = re.search(r"Dashboard:\s*(.+)", text)
    if dash_match:
        dash_path = Path(dash_match.group(1).strip())
        if dash_path.is_file():
            dashboard = dash_path.relative_to(FOXYIZ_ROOT).as_posix()
    elif run_dir and run_dir.is_dir():
        dash_files = sorted(run_dir.glob("*_zDash.html"))
        if dash_files:
            dashboard = dash_files[0].relative_to(FOXYIZ_ROOT).as_posix()

    job = BatchJob(
        label=label,
        tag=tag,
        config=config,
        run_dir=run_dir if run_dir and run_dir.is_dir() else None,
        run_name=run_name,
        total_plans=total,
        passed=passed,
        failed=failed,
        wall_seconds=wall_seconds,
        dashboard=dashboard,
        log_path=log_path,
        started_at=started_at,
        finished_at=finished_at,
    )
    if job.run_dir:
        csv_total, csv_pass, csv_fail, step_seconds = parse_zresults(job.run_dir)
        if job.log_path:
            if step_seconds:
                job.step_seconds = step_seconds
        elif csv_total:
            job.total_plans = csv_total
            job.passed = csv_pass
            job.failed = csv_fail
            job.step_seconds = step_seconds
        meta = parse_zdash_meta(job.run_dir)
        if meta.get("wallClockSeconds") and not job.wall_seconds:
            job.wall_seconds = float(meta["wallClockSeconds"])
        if meta.get("tagsFilter") and not job.tag:
            job.tag = ", ".join(meta["tagsFilter"])
        if not job.dashboard:
            dash_files = sorted(job.run_dir.glob("*_zDash.html"))
            if dash_files:
                job.dashboard = dash_files[0].relative_to(FOXYIZ_ROOT).as_posix()
    return job


def analyze_run_dir(run_dir: Path, label: str = "") -> BatchJob:
    run_dir = run_dir if run_dir.is_absolute() else FOXYIZ_ROOT / run_dir
    total, passed, failed, step_seconds = parse_zresults(run_dir)
    meta = parse_zdash_meta(run_dir)
    tag = ", ".join(meta.get("tagsFilter") or []) or label or run_dir.name
    wall_seconds = float(meta.get("wallClockSeconds") or step_seconds or 0)
    dashboard = ""
    dash_files = sorted(run_dir.glob("*_zDash.html"))
    if dash_files:
        dashboard = dash_files[0].relative_to(FOXYIZ_ROOT).as_posix()
    return BatchJob(
        label=label or run_dir.name,
        tag=tag,
        run_dir=run_dir,
        run_name=run_dir.name,
        total_plans=total,
        passed=passed,
        failed=failed,
        wall_seconds=wall_seconds,
        step_seconds=step_seconds,
        dashboard=dashboard,
    )


def discover_runs_since(prefix: str, suite_suffix: str = "qoa_web") -> list[Path]:
    if not Z_DIR.is_dir():
        return []
    found: list[Path] = []
    for path in sorted(Z_DIR.iterdir()):
        if not path.is_dir():
            continue
        if not path.name.startswith(prefix):
            continue
        if suite_suffix and not path.name.endswith(f"_{suite_suffix}"):
            continue
        if list(path.glob("*_zResults.csv")):
            found.append(path)
    return found


def merge_jobs(jobs: list[BatchJob]) -> list[BatchJob]:
    """Deduplicate; keep one entry per batch label (logs) or run folder (dirs)."""
    by_key: dict[str, BatchJob] = {}
    for job in jobs:
        key = job.label if job.log_path else (job.run_name or job.label)
        existing = by_key.get(key)
        if existing is None:
            by_key[key] = job
            continue
        if job.log_path and not existing.log_path:
            by_key[key] = job
        elif job.total_plans > existing.total_plans:
            by_key[key] = job
    return sorted(by_key.values(), key=lambda item: (item.tag.lower(), item.label.lower()))


def collect_failures(jobs: list[BatchJob], limit: int = 200) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for job in jobs:
        if not job.run_dir or not job.run_dir.is_dir():
            continue
        for results_path in sorted(job.run_dir.glob("*_zResults.csv")):
            with results_path.open(encoding="utf-8-sig", newline="") as handle:
                for row in csv.DictReader(handle):
                    if (row.get("Result") or "").strip().lower() != "fail":
                        continue
                    rows.append(
                        {
                            "batch": job.label,
                            "tag": job.tag,
                            "planId": row.get("PlanId", ""),
                            "stepId": row.get("StepId", ""),
                            "stepInfo": row.get("StepInfo", ""),
                            "output": (row.get("Output") or "")[:240],
                        }
                    )
                    if len(rows) >= limit:
                        return rows
    return rows


def build_html(batch_name: str, jobs: list[BatchJob], failures: list[dict[str, str]]) -> str:
    generated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    total_plans = sum(job.total_plans for job in jobs)
    total_pass = sum(job.passed for job in jobs)
    total_fail = sum(job.failed for job in jobs)
    overall_rate = round(100.0 * total_pass / total_plans, 1) if total_plans else 0.0

    sequential_wall = sum(job.wall_seconds for job in jobs)
    parallel_wall = max((job.wall_seconds for job in jobs), default=0.0)
    time_saved = max(0.0, sequential_wall - parallel_wall)
    speedup = round(sequential_wall / parallel_wall, 2) if parallel_wall > 0 else 0.0
    step_total = sum(job.step_seconds for job in jobs)

    job_rows = []
    max_wall = max((job.wall_seconds for job in jobs), default=1.0) or 1.0
    for job in jobs:
        bar_width = int(round(100 * job.wall_seconds / max_wall)) if job.wall_seconds else 0
        dash_link = (
            f'<a href="../{escape_html(job.dashboard)}" target="_blank">Open zDash</a>'
            if job.dashboard
            else "—"
        )
        log_link = (
            f'<a href="../{escape_html(job.log_path.relative_to(FOXYIZ_ROOT).as_posix())}" target="_blank">Log</a>'
            if job.log_path and job.log_path.is_file()
            else "—"
        )
        job_rows.append(
            f"""
        <tr>
            <td><strong>{escape_html(job.label)}</strong><div class="sub">{escape_html(job.tag)}</div></td>
            <td>{escape_html(job.config or "—")}</td>
            <td>{escape_html(job.run_name or "—")}</td>
            <td class="num">{job.total_plans}</td>
            <td class="num pass">{job.passed}</td>
            <td class="num fail">{job.failed}</td>
            <td class="num">{job.pass_rate}%</td>
            <td class="num">{format_duration(job.wall_seconds)}</td>
            <td class="num">{format_duration(job.step_seconds)}</td>
            <td><div class="bar"><span style="width:{bar_width}%"></span></div></td>
            <td>{dash_link} · {log_link}</td>
        </tr>"""
        )

    failure_rows = []
    for row in failures:
        failure_rows.append(
            f"""
        <tr>
            <td>{escape_html(row["batch"])}</td>
            <td>{escape_html(row["tag"])}</td>
            <td>{escape_html(row["planId"])}</td>
            <td>{escape_html(row["stepId"])}</td>
            <td>{escape_html(row["stepInfo"])}</td>
            <td class="output-cell" title="{escape_html(row["output"])}">{escape_html(row["output"][:100])}{"…" if len(row["output"]) > 100 else ""}</td>
        </tr>"""
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FoXYiZ Batch Report — {escape_html(batch_name)}</title>
    <style>
        *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f1f5f9;
            color: #0f172a;
            line-height: 1.5;
        }}
        .container {{ max-width: 1440px; margin: 0 auto; padding: 1.5rem; }}
        .header {{
            background: linear-gradient(135deg, #0ea5e9 0%, #4f46e5 100%);
            color: #fff;
            border-radius: 16px;
            padding: 2rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 10px 25px rgba(14, 165, 233, 0.25);
        }}
        .header h1 {{ font-size: 2rem; margin-bottom: 0.35rem; }}
        .header p {{ opacity: 0.92; }}
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 1rem;
            margin-bottom: 1.5rem;
        }}
        .card {{
            background: #fff;
            border-radius: 12px;
            padding: 1.25rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        }}
        .card h2 {{
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            color: #64748b;
            margin-bottom: 0.5rem;
        }}
        .card .value {{ font-size: 1.75rem; font-weight: 700; }}
        .card.pass .value {{ color: #16a34a; }}
        .card.fail .value {{ color: #dc2626; }}
        .card.time .value {{ color: #4f46e5; font-size: 1.35rem; }}
        section {{
            background: #fff;
            border-radius: 12px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.08);
            margin-bottom: 1.5rem;
            overflow: hidden;
        }}
        section h2 {{
            padding: 1rem 1.25rem;
            background: #f8fafc;
            border-bottom: 1px solid #e2e8f0;
            font-size: 1.05rem;
        }}
        .table-wrap {{ overflow: auto; }}
        table {{ width: 100%; border-collapse: collapse; font-size: 0.875rem; }}
        th {{
            background: #f1f5f9;
            padding: 0.65rem 0.75rem;
            text-align: left;
            font-weight: 600;
            color: #475569;
            position: sticky;
            top: 0;
        }}
        td {{ padding: 0.65rem 0.75rem; border-bottom: 1px solid #f1f5f9; vertical-align: top; }}
        tr:hover {{ background: #f8fafc; }}
        .num {{ text-align: right; white-space: nowrap; }}
        .pass {{ color: #16a34a; font-weight: 600; }}
        .fail {{ color: #dc2626; font-weight: 600; }}
        .sub {{ font-size: 0.75rem; color: #64748b; margin-top: 0.15rem; }}
        .bar {{ height: 8px; background: #e2e8f0; border-radius: 999px; overflow: hidden; min-width: 80px; }}
        .bar span {{ display: block; height: 100%; background: linear-gradient(90deg, #38bdf8, #4f46e5); }}
        .compare {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 1rem;
            padding: 1.25rem;
        }}
        .compare .metric {{
            background: #f8fafc;
            border-radius: 10px;
            padding: 1rem;
        }}
        .compare .metric .label {{ color: #64748b; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.05em; }}
        .compare .metric .value {{ font-size: 1.5rem; font-weight: 700; margin-top: 0.25rem; }}
        .compare .metric .hint {{ color: #64748b; font-size: 0.85rem; margin-top: 0.35rem; }}
        .output-cell {{ max-width: 320px; word-break: break-word; }}
        a {{ color: #2563eb; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Parallel Batch Report — {escape_html(batch_name)}</h1>
            <p>{len(jobs)} parallel jobs · {total_pass}/{total_plans} plans passed ({overall_rate}%) · generated {generated}</p>
        </div>

        <div class="summary-grid">
            <div class="card"><h2>Jobs</h2><div class="value">{len(jobs)}</div></div>
            <div class="card"><h2>Total plans</h2><div class="value">{total_plans}</div></div>
            <div class="card pass"><h2>Passed</h2><div class="value">{total_pass}</div></div>
            <div class="card fail"><h2>Failed</h2><div class="value">{total_fail}</div></div>
            <div class="card time"><h2>Parallel wall time</h2><div class="value">{format_duration(parallel_wall)}</div></div>
            <div class="card time"><h2>Sequential (sum)</h2><div class="value">{format_duration(sequential_wall)}</div></div>
        </div>

        <section>
            <h2>Time comparison — parallel vs sequential</h2>
            <div class="compare">
                <div class="metric">
                    <div class="label">If run one after another</div>
                    <div class="value">{format_duration(sequential_wall)}</div>
                    <div class="hint">Sum of each job&apos;s wall-clock time</div>
                </div>
                <div class="metric">
                    <div class="label">Parallel batch wall time</div>
                    <div class="value">{format_duration(parallel_wall)}</div>
                    <div class="hint">Longest job (bottleneck) sets total wait</div>
                </div>
                <div class="metric">
                    <div class="label">Time saved</div>
                    <div class="value">{format_duration(time_saved)}</div>
                    <div class="hint">{speedup}x faster than sequential</div>
                </div>
                <div class="metric">
                    <div class="label">Engine step time (all jobs)</div>
                    <div class="value">{format_duration(step_total)}</div>
                    <div class="hint">Sum of step durations across batches</div>
                </div>
            </div>
        </section>

        <section>
            <h2>Jobs in this batch</h2>
            <div class="table-wrap">
                <table>
                    <thead>
                        <tr>
                            <th>Batch / tag</th>
                            <th>fStart</th>
                            <th>Run folder</th>
                            <th>Plans</th>
                            <th>Pass</th>
                            <th>Fail</th>
                            <th>Rate</th>
                            <th>Wall</th>
                            <th>Steps</th>
                            <th>Duration bar</th>
                            <th>Links</th>
                        </tr>
                    </thead>
                    <tbody>
                        {''.join(job_rows)}
                    </tbody>
                </table>
            </div>
        </section>

        <section>
            <h2>Failures across batch ({len(failures)} shown)</h2>
            <div class="table-wrap">
                <table>
                    <thead>
                        <tr>
                            <th>Batch</th>
                            <th>Tag</th>
                            <th>Plan</th>
                            <th>Step</th>
                            <th>Step info</th>
                            <th>Output</th>
                        </tr>
                    </thead>
                    <tbody>
                        {''.join(failure_rows) if failure_rows else '<tr><td colspan="6">No failures 🎉</td></tr>'}
                    </tbody>
                </table>
            </div>
        </section>
    </div>
</body>
</html>"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Build aggregated zDash batch HTML for parallel FoXYiZ runs.")
    parser.add_argument("--name", required=True, help="Batch label used in output filename (e.g. parallel_demo)")
    parser.add_argument("--runs", nargs="*", default=[], help="Explicit z run directories")
    parser.add_argument("--logs", nargs="*", default=[], help="Glob(s) for parallel run logs (e.g. z/parallel_demo_*.log)")
    parser.add_argument("--since", default="", help="Include z/<since>*_<suite>/ folders with zResults")
    parser.add_argument("--suite", default="qoa_web", help="Suite suffix when using --since (default: qoa_web)")
    args = parser.parse_args()

    jobs: list[BatchJob] = []

    for pattern in args.logs:
        for log_path in sorted(glob.glob(pattern)):
            resolved = Path(log_path)
            if not resolved.is_absolute():
                resolved = FOXYIZ_ROOT / resolved
            jobs.append(parse_parallel_log(resolved))

    for run in args.runs:
        jobs.append(analyze_run_dir(Path(run)))

    if args.since:
        for run_dir in discover_runs_since(args.since, args.suite):
            jobs.append(analyze_run_dir(run_dir))

    jobs = merge_jobs(jobs)
    if not jobs:
        raise SystemExit("No batch jobs found. Pass --logs, --runs, and/or --since.")

    failures = collect_failures(jobs)
    html = build_html(args.name, jobs, failures)
    out_path = Z_DIR / f"zDash_batch_{args.name}.html"
    out_path.write_text(html, encoding="utf-8")

    total_plans = sum(job.total_plans for job in jobs)
    total_pass = sum(job.passed for job in jobs)
    sequential = sum(job.wall_seconds for job in jobs)
    parallel = max((job.wall_seconds for job in jobs), default=0.0)
    print(f"Batch dashboard: {out_path}")
    print(f"Jobs: {len(jobs)} · Plans: {total_pass}/{total_plans} passed")
    print(f"Sequential wall: {format_duration(sequential)} · Parallel wall: {format_duration(parallel)}")


if __name__ == "__main__":
    main()
