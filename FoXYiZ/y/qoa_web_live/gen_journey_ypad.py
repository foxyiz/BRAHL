#!/usr/bin/env python3
"""Deprecated location — use: python pyUtils/gen_journey_ypad.py (from KK/).

V2: retarget generator output to y/qoa_web_live before regenerating ~800 journeys.
"""
from __future__ import annotations

import runpy
import sys
from pathlib import Path

_script = Path(__file__).resolve().parents[2] / "pyUtils" / "gen_journey_ypad.py"
sys.path.insert(0, str(_script.parent))
runpy.run_path(str(_script), run_name="__main__")
