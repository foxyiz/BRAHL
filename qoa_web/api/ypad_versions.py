"""Immutable yPAD version snapshots under y/<suite>/versions/<id>/."""

from __future__ import annotations

import csv
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from paths import Y_DIR, repo_rel, resolve_repo
from ypad import _resolve_cfg_path, _resolve_sheet_paths, read_ypad_sheet, write_ypad_sheet

SHEETS = ("plans", "actions", "designs")


def _suite_dir(suite_config: str) -> Path:
    return _resolve_cfg_path(suite_config).parent


def _versions_root(suite_config: str) -> Path:
    return _suite_dir(suite_config) / "versions"


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _version_id(label: str = "") -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    slug = "".join(c if c.isalnum() or c in "-_" else "-" for c in (label or "").strip())[:40]
    return f"{stamp}_{slug}" if slug else stamp


def _suite_has_live_csvs(suite_config: str) -> bool:
    for sheet in SHEETS:
        try:
            if _resolve_sheet_paths(suite_config, sheet):
                return True
        except FileNotFoundError:
            continue
    return False


def list_versions(suite_config: str, *, ensure_baseline: bool = True) -> dict[str, Any]:
    """List immutable snapshots. When live CSVs exist and versions/ is empty, seed an initial snapshot."""
    root = _versions_root(suite_config)
    items: list[dict[str, Any]] = []
    if root.is_dir():
        for d in sorted(root.iterdir(), reverse=True):
            if not d.is_dir():
                continue
            manifest = d / "manifest.json"
            if not manifest.is_file():
                continue
            try:
                data = json.loads(manifest.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            data["id"] = data.get("id") or d.name
            data["path"] = repo_rel(d).replace("\\", "/")
            items.append(data)
    if ensure_baseline and not items and _suite_has_live_csvs(suite_config):
        try:
            create_snapshot(
                suite_config,
                label="initial",
                author="system",
                source_build="auto-baseline",
            )
        except (OSError, ValueError, FileNotFoundError):
            pass
        else:
            return list_versions(suite_config, ensure_baseline=False)
    return {"suite_config": suite_config, "versions": items, "count": len(items)}


def create_snapshot(
    suite_config: str,
    *,
    label: str = "",
    author: str = "",
    source_build: str = "",
) -> dict[str, Any]:
    """Copy current sheet CSVs into an immutable versions/<id>/ folder."""
    vid = _version_id(label)
    dest = _versions_root(suite_config) / vid
    dest.mkdir(parents=True, exist_ok=False)
    files: list[dict[str, str]] = []
    for sheet in SHEETS:
        try:
            paths = _resolve_sheet_paths(suite_config, sheet)
        except FileNotFoundError:
            continue
        for src in paths:
            rel = repo_rel(src).replace("\\", "/")
            target_name = Path(rel).name
            target = dest / target_name
            # Avoid collisions across sheets with same basename (rare)
            if target.exists():
                target = dest / f"{sheet}_{target_name}"
            shutil.copy2(src, target)
            files.append({"sheet": sheet, "source": rel, "snapshot": repo_rel(target).replace("\\", "/")})
    manifest = {
        "id": vid,
        "label": (label or "").strip() or vid,
        "author": (author or "").strip() or "unknown",
        "created_at": _now_iso(),
        "source_build": (source_build or "").strip(),
        "suite_config": suite_config,
        "files": files,
        "immutable": True,
    }
    (dest / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def _load_manifest(suite_config: str, version_id: str) -> tuple[Path, dict[str, Any]]:
    dest = _versions_root(suite_config) / version_id
    manifest_path = dest / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Version not found: {version_id}")
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    return dest, data


def get_version(suite_config: str, version_id: str) -> dict[str, Any]:
    dest, data = _load_manifest(suite_config, version_id)
    data["path"] = repo_rel(dest).replace("\\", "/")
    return data


def _plan_key(row: dict[str, str]) -> str:
    return (row.get("PlanId") or "").strip()


def _action_key(row: dict[str, str]) -> str:
    return f"{(row.get('PlanId') or '').strip()}::{(row.get('StepId') or '').strip()}"


def _design_key(row: dict[str, str]) -> str:
    return (row.get("DataName") or "").strip()


def _row_key(sheet: str, row: dict[str, str]) -> str:
    if sheet == "plans":
        return _plan_key(row)
    if sheet == "actions":
        return _action_key(row)
    return _design_key(row)


def _read_snapshot_sheet(dest: Path, sheet: str, files: list[dict[str, str]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for entry in files:
        if entry.get("sheet") != sheet:
            continue
        snap = entry.get("snapshot") or ""
        path = resolve_repo(snap) if snap.startswith(("y/", "f/", "z/")) else dest / Path(snap).name
        if not path.is_file():
            # fallback: basename in dest
            path = dest / Path(entry.get("source") or snap).name
        if not path.is_file():
            continue
        with path.open(encoding="utf-8-sig", newline="") as f:
            rows.extend(dict(r) for r in csv.DictReader(f))
    return rows


def diff_version(
    suite_config: str,
    version_id: str,
    *,
    sheet: str = "plans",
) -> dict[str, Any]:
    """Compare a snapshot sheet against current suite sheet (by PlanId/StepId/DataName)."""
    dest, manifest = _load_manifest(suite_config, version_id)
    old_rows = _read_snapshot_sheet(dest, sheet, manifest.get("files") or [])
    current = read_ypad_sheet(suite_config, sheet)
    new_rows = current["rows"]
    old_map = {_row_key(sheet, r): r for r in old_rows if _row_key(sheet, r)}
    new_map = {_row_key(sheet, r): r for r in new_rows if _row_key(sheet, r)}
    added = [new_map[k] for k in sorted(set(new_map) - set(old_map))]
    removed = [old_map[k] for k in sorted(set(old_map) - set(new_map))]
    changed: list[dict[str, Any]] = []
    for k in sorted(set(old_map) & set(new_map)):
        o, n = old_map[k], new_map[k]
        deltas = {
            col: {"old": o.get(col, ""), "new": n.get(col, "")}
            for col in sorted(set(o) | set(n))
            if not str(col).startswith("_") and (o.get(col) or "") != (n.get(col) or "")
        }
        if deltas:
            changed.append({"key": k, "fields": deltas})
    return {
        "version_id": version_id,
        "sheet": sheet,
        "added": added,
        "removed": removed,
        "changed": changed,
        "counts": {
            "added": len(added),
            "removed": len(removed),
            "changed": len(changed),
            "old": len(old_map),
            "current": len(new_map),
        },
        "manifest": {
            "id": manifest.get("id"),
            "label": manifest.get("label"),
            "author": manifest.get("author"),
            "created_at": manifest.get("created_at"),
        },
    }


def restore_version(suite_config: str, version_id: str) -> dict[str, Any]:
    """Replace current sheet CSVs with snapshot files (still requires per-file write)."""
    dest, manifest = _load_manifest(suite_config, version_id)
    written: list[str] = []
    for entry in manifest.get("files") or []:
        source_rel = (entry.get("source") or "").replace("\\", "/")
        snap_rel = entry.get("snapshot") or ""
        snap = resolve_repo(snap_rel) if snap_rel else dest / Path(source_rel).name
        if not snap.is_file():
            snap = dest / Path(source_rel).name
        if not snap.is_file() or not source_rel:
            continue
        target = resolve_repo(source_rel)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(snap, target)
        written.append(source_rel)
    return {"ok": True, "version_id": version_id, "written": written}


def merge_missing(
    suite_config: str,
    version_id: str,
    *,
    sheet: str = "plans",
    keys: list[str] | None = None,
) -> dict[str, Any]:
    """Selectively merge rows present in snapshot but missing in current (by key)."""
    dest, manifest = _load_manifest(suite_config, version_id)
    old_rows = _read_snapshot_sheet(dest, sheet, manifest.get("files") or [])
    # Merge only into gate (or single) file for safety — prefer first matching source
    try:
        paths = _resolve_sheet_paths(suite_config, sheet)
    except FileNotFoundError as exc:
        raise ValueError(str(exc)) from exc
    # Prefer writing into a single explicit source (first path / gate)
    target = paths[0]
    for p in paths:
        if "_journey" not in p.name.lower():
            target = p
            break
    source_rel = repo_rel(target).replace("\\", "/")
    current = read_ypad_sheet(suite_config, sheet, source=source_rel)
    cur_rows = [dict(r) for r in current["rows"]]
    cur_keys = {_row_key(sheet, r) for r in cur_rows if _row_key(sheet, r)}
    wanted = {k.strip() for k in (keys or []) if str(k).strip()} or None
    added: list[str] = []
    for row in old_rows:
        key = _row_key(sheet, row)
        if not key or key in cur_keys:
            continue
        if wanted is not None and key not in wanted:
            continue
        clean = {k: v for k, v in row.items() if not str(k).startswith("_")}
        cur_rows.append(clean)
        cur_keys.add(key)
        added.append(key)
    if not added:
        return {"ok": True, "merged": 0, "keys": [], "source": source_rel}
    res = write_ypad_sheet(
        suite_config,
        sheet,
        cur_rows,
        current["headers"],
        source=source_rel,
    )
    return {"ok": True, "merged": len(added), "keys": added, "source": source_rel, "write": res}


def annotate_plan_creator(
    row: dict[str, str],
    *,
    created_by: str,
    created_at: str | None = None,
) -> dict[str, str]:
    """Ensure CreatedBy / CreatedAt on a plan row."""
    out = dict(row)
    if created_by and not (out.get("CreatedBy") or "").strip():
        out["CreatedBy"] = created_by
    if not (out.get("CreatedAt") or "").strip():
        out["CreatedAt"] = created_at or _now_iso()
    return out


# Keep Y_DIR import used for typing/docs
_ = Y_DIR
