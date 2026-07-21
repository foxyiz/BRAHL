# Build FoXYiZ.exe (onedir) and assemble an end-user folder.
# Run from anywhere:
#   powershell -ExecutionPolicy Bypass -File FoXYiZ\packaging\build_exe.ps1

$ErrorActionPreference = "Stop"
$Packaging = Split-Path -Parent $MyInvocation.MyCommand.Path
$FoXYiZ = Split-Path -Parent $Packaging
$KK = Split-Path -Parent $FoXYiZ
$Work = Join-Path $Packaging "_build"
$DistOut = Join-Path $Packaging "dist"
$UserDist = Join-Path $DistOut "FoXYiZ_user"

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
New-Item -ItemType Directory -Path $UserDist | Out-Null

# Engine binaries (_internal + FoXYiZ.exe)
Copy-Item -Path (Join-Path $Built "*") -Destination $UserDist -Recurse -Force

# Note: on Windows, Foxyiz.exe == FoXYiZ.exe (case-insensitive FS). fGUI looks for FoXYiZ.exe first.

# Editable configs + sample suite (not frozen into the exe)
New-Item -ItemType Directory -Path (Join-Path $UserDist "fStart") -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $UserDist "f") -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $UserDist "y\Math") -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $UserDist "z") -Force | Out-Null

Copy-Item (Join-Path $FoXYiZ "f\fStart\Math.json") (Join-Path $UserDist "fStart\Math.json") -Force
# default → Math so double-click / bare run works for end users
$default = @{
  configs      = @("y/Math/Math.json")
  thread_count = 1
  timeout      = 6
  headless     = $true
  debug        = $false
  tags         = @("Smoke")
  capture      = @{ image = "on_fail"; video = "off"; video_fps = 2; subdir = "" }
} | ConvertTo-Json -Depth 5
Set-Content -Path (Join-Path $UserDist "fStart\default.json") -Value $default -Encoding UTF8
# Also mirror under f/fStart for paths that still use that layout
New-Item -ItemType Directory -Path (Join-Path $UserDist "f\fStart") -Force | Out-Null
Copy-Item (Join-Path $UserDist "fStart\Math.json") (Join-Path $UserDist "f\fStart\Math.json") -Force
Copy-Item (Join-Path $UserDist "fStart\default.json") (Join-Path $UserDist "f\fStart\default.json") -Force

Copy-Item (Join-Path $FoXYiZ "y\Math\Math.json") (Join-Path $UserDist "y\Math\Math.json") -Force
Copy-Item (Join-Path $FoXYiZ "y\Math\y1Plans.csv") (Join-Path $UserDist "y\Math\y1Plans.csv") -Force
Copy-Item (Join-Path $FoXYiZ "y\Math\y2Actions.csv") (Join-Path $UserDist "y\Math\y2Actions.csv") -Force
Copy-Item (Join-Path $FoXYiZ "y\Math\y3Designs.csv") (Join-Path $UserDist "y\Math\y3Designs.csv") -Force

$readme = @"
FoXYiZ — end-user package
=========================

Run a suite:
  FoXYiZ.exe --config fStart\Math.json

Or (uses fStart\default.json → Math Smoke):
  FoXYiZ.exe

Layout (edit these; do not need Python):
  FoXYiZ.exe / Foxyiz.exe   engine (Windows: same file name, case-insensitive)
  _internal\                runtime libs (do not edit)
  fStart\                   run configs (JSON)
  y\<suite>\                plans / actions / designs (CSV)
  z\                        run results (created automatically)
  f\                        orchestrator temp configs

Add another suite: copy a y\<name>\ folder and point fStart at y/<name>/<name>.json.

Architects who need full source: use the KK/FoXYiZ tree (python f\fEngine2.py).
"@
Set-Content -Path (Join-Path $UserDist "README.txt") -Value $readme -Encoding UTF8

$size = [math]::Round(((Get-ChildItem $UserDist -Recurse -File | Measure-Object Length -Sum).Sum) / 1MB, 1)
Write-Host ""
Write-Host "DONE: $UserDist"
Write-Host "Size: ~${size} MB"
Write-Host "Smoke:  & `"$UserDist\FoXYiZ.exe`" --config fStart\Math.json"
