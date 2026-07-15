#!/usr/bin/env python3
"""
Patch yPAD and seed URLs for production deploy.

Usage:
  set APP_BASE_URL=https://demo.yourdomain.com
  python u/patch_ypad_urls.py
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from _paths import KK_ROOT, FOXYIZ_ROOT

LOCAL = "http://127.0.0.1:8765"


def main() -> None:
    base = os.environ.get("APP_BASE_URL", "").strip().rstrip("/")
    if not base:
        print("Set APP_BASE_URL (e.g. https://demo.yourdomain.com)")
        raise SystemExit(1)
    if base == LOCAL.rstrip("/"):
        print("APP_BASE_URL is still local — no patch needed")
        return

    targets = [
        FOXYIZ_ROOT / "y/qoa_web/y3Designs.csv",
        KK_ROOT / "qoa_web/data/projects.seed.json",
    ]
    proj = KK_ROOT / "qoa_web/data/projects.json"
    if proj.is_file():
        targets.append(proj)

    for path in targets:
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        new = text.replace(LOCAL, base).replace(LOCAL + "/", base + "/")
        if new != text:
            path.write_text(new, encoding="utf-8")
            print(f"Patched {path.relative_to(KK_ROOT)}")

    print(f"Done — base URL: {base}")


if __name__ == "__main__":
    main()
