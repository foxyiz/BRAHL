#!/usr/bin/env python3
"""Backup qoa_web/data (projects, users, schedules, uploads) for production.

Usage (from KK/):
  python qoa_web/scripts/backup_data.py
  python qoa_web/scripts/backup_data.py --dest D:/backups/brahl
"""

from __future__ import annotations

import argparse
import shutil
from datetime import datetime
from pathlib import Path

KK = Path(__file__).resolve().parents[2]
DATA = KK / "qoa_web" / "data"
DEFAULT_DEST = KK / "archive" / "backups"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dest", type=Path, default=DEFAULT_DEST)
    args = ap.parse_args()
    if not DATA.is_dir():
        print(f"[backup] missing {DATA}")
        return 1
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = args.dest / f"qoa_web_data_{stamp}"
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(
        DATA,
        out,
        ignore=shutil.ignore_patterns("*.pyc", "__pycache__", "*.tmp"),
    )
    print(f"[backup] wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
