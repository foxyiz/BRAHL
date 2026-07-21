# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec — build FoXYiZ.exe from fEngine2 + xActions + runtime pyUtils.
# Run from KK/:  powershell -File FoXYiZ\packaging\build_exe.ps1

from pathlib import Path

from PyInstaller.building.api import COLLECT, EXE, PYZ
from PyInstaller.building.build_main import Analysis
from PyInstaller.utils.hooks import collect_all, collect_submodules

SPECDIR = Path(SPECPATH).resolve()
FOXYIZ = SPECDIR.parent
ROOT = FOXYIZ  # FoXYiZ/

datas = [
    (str(FOXYIZ / "x" / "xActions.py"), "x"),
    (str(FOXYIZ / "x" / "xCapa.csv"), "x"),
    (str(FOXYIZ / "pyUtils" / "xCustom.py"), "pyUtils"),
    (str(FOXYIZ / "pyUtils" / "fOrchestrate.py"), "pyUtils"),
    (str(FOXYIZ / "pyUtils" / "zBatchDash.py"), "pyUtils"),
    (str(FOXYIZ / "pyUtils" / "_paths.py"), "pyUtils"),
]

binaries = []
hiddenimports = [
    "xActions",
    "xCustom",
    "fOrchestrate",
    "zBatchDash",
    "_paths",
    "pandas",
    "openpyxl",
    "dotenv",
    "requests",
    "selenium",
    "selenium.webdriver",
    "selenium.webdriver.chrome",
    "selenium.webdriver.chrome.service",
    "selenium.webdriver.chrome.options",
    "selenium.webdriver.common.by",
    "selenium.webdriver.support.ui",
    "selenium.webdriver.support.expected_conditions",
    "webdriver_manager",
    "webdriver_manager.chrome",
]

for pkg in ("selenium", "webdriver_manager", "certifi"):
    try:
        pkg_datas, pkg_binaries, pkg_hidden = collect_all(pkg)
        datas += pkg_datas
        binaries += pkg_binaries
        hiddenimports += pkg_hidden
    except Exception:
        hiddenimports += collect_submodules(pkg)

a = Analysis(
    [str(FOXYIZ / "f" / "fEngine2.py")],
    pathex=[str(FOXYIZ), str(FOXYIZ / "x"), str(FOXYIZ / "pyUtils")],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "scipy", "PIL", "IPython", "notebook"],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="FoXYiZ",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="FoXYiZ",
)
