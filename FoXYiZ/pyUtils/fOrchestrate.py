"""FoXYiZ orchestrator — tag fan-out + multi-config batches.

Future FoXYiZ.exe entrypoint. Workers still run suites via fEngine2.

Semantics:
  - thread_count == 1: tags stay OR filter (engine default).
  - thread_count > 1 and 2+ tags on a single suite: one tag per worker
    (workers = min(thread_count, len(tags)); extras queue).
  - Multiple paths in configs[] with thread_count > 1: existing engine parallel.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import uuid
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any

FOXYIZ_ROOT = Path(__file__).resolve().parents[1]
PYUTILS_DIR = Path(__file__).resolve().parent
F_DIR = FOXYIZ_ROOT / "f"
Z_DIR = FOXYIZ_ROOT / "z"
ENGINE = F_DIR / "fEngine2.py"
OUTPUT_DIR_RE = re.compile(r"Output Directory:\s*(.+)")


def _load_fstart(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _normalize_tags(raw: Any) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, str):
        return [raw.strip()] if raw.strip() else []
    if isinstance(raw, list):
        return [str(t).strip() for t in raw if str(t).strip()]
    return []


def needs_tag_fanout(cfg: dict[str, Any]) -> bool:
    configs = cfg.get("configs") or []
    tags = _normalize_tags(cfg.get("tags"))
    try:
        thread_count = int(cfg.get("thread_count") or 1)
    except (TypeError, ValueError):
        thread_count = 1
    tags_no_all = [t for t in tags if t.lower() != "all"]
    return len(configs) == 1 and thread_count > 1 and len(tags_no_all) >= 2


def _write_temp_fstart(base: dict[str, Any], tag: str, batch_id: str) -> Path:
    data = dict(base)
    data["tags"] = [tag]
    data["thread_count"] = 1
    tmp = F_DIR / f"_orch_{batch_id}_{re.sub(r'[^a-zA-Z0-9_-]', '_', tag)[:40]}.json"
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return tmp


def _run_engine_config(config_rel: str, label: str = "") -> dict[str, Any]:
    """Run fEngine2 for one fStart; return {ok, output_dir, log, return_code, label}."""
    cfg_path = FOXYIZ_ROOT / config_rel.replace("/", "\\")
    if not cfg_path.is_file():
        return {
            "ok": False,
            "output_dir": None,
            "log": f"Config not found: {config_rel}",
            "return_code": 2,
            "label": label or config_rel,
            "config": config_rel,
        }
    env = os.environ.copy()
    env["FOXYIZ_ORCHESTRATED"] = "1"
    proc = subprocess.run(
        [sys.executable, str(ENGINE), "--config", str(cfg_path.relative_to(FOXYIZ_ROOT))],
        cwd=str(FOXYIZ_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    text = (proc.stdout or "") + (proc.stderr or "")
    output_dir = None
    for line in text.splitlines():
        m = OUTPUT_DIR_RE.search(line)
        if m:
            output_dir = m.group(1).strip()
    return {
        "ok": proc.returncode == 0,
        "output_dir": output_dir,
        "log": text,
        "return_code": proc.returncode,
        "label": label or config_rel,
        "config": config_rel,
    }


def _worker_run(args: tuple[str, str]) -> dict[str, Any]:
    config_rel, label = args
    return _run_engine_config(config_rel, label)


def build_batch_dashboard(name: str, run_dirs: list[str]) -> str | None:
    """Write z/zDash_batch_<name>.html; return relative path or None."""
    if not run_dirs:
        return None
    try:
        sys.path.insert(0, str(PYUTILS_DIR))
        import zBatchDash as zbd  # type: ignore

        jobs = []
        for rd in run_dirs:
            p = Path(rd)
            if not p.is_absolute():
                p = FOXYIZ_ROOT / rd.replace("/", "\\")
            if p.is_dir():
                jobs.append(zbd.analyze_run_dir(p))
        jobs = zbd.merge_jobs(jobs)
        if not jobs:
            return None
        failures = zbd.collect_failures(jobs)
        html = zbd.build_html(name, jobs, failures)
        out = Z_DIR / f"zDash_batch_{name}.html"
        out.write_text(html, encoding="utf-8")
        return str(out.relative_to(FOXYIZ_ROOT)).replace("\\", "/")
    except Exception as exc:
        print(f"[ORCH] batch dash failed: {exc}", file=sys.stderr)
        return None


def run_tag_fanout(config_path: Path, cfg: dict[str, Any] | None = None) -> int:
    cfg = cfg or _load_fstart(config_path)
    tags = [t for t in _normalize_tags(cfg.get("tags")) if t.lower() != "all"]
    try:
        thread_count = int(cfg.get("thread_count") or 1)
    except (TypeError, ValueError):
        thread_count = 1
    workers = max(1, min(thread_count, len(tags)))
    batch_id = time.strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6]
    print(f"[ORCH] Tag fan-out: {len(tags)} tags · {workers} workers · batch {batch_id}")
    temp_files: list[Path] = []
    jobs_args: list[tuple[str, str]] = []
    try:
        for tag in tags:
            tmp = _write_temp_fstart(cfg, tag, batch_id)
            temp_files.append(tmp)
            rel = str(tmp.relative_to(FOXYIZ_ROOT)).replace("\\", "/")
            jobs_args.append((rel, f"tag:{tag}"))
            print(f"[ORCH] queued {rel} ({tag})")

        results: list[dict[str, Any]] = []
        if workers == 1:
            for args in jobs_args:
                r = _run_engine_config(*args)
                sys.stdout.write(r.get("log") or "")
                sys.stdout.flush()
                results.append(r)
        else:
            # Sequential process launches with bounded concurrency via ProcessPool
            with ProcessPoolExecutor(max_workers=workers) as ex:
                futs = {ex.submit(_worker_run, a): a for a in jobs_args}
                for fut in as_completed(futs):
                    r = fut.result()
                    print(f"\n[ORCH] finished {r.get('label')} rc={r.get('return_code')}")
                    sys.stdout.write(r.get("log") or "")
                    sys.stdout.flush()
                    results.append(r)

        run_dirs = [r["output_dir"] for r in results if r.get("output_dir")]
        dash = build_batch_dashboard(f"orch_{batch_id}", run_dirs)
        if dash:
            print(f"[ORCH] Batch dashboard: {dash}")
            print(f"Output Directory: {dash}")
        failed = sum(1 for r in results if not r.get("ok"))
        return 1 if failed else 0
    finally:
        for p in temp_files:
            try:
                p.unlink(missing_ok=True)
            except OSError:
                pass


def run_multi_configs(config_paths: list[str], *, parallel: bool = True) -> dict[str, Any]:
    """Run several fStarts (CLI / arena). Returns summary dict."""
    batch_id = time.strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6]
    print(f"[ORCH] Multi-config batch {batch_id} · parallel={parallel} · n={len(config_paths)}")
    results: list[dict[str, Any]] = []
    if parallel and len(config_paths) > 1:
        workers = min(len(config_paths), max(1, min(os.cpu_count() or 2, 4)))
        with ProcessPoolExecutor(max_workers=workers) as ex:
            futs = {
                ex.submit(_worker_run, (c, c)): c
                for c in config_paths
            }
            for fut in as_completed(futs):
                r = fut.result()
                print(f"\n[ORCH] finished {r.get('label')} rc={r.get('return_code')}")
                sys.stdout.write(r.get("log") or "")
                sys.stdout.flush()
                results.append(r)
    else:
        for c in config_paths:
            r = _run_engine_config(c, c)
            sys.stdout.write(r.get("log") or "")
            sys.stdout.flush()
            results.append(r)

    run_dirs = [r["output_dir"] for r in results if r.get("output_dir")]
    dash = build_batch_dashboard(f"batch_{batch_id}", run_dirs)
    if dash:
        print(f"[ORCH] Batch dashboard: {dash}")
        print(f"Output Directory: {dash}")
    return {
        "batch_id": batch_id,
        "results": results,
        "run_dirs": run_dirs,
        "batch_dashboard": dash,
        "ok": all(r.get("ok") for r in results) if results else False,
    }


def maybe_orchestrate_config(config_path: str | Path) -> int | None:
    """If tag fan-out applies, run it and return exit code; else return None."""
    if os.environ.get("FOXYIZ_ORCHESTRATED") == "1":
        return None
    path = Path(config_path)
    if not path.is_absolute():
        path = FOXYIZ_ROOT / str(config_path).replace("/", "\\")
    if not path.is_file():
        return None
    try:
        cfg = _load_fstart(path)
    except (OSError, json.JSONDecodeError):
        return None
    if not needs_tag_fanout(cfg):
        return None
    return run_tag_fanout(path, cfg)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="FoXYiZ orchestrator (future exe entry)")
    parser.add_argument("--config", help="Single fStart (tag fan-out when applicable)")
    parser.add_argument(
        "--configs",
        help="Comma-separated fStarts for multi-config batch",
    )
    parser.add_argument("--parallel", action="store_true", default=True)
    parser.add_argument("--sequential", action="store_true")
    args = parser.parse_args(argv)

    if args.configs:
        paths = [p.strip() for p in args.configs.split(",") if p.strip()]
        summary = run_multi_configs(paths, parallel=not args.sequential)
        return 0 if summary.get("ok") else 1

    if args.config:
        path = Path(args.config)
        if not path.is_absolute():
            path = FOXYIZ_ROOT / args.config.replace("/", "\\")
        cfg = _load_fstart(path)
        if needs_tag_fanout(cfg):
            return run_tag_fanout(path, cfg)
        # Delegate single run to engine
        r = _run_engine_config(str(path.relative_to(FOXYIZ_ROOT)).replace("\\", "/"))
        sys.stdout.write(r.get("log") or "")
        return int(r.get("return_code") or 0)

    parser.print_help()
    return 2


if __name__ == "__main__":
    try:
        if sys.platform == "win32":
            import multiprocessing

            multiprocessing.freeze_support()
            try:
                multiprocessing.set_start_method("spawn", force=True)
            except RuntimeError:
                pass
    except Exception:
        pass
    raise SystemExit(main())
