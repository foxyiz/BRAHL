#!/usr/bin/env python3
"""
Build a slim demo deploy bundle for VPS hosting.

Usage (from KK/):
  python u/export_demo_bundle.py
  python u/export_demo_bundle.py --out ../brahl-demo-bundle.zip
"""

from __future__ import annotations

import argparse
import shutil
import zipfile
from datetime import datetime
from pathlib import Path

from _paths import KK_ROOT

INCLUDE_DIRS = (
    "qoa_web/api",
    "qoa_web/web",
    "qoa_web/data",
    "qoa_web/mcp",
    "qoa_web/deploy",
    "y/qoa_web",
    "f",
    "x",
    "z",
    "Docs/test-user-data",
    "Docs",
    "u",
)

INCLUDE_FILES = (
    "Summary.md",
    "qoa_web/run_local.py",
    "qoa_web/Dockerfile",
    "qoa_web/DEPLOY.md",
    "qoa_web/DEMO_SCRIPT.md",
    "qoa_web/README.md",
)

EXCLUDE_DIR_NAMES = frozenset(
    {
        "__pycache__",
        ".git",
        "archive",
        "node_modules",
        ".venv",
        "venv",
    }
)

EXCLUDE_GLOBS = (
    "z/2026*",
    "z/2025*",
    "z/brahl_*",
    "f/Foxyiz2.exe",
    "qoa_web/data/projects.json",
)

SKIP_Y_SUITES = frozenset({"qoa2", "sunshine", "ivvu", "atomic77"})


def _should_skip(path: Path) -> bool:
    rel = path.relative_to(KK_ROOT).as_posix()
    for part in path.parts:
        if part in EXCLUDE_DIR_NAMES:
            return True
    if rel.startswith("y/"):
        suite = rel.split("/")[1] if len(rel.split("/")) > 1 else ""
        if suite in SKIP_Y_SUITES:
            return True
    for pat in EXCLUDE_GLOBS:
        if pat.endswith("*"):
            if rel.startswith(pat[:-1]):
                return True
        elif rel == pat:
            return True
    if rel == "Docs/QoA_Comps.md":
        return True
    return False


def _copy_tree(src: Path, dst: Path) -> int:
    count = 0
    if not src.exists():
        return 0
    if src.is_file():
        if _should_skip(src):
            return 0
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        return 1
    for item in src.rglob("*"):
        if item.is_dir():
            continue
        rel = item.relative_to(KK_ROOT)
        if _should_skip(item):
            continue
        target = dst / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item, target)
        count += 1
    return count


def export_bundle(out_dir: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    bundle_root = out_dir / f"brahl-demo-{stamp}"
    if bundle_root.exists():
        shutil.rmtree(bundle_root)
    bundle_root.mkdir(parents=True)
    files = 0
    for d in INCLUDE_DIRS:
        files += _copy_tree(KK_ROOT / d, bundle_root)
    for f in INCLUDE_FILES:
        src = KK_ROOT / f
        if src.is_file() and not _should_skip(src):
            rel = Path(f)
            dest = bundle_root / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            files += 1
    # Seed projects.json for fresh deploy
    seed = KK_ROOT / "qoa_web/data/projects.seed.json"
    if seed.is_file():
        dest = bundle_root / "qoa_web/data/projects.json"
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(seed, dest)
        files += 1
    wl = KK_ROOT / "qoa_web/data/waitlist.json"
    if wl.is_file():
        shutil.copy2(wl, bundle_root / "qoa_web/data/waitlist.json")
    readme = bundle_root / "BUNDLE_README.txt"
    readme.write_text(
        "BRAHL Web demo bundle\n"
        "1. Set APP_BASE_URL and run: python u/patch_ypad_urls.py\n"
        "2. docker build -t brahl-web -f qoa_web/Dockerfile .\n"
        "3. See qoa_web/DEPLOY.md and qoa_web/DEMO_SCRIPT.md\n",
        encoding="utf-8",
    )
    print(f"[export] Wrote {files} files -> {bundle_root}")
    return bundle_root


def zip_bundle(bundle_root: Path, zip_path: Path) -> None:
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in bundle_root.rglob("*"):
            if f.is_file():
                zf.write(f, f.relative_to(bundle_root.parent))
    print(f"[export] Zip -> {zip_path}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Export slim BRAHL demo bundle")
    ap.add_argument("--out", type=Path, default=KK_ROOT / "archive" / "demo-bundle")
    ap.add_argument("--zip", action="store_true", help="Also create .zip alongside folder")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    bundle = export_bundle(args.out)
    if args.zip:
        zip_bundle(bundle, args.out / f"{bundle.name}.zip")


if __name__ == "__main__":
    main()
