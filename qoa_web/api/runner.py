"""FoXYiZ engine subprocess runner for qoa_web API."""

from __future__ import annotations

import csv
import json
import os
import re
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import quote as urllib_quote

from paths import (
    F_DIR,
    FOXYIZ_ROOT,
    KK_ROOT,
    PYUTILS_DIR,
    Y_DIR,
    Z_DIR,
    engine_cmd,
    repo_rel,
    resolve_engine,
    resolve_repo,
)

FSTART_DIR = F_DIR / "fStart"
FSTART_RUNTIME_DIR = FSTART_DIR / ".runtime"

# Arena Run profiles (fixed order) → yPAD Tags (OR filter within a profile).
# Smoke → gate CSVs · UI/API/… → journey CSVs when the suite has them.
RUN_PROFILES: dict[str, list[str]] = {
    "Smoke": ["Smoke"],
    "UI": [
        "Nav",
        "Build",
        "Panel",
        "Heal",
        "Loop",
        "Analyze",
        "BRAHL",
        "Shell",
        "Landing",
        "Atomic77",
        "Cost",
        "Run",
    ],
    "API": ["API"],
    "Performance": ["Performance"],
    "Security": ["Security"],
    "Manual": ["Manual"],
}
RUN_PROFILE_ORDER = list(RUN_PROFILES.keys())

# Which yPAD file set each profile uses when the suite ships journey CSVs.
PROFILE_SUITE_MODE: dict[str, str] = {
    "Smoke": "gate",
    "UI": "journey",
    "API": "journey",
    "Performance": "journey",
    "Security": "journey",
    "Manual": "full",
}

OUTPUT_DIR_RE = re.compile(r"Output Directory:\s*(.+)")

DEFAULT_CAPTURE = {
    "image": "on_fail",
    "video": "off",
    "video_fps": 2,
    "subdir": "",
    "overlay": "off",
    "overlay_ms": 250,
}


def _engine_subprocess_env() -> dict[str, str]:
    """Force line-oriented stdout so Arena can stream the Run console live."""
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env.setdefault("PYTHONIOENCODING", "utf-8")
    return env


def _popen_engine(cmd: list[str]) -> subprocess.Popen[str]:
    """Start FoXYiZ with unbuffered, line-readable stdout (stderr merged)."""
    # -u duplicates PYTHONUNBUFFERED for the child interpreter on Windows pipes.
    exe = [cmd[0], "-u", *cmd[1:]] if cmd and cmd[0] == sys.executable else list(cmd)
    return subprocess.Popen(
        exe,
        cwd=str(FOXYIZ_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
        env=_engine_subprocess_env(),
    )


def _drain_stdout(proc: subprocess.Popen[str], job: Job) -> None:
    """Read engine stdout line-by-line into the job log (live polling in Arena)."""
    assert proc.stdout is not None
    while True:
        line = proc.stdout.readline()
        if line == "" and proc.poll() is not None:
            break
        if not line:
            if proc.poll() is not None:
                break
            time.sleep(0.05)
            continue
        job.log_lines.append(line.rstrip("\n"))
        m = OUTPUT_DIR_RE.search(line)
        if m:
            out = m.group(1).strip().replace("\\", "/")
            job.output_dir = out
            if "zDash_batch_" in out:
                job.batch_dashboard = out
            elif out not in job.run_dirs:
                job.run_dirs.append(out)


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
    batch_dashboard: str | None = None
    run_dirs: list[str] = field(default_factory=list)
    config_paths: list[str] = field(default_factory=list)
    parallel: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "config_path": self.config_path,
            "config_paths": self.config_paths or ([self.config_path] if self.config_path else []),
            "step_label": self.step_label,
            "status": self.status,
            "return_code": self.return_code,
            "output_dir": self.output_dir,
            "batch_dashboard": self.batch_dashboard,
            "run_dirs": self.run_dirs,
            "parallel": self.parallel,
            "log_lines": self.log_lines[-400:],
            "started_at": self.started_at,
            "finished_at": self.finished_at,
        }


_jobs: dict[str, Job] = {}
_lock = threading.Lock()


def list_fstart_configs() -> list[str]:
    """List fStarts under FoXYiZ/f/fStart/ (skip archive + .runtime)."""
    if not FSTART_DIR.is_dir():
        return []
    out: list[str] = []
    for p in sorted(FSTART_DIR.glob("*.json")):
        if p.name.startswith("_orch_") or p.name.startswith("."):
            continue
        out.append(f"f/fStart/{p.name}")
    return out


