# Build FoXYiZ.exe (onedir) and assemble a self-contained end-user package.
# Run from anywhere:
#   powershell -ExecutionPolicy Bypass -File FoXYiZ\packaging\build_exe.ps1
#
# Package layout (dist/FoXYiZ_user):
#   f/FoXYiZ.exe + f/_internal/   engine (onedir — both required)
#   f/fStart/                     run configs
#   x/xCapa.csv                   action capability catalog (reference)
#   y/<suite>/                    editable yPAD
#   z/                            results (+ per-run zlogs.txt)
#   _pyUtils/                     BRAHL helpers (Python required)
#   _Docs/                        BRAHL · FoXYiZ · QAonAir (+ _deprecated/)

$ErrorActionPreference = "Stop"
$Packaging = Split-Path -Parent $MyInvocation.MyCommand.Path
$FoXYiZ = Split-Path -Parent $Packaging
$KK = Split-Path -Parent $FoXYiZ
$Work = Join-Path $Packaging "_build"
$DistOut = Join-Path $Packaging "dist"
$UserDist = Join-Path $DistOut "FoXYiZ_user"
$DocsSrc = Join-Path $Packaging "Docs"

Set-Location $KK
Write-Host "KK root: $KK"
Write-Host "Building FoXYiZ.exe (PyInstaller onedir)..."

if (Test-Path $Work) { Remove-Item $Work -Recurse -Force }
New-Item -ItemType Directory -Path $Work | Out-Null

