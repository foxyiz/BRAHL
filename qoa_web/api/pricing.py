"""QA on Air pricing, wallet, and earnings rules (single source of truth)."""

from __future__ import annotations

from typing import Any

MEMBERSHIP_USD_PER_MONTH = 5.0
CREATOR_WALLET_MIN_USD = 50.0
PLATFORM_FEE_PCT = 5
ADMIN_OPS_PCT = 10
PAYOUT_THRESHOLD_USD = 100.0


def split_deposit(budget_usd: float, automation_pct: int = 50, human_pct: int = 50) -> dict[str, Any]:
    """Split a Creator QA wallet deposit after platform + ops fees."""
    budget = max(0.0, float(budget_usd))
    platform_usd = round(budget * PLATFORM_FEE_PCT / 100, 2)
    admin_ops_usd = round(budget * ADMIN_OPS_PCT / 100, 2)
    net_usd = round(max(0.0, budget - platform_usd - admin_ops_usd), 2)
    auto_pct = int(automation_pct)
    human_pct = int(human_pct)
    if auto_pct + human_pct <= 0:
        auto_pct, human_pct = 50, 50
    total_split = auto_pct + human_pct
    ai_usd = round(net_usd * auto_pct / total_split, 2)
    human_usd = round(net_usd * human_pct / total_split, 2)
    return {
        "budget_usd": budget,
        "platform_fee_pct": PLATFORM_FEE_PCT,
        "platform_fee_usd": platform_usd,
        "admin_ops_pct": ADMIN_OPS_PCT,
        "admin_ops_usd": admin_ops_usd,
        "net_pool_usd": net_usd,
        "automation_pct": auto_pct,
        "human_pct": human_pct,
        "ai_cost_usd": ai_usd,
        "human_payout_usd": human_usd,
    }


def get_pricing_rules(
    budget_usd: float = 0.0,
    automation_pct: int = 50,
    human_pct: int = 50,
    wallet_balance_usd: float = 0.0,
) -> dict[str, Any]:
    example = split_deposit(CREATOR_WALLET_MIN_USD, automation_pct, human_pct)
    project_split = split_deposit(budget_usd, automation_pct, human_pct) if budget_usd > 0 else None
    balance = max(0.0, float(wallet_balance_usd))
    return {
        "membership_usd_per_month": MEMBERSHIP_USD_PER_MONTH,
        "creator_wallet_min_usd": CREATOR_WALLET_MIN_USD,
        "platform_fee_pct": PLATFORM_FEE_PCT,
        "admin_ops_pct": ADMIN_OPS_PCT,
        "payout_threshold_usd": PAYOUT_THRESHOLD_USD,
        "wallet_balance_usd": round(balance, 2),
        "payout_eligible": balance >= PAYOUT_THRESHOLD_USD,
        "payout_remaining_usd": round(max(0.0, PAYOUT_THRESHOLD_USD - balance), 2),
        "example_deposit_split": example,
        "project_deposit_split": project_split,
        "earn_tasks": [
            {
                "id": "qa_hunt",
                "title": "QA Hunting",
                "description": "Join challenges, run FoXYiZ, submit BRAHL reports — earn from the human pool.",
            },
            {
                "id": "promote",
                "title": "Promoting",
                "description": "Share challenges and grow the arena — XP and wallet credits for user acquisition.",
            },
        ],
        "payout_options": [
            "Cash out when your wallet reaches $100 equivalent.",
            "Apply balance toward QA Hunting your own creations instead of withdrawing.",
        ],
        "summary": (
            f"Every member ~${MEMBERSHIP_USD_PER_MONTH:.0f}/mo · Creators fund QA wallets from "
            f"${CREATOR_WALLET_MIN_USD:.0f}+ · QAonAIR retains {PLATFORM_FEE_PCT}% · "
            f"payouts at ${PAYOUT_THRESHOLD_USD:.0f}+ or spend on QA for your apps."
        ),
    }
