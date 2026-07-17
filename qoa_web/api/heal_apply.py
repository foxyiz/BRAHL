"""Apply structured Heal patches to yPAD CSVs (BRAHL Heal → yPAD edit)."""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any

from paths import repo_rel
from ypad import _read_csv_file, _resolve_sheet_paths

# Normalize model sheet names → ypad API sheet keys
_SHEET_ALIASES = {
    "plans": "plans",
    "y1plans": "plans",
    "y1": "plans",
    "yplans": "plans",
    "actions": "actions",
    "y2actions": "actions",
    "y2": "actions",
    "yactions": "actions",
    "designs": "designs",
    "y3designs": "designs",
    "y3": "designs",
    "ydesigns": "designs",
    "yd_common": "designs",
    "yd_secure": "designs",
    "ydcommon": "designs",
}

# Fields we never overwrite via auto-heal
_BLOCKED_SET_KEYS = {
    "planid",
    "stepid",
    "dataname",
    "actionname",
    "actiontype",
    "run",  # Heal must never flip Run=Y/N — that is Shrink/Restore only
}

_ALLOWED_SET_KEYS = {
    "input",
    "expected",
    "output",
    "stepinfo",
    "tags",
    "d1",
    "d2",
    "d3",
    "d4",
    "d5",
    "d6",
    "d7",
    "d8",
    "d9",
    "type",
    "description",
    "planname",
}


def normalize_sheet(name: str) -> str | None:
    key = re.sub(r"[^a-z0-9]", "", (name or "").strip().lower())
    return _SHEET_ALIASES.get(key)


