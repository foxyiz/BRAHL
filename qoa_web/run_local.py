#!/usr/bin/env python3
"""Start KK2 desktop BRAHL on http://127.0.0.1:8766"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
API_DIR = ROOT / "api"
PORT = int(os.environ.get("QOA_PORT", "8766"))


def main() -> None:
    os.environ.setdefault("QOA_DESKTOP", "1")
    try:
        import uvicorn  # noqa: F401
    except ImportError:
        print("Installing qoa_web API dependencies…")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "-q", "-r", str(API_DIR / "requirements.txt")]
        )
    sys.path.insert(0, str(API_DIR))
    import uvicorn

    print(f"KK2 BRAHL Desktop — http://127.0.0.1:{PORT}")
    print(f"API health — http://127.0.0.1:{PORT}/api/health")
    uvicorn.run("main:app", host="127.0.0.1", port=PORT, reload=False, app_dir=str(API_DIR))


if __name__ == "__main__":
    main()
