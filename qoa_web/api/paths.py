"""Repo roots for KK2 desktop BRAHL.

KK2/
  FoXYiZ/   ← f, x, y, z, pyUtils (engine)
  qoa_web/  ← slim Arena UI
  workspaces/ ← cloned / bound app-under-test repos
  Docs/
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

KK_ROOT = Path(__file__).resolve().parents[2]
FOXYIZ_ROOT = Path(os.environ.get("FOXYIZ_ROOT", str(KK_ROOT / "FoXYiZ"))).resolve()

F_DIR = FOXYIZ_ROOT / "f"
X_DIR = FOXYIZ_ROOT / "x"
Y_DIR = FOXYIZ_ROOT / "y"
Z_DIR = FOXYIZ_ROOT / "z"
PYUTILS_DIR = FOXYIZ_ROOT / "pyUtils"
# Run/Loop subprocess: prefer packaged exe (override with FOXYIZ_ENGINE).
ENGINE_EXE = F_DIR / "FoXYiZ.exe"
ENGINE_PY = F_DIR / "fEngine2.py"
ENGINE = ENGINE_EXE


def resolve_engine() -> Path:
    """Executable or script used to run suites. Env ``FOXYIZ_ENGINE`` wins."""
    override = (os.environ.get("FOXYIZ_ENGINE") or "").strip()
    if override:
        p = Path(override)
        if not p.is_absolute():
            p = (FOXYIZ_ROOT / p).resolve()
        return p
    if ENGINE_EXE.is_file():
        return ENGINE_EXE.resolve()
    return ENGINE_PY.resolve()


def engine_cmd(config_rel: str) -> list[str]:
    """Argv to run one fStart: ``FoXYiZ.exe --config …`` or ``python fEngine2.py …``."""
    eng = resolve_engine()
    if eng.suffix.lower() == ".py":
        return [sys.executable, str(eng), "--config", config_rel]
    return [str(eng), "--config", config_rel]

_FOXYIZ_TOPS = frozenset({"f", "x", "y", "z", "pyUtils", ".pyUtils"})


def resolve_repo(rel: str | Path) -> Path:
    """Map short engine paths (f/… y/… z/…) to FoXYiZ; everything else to KK2."""
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
        if top == ".pyUtils":
            s = "pyUtils" + s[len(".pyUtils") :]
        return (FOXYIZ_ROOT / s).resolve()
    return (KK_ROOT / s).resolve()


def repo_rel(path: Path) -> str:
    """Prefer FoXYiZ-relative short paths (z/run, f/…); else KK2-relative."""
    path = path.resolve()
    try:
        return path.relative_to(FOXYIZ_ROOT).as_posix()
    except ValueError:
        pass
    try:
        return path.relative_to(KK_ROOT).as_posix()
    except ValueError:
        return path.as_posix()
