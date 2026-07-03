# Building Executables with GitHub Actions

This project uses GitHub Actions to automatically build executables for Windows, macOS, and Linux.

## How It Works

The workflow (`.github/workflows/build-executables.yml`) automatically:
- Builds executables for **Windows**, **macOS**, and **Linux**
- Installs all dependencies including Chrome for Selenium
- Uses PyInstaller to create standalone executables
- Uploads build artifacts for download

## Triggering Builds

### Automatic Builds
The workflow runs automatically on:
- **Every push** to the `main` branch
- **Every pull request** to the `main` branch
- **Every tag** starting with `v` (e.g., `v1.0.0`)

### Manual Builds
You can manually trigger a build:
1. Go to your GitHub repository
2. Click on **Actions** tab
3. Select **Build Executables** workflow
4. Click **Run workflow** button
5. Select the branch and click **Run workflow**

## Downloading Built Executables

### From Workflow Runs
1. Go to the **Actions** tab in your GitHub repository
2. Click on a completed workflow run
3. Scroll down to **Artifacts** section
4. Download the executable for your platform:
   - `Foxyiz-windows` - Windows executable
   - `Foxyiz-macos` - macOS executable
   - `Foxyiz-linux` - Linux executable

### From Releases (Recommended)
When you create a version tag, executables are automatically attached to a GitHub Release:

1. Create a tag (e.g., `v1.0.0`):
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```

2. Go to the **Releases** section of your repository
3. Download the executable for your platform

## Creating a Release with Executables

To create a new release with built executables:

```bash
# Tag your commit
git tag -a v1.0.0 -m "Release version 1.0.0"

# Push the tag to GitHub
git push origin v1.0.0
```

The workflow will automatically:
1. Build executables for all platforms
2. Create a GitHub Release
3. Attach all executables to the release

## Build Artifacts

Each build produces:
- **Foxyiz-windows**: Windows executable (`.exe`)
- **Foxyiz-macos**: macOS executable (Unix executable)
- **Foxyiz-linux**: Linux executable (Unix executable)

All executables are standalone and include:
- Python runtime
- All dependencies (pandas, numpy, selenium, requests, urllib3)
- Required files from `x/`, `y/`, and `z/` directories

## Local Building (July2 workspace)

Build from the **installation root** (`July2/`), not from `f/`. Use **`fEngine2.py`** (current engine with semicolon tag matching) and **`x/xActions.py`** (timer fix applied).

```powershell
cd c:\00FoXYiZ\Apr_1\A15\July2

# 1. Install dependencies
pip install -r f\requirements.txt

# 2. Build Windows executable (run from July2 root)
pyinstaller --onefile ^
  --name Foxyiz2 ^
  --paths . ^
  --add-data "x\xActions.py;x" ^
  --add-data "z\zDash_template.html;z" ^
  --hidden-import pandas ^
  --hidden-import x.xActions ^
  --hidden-import numpy ^
  --hidden-import selenium ^
  --hidden-import requests ^
  --hidden-import urllib3 ^
  --hidden-import webdriver_manager ^
  --hidden-import dotenv ^
  --hidden-import multiprocessing.spawn ^
  f\fEngine2.py

# 3. Copy output next to existing config
copy dist\Foxyiz2.exe f\Foxyiz2.exe
```

**Run without rebuilding:** `python f\fEngine2.py` from `July2/` (uses live source; tags and fixes apply immediately).

**Why old `Foxyiz.exe` / shipped `Foxyiz2.exe` ignore tag fixes:** PyInstaller bundles Python source at build time. The exes still contain the old tag matcher (`full cell == tag`) until rebuilt from patched `fEngine2.py`.

**Dev vs shipped:**

| Run with | Admin tags | Notes |
|----------|------------|-------|
| `python f\fEngine2.py` | Works (15→7 plans after yPAD lean) | Use for day-to-day |
| `f\Foxyiz2.exe` (old build) | 0 plans | Rebuild required |
| `f\Foxyiz.exe` | 0 plans | Rebuild required |

## Local Building (original repo layout)

To build locally:

```bash
# Install dependencies
pip install -r requirements.txt

# Build executable (Unix: macOS/Linux)
pyinstaller --onefile --add-data "x/xActions.py:x" --add-data "y:y" --add-data "z/zDash_template.html:z" --hidden-import pandas --hidden-import x.xActions --hidden-import numpy --hidden-import selenium --hidden-import requests --hidden-import urllib3 --hidden-import requests.adapters --hidden-import requests.auth --hidden-import requests.cookies --hidden-import requests.exceptions --hidden-import requests.sessions --hidden-import requests.utils --hidden-import multiprocessing.spawn --hidden-import multiprocessing.semaphore_tracker --name Foxyiz f/fEngine.py

# Find executable in dist/ directory
```

Note: On Unix-based systems (macOS/Linux), use `:` as path separator. On Windows, use `;`:
```bash
# Windows
pyinstaller --onefile --add-data "x/xActions.py;x" --add-data "y;y" --add-data "z/zDash_template.html;z" --hidden-import pandas --hidden-import x.xActions --hidden-import numpy --hidden-import selenium --hidden-import requests --hidden-import urllib3 --hidden-import requests.adapters --hidden-import requests.auth --hidden-import requests.cookies --hidden-import requests.exceptions --hidden-import requests.sessions --hidden-import requests.utils --hidden-import multiprocessing.spawn --hidden-import multiprocessing.semaphore_tracker --name Foxyiz f/fEngine.py
```

## Troubleshooting

If builds fail:
1. Check the **Actions** tab for error logs
2. Ensure all dependencies are in `requirements.txt`
3. Verify the `x/` and `y/` directories exist in your repository
4. Check that `f/fEngine.py` exists in the repository

## Workflow Status

Check the current build status in the **Actions** tab of your GitHub repository.