def _y_suite_names() -> list[str]:
    if not Y_DIR.is_dir():
        return []
    return sorted(p.name for p in Y_DIR.iterdir() if p.is_dir())


def _fstart_stem_belongs_to_suite(stem: str, suite_name: str) -> bool:
    """True if fStart filename stem is suite or suite_* — not a longer sibling suite."""
    if stem == suite_name:
        return True
    if not stem.startswith(suite_name + "_"):
        return False
    for other in _y_suite_names():
        if other == suite_name:
            continue
        if stem == other or stem.startswith(other + "_"):
            return False
    return True


def _fstart_refs_suite(suite_name: str, config_entries: list[str]) -> bool:
    """True when fStart configs[] points at y/<suite>/… (path-prefix safe)."""
    prefix = f"y/{suite_name}/"
    for raw in config_entries:
        c = str(raw).replace("\\", "/").lstrip("./")
        if c == f"y/{suite_name}/{suite_name}.json" or c.startswith(prefix):
            return True
    return False


def list_fstart_for_suite(suite_name: str) -> list[str]:
    """Prefer canonical f/fStart/{suite}.json — one file per app."""
    suite_name = (suite_name or "").strip()
    if not suite_name:
        return []
    canonical = f"f/fStart/{suite_name}.json"
    if (FSTART_DIR / f"{suite_name}.json").is_file():
        return [canonical]
    matches: list[str] = []
    for rel in list_fstart_configs():
        if Path(rel).name == "default.json":
            continue
        try:
            data = json.loads(resolve_repo(rel).read_text(encoding="utf-8"))
            configs = data.get("configs") or []
            if _fstart_refs_suite(suite_name, configs):
                matches.append(rel)
                continue
        except (OSError, json.JSONDecodeError):
            pass
        stem = Path(rel).stem
        if _fstart_stem_belongs_to_suite(stem, suite_name):
            matches.append(rel)
    seen: set[str] = set()
    ordered: list[str] = []
    for m in matches:
        if m not in seen:
            seen.add(m)
            ordered.append(m)
    return ordered


def expand_run_profiles(profiles: list[str] | None) -> list[str]:
    """Map Arena profile names → unique yPAD tags (preserve order)."""
    if not profiles:
        return []
    tags: list[str] = []
    seen: set[str] = set()
    for raw in profiles:
        name = (raw or "").strip()
        mapped = list(RUN_PROFILES.get(name) or ([name] if name else []))
        # qoa_web / A77 use Navigation; profile map historically said Nav
        if "Nav" in mapped and "Navigation" not in mapped:
            mapped.append("Navigation")
        if name == "Smoke" and "Capture" not in mapped:
            mapped.append("Capture")
        for t in mapped:
            if t not in seen:
                seen.add(t)
                tags.append(t)
    return tags


def _collect_suite_plan_tag_sets(suite_name: str) -> list[set[str]]:
    """All plan Tags sets from y/<suite>/*Plans*.csv (lowercase)."""
    suite_dir = Y_DIR / suite_name
    if not suite_dir.is_dir():
        return []
    out: list[set[str]] = []
    for path in sorted(suite_dir.glob("*Plans*.csv")):
        try:
            with path.open(encoding="utf-8-sig", newline="") as f:
                for row in csv.DictReader(f):
                    raw = row.get("Tags") or row.get("tags") or ""
                    tags = {t.strip().lower() for t in str(raw).split(";") if t.strip()}
                    if tags:
                        out.append(tags)
        except OSError:
            continue
    return out


# Tags used only for suite-aware chip counting (exclude meta tags shared by Math etc.)
_PROFILE_COUNT_EXTRA = {
    "Smoke": {"capture", "smoke"},
    "UI": {"nav", "navigation", "build", "panel", "heal", "loop", "shell", "landing", "atomic77"},
    "API": {"api"},
    "Performance": {"performance", "perf"},
    "Security": {"security", "sec"},
    "Manual": {"manual"},
}


