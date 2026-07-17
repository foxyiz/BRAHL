"""yPAD Run=Y shrink/restore — parity with BRAHL.py Heal tab."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from paths import KK_ROOT, F_DIR, Z_DIR, repo_rel, resolve_repo
DEFAULT_SUITE = "y/Math/Math.json"


def _resolve_cfg_path(suite_config: str) -> Path:
    cfg_path = resolve_repo(suite_config)
    if not cfg_path.is_file():
        raise FileNotFoundError(
            f"Suite config not found: {suite_config}. "
            f"Use an existing lean suite (e.g. {DEFAULT_SUITE})."
        )
    return cfg_path


def _baseline_path(suite_config: str) -> Path:
    cfg = _resolve_cfg_path(suite_config)
    return cfg.with_name(f"{cfg.stem}_run_y_baseline.json")


def current_run_y_ids(suite_config: str = DEFAULT_SUITE) -> set[str]:
    ids: set[str] = set()
    for plans_path in _resolve_y1_paths(suite_config):
        with plans_path.open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                pid = (row.get("PlanId") or "").strip()
                if not pid or pid.startswith("PReuse_"):
                    continue
                if (row.get("Run") or "").strip().upper() == "Y":
                    ids.add(pid)
    return ids


def save_run_y_baseline(suite_config: str = DEFAULT_SUITE) -> list[str]:
    """Snapshot current Run=Y plan ids so restore recovers the pre-shrink set."""
    ids = sorted(current_run_y_ids(suite_config))
    path = _baseline_path(suite_config)
    path.write_text(json.dumps({"run_y": ids}, indent=2) + "\n", encoding="utf-8")
    return ids


def load_run_y_baseline(suite_config: str = DEFAULT_SUITE) -> set[str] | None:
    path = _baseline_path(suite_config)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    raw = data.get("run_y") if isinstance(data, dict) else None
    if not isinstance(raw, list):
        return None
    return {str(x).strip() for x in raw if str(x).strip()}


def _resolve_y1_paths(suite_config: str = DEFAULT_SUITE) -> list[Path]:
    cfg_path = _resolve_cfg_path(suite_config)
    data = json.loads(cfg_path.read_text(encoding="utf-8"))
    paths: list[Path] = []
    for rel in data.get("input_files", {}).get("yPlans", []):
        p = resolve_repo(rel)
        if p.is_file():
            paths.append(p)
    if not paths:
        raise FileNotFoundError("No y1Plans files in suite config")
    return paths


def failed_plan_ids(run_name: str) -> set[str]:
    run_dir = Z_DIR / run_name
    results = next(run_dir.glob("*_zResults.csv"), None) if run_dir.is_dir() else None
    if not results:
        return set()
    failed: set[str] = set()
    with results.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            if (row.get("Result") or "").strip().lower() == "fail":
                pid = (row.get("PlanId") or "").strip()
                if pid:
                    failed.add(pid)
                    # FoXYiZ may prefix PlanId with P in zResults
                    if pid.startswith("P") and len(pid) > 1:
                        failed.add(pid[1:])
                    else:
                        failed.add(f"P{pid}")
    return failed


def _normalize_plan_match(candidate: set[str], catalog: set[str]) -> set[str]:
    """Map zResults PlanIds onto y1Plans PlanIds (handles optional P prefix)."""
    matched: set[str] = set()
    for pid in catalog:
        if pid in candidate or f"P{pid}" in candidate:
            matched.add(pid)
            continue
        if pid.startswith("P") and pid[1:] in candidate:
            matched.add(pid)
    return matched


def plan_stats(suite_config: str = DEFAULT_SUITE) -> dict[str, Any]:
    """Count y1Plans rows for a suite."""
    total = run_y = run_n = reuse = 0
    ypaths: list[str] = []
    for plans_path in _resolve_y1_paths(suite_config):
        ypaths.append(repo_rel(plans_path))
        with plans_path.open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                pid = (row.get("PlanId") or "").strip()
                if not pid:
                    continue
                total += 1
                if pid.startswith("PReuse_"):
                    reuse += 1
                run = (row.get("Run") or "").strip().upper()
                if run == "Y":
                    run_y += 1
                elif run == "N":
                    run_n += 1
    return {
        "plan_total": total,
        "plan_run_y": run_y,
        "plan_run_n": run_n,
        "plan_reuse": reuse,
        "yplans_paths": ypaths,
    }


def all_plan_ids(suite_config: str = DEFAULT_SUITE) -> set[str]:
    ids: set[str] = set()
    for plans_path in _resolve_y1_paths(suite_config):
        with plans_path.open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                pid = (row.get("PlanId") or "").strip()
                if pid and not pid.startswith("PReuse_"):
                    ids.add(pid)
    return ids


def _edit_run_flags(
    run_y_ids: set[str] | None,
    run_n_ids: set[str] | None,
    suite_config: str = DEFAULT_SUITE,
) -> int:
    changed = 0
    for plans_path in _resolve_y1_paths(suite_config):
        rows: list[dict[str, str]] = []
        with plans_path.open(encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames or []
            for row in reader:
                pid = (row.get("PlanId") or "").strip()
                if pid.startswith("PReuse_"):
                    if (row.get("Run") or "").upper() != "N":
                        row["Run"] = "N"
                        changed += 1
                elif run_y_ids is not None and pid in run_y_ids and (row.get("Run") or "").upper() != "Y":
                    row["Run"] = "Y"
                    changed += 1
                elif run_n_ids is not None and pid in run_n_ids and (row.get("Run") or "").upper() != "N":
                    row["Run"] = "N"
                    changed += 1
                rows.append(row)
        with plans_path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
    return changed


def shrink_to_failures(run_name: str, suite_config: str = DEFAULT_SUITE) -> dict[str, Any]:
    failed_raw = failed_plan_ids(run_name)
    if not failed_raw:
        return {"ok": False, "error": "No failures in run", "run_y": 0, "run_n": 0, "changed": 0}
    baseline = load_run_y_baseline(suite_config)
    if baseline is None:
        baseline_ids = save_run_y_baseline(suite_config)
    else:
        baseline_ids = sorted(baseline)
    all_ids = all_plan_ids(suite_config)
    failed = _normalize_plan_match(failed_raw, all_ids)
    if not failed:
        return {
            "ok": False,
            "error": "Failures are not in this suite's y1Plans",
            "run_y": 0,
            "run_n": 0,
            "changed": 0,
            "baseline_run_y": baseline_ids,
            "raw_failed": sorted(failed_raw),
        }
    pass_ids = all_ids - failed
    changed = _edit_run_flags(run_y_ids=failed, run_n_ids=pass_ids, suite_config=suite_config)
    return {
        "ok": True,
        "run_y": len(failed),
        "run_n": len(pass_ids),
        "changed": changed,
        "failed_plans": sorted(failed),
        "baseline_run_y": baseline_ids,
    }


def restore_all_run_y(suite_config: str = DEFAULT_SUITE) -> dict[str, Any]:
    """Restore Run=Y to pre-shrink baseline when present; otherwise all non-PReuse plans."""
    all_ids = all_plan_ids(suite_config)
    baseline = load_run_y_baseline(suite_config)
    from_baseline = baseline is not None
    if from_baseline:
        run_y = baseline & all_ids
        if not run_y:
            run_y = all_ids
            from_baseline = False
    else:
        run_y = all_ids
    run_n = all_ids - run_y
    changed = _edit_run_flags(run_y_ids=run_y, run_n_ids=run_n, suite_config=suite_config)
    if not from_baseline:
        path = _baseline_path(suite_config)
        path.write_text(json.dumps({"run_y": sorted(run_y)}, indent=2) + "\n", encoding="utf-8")
    return {
        "ok": True,
        "run_y": len(run_y),
        "run_n": len(run_n),
        "changed": changed,
        "from_baseline": from_baseline,
    }


def list_automation_plans(suite_config: str = DEFAULT_SUITE) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for plans_path in _resolve_y1_paths(suite_config):
        with plans_path.open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                pid = (row.get("PlanId") or "").strip()
                if not pid or pid.startswith("PReuse_"):
                    continue
                run = (row.get("Run") or "").strip().upper()
                if run != "Y":
                    continue
                tags = (row.get("Tags") or "").strip()
                out.append(
                    {
                        "planId": pid,
                        "planName": (row.get("PlanName") or pid).strip(),
                        "tags": tags,
                        "output": (row.get("Output") or "").strip(),
                        "kind": "automation",
                    }
                )
    return out


_SHEET_KEYS = {
    "plans": "yPlans",
    "actions": "yActions",
    "designs": "yDesigns",
}


def _resolve_suite_config(suite_config: str = DEFAULT_SUITE) -> dict[str, Any]:
    return json.loads(_resolve_cfg_path(suite_config).read_text(encoding="utf-8"))


def _resolve_sheet_paths(suite_config: str, sheet: str) -> list[Path]:
    if sheet not in _SHEET_KEYS:
        raise ValueError(f"Unknown sheet: {sheet}")
    data = _resolve_suite_config(suite_config)
    key = _SHEET_KEYS[sheet]
    paths: list[Path] = []
    for rel in data.get("input_files", {}).get(key, []):
        p = resolve_repo(rel)
        if p.is_file():
            paths.append(p)
    if not paths:
        raise FileNotFoundError(f"No {key} files in suite config")
    return paths


def _read_csv_file(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = [dict(row) for row in reader]
    return fieldnames, rows


def _sheet_source_kind(rel_path: str) -> str:
    """Classify a sheet file as gate or journey based on filename."""
    name = Path(str(rel_path).replace("\\", "/")).name.lower()
    return "journey" if "_journey" in name else "gate"


def _annotate_source_rows(
    rows: list[dict[str, str]], rel_path: str
) -> list[dict[str, str]]:
    kind = _sheet_source_kind(rel_path)
    out: list[dict[str, str]] = []
    for row in rows:
        annotated = dict(row)
        annotated["_source"] = rel_path
        annotated["_source_kind"] = kind
        out.append(annotated)
    return out


def read_ypad_sheet(
    suite_config: str,
    sheet: str,
    *,
    source: str | None = None,
    source_kind: str | None = None,
) -> dict[str, Any]:
    """Read y1Plans, y2Actions, or y3Designs for a suite.

    Multi-file suites return merged rows annotated with `_source` / `_source_kind`.
    Optional `source` (rel path) or `source_kind` (`gate`|`journey`) filters files.
    """
    paths = _resolve_sheet_paths(suite_config, sheet)
    all_headers: list[str] = []
    all_rows: list[dict[str, str]] = []
    rel_paths: list[str] = []
    sources: list[dict[str, str]] = []
    wanted = (source or "").replace("\\", "/").strip() or None
    kind_filter = (source_kind or "").strip().lower() or None
    if kind_filter and kind_filter not in ("gate", "journey"):
        raise ValueError("source_kind must be gate or journey")

    for p in paths:
        rel = repo_rel(p).replace("\\", "/")
        kind = _sheet_source_kind(rel)
        if wanted and rel != wanted and Path(rel).name != Path(wanted).name:
            continue
        if kind_filter and kind != kind_filter:
            continue
        rel_paths.append(rel)
        sources.append({"path": rel, "kind": kind})
        headers, rows = _read_csv_file(p)
        if not all_headers:
            all_headers = headers
        all_rows.extend(_annotate_source_rows(rows, rel))

    if not rel_paths:
        raise FileNotFoundError(
            f"No {sheet} files matched source={wanted or '*'} kind={kind_filter or '*'}"
        )
    return {
        "sheet": sheet,
        "headers": all_headers,
        "rows": all_rows,
        "paths": rel_paths,
        "sources": sources,
        "multi_file": len(rel_paths) > 1,
        "row_count": len(all_rows),
    }


_ENV_TYPE_MARKERS = {"env", "secure", "credential", "secret", "token"}
_ENV_NAME_MARKERS = ("password", "secret", "token", "api_key", "credential", "client_secret")
_SECRET_PLACEHOLDER = ""
_D_COLUMN_RE = ("D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8", "D9")


def _is_env_design_row(row: dict[str, str]) -> bool:
    typ = (row.get("Type") or "").strip().lower()
    if typ in _ENV_TYPE_MARKERS:
        return True
    name = (row.get("DataName") or "").strip().lower()
    return any(m in name for m in _ENV_NAME_MARKERS)


def _is_httpish(value: str) -> bool:
    v = (value or "").strip().lower()
    return v.startswith("http://") or v.startswith("https://") or v.startswith("css=")


def redact_design_row(row: dict[str, str]) -> dict[str, str]:
    """Hide credential/env D* values; keep DataName and non-secret locator/URL cells."""
    out = dict(row)
    if not _is_env_design_row(out):
        return out
    for col in _D_COLUMN_RE:
        if col not in out:
            continue
        val = str(out.get(col) or "").strip()
        if not val:
            continue
        if _is_httpish(val):
            continue
        out[col] = _SECRET_PLACEHOLDER
        out[f"_{col}_redacted"] = "1"
    out["_redacted"] = "1"
    return out


def read_env_example(suite_config: str = DEFAULT_SUITE) -> dict[str, Any]:
    """ENV tab: credential/env row names + FoXYiZ .env.example (values redacted)."""
    designs = read_ypad_sheet(suite_config, "designs")
    env_rows = [redact_design_row(r) for r in designs["rows"] if _is_env_design_row(r)]
    example_path = F_DIR / ".env.example"
    example_text = ""
    if example_path.is_file():
        example_text = example_path.read_text(encoding="utf-8")
    lines: list[str] = []
    if example_text.strip():
        lines.append("# FoXYiZ / BRAHL — copy f/.env.example to f/.env")
        lines.append("# Copy to f/.env and fill in real values. Never commit f/.env to git.")
        lines.append(example_text.strip())
    if env_rows:
        if lines:
            lines.append("")
        lines.append("# From y3Designs (names only — values redacted in Arena)")
        for row in env_rows:
            name = (row.get("DataName") or "VAR").strip() or "VAR"
            key = name.upper().replace(" ", "_")
            lines.append(f'{key}=""')
    return {
        "sheet": "env",
        "headers": designs["headers"],
        "rows": env_rows,
        "env_example": "\n".join(lines) if lines else "# No ENV variables defined yet.\nOPENAI_API_KEY=",
        "paths": designs["paths"],
        "sources": designs.get("sources") or [],
        "redacted": True,
        "row_count": len(env_rows),
    }


def _resolve_write_target(
    suite_config: str,
    sheet: str,
    source: str | None,
) -> Path:
    paths = _resolve_sheet_paths(suite_config, sheet)
    if len(paths) == 1 and not source:
        return paths[0]
    if not source or not str(source).strip():
        rels = ", ".join(repo_rel(p) for p in paths)
        raise ValueError(
            f"Multi-file {sheet} suite requires an explicit source path. "
            f"Available: {rels}"
        )
    wanted = str(source).replace("\\", "/").strip()
    for p in paths:
        rel = repo_rel(p).replace("\\", "/")
        if rel == wanted or Path(rel).name == Path(wanted).name:
            return p
    raise ValueError(f"Unknown source for {sheet}: {wanted}")


def write_ypad_sheet(
    suite_config: str,
    sheet: str,
    rows: list[dict[str, str]],
    headers: list[str] | None = None,
    *,
    source: str | None = None,
) -> dict[str, Any]:
    """Write rows to one CSV. Multi-file suites require `source` (rel path)."""
    target = _resolve_write_target(suite_config, sheet, source)
    clean_rows: list[dict[str, str]] = []
    for row in rows:
        clean = {
            k: v
            for k, v in row.items()
            if not str(k).startswith("_")
        }
        clean_rows.append(clean)
    if headers is None:
        headers, _ = _read_csv_file(target)
        if not headers and clean_rows:
            headers = [k for k in clean_rows[0].keys() if not str(k).startswith("_")]
    else:
        headers = [h for h in headers if not str(h).startswith("_")]
    with target.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(clean_rows)
    rel = repo_rel(target).replace("\\", "/")
    return {
        "ok": True,
        "path": rel,
        "source": rel,
        "source_kind": _sheet_source_kind(rel),
        "row_count": len(clean_rows),
    }


def plan_tags_exact_match(plan_tags: str, wanted: str) -> bool:
    """Exact semicolon-tag match (case-insensitive), not substring."""
    needle = (wanted or "").strip().lower()
    if not needle:
        return True
    tags = [t.strip().lower() for t in str(plan_tags or "").split(";") if t.strip()]
    return needle in tags
