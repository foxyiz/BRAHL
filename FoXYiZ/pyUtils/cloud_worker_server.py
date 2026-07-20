#!/usr/bin/env python3
"""FoXYiZ cloud worker server — run on AWS EC2 (or any always-on box).

Listens for Arena job POSTs and executes fEngine2 locally (headless).

  export FOXYIZ_CLOUD_TOKEN=shared-secret
  export FOXYIZ_HEADLESS=true
  python FoXYiZ/pyUtils/cloud_worker_server.py --host 0.0.0.0 --port 8770

From KK/ or FoXYiZ parent. Requires the same FoXYiZ tree as production.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

# Allow imports from qoa_web/api when launched from KK
KK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KK / "qoa_web" / "api"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

os.environ.setdefault("FOXYIZ_HEADLESS", "true")

from runner import get_job, start_run  # noqa: E402

_TOKEN = (os.environ.get("FOXYIZ_CLOUD_TOKEN") or "").strip()
_jobs_map: dict[str, str] = {}  # remote_id -> local job_id
_lock = threading.Lock()


def _auth_ok(handler: BaseHTTPRequestHandler) -> bool:
    if not _TOKEN:
        return True
    auth = handler.headers.get("Authorization") or ""
    return auth == f"Bearer {_TOKEN}"


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args: Any) -> None:
        sys.stderr.write("[cloud_worker] " + (fmt % args) + "\n")

    def _json(self, code: int, payload: dict[str, Any]) -> None:
        raw = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if not _auth_ok(self) and path != "/health":
            self._json(401, {"error": "unauthorized"})
            return
        if path == "/health":
            self._json(
                200,
                {
                    "status": "ok",
                    "service": "foxyiz-cloud-worker",
                    "headless": os.environ.get("FOXYIZ_HEADLESS", ""),
                },
            )
            return
        if path.startswith("/v1/jobs/"):
            rid = path.rsplit("/", 1)[-1]
            with _lock:
                local_id = _jobs_map.get(rid)
            if not local_id:
                self._json(404, {"error": "unknown job"})
                return
            job = get_job(local_id)
            if not job:
                self._json(404, {"error": "job missing"})
                return
            d = job.to_dict()
            d["remote_job_id"] = rid
            self._json(200, d)
            return
        self._json(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if not _auth_ok(self):
            self._json(401, {"error": "unauthorized"})
            return
        if path != "/v1/jobs":
            self._json(404, {"error": "not found"})
            return
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self._json(400, {"error": "invalid json"})
            return
        config_path = (body.get("config_path") or "f/fStart/Math.json").strip()
        rid = uuid.uuid4().hex[:12]
        job = start_run(
            config_path,
            step_label=body.get("step_label") or "Cloud Run",
            tags=body.get("tags"),
            thread_count=body.get("thread_count"),
            profiles=body.get("profiles"),
            runtime_mode="local",  # worker always executes locally
        )
        with _lock:
            _jobs_map[rid] = job.job_id
        self._json(
            200,
            {
                "remote_job_id": rid,
                "job_id": job.job_id,
                "status": job.status,
                "config_path": config_path,
            },
        )


def main() -> int:
    ap = argparse.ArgumentParser(description="FoXYiZ cloud worker for Arena")
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=8770)
    args = ap.parse_args()
    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"[cloud_worker] listening on http://{args.host}:{args.port}", flush=True)
    if not _TOKEN:
        print("[cloud_worker] WARNING: FOXYIZ_CLOUD_TOKEN unset — open worker", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[cloud_worker] stop", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
