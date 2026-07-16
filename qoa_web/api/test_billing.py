"""Billing scaffold tests (no live Stripe calls)."""

from __future__ import annotations

import billing


def test_billing_status_unconfigured(monkeypatch):
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
    st = billing.billing_status()
    assert st["configured"] is False
    assert st["provider"] == "stripe"


def test_checkout_scaffold_without_key(monkeypatch):
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
    out = billing.create_checkout_session("membership")
    assert out["scaffold"] is True
    assert out["url"] is None
    assert "Stripe" in out["message"]


def test_checkout_rejects_bad_kind():
    try:
        billing.create_checkout_session("nope")
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "membership" in str(exc)


def test_webhook_scaffold_without_secret(monkeypatch):
    monkeypatch.delenv("STRIPE_WEBHOOK_SECRET", raising=False)
    out = billing.handle_webhook(b"{}", None)
    assert out["ok"] is True
    assert out["scaffold"] is True
