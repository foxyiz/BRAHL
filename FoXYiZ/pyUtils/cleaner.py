#!/usr/bin/env python3
"""
Archive ephemeral FoXYiZ z/ runs (and probe leftovers) outside KK.

Default destination: <FXYZ>/archive/cleanup/<timestamp>/  (sibling of KK/)

Keeps the KK working tree small for humans and AI context. Safe to delete the
entire archive/cleanup/ folder when you need disk space.

Does NOT touch f/fEngine2.py, x/xActions.py, or any engine/action code.

Usage (from KK/):
  python FoXYiZ/pyUtils/cleaner.py                    # dry-run
  python FoXYiZ/pyUtils/cleaner.py --apply            # archive; keep latest BRAHL run/suite
  python FoXYiZ/pyUtils/cleaner.py --apply --ypad-versions   # archive older y/<suite>/versions/
  python FoXYiZ/pyUtils/cleaner.py --apply --keep-latest 0   # archive all z/ runs
  python FoXYiZ/pyUtils/cleaner.py --apply --purge-archive

yPAD history: major expansions snapshot into y/<suite>/versions/<ts>_<label>/ (CSVs).
Cleanup can move older snapshots to ../archive/cleanup/ so they leave AI context.
"""

from __future__ import annotations

import argparse
import re
import shutil
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

from _paths import (
    ARCHIVE_CLEANUP,
    FOXYIZ_ROOT,
    FXYZ_ROOT,
    KK_ROOT,
    Y_VISUALIZATION_HTML,
    Z_DEFECTS_DASHBOARD_HTML,
    Z_DIR,
)

Y_DIR = FOXYIZ_ROOT / "y"

Z_KEEP_NAMES = frozenset(
    {
        ".gitkeep",
        "zDash_template.html",
    }
)

DEPRECATED_DOCS: tuple[Path, ...] = ()
REGENERATED_ARTIFACTS = (Y_VISUALIZATION_HTML, Z_DEFECTS_DASHBOARD_HTML)
ROOT_PROBE_GLOBS = ("*_probe.json", "*_probe.py")

_RUN_DIR_RE = re.compile(r"^(\d{8}_\d{6})_(.+)$")


def _rel(path: Path) -> str:
    for root in (FOXYIZ_ROOT, KK_ROOT, FXYZ_ROOT):
        try:
            return str(path.relative_to(root)).replace("\\", "/")
        except ValueError:
            continue
    return str(path)


def _parse_run_dir(name: str) -> tuple[str, str] | None:
    match = _RUN_DIR_RE.match(name)
    if not match:
        return None
    return match.group(1), match.group(2)


def _is_dated_run_dir(name: str) -> bool:
    return _parse_run_dir(name) is not None


def select_kept_run_dirs(z_dir: Path, keep_latest: int) -> set[Path]:
    """Keep newest N run dirs per suite (prefer dirs that already have brahl_report.md)."""
    if keep_latest <= 0 or not z_dir.is_dir():
        return set()

    by_suite: dict[str, list[Path]] = defaultdict(list)
    for entry in z_dir.iterdir():
        if not entry.is_dir():
            continue
        parsed = _parse_run_dir(entry.name)
        if not parsed:
            continue
        by_suite[parsed[1]].append(entry)

    keep: set[Path] = set()
    for _suite, runs in by_suite.items():
        with_report = [r for r in runs if (r / "brahl_report.md").is_file()]
        pool = with_report if with_report else runs
        pool_sorted = sorted(pool, key=lambda p: p.name)
        keep.update(pool_sorted[-keep_latest:])
    return keep


