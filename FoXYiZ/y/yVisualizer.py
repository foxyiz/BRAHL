#!/usr/bin/env python3
"""Deprecated location — use: python u/yVisualizer.py (from KK/)."""
from __future__ import annotations

import runpy
import sys
from pathlib import Path

_script = Path(__file__).resolve().parents[1] / "u" / "yVisualizer.py"
runpy.run_path(str(_script), run_name="__main__")
