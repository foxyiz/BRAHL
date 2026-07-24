"""Author a FoXYiZ site_shots yPAD: one plan per same-origin page + xCaptureImage.

Examples (from KK/):

  # Known ThoughtStream / ThoughtCapture public routes (default)
  python FoXYiZ/pyUtils/site_shot_author.py --base https://jusdone.base44.app/ --suite site_shots

  # Live BFS of same-origin <a href>
  python FoXYiZ/pyUtils/site_shot_author.py --base https://jusdone.base44.app/ --suite site_shots --crawl --max-pages 40
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urldefrag, urljoin, urlparse, urlunparse

from _paths import FOXYIZ_ROOT  # type: ignore[import-not-found]

# ThoughtStream / ThoughtCapture guest shell — (slug, path, alive_substring)
DEFAULT_PATHS: list[tuple[str, str, str]] = [
    ("home", "/", "ThoughtCapture"),
    ("ideas", "/ideas", "Ideas Library"),
    ("dashboard", "/dashboard", "Dashboard"),
    ("integrate", "/integrate", "Integrate"),
    ("docs", "/docs", "Thought"),
    ("login", "/login", "Welcome"),
    ("register", "/register", "Create your account"),
    ("forgot_password", "/forgot-password", "Reset password"),
    ("reset_password", "/reset-password", "reset"),
    ("embed", "/embed", "Sign in"),
    ("view_private", "/view/not-a-real-id", "not publicly available"),
    ("unknown_404", "/no-such-xyz", "404"),
]


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")


def _normalize_base(base: str) -> str:
    u = (base or "").strip()
    if not u:
        raise ValueError("base URL required")
    if not u.startswith(("http://", "https://")):
        u = "https://" + u
    p = urlparse(u)
    path = p.path or "/"
    return urlunparse((p.scheme, p.netloc, path if path else "/", "", "", ""))


def _origin(url: str) -> str:
    p = urlparse(url)
    return f"{p.scheme}://{p.netloc}"


def _canon_page(url: str, strip_query: bool = True) -> str:
    url, _frag = urldefrag(url)
    p = urlparse(url)
    query = "" if strip_query else p.query
    path = p.path or "/"
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    return urlunparse((p.scheme, p.netloc, path, "", query, ""))


def _slug_from_url(base: str, url: str) -> str:
    base_p = urlparse(base)
    u = urlparse(url)
    path = u.path or "/"
    if path in ("/", ""):
        return "home"
    slug = path.strip("/").replace("/", "_")
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", slug)
    slug = re.sub(r"_+", "_", slug).strip("_") or "page"
    if u.query:
        slug = f"{slug}_q"
    if u.netloc and u.netloc != base_p.netloc:
        slug = f"ext_{slug}"
    return slug[:60]


def _plan_id(slug: str) -> str:
    parts = [p.capitalize() for p in slug.replace("-", "_").split("_") if p]
    name = "".join(parts) or "Page"
    return f"PShot_{name}"[:80]


def _d9(v: str) -> list[str]:
    return [v] * 9


def default_pages(base: str) -> list[tuple[str, str, str]]:
    """Return (slug, absolute_url, alive_text) for DEFAULT_PATHS."""
    origin = _origin(base)
    out: list[tuple[str, str, str]] = []
    for slug, path, alive in DEFAULT_PATHS:
        url = origin + "/" if path == "/" else origin + path
        out.append((slug, _canon_page(url), alive))
    return out


def crawl_pages(
    base: str,
    max_pages: int = 40,
    strip_query: bool = True,
    alive_fallback: str = "",
) -> list[tuple[str, str, str]]:
    """BFS same-origin anchors. Returns (slug, url, alive_text)."""
    start = _canon_page(base, strip_query=strip_query)
    origin = _origin(start)
    seen: set[str] = {start}
    ordered: list[str] = [start]
    q: deque[str] = deque([start])
    alive_fb = alive_fallback or (urlparse(base).netloc.split(".")[0] or "http")

    def _add_hrefs(page_url: str, hrefs: list[str]) -> None:
        for href in hrefs:
            if not href or href.startswith(("mailto:", "tel:", "javascript:", "#")):
                continue
            abs_u = urljoin(page_url, href)
            if not abs_u.startswith(origin):
                continue
            canon = _canon_page(abs_u, strip_query=strip_query)
            if canon not in seen and len(ordered) < max_pages:
                seen.add(canon)
                ordered.append(canon)
                q.append(canon)

    try:
        from playwright.sync_api import sync_playwright  # type: ignore

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1280, "height": 720})
            while q:
                url = q.popleft()
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    page.wait_for_timeout(1200)
                    hrefs = page.eval_on_selector_all(
                        "a[href]",
                        "els => els.map(e => e.getAttribute('href') || '')",
                    )
                    _add_hrefs(url, hrefs)
                except Exception as exc:
                    print(f"[crawl] skip {url}: {exc}")
            browser.close()
    except ImportError:
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.edge.options import Options
        import time

        opts = Options()
        opts.add_argument("--headless=new")
        opts.add_argument("--window-size=1280,720")
        driver = webdriver.Edge(options=opts)
        try:
            while q:
                url = q.popleft()
                try:
                    driver.get(url)
                    time.sleep(1.2)
                    hrefs = [
                        a.get_attribute("href") or ""
                        for a in driver.find_elements(By.CSS_SELECTOR, "a[href]")
                    ]
                    _add_hrefs(url, hrefs)
                except Exception as exc:
                    print(f"[crawl] skip {url}: {exc}")
        finally:
            driver.quit()

    pages: list[tuple[str, str, str]] = []
    used: set[str] = set()
    for u in ordered[:max_pages]:
        slug = _slug_from_url(base, u)
        base_slug = slug
        n = 2
        while slug in used:
            slug = f"{base_slug}_{n}"
            n += 1
        used.add(slug)
        pages.append((slug, u, alive_fb))
    return pages


def write_suite(suite: str, base: str, pages: list[tuple[str, str, str]]) -> Path:
    ydir = FOXYIZ_ROOT / "y" / suite
    ydir.mkdir(parents=True, exist_ok=True)
    fstart_dir = FOXYIZ_ROOT / "f" / "fStart"
    fstart_dir.mkdir(parents=True, exist_ok=True)
    stamp = _stamp()
    by = "site_shot_author"

    suite_json = {
        "input_files": {
            "yPlans": [f"y/{suite}/y1Plans.csv"],
            "yActions": [f"y/{suite}/y2Actions.csv"],
            "yDesigns": [f"y/{suite}/y3Designs.csv"],
        },
        "name": suite,
        "description": f"Site screenshots for {base} — Capture Smoke",
        "version": "1.0.0",
        "url": base,
    }
    (ydir / f"{suite}.json").write_text(json.dumps(suite_json, indent=2) + "\n", encoding="utf-8")

    fstart = {
        "configs": [f"y/{suite}/{suite}.json"],
        "thread_count": 1,
        "timeout": 15,
        "headless": True,
        "debug": False,
        "tags": ["Capture", "Smoke"],
        "capture": {"image": "on_fail", "video": "off", "video_fps": 2, "subdir": ""},
    }
    (fstart_dir / f"{suite}.json").write_text(json.dumps(fstart, indent=2) + "\n", encoding="utf-8")

    designs: list[list[str]] = [
        ["UI", "persona_id", *_d9("p1")],
        ["UI", "persona_code", *_d9("P1")],
        ["UI", "persona_name", *_d9("Site Shot Visitor")],
        ["UI", "base_url", *_d9(base)],
        ["UI", "body_locator", *_d9("css=body")],
    ]
    for slug, url, alive in pages:
        designs.append(["UI", f"url_{slug}", *_d9(url)])
        designs.append(["UI", f"label_{slug}", *_d9(slug)])
        designs.append(["UI", f"alive_{slug}", *_d9(alive)])

    with (ydir / "y3Designs.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Type", "DataName", *[f"D{i}" for i in range(1, 10)]])
        w.writerows(designs)

    plans: list[list[str]] = []
    actions: list[list[str]] = []
    for slug, url, _alive in pages:
        pid = _plan_id(slug)
        plans.append(
            [
                pid,
                f"Screenshot {slug}",
                "D1",
                "Y",
                f"{suite};Capture;Smoke;{slug}",
                f"shot_{slug}",
                by,
                stamp,
            ]
        )
        actions.extend(
            [
                [pid, 1, "Open Edge", "xUI", "xOpenBrowser", "edge", "", "", "Y"],
                [pid, 2, "Navigate", "xUI", "xNavigate", f"url_{slug}", "", "", "Y"],
                [pid, 3, "Wait SPA", "xTime", "xTimeWait", "3", "", "", "Y"],
                [pid, 4, "Screenshot", "xCapture", "xCaptureImage", f"label_{slug}", "", "", "Y"],
                [pid, 5, "Alive", "xUI", "xGetText", "body_locator", "", f"alive_{slug}", "Y"],
            ]
        )

    with (ydir / "y1Plans.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["PlanId", "PlanName", "DesignId", "Run", "Tags", "Output", "CreatedBy", "CreatedAt"])
        w.writerows(plans)

    with (ydir / "y2Actions.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            ["PlanId", "StepId", "StepInfo", "ActionType", "ActionName", "Input", "Output", "Expected", "Critical"]
        )
        w.writerows(actions)

    (ydir / "test plan.md").write_text(
        f"""# Test plan — {suite} (site screenshots)

