#!/usr/bin/env python3
"""
Archive ephemeral KK artifacts to archive/cleanup/<timestamp>/.

Keeps the working tree small for humans and AI context. Safe to delete the entire
archive/cleanup/ folder when you need disk space.

Does NOT modify f/fEngine2.py, x/xActions.py, or any engine/action code.

Usage (from KK/):
  python u/cleaner.py              # dry-run — list what would move
  python u/cleaner.py --apply      # move files into archive/cleanup/
  python u/cleaner.py --apply --purge-archive   # also delete archive/cleanup/* older than 30 days
"""

from __future__ import annotations

import argparse
import re
import shutil
from datetime import datetime, timedelta
from pathlib import Path

from _paths import ARCHIVE_CLEANUP, FOXYIZ_ROOT, KK_ROOT, Y_VISUALIZATION_HTML, Z_DEFECTS_DASHBOARD_HTML, Z_DIR

# Files/dirs under z/ that are kept in place (engine templates, thin wrappers)
Z_KEEP_NAMES = frozenset(
    {
        ".gitkeep",
        "zDash_template.html",
        "zDefects.py",
    }
)

# Optional: deprecated doc stubs (removed in v1.3 — kept empty)
DEPRECATED_DOCS: tuple[Path, ...] = ()

# Regenerated HTML reports from u/ (optional --viz archives these)
REGENERATED_ARTIFACTS = (Y_VISUALIZATION_HTML, Z_DEFECTS_DASHBOARD_HTML)

# Root-level probe leftovers
ROOT_PROBE_GLOBS = ("*_probe.json", "*_probe.py")


def _rel(path: Path) -> str:
    try:
        try:
            return str(path.relative_to(FOXYIZ_ROOT)).replace("\\", "/")
        except ValueError:
            return str(path.relative_to(KK_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def _is_dated_run_dir(name: str) -> bool:
    return bool(re.match(r"^20\d{2}\d{4}_", name)) or name.startswith(("2025", "2026"))


def collect_z_targets(z_dir: Path) -> list[Path]:
    if not z_dir.is_dir():
        return []
    targets: list[Path] = []
    for entry in z_dir.iterdir():
        name = entry.name
        if name in Z_KEEP_NAMES:
            continue
        if entry.is_file():
            if name.startswith("brahl_"):
                targets.append(entry)
            elif "_zResults" in name or "_zDash" in name:
                targets.append(entry)
            elif name == "_errors.csv":
                targets.append(entry)
        elif entry.is_dir() and _is_dated_run_dir(name):
            targets.append(entry)
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
    ap = argparse.ArgumentParser(description="Archive ephemeral KK files to archive/cleanup/")
    ap.add_argument("--apply", action="store_true", help="Move files (default is dry-run)")
    ap.add_argument("--docs", action="store_true", help="Also archive deprecated doc stubs")
    ap.add_argument("--viz", action="store_true", help="Also archive u/*.html utility reports")
    ap.add_argument(
        "--purge-archive",
        action="store_true",
        help="Delete archive/cleanup/* folders older than --purge-days (use with --apply)",
    )
    ap.add_argument("--purge-days", type=int, default=30, help="Age for --purge-archive (default 30)")
    args = ap.parse_args()
    dry_run = not args.apply

    targets: list[Path] = []
    targets.extend(collect_z_targets(Z_DIR))
    targets.extend(collect_root_probes())
    targets.extend(collect_optional_docs(args.docs))
    targets.extend(collect_regenerated(args.viz))

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = ARCHIVE_CLEANUP / stamp

    mode = "DRY-RUN" if dry_run else "APPLY"
    print(f"[cleaner] {mode} — archive bucket: {_rel(dest)}")

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
        print("\nRun with --apply to move files. Delete archive/cleanup/ anytime to free disk.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