python -m PyInstaller `
  --noconfirm `
  --clean `
  --distpath (Join-Path $Work "dist") `
  --workpath (Join-Path $Work "work") `
  (Join-Path $Packaging "FoXYiZ.spec")

$Built = Join-Path $Work "dist\FoXYiZ"
if (-not (Test-Path (Join-Path $Built "FoXYiZ.exe"))) {
  throw "Build failed: FoXYiZ.exe not found under $Built"
}

Write-Host "Assembling end-user dist at $UserDist ..."
if (Test-Path $UserDist) { Remove-Item $UserDist -Recurse -Force }

# Package root folders
foreach ($d in @(
  $UserDist,
  (Join-Path $UserDist "f"),
  (Join-Path $UserDist "f\fStart"),
  (Join-Path $UserDist "x"),
  (Join-Path $UserDist "y\Math"),
  (Join-Path $UserDist "z"),
  (Join-Path $UserDist "_pyUtils"),
  (Join-Path $UserDist "_Docs"),
  (Join-Path $UserDist "_Docs\_deprecated")
)) {
  New-Item -ItemType Directory -Path $d -Force | Out-Null
}

# Engine: FoXYiZ.exe + _internal MUST live together under f/
Copy-Item -Path (Join-Path $Built "*") -Destination (Join-Path $UserDist "f") -Recurse -Force

# fStart only under f/fStart (canonical)
Copy-Item (Join-Path $FoXYiZ "f\fStart\Math.json") (Join-Path $UserDist "f\fStart\Math.json") -Force
$default = @{
  configs      = @("y/Math/Math.json")
  thread_count = 1
  timeout      = 6
  headless     = $true
  debug        = $false
  tags         = @("Smoke")
  capture      = @{ image = "on_fail"; video = "off"; video_fps = 2; subdir = "" }
} | ConvertTo-Json -Depth 5
Set-Content -Path (Join-Path $UserDist "f\fStart\default.json") -Value $default -Encoding UTF8

# x capability catalog (reference for authoring y2Actions)
Copy-Item (Join-Path $FoXYiZ "x\xCapa.csv") (Join-Path $UserDist "x\xCapa.csv") -Force
Copy-Item (Join-Path $DocsSrc "x_README.md") (Join-Path $UserDist "x\README.md") -Force

# Sample yPAD suite
Copy-Item (Join-Path $FoXYiZ "y\Math\Math.json") (Join-Path $UserDist "y\Math\Math.json") -Force
Copy-Item (Join-Path $FoXYiZ "y\Math\y1Plans.csv") (Join-Path $UserDist "y\Math\y1Plans.csv") -Force
Copy-Item (Join-Path $FoXYiZ "y\Math\y2Actions.csv") (Join-Path $UserDist "y\Math\y2Actions.csv") -Force
Copy-Item (Join-Path $FoXYiZ "y\Math\y3Designs.csv") (Join-Path $UserDist "y\Math\y3Designs.csv") -Force

# _pyUtils — BRAHL post-run helpers only (no fEngine2 / xActions source).
$pyUtilsSrc = Join-Path $FoXYiZ "pyUtils"
$pyUtilsDst = Join-Path $UserDist "_pyUtils"
$pyUtilsShip = @(
  "_paths.py",
  "cleaner.py",
  "yVisualizer.py",
  "zDefects.py",
  "zBatchDash.py"
)
foreach ($script in $pyUtilsShip) {
  $src = Join-Path $pyUtilsSrc $script
  if (Test-Path $src) {
    Copy-Item $src (Join-Path $pyUtilsDst $script) -Force
  }
}
$pyUtilsReadme = @"
# _pyUtils (packaged)

The only **editable Python** in this distributable. Run uses ``f\FoXYiZ.exe``.

Docs: ``_Docs\FoXYiZ.md`` · ``_Docs\BRAHL.md`` · ``_Docs\QAonAir.md``

``````powershell
python _pyUtils\cleaner.py
python _pyUtils\yVisualizer.py
python _pyUtils\zDefects.py
python _pyUtils\zBatchDash.py --name mybatch --since 20260721
``````
"@
Set-Content -Path (Join-Path $pyUtilsDst "README.md") -Value $pyUtilsReadme -Encoding UTF8

# Seed empty flat zlogs index (engine appends on each run)
Set-Content -Path (Join-Path $UserDist "z\zlogs.txt") -Value "# FoXYiZ zlogs index — one line per suite run`r`n" -Encoding UTF8

# _Docs — primary project docs only (BRAHL · FoXYiZ · QAonAir)
$docsDst = Join-Path $UserDist "_Docs"
foreach ($doc in @("README.md", "BRAHL.md", "FoXYiZ.md", "QAonAir.md")) {
  Copy-Item (Join-Path $DocsSrc $doc) (Join-Path $docsDst $doc) -Force
}
$depSrc = Join-Path $DocsSrc "_deprecated"
$depDst = Join-Path $docsDst "_deprecated"
if (Test-Path $depSrc) {
  Copy-Item (Join-Path $depSrc "*") $depDst -Force
}

$readme = @"
FoXYiZ — end-user package
=========================

Formula:  f(x, y) = z

Quick start (from this folder):
  .\f\FoXYiZ.exe --config f\fStart\Math.json

Or bare run (f\fStart\default.json -> Math Smoke):
  .\f\FoXYiZ.exe

Layout:
  f\FoXYiZ.exe + f\_internal\   engine (both required)
  f\fStart\                     run configs
  x\xCapa.csv                   action catalog
  y\<suite>\                    yPAD suites
  z\                            results + zlogs
  _pyUtils\                     Analyze helpers (optional Python)
  _Docs\                        BRAHL · FoXYiZ · QAonAir

Docs (primary):
  _Docs\README.md     index + skill map
  _Docs\BRAHL.md      lifecycle skill
  _Docs\FoXYiZ.md     engine / package skill
  _Docs\QAonAir.md    marketplace / Arena skill

Deprecated generics: _Docs\_deprecated\ (do not extend).

IMPORTANT: Never ship FoXYiZ.exe without f\_internal\.
"@
Set-Content -Path (Join-Path $UserDist "README.txt") -Value $readme -Encoding UTF8

$size = [math]::Round(((Get-ChildItem $UserDist -Recurse -File | Measure-Object Length -Sum).Sum) / 1MB, 1)
Write-Host ""
Write-Host "DONE: $UserDist"
Write-Host "Size: ~${size} MB"
Write-Host "Smoke:  & `"$UserDist\f\FoXYiZ.exe`" --config f\fStart\Math.json"
