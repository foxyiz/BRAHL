"""Repo roots after FoXYiZ fold-in.

KK/
  FoXYiZ/   ← f, x, y, z, pyUtils (engine)
  qoa_web/  ← web UI
  Docs/
  archive/  ← excluded from agent context
"""

from __future__ import annotations

import os
from pathlib import Path

KK_ROOT = Path(__file__).resolve().parents[2]
FOXYIZ_ROOT = Path(os.environ.get("FOXYIZ_ROOT", str(KK_ROOT / "FoXYiZ"))).resolve()

F_DIR = FOXYIZ_ROOT / "f"
X_DIR = FOXYIZ_ROOT / "x"
Y_DIR = FOXYIZ_ROOT / "y"
Z_DIR = FOXYIZ_ROOT / "z"
PYUTILS_DIR = FOXYIZ_ROOT / "pyUtils"
ENGINE = F_DIR / "fEngine2.py"

_FOXYIZ_TOPS = frozenset({"f", "x", "y", "z", "pyUtils", ".pyUtils"})


def resolve_repo(rel: str | Path) -> Path:
    """Map short engine paths (f/… y/… z/…) to FoXYiZ; everything else to KK."""
    if isinstance(rel, Path):
        p = rel
        if p.is_absolute():
            return p
        rel = p.as_posix()
    s = str(rel).replace("\\", "/").lstrip("./")
    if not s:
        return FOXYIZ_ROOT
    top = s.split("/", 1)[0]
    if top == "FoXYiZ":
        return (KK_ROOT / s).resolve()
    if top in _FOXYIZ_TOPS:
        # legacy .pyUtils → pyUtils
        if top == ".pyUtils":
            s = "pyUtils" + s[len(".pyUtils") :]
        return (FOXYIZ_ROOT / s).resolve()
    return (KK_ROOT / s).resolve()


def repo_rel(path: Path) -> str:
    """Prefer FoXYiZ-relative short paths (z/run, f/…); else KK-relative."""
    path = path.resolve()
    try:
        return path.relative_to(FOXYIZ_ROOT).as_posix()
    except ValueError:
        pass
    try:
        return path.relative_to(KK_ROOT).as_posix()
    except ValueError:
        return path.as_posix()
