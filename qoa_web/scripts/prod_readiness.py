#!/usr/bin/env python3
"""Print production readiness from current process env (+ optional .env load).

Usage (from KK/):
  python qoa_web/scripts/prod_readiness.py
  # On host after exporting env, or after loading .env.production.example values
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

API = Path(__file__).resolve().parents[1] / "api"
sys.path.insert(0, str(API))


def _bool_env(name: str, default: str = "0") -> bool:
    return os.environ.get(name, default).strip().lower() in ("1", "true", "yes")


def main() -> int:
    # Best-effort load qoa_web/.env if present (not committed)
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if env_path.is_file():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

    import auth as auth_store
    import billing
    import cloud_worker as cw

    jwt = (os.environ.get("JWT_SECRET") or "").strip()
    rows = [
        ("APP_BASE_URL", bool((os.environ.get("APP_BASE_URL") or "").strip())),
        ("JWT_SECRET strong", bool(jwt) and jwt != "qoa-dev-change-me-in-production"),
        ("GOOGLE_CLIENT_ID+SECRET", bool(os.environ.get("GOOGLE_CLIENT_ID")) and bool(os.environ.get("GOOGLE_CLIENT_SECRET"))),
        ("Stripe configured", billing.billing_status()["configured"]),
        ("Cloud worker URL", cw.cloud_configured()),
        ("Cloud worker reachable", cw.cloud_status().get("reachable")),
        ("OPENAI_API_KEY", bool((os.environ.get("OPENAI_API_KEY") or "").strip())),
        ("QOA_ALLOW_DEMO", auth_store.demo_allowed()),
        ("QOA_AUTH_REQUIRED", _bool_env("QOA_AUTH_REQUIRED")),
        ("QOA_ADMIN_OPEN", os.environ.get("QOA_ADMIN_OPEN", "1").strip() not in ("0", "false", "False")),
        ("FOXYIZ_HEADLESS", os.environ.get("FOXYIZ_HEADLESS", "")),
    ]
    print("Production readiness (process env)")
    print("-" * 48)
    for k, v in rows:
        print(f"  {k:28} {v}")
    print("-" * 48)
    print("Template: qoa_web/.env.production.example")
    print("Redirect: https://brahl.qaonair.com/api/auth/google/callback")
    print("Webhook:  https://brahl.qaonair.com/api/billing/webhook")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
