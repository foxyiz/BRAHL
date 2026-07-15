#!/usr/bin/env python3
"""Run persona yPAD + sign-in profile sync. From KK/: python u/sync_personas.py"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

U_DIR = Path(__file__).resolve().parent
KK_ROOT = U_DIR.parent.parent  # KK (Docs/qoa_web live here)

SCRIPTS = ("gen_persona_ypad.py", "sync_profiles_from_docs.py")


def main() -> None:
    for name in SCRIPTS:
        path = U_DIR / name
        print(f"--- {name} ---")
        subprocess.check_call([sys.executable, str(path)], cwd=KK_ROOT)
    print("Persona sync complete.")


if __name__ == "__main__":
    main()
