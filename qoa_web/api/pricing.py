"""QA on Air pricing, wallet, and earnings rules (single source of truth)."""

from __future__ import annotations

from typing import Any

# Free: anyone. Hunter AI plans: $5 / $20 / $50. Creator wallet: $50+.
MEMBERSHIP_USD_PER_MONTH = 5.0  # default Hunter AI tier (compat)
HUNTER_AI_TIERS_USD = (5.0, 20.0, 50.0)
# Hosted AI monthly token caps by Hunter AI subscription tier
HUNTER_AI_TOKEN_CAPS: dict[float, int] = {
    5.0: 500_000,
    20.0: 2_000_000,
    50.0: 5_000_000,
}
CREATOR_WALLET_MIN_USD = 50.0
PLATFORM_FEE_PCT = 5
ADMIN_OPS_PCT = 10
PROMOTER_SHARE_PCT = 5  # from Creator deposits and from Hunter earnings
PAYOUT_THRESHOLD_USD = 100.0


def hunter_ai_token_cap(tier_usd: float | None) -> int | None:
    """Return hosted monthly token cap for an active Hunter AI tier, or None if free."""
    if tier_usd is None:
        return None
    tier = float(tier_usd)
    if tier in HUNTER_AI_TOKEN_CAPS:
        return HUNTER_AI_TOKEN_CAPS[tier]
    # nearest known tier
    if tier <= 0:
        return None
    closest = min(HUNTER_AI_TIERS_USD, key=lambda t: abs(t - tier))
    return HUNTER_AI_TOKEN_CAPS.get(closest)


