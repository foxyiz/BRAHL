"""Billing integration tests (no live Stripe calls)."""

from __future__ import annotations

import json

import uuid

import auth
import billing
import projects


def _make_user(email: str, *, name: str = "Test", role: str = "creator") -> dict:
    """Insert a user row without bcrypt (passlib/Python 3.14 incompat)."""
    auth.init_db()
    uid = uuid.uuid4().hex
    with auth._connect() as conn:
        conn.execute(
            """
            INSERT INTO users (
                id, email, password_hash, name, role, created_at,
                first_name, last_name, roles_json, profile_complete
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            """,
            (
                uid,
                email.strip().lower(),
                "test-hash",
                name,
                role,
                auth._now(),
                name,
                "",
                f'["{role}"]',
            ),
        )
        conn.commit()
    user = auth.get_user(uid)
    assert user is not None
    return user


def test_billing_status_unconfigured(monkeypatch):
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
    st = billing.billing_status()
    assert st["configured"] is False
    assert st["provider"] == "stripe"


def test_checkout_scaffold_without_key(monkeypatch):
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
    out = billing.create_checkout_session("membership", customer_email="a@b.co", user_id="u1")
    assert out["scaffold"] is True
    assert out["url"] is None
    assert "Stripe" in out["message"]


def test_checkout_rejects_bad_kind():
    try:
        billing.create_checkout_session("nope", customer_email="a@b.co")
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "membership" in str(exc)


