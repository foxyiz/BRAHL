#!/usr/bin/env python3
"""Minimal FoXYiZ MCP bridge — calls qoa_web local API (http://127.0.0.1:8765).

Usage (Cursor MCP config):
  python qoa_web/mcp/server.py

Tools: foxyiz_run, foxyiz_run_status, foxyiz_analyze, foxyiz_list_runs
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

API_BASE = "http://127.0.0.1:8765"


def _get(path: str) -> dict:
    req = urllib.request.Request(f"{API_BASE}{path}")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def _post(path: str, body: dict) -> dict:
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        f"{API_BASE}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode())


TOOLS = [
    {
        "name": "foxyiz_run",
        "description": "Start a FoXYiZ engine job via qoa_web API",
        "inputSchema": {
            "type": "object",
            "properties": {
                "config_path": {"type": "string", "default": "f/fStart_qoa_web_verify.json"},
                "step_label": {"type": "string", "default": "Run"},
            },
        },
    },
    {
        "name": "foxyiz_run_status",
        "description": "Poll job status by job_id",
        "inputSchema": {
            "type": "object",
            "properties": {"job_id": {"type": "string"}},
            "required": ["job_id"],
        },
    },
    {
        "name": "foxyiz_analyze",
        "description": "Get failures for a z/ run folder",
        "inputSchema": {
            "type": "object",
            "properties": {"run_name": {"type": "string"}},
            "required": ["run_name"],
        },
    },
    {
        "name": "foxyiz_list_runs",
        "description": "List recent z/ runs for a suite suffix",
        "inputSchema": {
            "type": "object",
            "properties": {"suite": {"type": "string", "default": "qoa_web"}},
        },
    },
]


def handle_tool(name: str, arguments: dict) -> dict:
    if name == "foxyiz_run":
        return _post("/api/jobs", {
            "config_path": arguments.get("config_path", "f/fStart_qoa_web_verify.json"),
            "step_label": arguments.get("step_label", "Run"),
        })
    if name == "foxyiz_run_status":
        return _get(f"/api/jobs/{arguments['job_id']}")
    if name == "foxyiz_analyze":
        return _get(f"/api/runs/{arguments['run_name']}/failures")
    if name == "foxyiz_list_runs":
        suite = arguments.get("suite", "qoa_web")
        return _get(f"/api/runs?suite={suite}")
    raise ValueError(f"Unknown tool: {name}")


def send(msg: dict) -> None:
    sys.stdout.write(json.dumps(msg) + "\n")
    sys.stdout.flush()


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue
        method = req.get("method")
        req_id = req.get("id")
        if method == "initialize":
            send({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "foxyiz-qoa-web", "version": "1.0.0"},
                },
            })
        elif method == "tools/list":
            send({"jsonrpc": "2.0", "id": req_id, "result": {"tools": TOOLS}})
        elif method == "tools/call":
            params = req.get("params") or {}
            try:
                result = handle_tool(params.get("name", ""), params.get("arguments") or {})
                send({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]},
                })
            except (urllib.error.URLError, KeyError, ValueError) as exc:
                send({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32000, "message": str(exc)},
                })
        elif method == "notifications/initialized":
            pass
        elif req_id is not None:
            send({"jsonrpc": "2.0", "id": req_id, "result": {}})


if __name__ == "__main__":
    main()
