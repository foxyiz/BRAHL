#!/usr/bin/env python3
"""Start qoa_web local server on http://127.0.0.1:8765"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
API_DIR = ROOT / "api"


def main() -> None:
    try:
        import uvicorn  # noqa: F401
    except ImportError:
        print("Installing qoa_web API dependencies…")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "-q", "-r", str(API_DIR / "requirements.txt")]
        )
    sys.path.insert(0, str(API_DIR))
    import uvicorn

    print("BRAHL Web — http://127.0.0.1:8765")
    print("API health — http://127.0.0.1:8765/api/health")
    uvicorn.run("main:app", host="127.0.0.1", port=8765, reload=False, app_dir=str(API_DIR))


if __name__ == "__main__":
    main()