App: {base}

One plan per same-origin page: navigate → wait → `xCaptureImage` → body contains page-specific alive text.

## Regenerate

```powershell
python FoXYiZ\\pyUtils\\site_shot_author.py --base {base} --suite {suite}
python FoXYiZ\\pyUtils\\site_shot_author.py --base {base} --suite {suite} --crawl --max-pages 40
```

## Run

```powershell
$env:FOXYIZ_HEADLESS = "true"
python FoXYiZ\\f\\fEngine2.py --config f/fStart/{suite}.json
```

PNGs land under `z/<ts>_{suite}/` via Capture steps.
""",
        encoding="utf-8",
    )

    print(f"Authored {ydir} ({len(pages)} pages)")
    print(f"fStart  {fstart_dir / f'{suite}.json'}")
    for slug, url, alive in pages:
        print(f"  - {slug}: {url}  (alive={alive!r})")
    return ydir


def main() -> int:
    ap = argparse.ArgumentParser(description="Author FoXYiZ site_shots yPAD from URLs or crawl")
    ap.add_argument("--base", required=True, help="Site base URL, e.g. https://jusdone.base44.app/")
    ap.add_argument("--suite", default="site_shots", help="y/<suite>/ name (default site_shots)")
    ap.add_argument("--crawl", action="store_true", help="BFS same-origin links instead of DEFAULT_PATHS")
    ap.add_argument("--max-pages", type=int, default=40, help="Crawl cap (default 40)")
    ap.add_argument(
        "--alive",
        default="",
        help="Fallback alive substring for --crawl pages (default: first host label)",
    )
    ap.add_argument("--keep-query", action="store_true", help="Do not strip ?query when crawling")
    args = ap.parse_args()

    base = _normalize_base(args.base)
    if args.crawl:
        alive_fb = args.alive.strip() or urlparse(base).netloc.split(".")[0]
        pages = crawl_pages(
            base,
            max_pages=max(1, args.max_pages),
            strip_query=not args.keep_query,
            alive_fallback=alive_fb,
        )
    else:
        pages = default_pages(base)
        if args.alive.strip():
            pages = [(s, u, args.alive.strip()) for s, u, _a in pages]

    write_suite(args.suite, base, pages)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
