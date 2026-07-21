#!/usr/bin/env python3
"""Rewrite qoa_web_live y3 URL hosts for production smoke.

Usage (from KK/):
  python qoa_web/scripts/patch_live_urls.py
  python qoa_web/scripts/patch_live_urls.py --base https://brahl.qaonair.com
  python qoa_web/scripts/patch_live_urls.py --base http://127.0.0.1:8765   # restore local
"""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

Y3 = Path(__file__).resolve().parents[2] / "FoXYiZ" / "y" / "qoa_web_live" / "y3Designs.csv"
URL_KEYS = {
    "profile_url",
    "signin_url",
    "fresh_url",
    "base_url",
    "arena_ai_on_url",
}
HOST_RE = re.compile(r"https?://[^/\"']+")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="https://brahl.qaonair.com")
    args = ap.parse_args()
    base = args.base.rstrip("/")
    rows = list(csv.DictReader(Y3.open(encoding="utf-8-sig", newline="")))
    fields = list(rows[0].keys())
    dcols = [c for c in fields if c in {f"D{i}" for i in range(1, 10)}]
    n = 0
    for r in rows:
        if r.get("DataName") not in URL_KEYS:
            continue
        for c in dcols:
            old = r.get(c) or ""
            if not old:
                continue
            new = HOST_RE.sub(base, old, count=1)
            if new != old:
                r[c] = new
                n += 1
    with Y3.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"[patch_live_urls] updated {n} cells → {base}")
    print("Run: python FoXYiZ/f/fEngine2.py --config f/fStart/qoa_web_live.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