def collect_z_targets(z_dir: Path, keep_latest: int = 1) -> list[Path]:
    if not z_dir.is_dir():
        return []

    kept_dirs = select_kept_run_dirs(z_dir, keep_latest)
    kept_stamps = {p.name.split("_", 2)[0] + "_" + p.name.split("_", 2)[1] for p in kept_dirs}
    # full run folder names for matching flat brahl_* files
    kept_names = {p.name for p in kept_dirs}

    targets: list[Path] = []
    for entry in z_dir.iterdir():
        name = entry.name
        if name in Z_KEEP_NAMES:
            continue

        if entry.is_dir() and (_is_dated_run_dir(name) or name.startswith("20")):
            # Standard YYYYMMDD_HHMMSS_suite dirs, plus odd leftovers (e.g. 20260714_phaseb_…)
            if entry not in kept_dirs:
                targets.append(entry)
            continue

        if not entry.is_file():
            continue

        if name.startswith("brahl_report_") or name.startswith("brahl_context_"):
            # brahl_report_<ts>_<suite>.md  / brahl_context_<ts>_<suite>.json
            rest = name[len("brahl_report_") :] if name.startswith("brahl_report_") else name[len("brahl_context_") :]
            run_key = rest.rsplit(".", 1)[0]  # <ts>_<suite>
            if run_key in kept_names:
                continue
            targets.append(entry)
        elif name.startswith("zDash_batch"):
            targets.append(entry)
        elif name.endswith(".log") or name.startswith("_"):
            # probe / agent scratch logs (_ts_deep_latest.log, …)
            if name in Z_KEEP_NAMES:
                continue
            targets.append(entry)
        elif "_zResults" in name or "_zDash" in name:
            targets.append(entry)
        elif name == "_errors.csv":
            targets.append(entry)

    # silence unused (kept_stamps reserved for future flat-file heuristics)
    _ = kept_stamps
    return sorted(targets)


def collect_root_probes() -> list[Path]:
    found: list[Path] = []
    for pattern in ROOT_PROBE_GLOBS:
        found.extend(FOXYIZ_ROOT.glob(pattern))
        found.extend(KK_ROOT.glob(pattern))
    return sorted(p for p in found if p.is_file())


def collect_optional_docs(include_docs: bool) -> list[Path]:
    if not include_docs:
        return []
    return [p for p in DEPRECATED_DOCS if p.is_file()]


def collect_regenerated(include_viz: bool) -> list[Path]:
    if not include_viz:
        return []
    return [p for p in REGENERATED_ARTIFACTS if p.is_file()]


def collect_runtime_scratch() -> list[Path]:
    """One-off heal/conclusion fStarts under f/fStart/.runtime/ (not Arena run_* jobs)."""
    runtime = FOXYIZ_ROOT / "f" / "fStart" / ".runtime"
    if not runtime.is_dir():
        return []
    scratch_prefixes = (
        "thoughtstream_deep_heal",
        "thoughtstream_conclusion",
        "thoughtstream_ui",
        "a77_ui",
        "ultimate_showdown_ui",
    )
    out: list[Path] = []
    for entry in runtime.iterdir():
        if not entry.is_file():
            continue
        if any(entry.name.startswith(p) for p in scratch_prefixes):
            out.append(entry)
    return sorted(out)


def select_kept_ypad_versions(y_dir: Path, keep_versions: int) -> set[Path]:
    """Per suite, keep newest N folders under y/<suite>/versions/."""
    if keep_versions <= 0 or not y_dir.is_dir():
        return set()
    keep: set[Path] = set()
    for suite_dir in sorted(y_dir.iterdir()):
        if not suite_dir.is_dir():
            continue
        root = suite_dir / "versions"
        if not root.is_dir():
            continue
        snaps = sorted([p for p in root.iterdir() if p.is_dir()], key=lambda p: p.name)
        keep.update(snaps[-keep_versions:])
    return keep


def collect_ypad_version_targets(y_dir: Path, keep_versions: int) -> list[Path]:
    """Archive older immutable yPAD snapshots; live CSVs stay in y/<suite>/."""
    if not y_dir.is_dir():
        return []
    kept = select_kept_ypad_versions(y_dir, keep_versions)
    targets: list[Path] = []
    for suite_dir in sorted(y_dir.iterdir()):
        root = suite_dir / "versions"
        if not root.is_dir():
            continue
        for snap in sorted(root.iterdir()):
            if snap.is_dir() and snap not in kept:
                targets.append(snap)
    return targets


def archive_paths(paths: list[Path], dest: Path, dry_run: bool) -> list[str]:
    moved: list[str] = []
    for src in paths:
        rel = _rel(src)
        out = dest / rel
        if dry_run:
            moved.append(rel)
            continue
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(out))
        moved.append(rel)
    return moved