def suite_tag_inventory(suite_name: str) -> list[dict[str, Any]]:
    """Tag → plan_count from y/<suite>/*Plans*.csv (Run=Y, skip PReuse), sorted by count desc.

    Same vocabulary as Build's yPAD tag cloud so Arena Run chips match what authors see.
    """
    suite_dir = Y_DIR / suite_name
    if not suite_dir.is_dir():
        return []
    counts: dict[str, int] = {}
    canon: dict[str, str] = {}
    for path in sorted(suite_dir.glob("*Plans*.csv")):
        try:
            with path.open(encoding="utf-8-sig", newline="") as f:
                for row in csv.DictReader(f):
                    pid = (row.get("PlanId") or "").strip()
                    if not pid or pid.startswith("PReuse_"):
                        continue
                    if (row.get("Run") or "").strip().upper() != "Y":
                        continue
                    raw = row.get("Tags") or row.get("tags") or ""
                    for part in str(raw).split(";"):
                        tag = part.strip()
                        if not tag:
                            continue
                        key = tag.lower()
                        if key not in canon:
                            canon[key] = tag
                        counts[key] = counts.get(key, 0) + 1
        except OSError:
            continue
    items = [{"id": canon[k], "plan_count": counts[k]} for k in counts]
    items.sort(key=lambda x: (-int(x["plan_count"]), str(x["id"]).lower()))
    return items


def suite_run_profiles(suite_name: str) -> dict[str, Any]:
    """Profiles + suite-native tag inventory for Arena Run chips."""
    tag_sets = _collect_suite_plan_tag_sets(suite_name)
    profiles: list[dict[str, Any]] = []
    all_tags = set().union(*tag_sets) if tag_sets else set()
    for name in RUN_PROFILE_ORDER:
        match = set(_PROFILE_COUNT_EXTRA.get(name, set()))
        # Also allow exact profile tag names (lower) except noisy UI meta tags
        for t in RUN_PROFILES.get(name) or []:
            tl = t.lower()
            if name == "UI" and tl in {"brahl", "analyze", "cost", "run"}:
                continue
            match.add(tl)
        if "nav" in match:
            match.add("navigation")
        count = sum(1 for ts in tag_sets if ts & match)
        if count <= 0:
            continue
        profiles.append(
            {
                "id": name,
                "tags": list(RUN_PROFILES.get(name) or []),
                "plan_count": count,
                "mode": PROFILE_SUITE_MODE.get(name, "full"),
            }
        )
    browserish = bool(
        all_tags
        & {
            "capture",
            "nav",
            "navigation",
            "build",
            "panel",
            "landing",
            "shell",
            "heal",
            "loop",
            "ui",
        }
    )
    if suite_name.lower() in {"math"}:
        browserish = False
    return {
        "suite": suite_name,
        "order": [p["id"] for p in profiles],
        "profiles": profiles,
        "tags": suite_tag_inventory(suite_name),
        "ui_capable": browserish,
        "suite_mode": dict(PROFILE_SUITE_MODE),
    }


def _suite_mode_for_profiles(profiles: list[str] | None) -> str | None:
    """Resolve gate vs journey vs full for a profile selection."""
    clean = [p.strip() for p in (profiles or []) if (p or "").strip()]
    if not clean:
        return None
    modes = {PROFILE_SUITE_MODE.get(p, "full") for p in clean}
    if modes == {"gate"}:
        return "gate"
    if modes == {"journey"}:
        return "journey"
    if len(clean) == 1:
        return PROFILE_SUITE_MODE.get(clean[0], "full")
    # Mixed profiles (e.g. Smoke+UI OR) → full suite JSON
    return "full"


def _suite_name_from_config_rel(config_rel: str) -> str | None:
    parts = Path(str(config_rel).replace("\\", "/")).parts
    if len(parts) >= 2 and parts[0] == "y":
        return parts[1]
    return None


def _read_suite_json(suite_rel: str) -> dict[str, Any] | None:
    path = resolve_repo(suite_rel)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _filter_input_files_for_mode(
    input_files: dict[str, Any], mode: str
) -> dict[str, Any] | None:
    """Return a copy of input_files limited to gate or journey CSVs."""
    if mode not in ("gate", "journey"):
        return None
    out: dict[str, Any] = {}
    for key in ("yPlans", "yActions", "yDesigns"):
        files = list(input_files.get(key) or [])
        if key == "yDesigns":
            out[key] = files
            continue
        if mode == "journey":
            picked = [f for f in files if "_journey" in Path(str(f)).name.lower()]
        else:
            picked = [f for f in files if "_journey" not in Path(str(f)).name.lower()]
        if not picked:
            return None
        out[key] = picked
    if out.get("yPlans") == list(input_files.get("yPlans") or []):
        return None
    return out


