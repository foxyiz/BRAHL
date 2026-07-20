"""Stripe Checkout + webhook entitlements for QA on Air pricing.

Set STRIPE_SECRET_KEY (+ optional price ids / webhook secret) on the host.
Without keys, /api/billing/checkout returns a scaffold response (no live charge).

After payment, webhooks apply:
  - membership → users.hunter_ai_tier_usd / membership_status
  - wallet → users.creator_wallet_usd and/or project.budget_usd
"""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from pricing import (
    CREATOR_WALLET_MIN_USD,
    HUNTER_AI_TIERS_USD,
    MEMBERSHIP_USD_PER_MONTH,
    PAYOUT_THRESHOLD_USD,
)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
LEDGER_FILE = DATA_DIR / "billing_ledger.json"
_ledger_lock = threading.RLock()


def _stripe_secret() -> str:
    return (os.environ.get("STRIPE_SECRET_KEY") or "").strip()


def _app_base_url() -> str:
    return (os.environ.get("APP_BASE_URL") or "http://127.0.0.1:8765").rstrip("/")


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _ensure_ledger() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not LEDGER_FILE.is_file():
        LEDGER_FILE.write_text("[]", encoding="utf-8")


def load_ledger() -> list[dict[str, Any]]:
    _ensure_ledger()
    try:
        data = json.loads(LEDGER_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return data if isinstance(data, list) else []


def _save_ledger(entries: list[dict[str, Any]]) -> None:
    _ensure_ledger()
    LEDGER_FILE.write_text(json.dumps(entries, indent=2), encoding="utf-8")


def find_ledger_entry(*, session_id: str | None = None, event_id: str | None = None) -> dict[str, Any] | None:
    sid = (session_id or "").strip()
    eid = (event_id or "").strip()
    for row in load_ledger():
        if eid and row.get("event_id") == eid:
            return row
        if sid and row.get("session_id") == sid and row.get("status") == "applied":
            return row
    return None


def append_ledger(entry: dict[str, Any]) -> dict[str, Any]:
    with _ledger_lock:
        rows = load_ledger()
        eid = (entry.get("event_id") or "").strip()
        sid = (entry.get("session_id") or "").strip()
        if eid and any(r.get("event_id") == eid for r in rows):
            return next(r for r in rows if r.get("event_id") == eid)
        if sid and entry.get("status") == "applied":
            existing = next(
                (r for r in rows if r.get("session_id") == sid and r.get("status") == "applied"),
                None,
            )
            if existing:
                return existing
        row = dict(entry)
        row.setdefault("at", _now())
        rows.insert(0, row)
        _save_ledger(rows[:500])
        return row


def patch_ledger_entries(
    *,
    match_status: str,
    email: str | None = None,
    session_id: str | None = None,
    patch: dict[str, Any],
) -> int:
    """Update matching ledger rows in place. Returns count updated."""
    email_l = (email or "").strip().lower()
    sid = (session_id or "").strip()
    with _ledger_lock:
        rows = load_ledger()
        n = 0
        for i, row in enumerate(rows):
            if row.get("status") != match_status:
                continue
            if email_l and (row.get("email") or "").strip().lower() != email_l:
                continue
            if sid and row.get("session_id") != sid:
                continue
            updated = dict(row)
            updated.update(patch)
            updated["patched_at"] = _now()
            rows[i] = updated
            n += 1
        if n:
            _save_ledger(rows[:500])
        return n


def billing_status() -> dict[str, Any]:
    secret = _stripe_secret()
    configured = bool(secret) and not secret.startswith("sk_test_REPLACE")
    return {
        "configured": configured,
        "provider": "stripe",
        "membership_usd_per_month": MEMBERSHIP_USD_PER_MONTH,
        "hunter_ai_tiers_usd": list(HUNTER_AI_TIERS_USD),
        "creator_wallet_min_usd": CREATOR_WALLET_MIN_USD,
        "payout_threshold_usd": PAYOUT_THRESHOLD_USD,
        "has_webhook_secret": bool((os.environ.get("STRIPE_WEBHOOK_SECRET") or "").strip()),
        "has_membership_price": bool((os.environ.get("STRIPE_PRICE_MEMBERSHIP") or "").strip()),
        "note": (
            "Stripe Checkout ready — webhooks apply membership and wallet entitlements."
            if configured
            else "Set STRIPE_SECRET_KEY (and STRIPE_WEBHOOK_SECRET) to enable live Checkout + entitlements."
        ),
    }


def create_checkout_session(
    kind: str,
    *,
    amount_usd: float | None = None,
    customer_email: str | None = None,
    user_id: str | None = None,
    project_id: str | None = None,
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

    if not (user_id or "").strip():
        raise ValueError("Sign in required so entitlements can be applied after payment")

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

    metadata: dict[str, str] = {"qoa_kind": kind}
    if user_id:
        metadata["user_id"] = str(user_id).strip()
    if project_id:
        metadata["project_id"] = str(project_id).strip()
    if customer_email:
        metadata["customer_email"] = str(customer_email).strip().lower()

    line_items: list[dict[str, Any]]

    if kind == "membership":
        price_id = (os.environ.get("STRIPE_PRICE_MEMBERSHIP") or "").strip()
        tier = float(amount_usd if amount_usd is not None else MEMBERSHIP_USD_PER_MONTH)
        if tier not in HUNTER_AI_TIERS_USD:
            raise ValueError(
                f"Hunter AI plan must be one of: {', '.join(f'${t:.0f}' for t in HUNTER_AI_TIERS_USD)}"
            )
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
        params["customer_email"] = customer_email.strip().lower()
    if user_id:
        params["client_reference_id"] = str(user_id).strip()
    # Propagate metadata onto the Subscription object for later subscription.* events
    if mode == "subscription":
        params["subscription_data"] = {"metadata": dict(metadata)}

    session = stripe.checkout.Session.create(**params)
    return {
        "ok": True,
        "scaffold": False,
        "kind": kind,
        "url": session.url,
        "session_id": session.id,
        "mode": mode,
    }


def _session_as_dict(session: Any) -> dict[str, Any]:
    if isinstance(session, dict):
        return session
    if hasattr(session, "to_dict"):
        try:
            return session.to_dict()  # type: ignore[no-any-return]
        except Exception:
            pass
    out: dict[str, Any] = {}
    for key in (
        "id",
        "metadata",
        "customer",
        "customer_email",
        "customer_details",
        "subscription",
        "client_reference_id",
        "mode",
        "payment_status",
        "amount_total",
    ):
        if hasattr(session, key):
            out[key] = getattr(session, key)
    return out


def _resolve_user(
    *,
    user_id: str | None = None,
    email: str | None = None,
    stripe_customer_id: str | None = None,
) -> dict[str, Any] | None:
    import auth as auth_store

    if user_id:
        user = auth_store.get_user(str(user_id).strip())
        if user:
            return user
    if stripe_customer_id:
        user = auth_store.find_user_by_stripe_customer(str(stripe_customer_id).strip())
        if user:
            return user
    if email:
        return auth_store.get_user_by_email(str(email).strip().lower())
    return None


def _period_end_iso(ts: Any) -> str:
    try:
        if ts is None:
            return ""
        return datetime.fromtimestamp(int(ts), tz=timezone.utc).replace(microsecond=0).isoformat()
    except (TypeError, ValueError, OSError):
        return ""


def _estimate_period_end_iso(days: int = 30) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).replace(microsecond=0).isoformat()


def _fetch_subscription_period_end(subscription_id: str | None) -> str:
    """Best-effort: read current_period_end from Stripe Subscription."""
    sid = (subscription_id or "").strip()
    if not sid or not _stripe_secret():
        return ""
    try:
        import stripe

        stripe.api_key = _stripe_secret()
        sub = stripe.Subscription.retrieve(sid)
        if isinstance(sub, dict):
            return _period_end_iso(sub.get("current_period_end"))
        return _period_end_iso(getattr(sub, "current_period_end", None))
    except Exception:
        return ""


def apply_checkout_session(
    session: dict[str, Any],
    *,
    event_id: str | None = None,
) -> dict[str, Any]:
    """Apply membership or wallet entitlements from a completed Checkout Session."""
    import auth as auth_store
    import projects as project_store

    session = _session_as_dict(session)
    session_id = str(session.get("id") or "")
    payment_status = str(session.get("payment_status") or "").strip().lower()
    # unpaid/no_payment_required edge cases: only credit when paid (or unset in unit tests)
    if payment_status and payment_status not in ("paid", "no_payment_required"):
        entry = append_ledger(
            {
                "event_id": event_id,
                "session_id": session_id,
                "kind": str((session.get("metadata") or {}).get("qoa_kind") or "unknown"),
                "status": "skipped_unpaid",
                "payment_status": payment_status,
                "message": f"Checkout not paid yet (payment_status={payment_status}).",
            }
        )
        return {
            "ok": True,
            "applied": False,
            "skipped": True,
            "ledger": entry,
            "message": entry["message"],
        }

    # Resolve subscription period end before taking the ledger lock (network I/O).
    meta_peek = session.get("metadata") or {}
    if not isinstance(meta_peek, dict):
        meta_peek = {}
    kind_peek = str(meta_peek.get("qoa_kind") or "").strip().lower()
    sub_peek = session.get("subscription")
    sub_id_peek = sub_peek if isinstance(sub_peek, str) else getattr(sub_peek, "id", None)
    period_end_prefetch = ""
    if kind_peek == "membership":
        period_end_prefetch = _fetch_subscription_period_end(
            str(sub_id_peek) if sub_id_peek else None
        ) or _estimate_period_end_iso(30)

    with _ledger_lock:
        if session_id:
            prior = find_ledger_entry(session_id=session_id)
            if prior:
                return {
                    "ok": True,
                    "applied": False,
                    "duplicate": True,
                    "ledger": prior,
                    "message": "Entitlements already applied for this Checkout session.",
                }

        meta = session.get("metadata") or {}
        if not isinstance(meta, dict):
            meta = {}
        kind = str(meta.get("qoa_kind") or "").strip().lower()
        user_id = str(meta.get("user_id") or session.get("client_reference_id") or "").strip() or None
        project_id = str(meta.get("project_id") or "").strip() or None
        email = (
            str(meta.get("customer_email") or "").strip()
            or str(session.get("customer_email") or "").strip()
            or str((session.get("customer_details") or {}).get("email") or "").strip()
        )
        customer = session.get("customer")
        customer_id = customer if isinstance(customer, str) else getattr(customer, "id", None)

        user = _resolve_user(user_id=user_id, email=email or None, stripe_customer_id=customer_id)
        if not user:
            entry = append_ledger(
                {
                    "event_id": event_id,
                    "session_id": session_id,
                    "kind": kind or "unknown",
                    "status": "pending_user",
                    "email": email or None,
                    "metadata": meta,
                    "message": "No matching user — sign in with the same email to claim, or contact support.",
                }
            )
            return {
                "ok": False,
                "applied": False,
                "pending_user": True,
                "ledger": entry,
                "message": entry["message"],
            }

        subscription = session.get("subscription")
        subscription_id = (
            subscription if isinstance(subscription, str) else getattr(subscription, "id", None)
        )

        if kind == "membership":
            tier = float(meta.get("hunter_ai_tier_usd") or MEMBERSHIP_USD_PER_MONTH)
            if tier not in HUNTER_AI_TIERS_USD:
                tier = MEMBERSHIP_USD_PER_MONTH
            period_end = period_end_prefetch or _estimate_period_end_iso(30)
            updated = auth_store.apply_membership_entitlement(
                user["id"],
                tier_usd=tier,
                status="active",
                stripe_customer_id=str(customer_id) if customer_id else None,
                stripe_subscription_id=str(subscription_id) if subscription_id else None,
                period_end=period_end,
            )
            entry = append_ledger(
                {
                    "event_id": event_id,
                    "session_id": session_id,
                    "kind": "membership",
                    "status": "applied",
                    "user_id": user["id"],
                    "email": user.get("email"),
                    "tier_usd": tier,
                    "stripe_customer_id": customer_id,
                    "stripe_subscription_id": subscription_id,
                    "membership_period_end": period_end,
                }
            )
            return {
                "ok": True,
                "applied": True,
                "kind": "membership",
                "user": updated,
                "ledger": entry,
                "message": f"Hunter AI ${tier:.0f}/mo membership activated.",
            }

        if kind == "wallet":
            # Prefer Stripe-reported total when present (source of truth for charged amount)
            amount = 0.0
            if session.get("amount_total") is not None:
                try:
                    amount = float(session["amount_total"]) / 100.0
                except (TypeError, ValueError):
                    amount = 0.0
            if amount <= 0:
                amount = float(meta.get("wallet_amount_usd") or 0)
            if amount < CREATOR_WALLET_MIN_USD:
                raise ValueError(f"Wallet top-up below minimum (${CREATOR_WALLET_MIN_USD:.0f})")

            destinations: list[str] = []
            project_out: dict[str, Any] | None = None
            if project_id:
                project = project_store.get_project(project_id)
                if not project:
                    raise ValueError(f"Project not found: {project_id}")
                if not project_store.user_owns_project(project, user):
                    raise ValueError("Only the project owner can fund this project wallet")
                project_out = project_store.credit_project_budget(project_id, amount)
                destinations.append(f"project:{project_id}")
            else:
                auth_store.credit_creator_wallet(user["id"], amount)
                destinations.append("creator_wallet")

            updated = auth_store.get_user(user["id"])
            entry = append_ledger(
                {
                    "event_id": event_id,
                    "session_id": session_id,
                    "kind": "wallet",
                    "status": "applied",
                    "user_id": user["id"],
                    "email": user.get("email"),
                    "amount_usd": amount,
                    "project_id": project_id,
                    "destinations": destinations,
                }
            )
            return {
                "ok": True,
                "applied": True,
                "kind": "wallet",
                "amount_usd": amount,
                "user": updated,
                "project": project_out,
                "ledger": entry,
                "message": (
                    f"${amount:.0f} credited to project budget."
                    if project_id
                    else f"${amount:.0f} credited to Creator wallet."
                ),
            }

        entry = append_ledger(
            {
                "event_id": event_id,
                "session_id": session_id,
                "kind": kind or "unknown",
                "status": "ignored",
                "user_id": user["id"],
                "message": f"Unknown checkout kind: {kind or '(empty)'}",
            }
        )
        return {"ok": False, "applied": False, "ledger": entry, "message": entry["message"]}


def apply_subscription_event(subscription: dict[str, Any], *, event_type: str, event_id: str | None = None) -> dict[str, Any]:
    """Sync membership status from Stripe subscription.updated / deleted."""
    import auth as auth_store

    if not isinstance(subscription, dict):
        subscription = _session_as_dict(subscription)

    sub_id = str(subscription.get("id") or "")
    if event_id and find_ledger_entry(event_id=event_id):
        return {"ok": True, "applied": False, "duplicate": True, "message": "Event already processed."}

    meta = subscription.get("metadata") or {}
    if not isinstance(meta, dict):
        meta = {}
    customer = subscription.get("customer")
    customer_id = customer if isinstance(customer, str) else None
    user = _resolve_user(
        user_id=str(meta.get("user_id") or "").strip() or None,
        stripe_customer_id=customer_id,
    )
    if not user:
        entry = append_ledger(
            {
                "event_id": event_id,
                "kind": "membership",
                "status": "pending_user",
                "stripe_subscription_id": sub_id,
                "stripe_customer_id": customer_id,
                "message": "Subscription event with no matching user.",
            }
        )
        return {"ok": False, "applied": False, "pending_user": True, "ledger": entry}

    stripe_status = str(subscription.get("status") or "").strip().lower()
    if event_type.endswith("deleted") or stripe_status in ("canceled", "unpaid"):
        status = "canceled"
        tier = 0.0
    elif stripe_status in ("past_due", "incomplete", "incomplete_expired"):
        status = "past_due"
        tier = float(meta.get("hunter_ai_tier_usd") or user.get("hunter_ai_tier_usd") or MEMBERSHIP_USD_PER_MONTH)
    elif stripe_status in ("active", "trialing"):
        status = "active"
        tier = float(meta.get("hunter_ai_tier_usd") or user.get("hunter_ai_tier_usd") or MEMBERSHIP_USD_PER_MONTH)
        if tier not in HUNTER_AI_TIERS_USD:
            tier = MEMBERSHIP_USD_PER_MONTH
    else:
        status = stripe_status or "active"
        tier = float(meta.get("hunter_ai_tier_usd") or user.get("hunter_ai_tier_usd") or 0)

    period_end = _period_end_iso(subscription.get("current_period_end"))
    updated = auth_store.apply_membership_entitlement(
        user["id"],
        tier_usd=tier,
        status=status if status in ("active", "canceled", "past_due", "incomplete", "trialing", "unpaid") else "active",
        stripe_customer_id=str(customer_id) if customer_id else None,
        stripe_subscription_id=sub_id or None,
        period_end=period_end or None,
    )
    entry = append_ledger(
        {
            "event_id": event_id,
            "kind": "membership",
            "status": "applied",
            "user_id": user["id"],
            "membership_status": updated.get("membership_status"),
            "tier_usd": updated.get("hunter_ai_tier_usd"),
            "stripe_subscription_id": sub_id,
            "event_type": event_type,
        }
    )
    return {
        "ok": True,
        "applied": True,
        "kind": "membership",
        "user": updated,
        "ledger": entry,
        "message": f"Membership synced ({updated.get('membership_status')}).",
    }


def handle_webhook(payload: bytes, sig_header: str | None) -> dict[str, Any]:
    """Verify Stripe webhook and apply entitlements."""
    secret = (os.environ.get("STRIPE_WEBHOOK_SECRET") or "").strip()
    if not secret:
        return {
            "ok": True,
            "scaffold": True,
            "received": True,
            "message": (
                "Webhook received but STRIPE_WEBHOOK_SECRET is unset — "
                "entitlements are not applied yet. Set the secret to enable live updates."
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

    if isinstance(event, dict):
        etype = event.get("type")
        event_id = event.get("id")
        data_obj = (event.get("data") or {}).get("object") or {}
    else:
        etype = getattr(event, "type", None)
        event_id = getattr(event, "id", None)
        data = getattr(event, "data", None)
        data_obj = getattr(data, "object", None) if data is not None else {}
        if data_obj is not None and not isinstance(data_obj, dict):
            data_obj = _session_as_dict(data_obj)

    if not isinstance(data_obj, dict):
        data_obj = {}

    if event_id and find_ledger_entry(event_id=str(event_id)):
        return {
            "ok": True,
            "scaffold": False,
            "received": True,
            "duplicate": True,
            "type": etype,
            "message": "Event already processed.",
        }

    try:
        if etype in ("checkout.session.completed", "checkout.session.async_payment_succeeded"):
            result = apply_checkout_session(data_obj, event_id=str(event_id) if event_id else None)
            return {
                "ok": bool(result.get("ok")),
                "scaffold": False,
                "received": True,
                "type": etype,
                "session_id": data_obj.get("id"),
                **{k: v for k, v in result.items() if k != "user"},
                "user_id": (result.get("user") or {}).get("id") if isinstance(result.get("user"), dict) else None,
                "message": result.get("message"),
            }

        if etype in ("customer.subscription.updated", "customer.subscription.deleted"):
            result = apply_subscription_event(
                data_obj,
                event_type=str(etype),
                event_id=str(event_id) if event_id else None,
            )
            return {
                "ok": bool(result.get("ok")),
                "scaffold": False,
                "received": True,
                "type": etype,
                **{k: v for k, v in result.items() if k != "user"},
                "user_id": (result.get("user") or {}).get("id") if isinstance(result.get("user"), dict) else None,
                "message": result.get("message"),
            }
    except ValueError as exc:
        # Permanent apply failure after a valid Stripe event — acknowledge so Stripe
        # does not retry forever; record for ops follow-up.
        entry = append_ledger(
            {
                "event_id": str(event_id) if event_id else None,
                "session_id": data_obj.get("id")
                if etype
                in ("checkout.session.completed", "checkout.session.async_payment_succeeded")
                else None,
                "kind": str((data_obj.get("metadata") or {}).get("qoa_kind") or "unknown"),
                "status": "apply_failed",
                "message": str(exc),
                "event_type": etype,
            }
        )
        return {
            "ok": False,
            "scaffold": False,
            "received": True,
            "type": etype,
            "apply_failed": True,
            "ledger": entry,
            "message": str(exc),
        }

    # Acknowledge other events without failing the webhook
    return {
        "ok": True,
        "scaffold": False,
        "received": True,
        "type": etype,
        "ignored": True,
        "message": f"Acknowledged {etype} (no entitlement action).",
    }


def claim_pending_entitlements(user: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Apply ledger rows left as pending_user once the account exists (login/register)."""
    import auth as auth_store

    if not user or not user.get("id"):
        return [], user
    email = (user.get("email") or "").strip().lower()
    if not email:
        return [], user

    with _ledger_lock:
        pending = [
            dict(r)
            for r in load_ledger()
            if r.get("status") == "pending_user"
            and (r.get("email") or "").strip().lower() == email
        ]

    claimed: list[dict[str, Any]] = []
    for row in pending:
        session_id = str(row.get("session_id") or "")
        if session_id and find_ledger_entry(session_id=session_id):
            patch_ledger_entries(
                match_status="pending_user",
                email=email,
                session_id=session_id,
                patch={"status": "claimed_duplicate", "user_id": user["id"]},
            )
            continue
        meta = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
        kind = str(meta.get("qoa_kind") or row.get("kind") or "").strip().lower()
        synthetic = {
            "id": session_id or f"claim_{row.get('at') or _now()}",
            "payment_status": "paid",
            "metadata": {
                **meta,
                "qoa_kind": kind,
                "user_id": user["id"],
                "customer_email": email,
            },
            "customer_email": email,
            "client_reference_id": user["id"],
            "customer": row.get("stripe_customer_id"),
            "subscription": row.get("stripe_subscription_id"),
            "amount_total": int(round(float(meta.get("wallet_amount_usd") or row.get("amount_usd") or 0) * 100))
            or None,
        }
        try:
            result = apply_checkout_session(
                synthetic,
                event_id=f"claim_{(row.get('event_id') or session_id or email)}",
            )
        except ValueError as exc:
            patch_ledger_entries(
                match_status="pending_user",
                email=email,
                session_id=session_id or None,
                patch={"status": "claim_failed", "message": str(exc), "user_id": user["id"]},
            )
            continue
        if result.get("applied") or result.get("duplicate"):
            patch_ledger_entries(
                match_status="pending_user",
                email=email,
                session_id=session_id or None,
                patch={"status": "claimed", "user_id": user["id"], "claim_result": result.get("message")},
            )
            claimed.append(
                {
                    "kind": result.get("kind") or kind,
                    "message": result.get("message"),
                    "session_id": session_id,
                }
            )

    refreshed = auth_store.get_user(user["id"]) or user
    return claimed, refreshed


def apply_creator_wallet_to_project(
    user: dict[str, Any],
    *,
    project_id: str,
    amount_usd: float | None = None,
) -> dict[str, Any]:
    """Move portable Creator wallet funds onto a project budget_usd."""
    import auth as auth_store
    import projects as project_store

    if not user or not user.get("id"):
        raise ValueError("Sign in required")
    pid = (project_id or "").strip()
    if not pid:
        raise ValueError("project_id required")
    project = project_store.get_project(pid)
    if not project:
        raise ValueError(f"Project not found: {pid}")
    if not project_store.user_owns_project(project, user):
        raise ValueError("Only the project owner can fund this project wallet")

    balance = float(user.get("creator_wallet_usd") or 0)
    if balance <= 0:
        raise ValueError("Creator wallet is empty — top up first")
    amount = float(amount_usd) if amount_usd is not None else balance
    if amount <= 0:
        raise ValueError("Amount must be positive")
    if amount > balance + 1e-9:
        raise ValueError(f"Insufficient Creator wallet balance (${balance:.2f})")

    auth_store.debit_creator_wallet(user["id"], amount)
    project_out = project_store.credit_project_budget(pid, amount)
    updated = auth_store.get_user(user["id"])
    entry = append_ledger(
        {
            "kind": "wallet_apply",
            "status": "applied",
            "user_id": user["id"],
            "email": user.get("email"),
            "amount_usd": amount,
            "project_id": pid,
            "destinations": [f"project:{pid}"],
            "message": f"Applied ${amount:.2f} from Creator wallet to project.",
        }
    )
    return {
        "ok": True,
        "amount_usd": amount,
        "user": updated,
        "project": project_out,
        "ledger": entry,
        "message": f"${amount:.2f} moved to project budget.",
    }


def create_billing_portal_session(
    user: dict[str, Any],
    *,
    return_path: str = "/pricing",
) -> dict[str, Any]:
    """Stripe Customer Portal — cancel, update payment method, invoices."""
    status = billing_status()
    if not status["configured"]:
        return {
            "ok": False,
            "scaffold": True,
            "url": None,
            "message": "Stripe is not configured — set STRIPE_SECRET_KEY to open the billing portal.",
            "status": status,
        }
    if not user or not user.get("id"):
        raise ValueError("Sign in required")
    customer_id = (user.get("stripe_customer_id") or "").strip()
    if not customer_id:
        raise ValueError("No Stripe customer on this account — subscribe to Hunter AI first")

    try:
        import stripe
    except ImportError as exc:
        raise RuntimeError("stripe package not installed") from exc

    stripe.api_key = _stripe_secret()
    path = return_path if return_path.startswith("/") else "/pricing"
    session = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=f"{_app_base_url()}{path}",
    )
    return {
        "ok": True,
        "scaffold": False,
        "url": session.url,
        "message": "Redirecting to Stripe Customer Portal…",
    }


def entitlements_for_user(user: dict[str, Any] | None) -> dict[str, Any]:
    """Public summary of billing entitlements for /api/billing/me."""
    if not user:
        return {
            "authenticated": False,
            "membership_active": False,
            "hunter_ai_tier_usd": 0,
            "creator_wallet_usd": 0,
            "can_manage_subscription": False,
        }
    return {
        "authenticated": True,
        "membership_active": bool(user.get("membership_active")),
        "membership_status": user.get("membership_status") or "",
        "hunter_ai_tier_usd": float(user.get("hunter_ai_tier_usd") or 0),
        "membership_period_end": user.get("membership_period_end") or "",
        "creator_wallet_usd": float(user.get("creator_wallet_usd") or 0),
        "stripe_customer_id": bool(user.get("stripe_customer_id")),
        "stripe_subscription_id": bool(user.get("stripe_subscription_id")),
        "can_manage_subscription": bool(user.get("stripe_customer_id")),
    }
