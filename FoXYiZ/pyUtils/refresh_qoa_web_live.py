#!/usr/bin/env python3
"""Re-BRAHL qoa_web_live: V1 verify patches + journey library regen.

From KK/:
  python FoXYiZ/pyUtils/refresh_qoa_web_live.py
  python FoXYiZ/pyUtils/refresh_qoa_web_live.py --target 300
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

PYUTILS = Path(__file__).resolve().parent
KK_ROOT = PYUTILS.parent.parent


def run(script: str, *args: str) -> None:
    cmd = [sys.executable, str(PYUTILS / script), *args]
    print(f"\n>> {' '.join(cmd)}")
    subprocess.run(cmd, cwd=str(KK_ROOT), check=True)


def main() -> None:
    ap = argparse.ArgumentParser(description="Refresh qoa_web_live yPAD (V1 + journey)")
    ap.add_argument("--target", type=int, default=300, help="Journey plan count (150–500)")
    ap.add_argument("--skip-patch", action="store_true", help="Skip patch_qoa_web_live_v1.py")
    ap.add_argument("--skip-journey", action="store_true", help="Skip journey regeneration")
    args = ap.parse_args()

    if not args.skip_patch:
        run("patch_qoa_web_live_v1.py")
    if not args.skip_journey:
        run("gen_journey_ypad.py", "--suite", "qoa_web_live", "--target", str(args.target))

    print("\nDone. Smoke:")
    print("  python qoa_web/run_local.py")
    print("  python FoXYiZ\\f\\fEngine2.py --config f/fStart/qoa_web_live_smoke_headless.json")
    print("  python FoXYiZ\\f\\fEngine2.py --config f/fStart/qoa_web_live_journey_nav.json")


if __name__ == "__main__":
    main()