def _gate_suite_rel(suite_name: str) -> str | None:
    """Prefer dedicated verify-gate suite JSON when present."""
    candidates = [
        f"y/{suite_name}/{suite_name}_verify_gate.json",
        f"y/{suite_name}/qoa_web_verify_gate.json",
        f"y/{suite_name}/{suite_name}_gate.json",
    ]
    for rel in candidates:
        if resolve_repo(rel).is_file():
            return rel
    return None


def _materialize_suite_override(
    suite_rel: str, mode: str
) -> str | None:
    """Write f/fStart/.runtime/suite_*.json for gate/journey file sets; return rel."""
    if mode == "gate":
        suite_name = _suite_name_from_config_rel(suite_rel)
        gate = _gate_suite_rel(suite_name) if suite_name else None
        if gate:
            return gate

    suite = _read_suite_json(suite_rel)
    if not suite:
        return None
    input_files = suite.get("input_files")
    if not isinstance(input_files, dict):
        return None
    filtered = _filter_input_files_for_mode(input_files, mode)
    if not filtered:
        return None
    if filtered == input_files and mode != "journey":
        return None

    data = dict(suite)
    data["input_files"] = filtered
    data["description"] = (
        f"{suite.get('description') or suite.get('name') or 'suite'} "
        f"[runtime {mode}]"
    )
    FSTART_RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    name = f"suite_{mode}_{uuid.uuid4().hex[:8]}.json"
    # Engine resolves y/… paths; keep runtime suites under fStart/.runtime but
    # reference them as repo-relative paths the engine can open via FOXYIZ_ROOT.
    rel = f"f/fStart/.runtime/{name}"
    path = FSTART_RUNTIME_DIR / name
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return rel


def materialize_runtime_fstart(
    base_config_path: str,
    *,
    tags: list[str] | None = None,
    thread_count: int | None = None,
    profiles: list[str] | None = None,
) -> str:
    """Write f/fStart/.runtime/<id>.json with tag/thread/suite overrides; return rel path."""
    base = read_fstart_config(base_config_path)
    data = dict(base)
    data.setdefault("capture", dict(DEFAULT_CAPTURE))
    if not isinstance(data.get("capture"), dict):
        data["capture"] = dict(DEFAULT_CAPTURE)
    else:
        cap = dict(DEFAULT_CAPTURE)
        cap.update({k: v for k, v in data["capture"].items() if v is not None})
        data["capture"] = cap

    resolved_tags = expand_run_profiles(profiles) if profiles else None
    if resolved_tags is None and tags is not None:
        resolved_tags = [t for t in tags if t]
    if resolved_tags is not None:
        data["tags"] = resolved_tags
    if thread_count is not None:
        data["thread_count"] = max(1, int(thread_count))

    suite_mode = _suite_mode_for_profiles(profiles)
    if suite_mode in ("gate", "journey"):
        configs = list(data.get("configs") or [])
        new_configs: list[str] = []
        for cfg in configs:
            override = _materialize_suite_override(str(cfg), suite_mode)
            new_configs.append(override or str(cfg))
        if new_configs:
            data["configs"] = new_configs

    FSTART_RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    name = f"run_{uuid.uuid4().hex[:10]}.json"
    rel = f"f/fStart/.runtime/{name}"
    path = FSTART_RUNTIME_DIR / name
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return rel


def _validate_fstart_path(rel_path: str) -> Path:
    rel = rel_path.replace("\\", "/").strip()
    if not rel.startswith("f/fStart/") or not rel.endswith(".json"):
        raise ValueError("Invalid fStart path")
    # Allow f/fStart/.runtime/*.json for job overrides
    if "/archive/" in rel or rel.startswith("f/fStart/archive/"):
        raise ValueError("Archived fStarts are read-only")
    path = resolve_repo(rel)
    if not path.resolve().is_relative_to(FSTART_DIR.resolve()):
        raise ValueError("Path must be under f/fStart/")
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


def default_fstart_template(suite_name: str, variant: str = "smoke") -> dict[str, Any]:
    cfg_path = f"y/{suite_name}/{suite_name}.json"
    return {
        "configs": [cfg_path],
        "thread_count": 1,
        "timeout": 8,
        "headless": True,
        "debug": False,
        "tags": ["Smoke"],
        "capture": dict(DEFAULT_CAPTURE),
    }