def test_checkout_requires_identity_when_configured(monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_fake_for_identity_check")
    try:
        billing.create_checkout_session("membership", customer_email="a@b.co")
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "sign in" in str(exc).lower()


def test_webhook_scaffold_without_secret(monkeypatch):
    monkeypatch.delenv("STRIPE_WEBHOOK_SECRET", raising=False)
    out = billing.handle_webhook(b"{}", None)
    assert out["ok"] is True
    assert out["scaffold"] is True


def test_apply_membership_checkout(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "DB_PATH", tmp_path / "users.db")
    monkeypatch.setattr(billing, "DATA_DIR", tmp_path)
    monkeypatch.setattr(billing, "LEDGER_FILE", tmp_path / "billing_ledger.json")
    user = _make_user("hunter@example.com", name="Hunter", role="qa_hunter")

    result = billing.apply_checkout_session(
        {
            "id": "cs_test_membership_1",
            "payment_status": "paid",
            "metadata": {
                "qoa_kind": "membership",
                "user_id": user["id"],
                "hunter_ai_tier_usd": "20",
            },
            "customer": "cus_test_1",
            "subscription": "sub_test_1",
            "customer_email": "hunter@example.com",
        },
        event_id="evt_mem_1",
    )
    assert result["ok"] is True
    assert result["applied"] is True
    updated = auth.get_user(user["id"])
    assert updated["membership_active"] is True
    assert updated["hunter_ai_tier_usd"] == 20.0
    assert updated["stripe_customer_id"] == "cus_test_1"
    assert updated["membership_period_end"]  # estimated or fetched

    dup = billing.apply_checkout_session(
        {
            "id": "cs_test_membership_1",
            "metadata": {"qoa_kind": "membership", "user_id": user["id"], "hunter_ai_tier_usd": "20"},
        },
        event_id="evt_mem_1b",
    )
    assert dup["duplicate"] is True


def test_apply_wallet_to_creator_balance(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "DB_PATH", tmp_path / "users.db")
    monkeypatch.setattr(billing, "DATA_DIR", tmp_path)
    monkeypatch.setattr(billing, "LEDGER_FILE", tmp_path / "billing_ledger.json")
    user = _make_user("creator@example.com", name="Creator", role="creator")

    result = billing.apply_checkout_session(
        {
            "id": "cs_test_wallet_1",
            "payment_status": "paid",
            "metadata": {
                "qoa_kind": "wallet",
                "user_id": user["id"],
                "wallet_amount_usd": "50",
            },
            "customer_email": "creator@example.com",
            "amount_total": 5000,
        },
        event_id="evt_wallet_1",
    )
    assert result["ok"] is True
    assert result["applied"] is True
    updated = auth.get_user(user["id"])
    assert updated["creator_wallet_usd"] == 50.0


def test_apply_wallet_to_project(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "DB_PATH", tmp_path / "users.db")
    monkeypatch.setattr(billing, "DATA_DIR", tmp_path)
    monkeypatch.setattr(billing, "LEDGER_FILE", tmp_path / "billing_ledger.json")
    monkeypatch.setattr(projects, "DATA_DIR", tmp_path)
    monkeypatch.setattr(projects, "PROJECTS_FILE", tmp_path / "projects.json")
    monkeypatch.setattr(projects, "UPLOADS_DIR", tmp_path / "uploads")
    user = _make_user("owner@example.com", name="Owner", role="creator")
    project = projects.create_project(
        {
            "name": "Funded app",
            "owner_avatar": "client",
            "owner_user_id": user["id"],
            "budget_usd": 10,
        }
    )

    result = billing.apply_checkout_session(
        {
            "id": "cs_test_wallet_proj",
            "payment_status": "paid",
            "metadata": {
                "qoa_kind": "wallet",
                "user_id": user["id"],
                "project_id": project["id"],
                "wallet_amount_usd": "75",
            },
            "amount_total": 7500,
        },
        event_id="evt_wallet_proj",
    )
    assert result["ok"] is True
    refreshed = projects.get_project(project["id"])
    assert float(refreshed["budget_usd"]) == 85.0
    # Portable wallet unchanged when project is targeted
    assert auth.get_user(user["id"])["creator_wallet_usd"] == 0.0


def test_skip_unpaid_checkout(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "DB_PATH", tmp_path / "users.db")
    monkeypatch.setattr(billing, "DATA_DIR", tmp_path)
    monkeypatch.setattr(billing, "LEDGER_FILE", tmp_path / "billing_ledger.json")
    user = _make_user("unpaid@example.com", name="Unpaid", role="creator")
    result = billing.apply_checkout_session(
        {
            "id": "cs_unpaid",
            "payment_status": "unpaid",
            "metadata": {
                "qoa_kind": "wallet",
                "user_id": user["id"],
                "wallet_amount_usd": "50",
            },
            "amount_total": 5000,
        },
        event_id="evt_unpaid",
    )
    assert result["skipped"] is True
    assert auth.get_user(user["id"])["creator_wallet_usd"] == 0.0


def test_reject_non_owner_project_funding(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "DB_PATH", tmp_path / "users.db")
    monkeypatch.setattr(billing, "DATA_DIR", tmp_path)
    monkeypatch.setattr(billing, "LEDGER_FILE", tmp_path / "billing_ledger.json")
    monkeypatch.setattr(projects, "DATA_DIR", tmp_path)
    monkeypatch.setattr(projects, "PROJECTS_FILE", tmp_path / "projects.json")
    monkeypatch.setattr(projects, "UPLOADS_DIR", tmp_path / "uploads")
    owner = _make_user("owner2@example.com", name="Owner", role="creator")
    hunter = _make_user("hunter2@example.com", name="Hunter", role="qa_hunter")
    project = projects.create_project(
        {"name": "Owned", "owner_user_id": owner["id"], "budget_usd": 0}
    )
    try:
        billing.apply_checkout_session(
            {
                "id": "cs_steal",
                "payment_status": "paid",
                "metadata": {
                    "qoa_kind": "wallet",
                    "user_id": hunter["id"],
                    "project_id": project["id"],
                    "wallet_amount_usd": "50",
                },
                "amount_total": 5000,
            },
            event_id="evt_steal",
        )
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "owner" in str(exc).lower()


def test_claim_pending_entitlements(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "DB_PATH", tmp_path / "users.db")
    monkeypatch.setattr(billing, "DATA_DIR", tmp_path)
    monkeypatch.setattr(billing, "LEDGER_FILE", tmp_path / "billing_ledger.json")
    billing.append_ledger(
        {
            "event_id": "evt_pending",
            "session_id": "cs_pending_mem",
            "kind": "membership",
            "status": "pending_user",
            "email": "later@example.com",
            "metadata": {"qoa_kind": "membership", "hunter_ai_tier_usd": "5"},
        }
    )
    user = _make_user("later@example.com", name="Later", role="qa_hunter")
    claimed, refreshed = billing.claim_pending_entitlements(user)
    assert claimed
    assert refreshed["membership_active"] is True
    assert refreshed["hunter_ai_tier_usd"] == 5.0


def test_apply_creator_wallet_to_project(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "DB_PATH", tmp_path / "users.db")
    monkeypatch.setattr(billing, "DATA_DIR", tmp_path)
    monkeypatch.setattr(billing, "LEDGER_FILE", tmp_path / "billing_ledger.json")
    monkeypatch.setattr(projects, "DATA_DIR", tmp_path)
    monkeypatch.setattr(projects, "PROJECTS_FILE", tmp_path / "projects.json")
    monkeypatch.setattr(projects, "UPLOADS_DIR", tmp_path / "uploads")
    user = _make_user("apply@example.com", name="Apply", role="creator")
    auth.credit_creator_wallet(user["id"], 80)
    user = auth.get_user(user["id"])
    project = projects.create_project(
        {"name": "Target", "owner_user_id": user["id"], "budget_usd": 20}
    )
    out = billing.apply_creator_wallet_to_project(user, project_id=project["id"], amount_usd=50)
    assert out["ok"] is True
    assert float(projects.get_project(project["id"])["budget_usd"]) == 70.0
    assert auth.get_user(user["id"])["creator_wallet_usd"] == 30.0


def test_portal_scaffold_without_key(monkeypatch):
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
    out = billing.create_billing_portal_session(
        {"id": "u1", "stripe_customer_id": "cus_x"},
        return_path="/pricing",
    )
    assert out["scaffold"] is True
    assert out["url"] is None


def test_subscription_cancel_clears_membership(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "DB_PATH", tmp_path / "users.db")
    monkeypatch.setattr(billing, "DATA_DIR", tmp_path)
    monkeypatch.setattr(billing, "LEDGER_FILE", tmp_path / "billing_ledger.json")
    user = _make_user("sub@example.com", name="Sub", role="qa_hunter")
    auth.apply_membership_entitlement(
        user["id"],
        tier_usd=5,
        status="active",
        stripe_customer_id="cus_cancel",
        stripe_subscription_id="sub_cancel",
    )

    result = billing.apply_subscription_event(
        {
            "id": "sub_cancel",
            "status": "canceled",
            "customer": "cus_cancel",
            "metadata": {"user_id": user["id"], "hunter_ai_tier_usd": "5"},
            "current_period_end": 1_700_000_000,
        },
        event_type="customer.subscription.deleted",
        event_id="evt_cancel_1",
    )
    assert result["ok"] is True
    updated = auth.get_user(user["id"])
    assert updated["membership_status"] == "canceled"
    assert updated["membership_active"] is False


def test_entitlements_for_user_shape():
    assert billing.entitlements_for_user(None)["authenticated"] is False
    fake = {
        "membership_active": True,
        "membership_status": "active",
        "hunter_ai_tier_usd": 5,
        "creator_wallet_usd": 12.5,
        "membership_period_end": "",
        "stripe_customer_id": "cus_x",
        "stripe_subscription_id": "sub_x",
    }
    out = billing.entitlements_for_user(fake)
    assert out["authenticated"] is True
    assert out["membership_active"] is True
    assert out["creator_wallet_usd"] == 12.5


def test_ledger_persists(tmp_path, monkeypatch):
    monkeypatch.setattr(billing, "DATA_DIR", tmp_path)
    monkeypatch.setattr(billing, "LEDGER_FILE", tmp_path / "billing_ledger.json")
    billing.append_ledger({"event_id": "evt_a", "status": "applied", "session_id": "cs_a"})
    found = billing.find_ledger_entry(event_id="evt_a")
    assert found is not None
    assert found["session_id"] == "cs_a"
    raw = json.loads((tmp_path / "billing_ledger.json").read_text(encoding="utf-8"))
    assert isinstance(raw, list) and raw