def _loads_json_lenient(text: str) -> Any | None:
    """Parse JSON; tolerate trailing commas common in model output."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        cleaned = re.sub(r",\s*([}\]])", r"\1", text)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return None


def extract_patches_from_markdown(markdown: str) -> list[dict[str, Any]]:
    """Pull patches from ```json fences or a raw {"patches":[...]} object."""
    if not markdown:
        return []

    candidates: list[str] = re.findall(
        r"```(?:json)?\s*([\s\S]*?)```", markdown, flags=re.IGNORECASE
    )
    # Also try last {"patches": ... } blob (models sometimes omit fences)
    bare = re.search(r'\{\s*"patches"\s*:\s*\[[\s\S]*\]\s*\}', markdown)
    if bare:
        candidates.append(bare.group(0))

    for block in candidates:
        text = block.strip()
        if "patches" not in text:
            continue
        data = _loads_json_lenient(text)
        if data is None:
            m = re.search(r"\{[\s\S]*\}", text)
            if m:
                data = _loads_json_lenient(m.group(0))
        if not isinstance(data, dict):
            continue
        patches = data.get("patches")
        if isinstance(patches, list):
            return [p for p in patches if isinstance(p, dict)]
    return []


def _row_matches(row: dict[str, str], match: dict[str, Any]) -> bool:
    if not match:
        return False
    for key, want in match.items():
        if want is None or want == "":
            continue
        actual = None
        for rk, rv in row.items():
            if rk.lower() == str(key).lower():
                actual = (rv or "").strip()
                break
        if actual is None:
            return False
        want_s = str(want).strip()
        if actual != want_s:
            if str(key).lower() == "planid":
                a = actual.lstrip("P")
                w = want_s.lstrip("P")
                if a == w:
                    continue
            return False
    return True


def _sanitize_set(fields: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for k, v in (fields or {}).items():
        kl = str(k).strip()
        if not kl:
            continue
        if kl.lower() in _BLOCKED_SET_KEYS:
            continue
        if kl.lower() not in _ALLOWED_SET_KEYS and not re.fullmatch(r"d\d+", kl.lower()):
            continue
        if v is None:
            continue
        out[kl] = str(v)
    return out


def _load_sheet_files(suite_config: str, sheet: str) -> list[dict[str, Any]]:
    """Load every CSV path for a sheet (multi-file suites like gate + journey)."""
    paths = _resolve_sheet_paths(suite_config, sheet)
    files: list[dict[str, Any]] = []
    for path in paths:
        headers, rows = _read_csv_file(path)
        files.append(
            {
                "path": path,
                "headers": headers,
                "rows": copy.deepcopy(rows),
                "dirty": False,
            }
        )
    return files


def apply_heal_patches(
    suite_config: str,
    patches: list[dict[str, Any]],
    *,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Apply structured CSV patches. Skips A1 and never changes Run flags."""
    if not patches:
        return {
            "ok": False,
            "error": "No patches to apply — run AI auto-heal first (needs a ```json patches block)",
            "applied": 0,
            "skipped": 0,
            "changes": [],
            "suite_config": suite_config,
        }

    applied = 0
    skipped = 0
    changes: list[dict[str, Any]] = []
    errors: list[str] = []
    sheet_cache: dict[str, list[dict[str, Any]]] = {}

    for i, patch in enumerate(patches):
        if not isinstance(patch, dict):
            skipped += 1
            continue
        klass = str(patch.get("class") or patch.get("classification") or "").upper()
        if klass == "A1":
            skipped += 1
            changes.append({"index": i, "status": "skipped", "reason": "A1 app defect — not auto-healed"})
            continue
        raw_sheet = str(patch.get("sheet") or "")
        sheet = normalize_sheet(raw_sheet)
        if not sheet:
            skipped += 1
            changes.append({"index": i, "status": "skipped", "reason": f"unknown sheet {raw_sheet!r}"})
            continue
        match = patch.get("match") if isinstance(patch.get("match"), dict) else {}
        sets = _sanitize_set(patch.get("set") if isinstance(patch.get("set"), dict) else {})
        if patch.get("set") and isinstance(patch.get("set"), dict) and "Run" in patch["set"]:
            # Explicit note when model tried to change Run
            changes.append(
                {
                    "index": i,
                    "status": "note",
                    "reason": "Ignored set.Run — use Shrink/Restore on Heal (not Apply)",
                }
            )
        if not match or not sets:
            skipped += 1
            reason = "missing match or set"
            if match and not sets:
                reason = "no safe fields left in set (Run/PlanId/StepId blocked)"
            changes.append({"index": i, "status": "skipped", "reason": reason})
            continue

        if sheet not in sheet_cache:
            try:
                sheet_cache[sheet] = _load_sheet_files(suite_config, sheet)
            except Exception as exc:
                errors.append(f"{sheet}: {exc}")
                skipped += 1
                changes.append(
                    {
                        "index": i,
                        "status": "skipped",
                        "reason": f"CSV not found for suite `{suite_config}`: {exc}",
                    }
                )
                continue

        files = sheet_cache[sheet]
        matched_any = False
        for bucket in files:
            matched_rows = [r for r in bucket["rows"] if _row_matches(r, match)]
            if not matched_rows:
                continue
            matched_any = True
            for row in matched_rows:
                before = {}
                for k in sets:
                    header = next((h for h in bucket["headers"] if h.lower() == k.lower()), k)
                    before[header] = row.get(header)
                for k, v in sets.items():
                    header = next((h for h in bucket["headers"] if h.lower() == k.lower()), k)
                    if header not in bucket["headers"]:
                        bucket["headers"].append(header)
                    row[header] = v
                bucket["dirty"] = True
                applied += 1
                changes.append(
                    {
                        "index": i,
                        "status": "applied" if not dry_run else "would_apply",
                        "sheet": sheet,
                        "path": repo_rel(bucket["path"]),
                        "match": match,
                        "before": before,
                        "after": sets,
                        "note": patch.get("note") or patch.get("reason") or "",
                    }
                )

        if not matched_any:
            skipped += 1
            paths = [repo_rel(b["path"]) for b in files]
            changes.append(
                {
                    "index": i,
                    "status": "skipped",
                    "reason": f"no row match {match} in {paths}",
                }
            )

    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "applied": applied,
            "skipped": skipped,
            "changes": changes,
            "errors": errors,
            "suite_config": suite_config,
            "error": None
            if applied > 0
            else (
                errors[0]
                if errors
                else "No matching CSV rows — check PlanId/StepId and suite_config path"
            ),
        }

    written: list[str] = []
    for sheet, files in sheet_cache.items():
        for bucket in files:
            if not bucket.get("dirty"):
                continue
            # write_ypad_sheet only writes first path — write this file directly
            target: Path = bucket["path"]
            headers = bucket["headers"]
            rows = bucket["rows"]
            with target.open("w", encoding="utf-8-sig", newline="") as f:
                import csv

                writer = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
                writer.writeheader()
                writer.writerows(rows)
            written.append(repo_rel(target))

    return {
        "ok": applied > 0,
        "dry_run": False,
        "applied": applied,
        "skipped": skipped,
        "changes": changes,
        "written": [w for w in written if w],
        "errors": errors,
        "suite_config": suite_config,
        "error": None if applied > 0 else (errors[0] if errors else "No patches applied"),
    }