def create_fstart_config(suite_name: str, variant: str = "smoke") -> str:
    """Create canonical f/fStart/{suite}.json for a y/ suite."""
    filename = f"{suite_name}.json"
    rel = f"f/fStart/{filename}"
    path = FSTART_DIR / filename
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
        if suite_suffix and suite_suffix not in ("*", "all") and not path.name.endswith(
            f"_{suite_suffix}"
        ):
            continue
        results = next(path.glob("*_zResults.csv"), None)
        if not results:
            continue
        agg = plan_stats_from_zresults(results)
        dash = next(path.glob("*_zDash.html"), None)
        # Folder: YYYYMMDD_HHMMSS_<suite>
        ts, _, suite_part = path.name.partition("_")
        # Prefer full timestamp prefix YYYYMMDD_HHMMSS
        m = re.match(r"^(\d{8}_\d{6})_(.+)$", path.name)
        timestamp = m.group(1) if m else ts
        suite_name = m.group(2) if m else suite_part or path.name
        runs.append(
            {
                "name": path.name,
                "path": repo_rel(path),
                "suite": suite_name,
                "timestamp": timestamp,
                "passes": agg["passes"],
                "fails": agg["fails"],
                "total_plans": agg["total_plans"],
                "dashboard": repo_rel(dash) if dash else None,
                "report": repo_rel(path / "brahl_report.md")
                if (path / "brahl_report.md").is_file()
                else None,
            }
        )
    return runs


def _trim_keep_png_refs(text: str, limit: int) -> str:
    """Truncate failure fields but keep screenshot / .png path hints when possible."""
    raw = text or ""
    if len(raw) <= limit:
        return raw
    lower = raw.lower()
    png_i = lower.rfind(".png")
    shot_i = lower.find("screenshot:")
    keep_from = -1
    if shot_i >= 0:
        keep_from = shot_i
    elif png_i >= 0:
        keep_from = max(0, png_i - 120)
        while keep_from > 0 and raw[keep_from - 1] not in " \t\n|;,":
            keep_from -= 1
    if keep_from >= 0:
        tail = raw[keep_from:]
        if len(tail) <= limit:
            return tail if keep_from == 0 else ("…" + tail)
        return "…" + tail[-(limit - 1) :]
    return raw[: limit - 1] + "…"


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
                    "input": _trim_keep_png_refs(row.get("Input") or "", 200),
                    "output": _trim_keep_png_refs(row.get("Output") or "", 800),
                    "expected": _trim_keep_png_refs(row.get("Expected") or "", 200),
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


