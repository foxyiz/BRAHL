#!/usr/bin/env python3
"""Deprecated location — use: python u/sync_profiles_from_docs.py (from KK/)."""
from __future__ import annotations

import runpy
import sys
from pathlib import Path

_script = Path(__file__).resolve().parents[2] / "u" / "sync_profiles_from_docs.py"
sys.path.insert(0, str(_script.parent))
runpy.run_path(str(_script), run_name="__main__")
