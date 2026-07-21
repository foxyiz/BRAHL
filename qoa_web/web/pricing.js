(() => {
  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => Array.from(document.querySelectorAll(sel));
  const statusEl = $("#pricing-status");
  const STORAGE_AUTH_TOKEN = "qoa_auth_token";
  let hunterTierUsd = 5;
  let entitlements = { authenticated: false, projects: [] };

  function setStatus(msg, isErr) {
    if (!statusEl) return;
    statusEl.textContent = msg || "";
    statusEl.classList.toggle("err", Boolean(isErr));
  }

  function authHeaders() {
    const headers = { "Content-Type": "application/json" };
    const token = localStorage.getItem(STORAGE_AUTH_TOKEN);
    if (token) headers.Authorization = `Bearer ${token}`;
    return headers;
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  async function api(path, opts = {}) {
    const res = await fetch(path, {
      headers: { ...authHeaders(), ...(opts.headers || {}) },
      ...opts,
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const detail = data.detail || data.error || res.statusText;
      throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
    }
    return data;
  }

  function setHunterTier(usd) {
    hunterTierUsd = Number(usd) || 5;
    const price = $("#tier-hunter-price");
    if (price) price.textContent = `$${hunterTierUsd}`;
    $$(".pricing-tier-chip").forEach((chip) => {
      const on = Number(chip.dataset.tierUsd) === hunterTierUsd;
      chip.classList.toggle("active", on);
      chip.setAttribute("aria-pressed", on ? "true" : "false");
    });
  }

  function fillProjectSelect(select, projects, includePortable) {
    if (!select) return;
    const opts = [];
    if (includePortable) {
      opts.push('<option value="">Creator wallet (portable)</option>');
    }
    (projects || []).forEach((p) => {
      opts.push(
        `<option value="${escapeHtml(p.id)}">${escapeHtml(p.name || p.id)} · $${Number(
          p.budget_usd || 0
        ).toFixed(0)}</option>`
      );
    });
    select.innerHTML = opts.join("");
  }

  function renderPricing(p) {
    const walletMin = Math.round(p.creator_wallet_min_usd ?? 50);
    const promoterPct = p.promoter_share_pct ?? 5;
    const tiers = p.hunter_ai_tiers_usd || [5, 20, 50];

    const summary = $("#pricing-summary");
    if (summary) summary.textContent = p.summary || "Free to start · Hunter AI · Creator wallets.";

    const plans = p.plans || {};
    const setText = (id, text) => {
      const el = $(id);
      if (el && text != null) el.textContent = text;
    };
    setText("#plan-free-blurb", plans.free?.blurb);
    setText("#plan-hunter-blurb", plans.hunter_ai?.blurb);
    setText("#plan-creator-blurb", plans.creator_wallet?.blurb);
    setText("#plan-promoter-blurb", plans.promoter?.blurb);
    setText("#tier-wallet-min", `$${walletMin}`);
    setText("#tier-wallet-min-copy", `$${walletMin}`);
    setText("#tier-promoter-pct", String(promoterPct));

    const walletInput = $("#wallet-amount");
    if (walletInput) {
      walletInput.min = String(walletMin);
      walletInput.value = String(walletMin);
    }

    $$(".pricing-tier-chip").forEach((chip, i) => {
      if (tiers[i] != null) {
        chip.dataset.tierUsd = String(tiers[i]);
        chip.textContent = `$${tiers[i]}`;
      }
    });
    setHunterTier(tiers[0] ?? 5);

    const payoutList = $("#pricing-payout-list");
    if (payoutList && Array.isArray(p.payout_options)) {
      payoutList.innerHTML = p.payout_options
        .map((x) => {
          if (typeof x === "string") return `<li>${escapeHtml(x)}</li>`;
          return (
            `<li><strong>${escapeHtml(x.title || "")}</strong>` +
            (x.detail ? `<span>${escapeHtml(x.detail)}</span>` : "") +
            `</li>`
          );
        })
        .join("");
    }

    const ex = p.example_deposit_split;
    if (ex) {
      const blurb = $("#pricing-example-blurb");
      if (blurb) {
        blurb.textContent =
          `Deposit $${ex.budget_usd}: platform $${ex.platform_fee_usd} (${ex.platform_fee_pct}%), ` +
          `ops $${ex.admin_ops_usd} (${ex.admin_ops_pct}%), ` +
          `promoter $${ex.promoter_usd} (${ex.promoter_pct}%), ` +
          `net pool $${ex.net_pool_usd} (you choose AI $${ex.ai_cost_usd} · Hunter $${ex.human_payout_usd}). ` +
          `Of the Hunter pool, promoter also earns $${ex.promoter_from_human_usd} (${ex.promoter_from_hunter_earnings_pct}%) → hunter net $${ex.hunter_net_usd}.`;
      }
      const bar = $("#pricing-split-bar");
      if (bar) {
        bar.hidden = false;
        $("#split-platform").style.flex = String(ex.platform_fee_usd || 1);
        $("#split-ops").style.flex = String(ex.admin_ops_usd || 1);
        const prom = $("#split-promoter");
        if (prom) prom.style.flex = String(ex.promoter_usd || 1);
        $("#split-ai").style.flex = String(ex.ai_cost_usd || 1);
        $("#split-human").style.flex = String(ex.human_payout_usd || 1);
      }
      const legend = $("#pricing-split-legend");
      if (legend) {
        legend.innerHTML =
          `<li>Platform ${ex.platform_fee_pct}% · $${ex.platform_fee_usd}</li>` +
          `<li>Ops ${ex.admin_ops_pct}% · $${ex.admin_ops_usd}</li>` +
          `<li>Promoter ${ex.promoter_pct}% · $${ex.promoter_usd}</li>` +
          `<li>AI pool (your split) · $${ex.ai_cost_usd}</li>` +
          `<li>Hunter pool (your split) · $${ex.human_payout_usd}` +
          ` <span class="pricing-legend-note">(promoter ${ex.promoter_from_hunter_earnings_pct}% of this → hunter net $${ex.hunter_net_usd})</span></li>`;
      }
    }
  }

  async function loadBillingStatus() {
    const note = $("#pricing-billing-note");
    try {
      const st = await api("/api/billing/status");
      if (!note) return st;
      note.hidden = false;
      if (st.configured) {
        note.classList.remove("warn");
        note.textContent =
          "Stripe is configured — subscribe or top up; webhooks unlock membership and wallet credits.";
      } else {
        note.classList.add("warn");
        note.textContent =
          st.note ||
          "Stripe keys are not set yet — Checkout shows a setup message. Use Free / invite trial to start.";
      }
      return st;
    } catch {
      if (note) {
        note.hidden = false;
        note.classList.add("warn");
        note.textContent = "Billing status unavailable — you can still start free.";
      }
      return { configured: false };
    }
  }

  async function loadEntitlements() {
    const el = $("#membership-entitlement");
    const wrap = $("#wallet-project-wrap");
    const select = $("#wallet-project");
    const portalBtn = $("#btn-billing-portal");
    const applyWrap = $("#wallet-apply-wrap");
    try {
      const me = await api("/api/billing/me");
      entitlements = me;
      if (Array.isArray(me.claimed) && me.claimed.length) {
        setStatus(me.claimed.map((c) => c.message || "Entitlement claimed").join(" · "));
      }
      if (!me.authenticated) {
        if (el) {
          el.hidden = false;
          el.textContent = "Sign in before Checkout so your plan is linked to your account.";
        }
        if (wrap) wrap.hidden = true;
        if (portalBtn) portalBtn.hidden = true;
        if (applyWrap) applyWrap.hidden = true;
        return me;
      }
      if (el) {
        el.hidden = false;
        if (me.membership_active) {
          el.textContent =
            `Active: Hunter AI $${Number(me.hunter_ai_tier_usd || 0).toFixed(0)}/mo` +
            (me.membership_period_end
              ? ` · period ends ${String(me.membership_period_end).slice(0, 10)}`
              : "");
        } else if (me.membership_status) {
          el.textContent = `Membership status: ${me.membership_status}`;
        } else {
          el.textContent =
            `Signed in · Creator wallet $${Number(me.creator_wallet_usd || 0).toFixed(0)}` +
            " · pick a plan below to subscribe.";
        }
      }
      if (portalBtn) {
        portalBtn.hidden = !me.can_manage_subscription;
      }
      const projects = Array.isArray(me.projects) ? me.projects : [];
      if (wrap && select && projects.length) {
        wrap.hidden = false;
        fillProjectSelect(select, projects, true);
      } else if (wrap) {
        wrap.hidden = true;
      }

      const bal = Number(me.creator_wallet_usd || 0);
      if (applyWrap && bal > 0 && projects.length) {
        applyWrap.hidden = false;
        const note = $("#wallet-balance-note");
        if (note) note.textContent = `Portable Creator wallet: $${bal.toFixed(2)}`;
        fillProjectSelect($("#wallet-apply-project"), projects, false);
        const amt = $("#wallet-apply-amount");
        if (amt) {
          amt.max = String(bal);
          amt.value = String(Math.floor(bal));
        }
      } else if (applyWrap) {
        applyWrap.hidden = true;
      }
      return me;
    } catch {
      if (el) {
        el.hidden = false;
        el.textContent = "Sign in before Checkout so entitlements land on your account.";
      }
      if (portalBtn) portalBtn.hidden = true;
      if (applyWrap) applyWrap.hidden = true;
      return { authenticated: false };
    }
  }

  async function startCheckout(kind) {
    setStatus("");
    const token = localStorage.getItem(STORAGE_AUTH_TOKEN);
    if (!token) {
      setStatus("Sign in first so Stripe can unlock your membership or wallet after payment.", true);
      return;
    }
    const body = { kind };
    if (kind === "wallet") {
      body.amount_usd = Number($("#wallet-amount")?.value || 50);
      const projectId = ($("#wallet-project")?.value || "").trim();
      if (projectId) body.project_id = projectId;
    } else if (kind === "membership") {
      body.amount_usd = hunterTierUsd;
    }
    const btn =
      kind === "wallet" ? $("#btn-checkout-wallet") : $("#btn-checkout-membership");
    if (btn) btn.disabled = true;
    try {
      const data = await api("/api/billing/checkout", {
        method: "POST",
        body: JSON.stringify(body),
      });
      if (data.url) {
        setStatus("Redirecting to Stripe Checkout…");
        window.location.href = data.url;
        return;
      }
      if (data.scaffold) {
        setStatus(
          data.message ||
            "Stripe scaffold only — set STRIPE_SECRET_KEY on the host to enable Checkout.",
          true
        );
        return;
      }
      setStatus(data.message || "No checkout URL returned.", true);
    } catch (e) {
      setStatus(e.message || "Checkout failed", true);
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  async function openBillingPortal() {
    setStatus("");
    const btn = $("#btn-billing-portal");
    if (btn) btn.disabled = true;
    try {
      const data = await api("/api/billing/portal", {
        method: "POST",
        body: JSON.stringify({ return_path: "/pricing" }),
      });
      if (data.url) {
        setStatus("Opening Stripe Customer Portal…");
        window.location.href = data.url;
        return;
      }
      setStatus(data.message || "Billing portal unavailable.", true);
    } catch (e) {
      setStatus(e.message || "Could not open billing portal", true);
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  async function applyWalletToProject() {
    setStatus("");
    const projectId = ($("#wallet-apply-project")?.value || "").trim();
    const amount = Number($("#wallet-apply-amount")?.value || 0);
    if (!projectId) {
      setStatus("Choose a project to fund.", true);
      return;
    }
    const btn = $("#btn-wallet-apply");
    if (btn) btn.disabled = true;
    try {
      const data = await api("/api/billing/wallet/apply", {
        method: "POST",
        body: JSON.stringify({ project_id: projectId, amount_usd: amount }),
      });
      setStatus(data.message || "Wallet applied to project.");
      await loadEntitlements();
    } catch (e) {
      setStatus(e.message || "Could not apply wallet", true);
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  async function boot() {
    try {
      const data = await api("/api/pricing");
      renderPricing(data.pricing || data);
    } catch (e) {
      setStatus(`Could not load pricing rules: ${e.message}`, true);
    }
    await loadBillingStatus();
    await loadEntitlements();

    $("#btn-checkout-membership")?.addEventListener("click", () => startCheckout("membership"));
    $("#btn-checkout-wallet")?.addEventListener("click", () => startCheckout("wallet"));
    $("#btn-billing-portal")?.addEventListener("click", () => openBillingPortal());
    $("#btn-wallet-apply")?.addEventListener("click", () => applyWalletToProject());
    $$(".pricing-tier-chip").forEach((chip) => {
      chip.addEventListener("click", () => setHunterTier(chip.dataset.tierUsd));
    });

    const params = new URLSearchParams(location.search);
    if (params.get("checkout") === "success") {
      setStatus(
        "Checkout completed — thank you. Your membership or wallet updates when Stripe confirms payment."
      );
      await loadEntitlements();
    } else if (params.get("checkout") === "cancel") {
      setStatus("Checkout canceled.", true);
    }
  }

  boot();
})();
