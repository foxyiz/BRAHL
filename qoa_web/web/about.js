const CLIENT_PROMPTS = [
  "You Build, We QA — let's BRAHL! I'm the Champion posting my challenge to the arena.",
  "Go/No-Go before launch — I need the green scorecard, not guesswork.",
  "Our last build changed — baseline the old version, verify the new, then BRAHL it.",
  "P2P marketplace: I set budget, QA Hunters hunt defects — minimal middleman.",
  "Run FoXYiZ automation — then bring Contenders for UX evidence and hunt recordings.",
  "Sometimes I build, sometimes I hunt — same arena, different avatar.",
  "Perfect-quality launch is the vision — version compare old vs new in every report.",
];

const CONSULTANT_PROMPTS = [
  "Ships are sinking — I'm the Contender hunting bugs before premature launch.",
  "Human QA + Automation + AI — hunt evidence, screenshots, screen recordings.",
  "Direct P2P with Creators — fair pay from the human pool, not a gig middleman.",
  "I'll BRAHL it: join your challenge, cover stories automation skips, submit the report.",
  "Bug-bounty mindset with recordings Creators can replay in Heal.",
  "Sometimes you're the builder, sometimes the tester — I love both sides of the arena.",
  "Enriched BRAHL reports Creators trust — defect teams, not checkbox QA.",
];

function buildMarquee(containerId, prompts) {
  const el = document.getElementById(containerId);
  if (!el) return;
  const items = prompts
    .map((text) => `<span class="story-marquee-item">${escapeHtml(text)}</span>`)
    .join("");
  el.innerHTML = items + items;
}

function escapeHtml(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function setText(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = value;
}

async function loadEcosystem() {
  try {
    const res = await fetch("/api/about/ecosystem");
    if (!res.ok) throw new Error("stats unavailable");
    const { ecosystem: e, gtm } = await res.json();
    const c = e.clients || {};
    const h = e.consultants || {};
    const b = e.brahl || {};
    const a77 = e.atomic77 || {};
    const s = e.satisfaction || {};

    setText("stat-client-score", s.client_score != null ? `${s.client_score}%` : "—");
    setText("stat-consultant-score", s.consultant_score != null ? `${s.consultant_score}%` : "—");
    if (s.headline) setText("stat-satisfaction-headline", s.headline);

    setText("stat-clients", c.count ?? "0");
    setText("stat-active", c.active_building ?? "0");
    setText("stat-chat", c.chat_messages ?? "0");
    setText("stat-rebuilds", c.change_requests ?? "0");
    setText("stat-verify", c.projects_with_verify ?? "0");
    setText("stat-cycles", b.cycle_events ?? "0");
    setText("stat-hitl-joined", h.joined ?? "0");
    setText("stat-hitl-invites", h.invites_sent ?? "0");
    setText("stat-stories", c.hitl_stories ?? "0");
    setText("stat-budget", c.budget_usd != null ? c.budget_usd.toLocaleString() : "0");
    setText("stat-a77-msgs", a77.messages ?? "0");
    setText("stat-a77-tokens", a77.tokens_est != null ? a77.tokens_est.toLocaleString() : "0");
    if (gtm) {
      setText("stat-gtm-batches", gtm.batch_count ?? "0");
      setText("stat-gtm-redeemed", gtm.redeemed_count ?? "0");
      setText("stat-gtm-trials", gtm.active_trials ?? "0");
    }

    const updated = document.getElementById("about-updated");
    if (updated) updated.textContent = `Live stats · ${new Date().toLocaleString()}`;
  } catch {
    const updated = document.getElementById("about-updated");
    if (updated) updated.textContent = "Stats offline — start qoa_web locally";
  }
}

buildMarquee("client-marquee", CLIENT_PROMPTS);
buildMarquee("consultant-marquee", CONSULTANT_PROMPTS);
loadEcosystem();
loadAdminInvites();
bindGtmAdmin();

async function loadAdminInvites() {
  const tbody = document.getElementById("admin-gtm-batches-body");
  const redemptionsEl = document.getElementById("admin-gtm-redemptions");
  if (!tbody) return;
  try {
    const res = await fetch("/api/admin/invites");
    if (!res.ok) throw new Error("Admin invites unavailable (set QOA_ADMIN_TOKEN on remote)");
    const data = await res.json();
    const batches = data.batches || [];
    tbody.innerHTML = batches.length
      ? batches
          .map((b) => {
            const created = (b.created_at || "").slice(0, 10);
            return (
              `<tr>` +
              `<td><strong>${escapeHtml(b.label || b.id)}</strong><br /><span class="meta">${escapeHtml(b.id)}</span></td>` +
              `<td>${escapeHtml(b.batch_type === "creator" ? "Creator" : "QA Hunter")}</td>` +
              `<td>${b.size ?? "—"}</td>` +
              `<td>${b.trial_days ?? 7}d</td>` +
              `<td>${escapeHtml(created)}</td>` +
              `<td><a href="/api/admin/invites/export?batch_id=${encodeURIComponent(b.id)}" download>CSV</a></td>` +
              `</tr>`
            );
          })
          .join("")
      : `<tr><td colspan="6" class="meta">No batches yet — generate one below.</td></tr>`;

    const recent = data.recent_redemptions || [];
    if (redemptionsEl) {
      redemptionsEl.innerHTML = recent.length
        ? recent
            .map(
              (r) =>
                `<li><code>${escapeHtml(r.code)}</code> · ${escapeHtml(r.batch_type)} · ${escapeHtml((r.redeemed_at || "").slice(0, 16))}${r.email ? ` · ${escapeHtml(r.email)}` : ""}</li>`
            )
            .join("")
        : `<li class="meta">No redemptions yet.</li>`;
    }
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="6" class="meta">${escapeHtml(err.message)}</td></tr>`;
    if (redemptionsEl) redemptionsEl.innerHTML = `<li class="meta">${escapeHtml(err.message)}</li>`;
  }
}

function bindGtmAdmin() {
  const status = document.getElementById("admin-gtm-status");
  async function generate(batchType, label) {
    if (status) status.textContent = `Generating ${batchType} batch…`;
    try {
      const res = await fetch("/api/admin/invites/batch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ batch_type: batchType, label, count: 50, trial_days: 7 }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Batch failed");
      if (status) {
        status.textContent = `Created ${data.codes?.length || 50} codes. Sample link: ${location.origin}${data.sample_link || ""}`;
      }
      loadAdminInvites();
      loadEcosystem();
    } catch (err) {
      if (status) status.textContent = err.message || "Could not generate batch";
    }
  }
  document.getElementById("btn-gtm-creators")?.addEventListener("click", () =>
    generate("creator", `Creator launch ${new Date().toISOString().slice(0, 10)}`)
  );
  document.getElementById("btn-gtm-hunters")?.addEventListener("click", () =>
    generate("consultant", `QA Hunter launch ${new Date().toISOString().slice(0, 10)}`)
  );
  document.getElementById("btn-gtm-refresh")?.addEventListener("click", () => {
    loadAdminInvites();
    loadEcosystem();
  });
}

if (location.pathname.endsWith("/admin") || location.hash === "#about-admin-title") {
  const adminEl = document.getElementById("about-admin-title");
  if (adminEl) {
    requestAnimationFrame(() => adminEl.scrollIntoView({ behavior: "smooth", block: "start" }));
  }
}