def split_deposit(budget_usd: float, automation_pct: int = 50, human_pct: int = 50) -> dict[str, Any]:
    """Split a Creator QA wallet deposit after platform, ops, and promoter shares.

    Order: platform → ops → promoter (Creator side) → remaining net pool
    (Creator chooses AI vs Hunter split of the net pool on Build).
    """
    budget = max(0.0, float(budget_usd))
    platform_usd = round(budget * PLATFORM_FEE_PCT / 100, 2)
    admin_ops_usd = round(budget * ADMIN_OPS_PCT / 100, 2)
    promoter_usd = round(budget * PROMOTER_SHARE_PCT / 100, 2)
    net_usd = round(max(0.0, budget - platform_usd - admin_ops_usd - promoter_usd), 2)
    auto_pct = int(automation_pct)
    human_pct = int(human_pct)
    if auto_pct + human_pct <= 0:
        auto_pct, human_pct = 50, 50
    total_split = auto_pct + human_pct
    ai_usd = round(net_usd * auto_pct / total_split, 2)
    human_usd = round(net_usd * human_pct / total_split, 2)
    # Promoter also takes 5% of Hunter (human) pool earnings — illustrated for transparency
    promoter_from_human_usd = round(human_usd * PROMOTER_SHARE_PCT / 100, 2)
    hunter_net_usd = round(max(0.0, human_usd - promoter_from_human_usd), 2)
    return {
        "budget_usd": budget,
        "platform_fee_pct": PLATFORM_FEE_PCT,
        "platform_fee_usd": platform_usd,
        "admin_ops_pct": ADMIN_OPS_PCT,
        "admin_ops_usd": admin_ops_usd,
        "promoter_pct": PROMOTER_SHARE_PCT,
        "promoter_usd": promoter_usd,
        "promoter_from_hunter_earnings_pct": PROMOTER_SHARE_PCT,
        "promoter_from_human_usd": promoter_from_human_usd,
        "hunter_net_usd": hunter_net_usd,
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
        "hunter_ai_tiers_usd": list(HUNTER_AI_TIERS_USD),
        "creator_wallet_min_usd": CREATOR_WALLET_MIN_USD,
        "platform_fee_pct": PLATFORM_FEE_PCT,
        "admin_ops_pct": ADMIN_OPS_PCT,
        "promoter_share_pct": PROMOTER_SHARE_PCT,
        "promoter_from_hunter_earnings_pct": PROMOTER_SHARE_PCT,
        "payout_threshold_usd": PAYOUT_THRESHOLD_USD,
        "wallet_balance_usd": round(balance, 2),
        "payout_eligible": balance >= PAYOUT_THRESHOLD_USD,
        "payout_remaining_usd": round(max(0.0, PAYOUT_THRESHOLD_USD - balance), 2),
        "example_deposit_split": example,
        "project_deposit_split": project_split,
        "plans": {
            "free": {
                "id": "free",
                "name": "Free",
                "price_usd": 0,
                "unit": "",
                "blurb": "Anyone can start BRAHL — limited hosted AI, or bring your own OpenAI key.",
            },
            "hunter_ai": {
                "id": "hunter_ai",
                "name": "QA Hunter AI",
                "tiers_usd": list(HUNTER_AI_TIERS_USD),
                "unit": "/mo",
                "blurb": "Hosted AI and tools across multiple projects — upgrade as you use more AI.",
            },
            "creator_wallet": {
                "id": "creator_wallet",
                "name": "Creator wallet",
                "min_usd": CREATOR_WALLET_MIN_USD,
                "unit": "+",
                "blurb": "Fund your challenge. You choose how the net pool splits between AI and QA Hunters.",
            },
            "promoter": {
                "id": "promoter",
                "name": "Promoter",
                "share_pct": PROMOTER_SHARE_PCT,
                "blurb": (
                    f"{PROMOTER_SHARE_PCT}% of referred Creator deposits and "
                    f"{PROMOTER_SHARE_PCT}% of referred QA Hunter earnings."
                ),
            },
        },
        "earn_tasks": [
            {
                "id": "qa_hunt",
                "title": "QA Hunting",
                "description": "Join challenges, run FoXYiZ, submit BRAHL reports — earn from the human pool.",
            },
            {
                "id": "promote",
                "title": "Promoting",
                "description": "Invite Creators and Hunters — earn a 5% share from both sides.",
            },
        ],
        "payout_options": [
            {
                "title": "Cash out at $100",
                "detail": (
                    f"When your wallet balance reaches ${PAYOUT_THRESHOLD_USD:.0f} equivalent, "
                    "you can request a cash-out (Stripe payouts when enabled on the host)."
                ),
            },
            {
                "title": "Spend on your own QA",
                "detail": (
                    "Apply wallet balance toward Creator QA for your own apps instead of withdrawing — "
                    "hunt your builds or fund automation without a cash transfer."
                ),
            },
            {
                "title": "QA Hunter earnings path",
                "detail": (
                    "Deliverables credit the human pool → your wallet. From there: hold to threshold, "
                    "cash out, or spend on your own Creator challenges."
                ),
            },
            {
                "title": "Promoter share accrual",
                "detail": (
                    f"Referrers earn {PROMOTER_SHARE_PCT}% of Creator wallet top-ups they brought in, "
                    f"plus {PROMOTER_SHARE_PCT}% of QA Hunter earnings from hunters they invited. "
                    "Credits land in the Promoter wallet toward the same payout rules."
                ),
            },
            {
                "title": "Timing",
                "detail": (
                    "Live payouts require Stripe Connect (or similar) on the host. Until then, balances "
                    "are tracked in BRAHL; checkout and cash-out stay scaffolded."
                ),
            },
        ],
        "summary": (
            f"Free to start · Hunter AI ${HUNTER_AI_TIERS_USD[0]:.0f}/"
            f"${HUNTER_AI_TIERS_USD[1]:.0f}/${HUNTER_AI_TIERS_USD[2]:.0f} · "
            f"Creator wallets from ${CREATOR_WALLET_MIN_USD:.0f} · "
            f"Promoters {PROMOTER_SHARE_PCT}% both sides."
        ),
    }
