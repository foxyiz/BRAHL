# Build FoXYiZ.exe (onedir) and assemble a self-contained end-user package.
# Run from anywhere:
#   powershell -ExecutionPolicy Bypass -File FoXYiZ\packaging\build_exe.ps1
#
# Package layout (dist/FoXYiZ_user):
#   f/FoXYiZ.exe + f/_internal/   engine (onedir — both required)
#   f/fStart/                     run configs
#   x/xCapa.csv                   action capability catalog (reference)
#   y/<suite>/                    editable yPAD
#   z/                            results
#   Docs/                         BRAHL + terminology + how-to

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
  (Join-Path $UserDist "Docs")
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

# Package docs (self-contained — no KK/Docs required at runtime)
Copy-Item (Join-Path $DocsSrc "BRAHL.md") (Join-Path $UserDist "Docs\BRAHL.md") -Force
Copy-Item (Join-Path $DocsSrc "terminology.md") (Join-Path $UserDist "Docs\terminology.md") -Force
Copy-Item (Join-Path $DocsSrc "DISTRIBUTION.md") (Join-Path $UserDist "Docs\DISTRIBUTION.md") -Force
Copy-Item (Join-Path $DocsSrc "USER_GUIDE.md") (Join-Path $UserDist "Docs\USER_GUIDE.md") -Force
Copy-Item (Join-Path $Packaging "README.md") (Join-Path $UserDist "Docs\PACKAGING.md") -Force

$readme = @"
FoXYiZ — end-user package
=========================

Formula:  f(x, y) = z

Quick start (from this folder):
  .\f\FoXYiZ.exe --config f\fStart\Math.json

Or double-click / bare run (uses f\fStart\default.json -> Math Smoke):
  .\f\FoXYiZ.exe

Layout:
  f\FoXYiZ.exe      engine bootloader
  f\_internal\      REQUIRED runtime libs (do not delete / move alone)
  f\fStart\         run configs (JSON) — edit these
  x\xCapa.csv       action catalog — what you can put in y2Actions
  y\<suite>\        yPAD plans / actions / designs (CSV) — edit these
  z\                run results (created automatically)
  Docs\             BRAHL, terminology, distribution notes

IMPORTANT: FoXYiZ.exe will NOT run without f\_internal\ beside it.
Ship the whole FoXYiZ_user folder (or zip it). Never ship the .exe alone.

Read next: Docs\USER_GUIDE.md · Docs\BRAHL.md · Docs\DISTRIBUTION.md
"@
Set-Content -Path (Join-Path $UserDist "README.txt") -Value $readme -Encoding UTF8

$size = [math]::Round(((Get-ChildItem $UserDist -Recurse -File | Measure-Object Length -Sum).Sum) / 1MB, 1)
Write-Host ""
Write-Host "DONE: $UserDist"
Write-Host "Size: ~${size} MB"
Write-Host "Smoke:  & `"$UserDist\f\FoXYiZ.exe`" --config f\fStart\Math.json"
