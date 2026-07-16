"""Stripe Checkout scaffold for QA on Air pricing.

Set STRIPE_SECRET_KEY (+ optional price ids / webhook secret) on the host.
Without keys, /api/billing/checkout returns a scaffold response (no live charge).
"""

from __future__ import annotations

import os
from typing import Any

from pricing import CREATOR_WALLET_MIN_USD, MEMBERSHIP_USD_PER_MONTH, PAYOUT_THRESHOLD_USD


def _stripe_secret() -> str:
    return (os.environ.get("STRIPE_SECRET_KEY") or "").strip()


def _app_base_url() -> str:
    return (os.environ.get("APP_BASE_URL") or "http://127.0.0.1:8765").rstrip("/")


def billing_status() -> dict[str, Any]:
    secret = _stripe_secret()
    configured = bool(secret) and not secret.startswith("sk_test_REPLACE")
    return {
        "configured": configured,
        "provider": "stripe",
        "membership_usd_per_month": MEMBERSHIP_USD_PER_MONTH,
        "creator_wallet_min_usd": CREATOR_WALLET_MIN_USD,
        "payout_threshold_usd": PAYOUT_THRESHOLD_USD,
        "has_webhook_secret": bool((os.environ.get("STRIPE_WEBHOOK_SECRET") or "").strip()),
        "has_membership_price": bool((os.environ.get("STRIPE_PRICE_MEMBERSHIP") or "").strip()),
        "note": (
            "Stripe Checkout ready."
            if configured
            else "Set STRIPE_SECRET_KEY (and optional STRIPE_PRICE_MEMBERSHIP / STRIPE_WEBHOOK_SECRET) to enable live Checkout."
        ),
    }


def create_checkout_session(
    kind: str,
    *,
    amount_usd: float | None = None,
    customer_email: str | None = None,
    success_path: str = "/pricing?checkout=success",
    cancel_path: str = "/pricing?checkout=cancel",
) -> dict[str, Any]:
    """Create a Stripe Checkout Session or return a scaffold stub."""
    kind = (kind or "").strip().lower()
    if kind not in ("membership", "wallet"):
        raise ValueError("kind must be 'membership' or 'wallet'")

    status = billing_status()
    if not status["configured"]:
        return {
            "ok": False,
            "scaffold": True,
            "kind": kind,
            "url": None,
            "message": (
                "Stripe is not configured on this host. "
                "Add STRIPE_SECRET_KEY to enable Checkout, or start a free invite trial at /welcome."
            ),
            "status": status,
        }

    try:
        import stripe
    except ImportError as exc:
        raise RuntimeError(
            "stripe package not installed — pip install stripe (see qoa_web/api/requirements.txt)"
        ) from exc

    stripe.api_key = _stripe_secret()
    base = _app_base_url()
    success_url = f"{base}{success_path}"
    cancel_url = f"{base}{cancel_path}"

    metadata = {"qoa_kind": kind}
    line_items: list[dict[str, Any]]

    if kind == "membership":
        price_id = (os.environ.get("STRIPE_PRICE_MEMBERSHIP") or "").strip()
        tier = float(amount_usd if amount_usd is not None else MEMBERSHIP_USD_PER_MONTH)
        if tier not in (5.0, 20.0, 50.0, MEMBERSHIP_USD_PER_MONTH):
            # allow any positive hunter AI tier; clamp to known set if close
            from pricing import HUNTER_AI_TIERS_USD

            if tier not in HUNTER_AI_TIERS_USD:
                raise ValueError(f"Hunter AI plan must be one of: {', '.join(f'${t:.0f}' for t in HUNTER_AI_TIERS_USD)}")
        metadata["hunter_ai_tier_usd"] = str(tier)
        if price_id and tier == MEMBERSHIP_USD_PER_MONTH:
            line_items = [{"price": price_id, "quantity": 1}]
            mode = "subscription"
        else:
            cents = int(round(tier * 100))
            line_items = [
                {
                    "price_data": {
                        "currency": "usd",
                        "unit_amount": cents,
                        "recurring": {"interval": "month"},
                        "product_data": {
                            "name": f"QA Hunter AI · ${tier:.0f}/mo",
                            "description": "Hosted AI and tools for QA Hunters across projects",
                        },
                    },
                    "quantity": 1,
                }
            ]
            mode = "subscription"
    else:
        amount = float(amount_usd if amount_usd is not None else CREATOR_WALLET_MIN_USD)
        if amount < CREATOR_WALLET_MIN_USD:
            raise ValueError(f"Wallet top-up minimum is ${CREATOR_WALLET_MIN_USD:.0f}")
        cents = int(round(amount * 100))
        metadata["wallet_amount_usd"] = str(amount)
        line_items = [
            {
                "price_data": {
                    "currency": "usd",
                    "unit_amount": cents,
                    "product_data": {
                        "name": "Creator QA wallet top-up",
                        "description": f"${amount:.0f} QA wallet deposit",
                    },
                },
                "quantity": 1,
            }
        ]
        mode = "payment"

    params: dict[str, Any] = {
        "mode": mode,
        "line_items": line_items,
        "success_url": success_url,
        "cancel_url": cancel_url,
        "metadata": metadata,
    }
    if customer_email:
        params["customer_email"] = customer_email

    session = stripe.checkout.Session.create(**params)
    return {
        "ok": True,
        "scaffold": False,
        "kind": kind,
        "url": session.url,
        "session_id": session.id,
        "mode": mode,
    }


def handle_webhook(payload: bytes, sig_header: str | None) -> dict[str, Any]:
    """Verify Stripe webhook when secret is set; otherwise acknowledge scaffold receipt."""
    secret = (os.environ.get("STRIPE_WEBHOOK_SECRET") or "").strip()
    if not secret:
        return {
            "ok": True,
            "scaffold": True,
            "received": True,
            "message": (
                "Webhook received but STRIPE_WEBHOOK_SECRET is unset — "
                "entitlements are not applied yet (scaffold)."
            ),
        }

    try:
        import stripe
    except ImportError as exc:
        raise RuntimeError("stripe package not installed") from exc

    stripe.api_key = _stripe_secret() or None
    try:
        event = stripe.Webhook.construct_event(payload, sig_header or "", secret)
    except Exception as exc:
        raise ValueError(f"Invalid webhook signature: {exc}") from exc

    etype = event.get("type") if isinstance(event, dict) else getattr(event, "type", None)
    data_obj = event.get("data", {}).get("object", {}) if isinstance(event, dict) else {}
    # Scaffold: acknowledge known events; entitlement writes land in a later pass.
    return {
        "ok": True,
        "scaffold": True,
        "received": True,
        "type": etype,
        "session_id": data_obj.get("id") if isinstance(data_obj, dict) else None,
        "message": (
            f"Handled {etype} (scaffold — wire membership/wallet entitlements next)."
            if etype
            else "Webhook verified (scaffold)."
        ),
    }