def start_run(
    config_path: str,
    step_label: str = "Run",
    *,
    tags: list[str] | None = None,
    thread_count: int | None = None,
    profiles: list[str] | None = None,
    runtime_mode: str | None = None,
) -> Job:
    """Start one fStart. Optional profiles/tags/thread_count override via runtime JSON.

    Multi-profile + thread_count>1 → one worker per profile (parallel batch).
    Otherwise → single engine process (OR filter), or engine tag fan-out if
    thread_count>1 and 2+ raw tags.

    runtime_mode=cloud → POST to FOXYIZ_CLOUD_WORKER_URL (EC2 worker) when configured.
    """
    clean_profiles = [p for p in (profiles or []) if (p or "").strip()]
    tc = max(1, int(thread_count)) if thread_count is not None else None
    mode = (runtime_mode or "local").strip().lower()
    if mode not in ("local", "cloud", "desktop"):
        mode = "local"
    if mode == "desktop":
        mode = "local"

    # Parallel by profile: Smoke+API with thread_count=2 → two jobs
    if len(clean_profiles) >= 2 and tc is not None and tc > 1 and mode == "local":
        runtime_paths: list[str] = []
        for prof in clean_profiles:
            runtime_paths.append(
                materialize_runtime_fstart(
                    config_path,
                    profiles=[prof],
                    thread_count=1,
                )
            )
        job = start_batch(
            runtime_paths,
            parallel=True,
            step_label=step_label or "Run parallel",
        )
        job.config_path = config_path
        return job

    job_id = uuid.uuid4().hex[:10]
    job = Job(job_id=job_id, config_path=config_path, step_label=step_label)
    with _lock:
        _jobs[job_id] = job

    def worker() -> None:
        job.status = "running"
        job.started_at = time.time()
        runtime_rel: str | None = None
        try:
            if mode == "cloud":
                import cloud_worker as cw

                if not cw.cloud_configured():
                    job.status = "failed"
                    job.log_lines.append(
                        "[ERROR] runtime_mode=cloud but FOXYIZ_CLOUD_WORKER_URL is unset"
                    )
                    return
                job.log_lines.append("[i] Dispatching to FOXYIZ_CLOUD_WORKER_URL …")
                remote = cw.submit_job(
                    config_path=config_path,
                    step_label=step_label,
                    tags=tags,
                    thread_count=tc,
                    profiles=clean_profiles or None,
                )
                remote_id = remote.get("remote_job_id") or remote.get("job_id")
                job.log_lines.append(f"[i] Cloud job: {remote_id}")
                # Poll until terminal
                for _ in range(3600):
                    time.sleep(2)
                    st = cw.poll_job(str(remote_id))
                    for line in st.get("log_lines") or []:
                        if line not in job.log_lines:
                            job.log_lines.append(line)
                    if st.get("output_dir"):
                        job.output_dir = st["output_dir"]
                    status = (st.get("status") or "").lower()
                    if status in ("completed", "failed"):
                        job.return_code = st.get("return_code")
                        job.status = status
                        return
                job.status = "failed"
                job.log_lines.append("[ERROR] cloud job poll timeout")
                return

            use_override = tags is not None or tc is not None or bool(clean_profiles)
            if use_override:
                runtime_rel = materialize_runtime_fstart(
                    config_path,
                    tags=tags,
                    thread_count=tc,
                    profiles=clean_profiles or None,
                )
                job.log_lines.append(
                    f"[i] Runtime fStart: {runtime_rel}"
                    + (f" profiles={clean_profiles}" if clean_profiles else "")
                    + (f" tags={tags}" if tags and not clean_profiles else "")
                    + (f" thread_count={tc}" if tc is not None else "")
                )
                cfg = resolve_repo(runtime_rel)
                engine_rel = runtime_rel
            else:
                cfg = resolve_repo(config_path)
                engine_rel = str(Path(config_path).as_posix())
            if not cfg.is_file():
                job.status = "failed"
                job.log_lines.append(f"Config not found: {config_path}")
                job.finished_at = time.time()
                return
            job.log_lines.append(f"[i] Engine: {resolve_engine()}")
            proc = _popen_engine(engine_cmd(engine_rel))
            _drain_stdout(proc, job)
            proc.wait()
            job.return_code = proc.returncode
            job.status = "completed" if proc.returncode == 0 else "failed"
        except Exception as exc:
            job.log_lines.append(f"[ERROR] {exc}")
            job.status = "failed"
        finally:
            if runtime_rel:
                try:
                    resolve_repo(runtime_rel).unlink(missing_ok=True)
                except OSError:
                    pass
            job.finished_at = time.time()

    threading.Thread(target=worker, daemon=True).start()
    return job


def start_batch(
    config_paths: list[str],
    *,
    parallel: bool = True,
    step_label: str = "Run parallel",
) -> Job:
    """Run multiple fStarts via fOrchestrate (parallel or sequential) + batch zDash."""
    paths = [p.strip() for p in config_paths if p and str(p).strip()]
    if not paths:
        raise ValueError("config_paths required")
    if len(paths) == 1 and not parallel:
        return start_run(paths[0], step_label="Run")

    job_id = uuid.uuid4().hex[:10]
    job = Job(
        job_id=job_id,
        config_path=paths[0],
        config_paths=paths,
        step_label=step_label,
        parallel=parallel,
    )
    with _lock:
        _jobs[job_id] = job

    orch = PYUTILS_DIR / "fOrchestrate.py"

    def worker() -> None:
        job.status = "running"
        job.started_at = time.time()
        try:
            cmd = [
                sys.executable,
                str(orch),
                "--configs",
                ",".join(paths),
            ]
            if not parallel:
                cmd.append("--sequential")
            else:
                cmd.append("--parallel")
            proc = _popen_engine(cmd)
            _drain_stdout(proc, job)
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
        "visual_playback": None,
        "screenshot_count": 0,
        "overlay_count": 0,
        "has_filmstrip": False,
        "has_gif": False,
    }
    if not run_dir.is_dir():
        return out
    results = next(run_dir.glob("*_zResults.csv"), None)
    dash = next(run_dir.glob("*_zDash.html"), None)
    if dash:
        out["dashboard"] = repo_rel(dash)
    arts = list_run_artifacts(run_name)
    out["visual_playback"] = arts.get("visual_playback")
    out["screenshot_count"] = arts.get("counts", {}).get("screenshots", 0)
    out["overlay_count"] = arts.get("counts", {}).get("overlays", 0)
    out["has_filmstrip"] = bool(arts.get("filmstrip"))
    out["has_gif"] = bool(arts.get("gif"))
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


