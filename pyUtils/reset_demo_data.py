#!/usr/bin/env python3
"""Reset qoa_web demo workspace to seed (fixes verify state after join/submit tests)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from _paths import KK_ROOT

SEED = KK_ROOT / "qoa_web/data/projects.seed.json"
NALANDA_PROJECT_SEED = KK_ROOT / "qoa_web/data/nalanda_launch.seed.json"
TARGET = KK_ROOT / "qoa_web/data/projects.json"
NALANDA_SEED = KK_ROOT / "qoa_web/data/nalanda.seed.json"
NALANDA_TARGET = KK_ROOT / "qoa_web/data/nalanda.json"


def _load_project_seeds() -> list[dict]:
    projects: list[dict] = []
    if SEED.is_file():
        data = json.loads(SEED.read_text(encoding="utf-8-sig"))
        if isinstance(data, list):
            projects.extend(data)
        else:
            projects.append(data)
    if NALANDA_PROJECT_SEED.is_file():
        extra = json.loads(NALANDA_PROJECT_SEED.read_text(encoding="utf-8-sig"))
        if isinstance(extra, dict):
            projects.append(extra)
    return projects


def main() -> None:
    projects = _load_project_seeds()
    if not projects:
        raise SystemExit(f"Missing seed: {SEED}")
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(json.dumps(projects, indent=2), encoding="utf-8")
    print(f"Reset {TARGET.relative_to(KK_ROOT)} ({len(projects)} project(s))")
    if NALANDA_SEED.is_file():
        shutil.copy2(NALANDA_SEED, NALANDA_TARGET)
        print(f"Reset {NALANDA_TARGET.relative_to(KK_ROOT)} from seed")


if __name__ == "__main__":
    main()