def purge_old_archives(days: int, dry_run: bool) -> list[str]:
    if not ARCHIVE_CLEANUP.is_dir():
        return []
    cutoff = datetime.now() - timedelta(days=days)
    removed: list[str] = []
    for child in sorted(ARCHIVE_CLEANUP.iterdir()):
        if not child.is_dir():
            continue
        try:
            mtime = datetime.fromtimestamp(child.stat().st_mtime)
        except OSError:
            continue
        if mtime >= cutoff:
            continue
        rel = _rel(child)
        if dry_run:
            removed.append(rel)
        else:
            shutil.rmtree(child)
            removed.append(rel)
    return removed


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Archive ephemeral z/ runs to <FXYZ>/archive/cleanup/ (outside KK)"
    )
    ap.add_argument("--apply", action="store_true", help="Move files (default is dry-run)")
    ap.add_argument("--docs", action="store_true", help="Also archive deprecated doc stubs")
    ap.add_argument("--viz", action="store_true", help="Also archive u/*.html utility reports")
    ap.add_argument(
        "--keep-latest",
        type=int,
        default=1,
        help="Per suite, keep newest N run dirs that have brahl_report.md (default 1; 0 = keep none)",
    )
    ap.add_argument(
        "--runtime-scratch",
        action="store_true",
        help="Also archive one-off f/fStart/.runtime/* heal/conclusion configs",
    )
    ap.add_argument(
        "--ypad-versions",
        action="store_true",
        help="Archive older y/<suite>/versions/* snapshots (keeps --keep-versions newest per suite)",
    )
    ap.add_argument(
        "--keep-versions",
        type=int,
        default=2,
        help="With --ypad-versions: keep newest N snapshots per suite (default 2)",
    )
    ap.add_argument(
        "--purge-archive",
        action="store_true",
        help="Delete <FXYZ>/archive/cleanup/* folders older than --purge-days (use with --apply)",
    )
    ap.add_argument("--purge-days", type=int, default=30, help="Age for --purge-archive (default 30)")
    args = ap.parse_args()
    dry_run = not args.apply

    targets: list[Path] = []
    targets.extend(collect_z_targets(Z_DIR, keep_latest=args.keep_latest))
    targets.extend(collect_root_probes())
    targets.extend(collect_optional_docs(args.docs))
    targets.extend(collect_regenerated(args.viz))
    if args.runtime_scratch:
        targets.extend(collect_runtime_scratch())
    if args.ypad_versions:
        targets.extend(collect_ypad_version_targets(Y_DIR, keep_versions=args.keep_versions))

    # de-dupe while preserving order
    seen: set[Path] = set()
    uniq: list[Path] = []
    for p in targets:
        if p in seen:
            continue
        seen.add(p)
        uniq.append(p)
    targets = uniq

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = ARCHIVE_CLEANUP / stamp

    mode = "DRY-RUN" if dry_run else "APPLY"
    print(f"[cleaner] {mode} — archive bucket: {_rel(dest)}")
    print(f"[cleaner] keep-latest={args.keep_latest}")
    if args.ypad_versions:
        print(f"[cleaner] ypad-versions keep-versions={args.keep_versions}")
    if args.keep_latest > 0:
        kept = select_kept_run_dirs(Z_DIR, args.keep_latest)
        if kept:
            print("[cleaner] Keeping z/ runs:")
            for p in sorted(kept, key=lambda x: x.name):
                print(f"  + {_rel(p)}")
    if args.ypad_versions and args.keep_versions > 0:
        kept_v = select_kept_ypad_versions(Y_DIR, args.keep_versions)
        if kept_v:
            print("[cleaner] Keeping yPAD versions:")
            for p in sorted(kept_v, key=lambda x: str(x)):
                print(f"  + {_rel(p)}")

    if not targets:
        print("[cleaner] Nothing to archive.")
    else:
        moved = archive_paths(targets, dest, dry_run)
        verb = "Would archive" if dry_run else "Archived"
        print(f"[cleaner] {verb} {len(moved)} item(s):")
        for rel in moved:
            print(f"  - {rel}")

    if args.purge_archive:
        purged = purge_old_archives(args.purge_days, dry_run)
        if purged:
            verb = "Would remove" if dry_run else "Removed"
            print(f"[cleaner] {verb} {len(purged)} old archive folder(s):")
            for rel in purged:
                print(f"  - {rel}")
        else:
            print("[cleaner] No old archive folders to purge.")

    if dry_run and targets:
        print("\nRun with --apply to move files. Delete ../archive/cleanup/ anytime to free disk.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