def list_run_artifacts(run_name: str) -> dict[str, Any]:
    """Discover zDash, visual playback, overlay/status PNGs, filmstrip/GIF under a run folder."""
    run_dir = Z_DIR / run_name
    out: dict[str, Any] = {
        "run_name": run_name,
        "visual_playback": None,
        "visual_frames": None,
        "dashboard": None,
        "zlogs": None,
        "brahl_report": None,
        "screenshots": [],
        "overlay_shots": [],
        "filmstrip": None,
        "gif": None,
        "counts": {
            "screenshots": 0,
            "overlays": 0,
            "total_png": 0,
        },
    }
    if not run_dir.is_dir():
        return out

    def _file_url(rel_posix: str) -> str:
        # Keep path segments encoded but preserve slashes for FastAPI path param
        parts = [urllib_quote(p, safe="") for p in rel_posix.split("/") if p]
        return f"/api/files/z/{urllib_quote(run_name, safe='')}/{'/'.join(parts)}"

    dash = next(run_dir.glob("*_zDash.html"), None)
    if dash and dash.is_file():
        rel = dash.relative_to(run_dir).as_posix()
        out["dashboard"] = {
            "path": rel,
            "url": _file_url(rel),
            "repo": repo_rel(dash),
        }

    vp = run_dir / "visual_playback.html"
    if vp.is_file():
        out["visual_playback"] = {
            "path": "visual_playback.html",
            "url": _file_url("visual_playback.html"),
        }

    vf = run_dir / "visual_frames.jsonl"
    if vf.is_file():
        out["visual_frames"] = {
            "path": "visual_frames.jsonl",
            "url": _file_url("visual_frames.jsonl"),
        }

    zlogs = run_dir / "zlogs.txt"
    if zlogs.is_file():
        out["zlogs"] = {"path": "zlogs.txt", "url": _file_url("zlogs.txt")}

    brahl = run_dir / "brahl_report.md"
    if brahl.is_file():
        out["brahl_report"] = {"path": "brahl_report.md", "url": _file_url("brahl_report.md")}

    screenshots: list[dict[str, str]] = []
    overlays: list[dict[str, str]] = []
    for png in sorted(run_dir.rglob("*.png")):
        if not png.is_file():
            continue
        rel = png.relative_to(run_dir).as_posix()
        name_l = png.name.lower()
        entry = {"path": rel, "url": _file_url(rel), "name": png.name}
        if "filmstrip" in name_l:
            out["filmstrip"] = entry
            continue
        if any(tag in name_l for tag in ("ov_orange", "ov_green", "ov_red")):
            overlays.append(entry)
        else:
            screenshots.append(entry)

    for gif in sorted(run_dir.rglob("*.gif")):
        if gif.is_file() and ("roll" in gif.name.lower() or "site_shots" in gif.name.lower()):
            rel = gif.relative_to(run_dir).as_posix()
            out["gif"] = {"path": rel, "url": _file_url(rel), "name": gif.name}
            break

    out["screenshots"] = screenshots
    out["overlay_shots"] = overlays
    out["counts"] = {
        "screenshots": len(screenshots),
        "overlays": len(overlays),
        "total_png": len(screenshots) + len(overlays) + (1 if out["filmstrip"] else 0),
    }
    return out


def generate_run_filmstrip(run_name: str) -> dict[str, Any]:
    """Run site_shot_roll.py against an existing z/ run (GIF + filmstrip)."""
    run_dir = Z_DIR / run_name
    if not run_dir.is_dir():
        raise FileNotFoundError(run_name)
    script = FOXYIZ_ROOT / "pyUtils" / "site_shot_roll.py"
    if not script.is_file():
        raise FileNotFoundError("FoXYiZ/pyUtils/site_shot_roll.py not found")
    # Prefer --run with path relative to FoXYiZ
    rel_run = f"z/{run_name}"
    cmd = [
        sys.executable,
        "-u",
        str(script),
        "--run",
        rel_run,
        "--gif",
        "--filmstrip",
    ]
    proc = subprocess.run(
        cmd,
        cwd=str(FOXYIZ_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=_engine_subprocess_env(),
        timeout=180,
    )
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "site_shot_roll failed").strip()
        raise RuntimeError(err[:800])
    try:
        from fEngine2 import refresh_zdash_artifact_links  # type: ignore

        refresh_zdash_artifact_links(str(run_dir))
    except Exception:
        # Best-effort: engine may not be importable from api cwd
        eng = FOXYIZ_ROOT / "f" / "fEngine2.py"
        if eng.is_file():
            try:
                sys.path.insert(0, str(FOXYIZ_ROOT / "f"))
                import fEngine2 as _fe  # type: ignore

                _fe.refresh_zdash_artifact_links(str(run_dir))
            except Exception:
                pass
    return list_run_artifacts(run_name)


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
        rel = resolve_repo(context_path)
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
    config_path: str = "f/fStart/qoa_web_verify.json",
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

