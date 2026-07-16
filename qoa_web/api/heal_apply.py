"""Apply structured Heal patches to yPAD CSVs (BRAHL Heal → yPAD edit)."""

from __future__ import annotations

import copy
import re
from typing import Any

from paths import repo_rel
from ypad import _read_csv_file, _resolve_sheet_paths, write_ypad_sheet

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
    "actionname",  # changing action name is high risk — allow only if we soften later
}

_ALLOWED_SET_KEYS = {
    "input",
    "expected",
    "output",
    "stepinfo",
    "run",
    "tags",
    "d1",
    "d2",
    "d3",
    "d4",
    "d5",
    "type",
    "description",
    "planname",
}


def normalize_sheet(name: str) -> str | None:
    key = re.sub(r"[^a-z0-9]", "", (name or "").strip().lower())
    return _SHEET_ALIASES.get(key)


def extract_patches_from_markdown(markdown: str) -> list[dict[str, Any]]:
    """Pull patches from a ```json fenced block containing {"patches":[...]}."""
    if not markdown:
        return []
    blocks = re.findall(r"```(?:json)?\s*([\s\S]*?)```", markdown, flags=re.IGNORECASE)
    import json

    for block in blocks:
        text = block.strip()
        if "patches" not in text:
            continue
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            # try first {...} object
            m = re.search(r"\{[\s\S]*\}", text)
            if not m:
                continue
            try:
                data = json.loads(m.group(0))
            except json.JSONDecodeError:
                continue
        patches = data.get("patches") if isinstance(data, dict) else None
        if isinstance(patches, list):
            return [p for p in patches if isinstance(p, dict)]
    return []


def _row_matches(row: dict[str, str], match: dict[str, Any]) -> bool:
    if not match:
        return False
    for key, want in match.items():
        if want is None or want == "":
            continue
        # case-insensitive header lookup
        actual = None
        for rk, rv in row.items():
            if rk.lower() == str(key).lower():
                actual = (rv or "").strip()
                break
        if actual is None:
            return False
        want_s = str(want).strip()
        if actual != want_s:
            # PlanId P1 vs 1
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
        if kl.lower() not in _ALLOWED_SET_KEYS and not kl.lower().startswith("d"):
            continue
        if v is None:
            continue
        out[kl] = str(v)
    return out


def apply_heal_patches(
    suite_config: str,
    patches: list[dict[str, Any]],
    *,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Apply structured CSV patches. Skips A1-classified patches and empty sets."""
    if not patches:
        return {"ok": False, "error": "No patches to apply", "applied": 0, "skipped": 0, "changes": []}

    # Group by sheet → apply to first matching CSV path
    applied = 0
    skipped = 0
    changes: list[dict[str, Any]] = []
    errors: list[str] = []

    # Work on a copy of each sheet once
    sheet_cache: dict[str, dict[str, Any]] = {}

    for i, patch in enumerate(patches):
        if not isinstance(patch, dict):
            skipped += 1
            continue
        klass = str(patch.get("class") or patch.get("classification") or "").upper()
        if klass == "A1":
            skipped += 1
            changes.append({"index": i, "status": "skipped", "reason": "A1 app defect — not auto-healed"})
            continue
        sheet = normalize_sheet(str(patch.get("sheet") or ""))
        if not sheet:
            skipped += 1
            changes.append({"index": i, "status": "skipped", "reason": f"unknown sheet {patch.get('sheet')}"})
            continue
        match = patch.get("match") if isinstance(patch.get("match"), dict) else {}
        sets = _sanitize_set(patch.get("set") if isinstance(patch.get("set"), dict) else {})
        if not match or not sets:
            skipped += 1
            changes.append({"index": i, "status": "skipped", "reason": "missing match or set"})
            continue

        if sheet not in sheet_cache:
            try:
                paths = _resolve_sheet_paths(suite_config, sheet)
                headers, rows = _read_csv_file(paths[0])
                sheet_cache[sheet] = {
                    "path": paths[0],
                    "headers": headers,
                    "rows": copy.deepcopy(rows),
                    "dirty": False,
                }
            except Exception as exc:
                errors.append(f"{sheet}: {exc}")
                skipped += 1
                continue

        bucket = sheet_cache[sheet]
        matched_rows = [r for r in bucket["rows"] if _row_matches(r, match)]
        if not matched_rows:
            skipped += 1
            changes.append({"index": i, "status": "skipped", "reason": f"no row match {match}"})
            continue

        for row in matched_rows:
            before = {k: row.get(k) for k in sets}
            for k, v in sets.items():
                # Prefer exact header casing from CSV
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

    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "applied": applied,
            "skipped": skipped,
            "changes": changes,
            "errors": errors,
        }

    written: list[str] = []
    for sheet, bucket in sheet_cache.items():
        if not bucket.get("dirty"):
            continue
        res = write_ypad_sheet(suite_config, sheet, bucket["rows"], bucket["headers"])
        written.append(res.get("path") or "")

    return {
        "ok": applied > 0,
        "dry_run": False,
        "applied": applied,
        "skipped": skipped,
        "changes": changes,
        "written": [w for w in written if w],
        "errors": errors,
        "error": None if applied > 0 else (errors[0] if errors else "No patches applied"),
    }