## Conclusion

{"**GO** — Verify is green; automation for this scope is ready to publish." if fails == 0 and total > 0 else "**NO-GO** — Verify has failures; heal yPAD (or document A1 defects) before launch readiness."}
Health: **{health}** · {passes}/{total} plans passed · step `{step_label}`.

## Verdict

{chr(10).join(verdict_checks)}
- [{'x' if fails == 0 and total > 0 else ' '}] Conclusion: {'GO' if fails == 0 and total > 0 else 'NO-GO'}

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
        "in_run": repo_rel(in_run),
        "flat": repo_rel(flat_path),
    }


def ensure_brahl_report(
    run_name: str,
    config_path: str = "f/fStart/qoa_web_verify.json",
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


def _suite_entry_from_json(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict) or "input_files" not in data:
        return None
    name = data.get("name") or path.parent.name
    rel = repo_rel(path)
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
    return entry


def list_suites() -> list[dict[str, Any]]:
    """One project per y/<suite>/ folder — primary JSON is y/<suite>/<suite>.json."""
    y_dir = Y_DIR
    out: list[dict[str, Any]] = []
    if not y_dir.is_dir():
        return out
    for suite_dir in sorted(p for p in y_dir.iterdir() if p.is_dir()):
        primary = suite_dir / f"{suite_dir.name}.json"
        entry = None
        if primary.is_file():
            entry = _suite_entry_from_json(primary)
        if entry is None:
            # Scaffold edge case: first suite JSON with input_files in the folder.
            for path in sorted(suite_dir.glob("*.json")):
                entry = _suite_entry_from_json(path)
                if entry:
                    break
        if entry:
            # Canonical name = folder name so topbar keys stay unique.
            entry["name"] = suite_dir.name
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
    """Best-match fStart config for a suite — prefer canonical f/fStart/{suite}.json."""
    canonical = f"f/fStart/{suite_name}.json"
    if resolve_repo(canonical).is_file():
        return canonical
    matches = list_fstart_for_suite(suite_name)
    if matches:
        return matches[0]
    if resolve_repo("f/fStart/Math.json").is_file():
        return "f/fStart/Math.json"
    return "f/fStart/Math.json"


def slug_suite_name(name: str) -> str:
    slug = re.sub(r"[^\w\-]", "_", name.strip().lower())
    slug = re.sub(r"_+", "_", slug).strip("_")
    return slug or "project"


def create_ypad_suite(
    name: str,
    app_url: str = "",
    description: str = "",
    brahl_plan: dict[str, Any] | None = None,
    *,
    created_by: str = "",
) -> dict[str, Any]:
    """Scaffold y/<name>/ with persona y3Designs and plan-driven or smoke plans."""
    import sys

    py_utils = PYUTILS_DIR
    if str(py_utils) not in sys.path:
        sys.path.insert(0, str(py_utils))
    from scaffold_app_ypad import write_app_ypad_suite

    try:
        result = write_app_ypad_suite(name, app_url, description, brahl_plan=brahl_plan, created_by=created_by)
    except ValueError:
        raise
    safe = result["name"]
    detail = get_suite_detail(safe)
    if detail:
        detail["ypad"] = result.get("ypad")
        return detail
    return result


def materialize_brahl_plan_for_suite(
    suite_name: str,
    app_url: str = "",
    brahl_plan: dict[str, Any] | None = None,
    *,
    created_by: str = "",
) -> dict[str, Any]:
    """Rewrite existing suite y1/y2 from an accepted BRAHL plan."""
    import sys

    py_utils = PYUTILS_DIR
    if str(py_utils) not in sys.path:
        sys.path.insert(0, str(py_utils))
    from scaffold_app_ypad import materialize_brahl_plan_suite

    return materialize_brahl_plan_suite(suite_name, app_url, brahl_plan, created_by=created_by)
