const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => [...document.querySelectorAll(sel)];

const STORAGE_AVATAR = "qoa_web_avatar";

const ROLE_META = {
  client: {
    label: "Creator",
    blurb: "Scope with AI, fund a QA wallet, invite hunters, and ship a Go/No-Go with BRAHL.",
    avatar: "client",
    path: "/app?demo=1",
  },
  consultant: {
    label: "QA Hunter",
    blurb: "Join open challenges, hunt defects, enrich reports, and earn toward payout.",
    avatar: "consultant",
    path: "/app?demo=1",
  },
  promoter: {
    label: "Promoter",
    blurb: "Share invites, grow the arena, and earn XP & wallet credits.",
    avatar: "client",
    path: "/app?demo=1#promoter",
  },
  networker: {
    label: "Nalanda",
    blurb: "Learn, teach, and discuss — coming soon in the Arena menu.",
    avatar: "client",
    path: "/app?demo=1",
  },
};

function selectedRole() {
  const btn = $(".welcome-avatar-btn.active");
  return btn?.dataset.role || "client";
}

function unlockArena() {
  window.QoaInviteGate?.enableDemoBypass?.();
}

function applyRoleToStorage(roleKey) {
  const meta = ROLE_META[roleKey] || ROLE_META.client;
  if (meta.avatar) localStorage.setItem(STORAGE_AVATAR, meta.avatar);
  try {
    localStorage.removeItem("qoa_web_profile");
  } catch {
    /* ignore */
  }
  return meta;
}

function enterArena(roleKey = selectedRole()) {
  unlockArena();
  const meta = applyRoleToStorage(roleKey);
  location.href = meta.path;
}

function syncRoleUi() {
  const key = selectedRole();
  const meta = ROLE_META[key] || ROLE_META.client;
  const blurb = $("#welcome-role-blurb");
  if (blurb) blurb.textContent = meta.blurb;
  const enterBtn = $("#welcome-enter-role");
  if (enterBtn) enterBtn.textContent = `Enter as ${meta.label} →`;
}

function bindAvatars() {
  $$(".welcome-avatar-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      $$(".welcome-avatar-btn").forEach((b) => {
        b.classList.toggle("active", b === btn);
        b.setAttribute("aria-checked", b === btn ? "true" : "false");
      });
      syncRoleUi();
    });
  });
  syncRoleUi();
}

function prefillCodeFromUrl() {
  const params = new URLSearchParams(location.search);
  const code = params.get("code");
  if (!code) return;
  const input = $("#invite-code");
  if (input) input.value = code.trim();
  const details = document.querySelector(".welcome-invite-details");
  if (details) details.open = true;
}

function bindInviteForm() {
  const form = $("#invite-form");
  if (!form) return;
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const status = $("#invite-status");
    const code = $("#invite-code")?.value?.trim();
    const email = $("#invite-email")?.value?.trim() || "";
    if (!code) return;
    if (status) {
      status.hidden = false;
      status.textContent = "Checking invite…";
      status.className = "welcome-status";
    }
    try {
      const res = await fetch("/api/invites/redeem", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code, email }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Invalid invite");
      window.QoaInviteGate?.saveInviteTrial(data.trial);
      if (data.trial?.nalanda_community) {
        localStorage.setItem("qoa_nalanda_community", "1");
      }
      if (status) {
        status.className = "welcome-status welcome-status-ok";
        status.textContent = data.message || "Trial started — opening Arena…";
      }
      applyRoleToStorage(selectedRole());
      setTimeout(() => {
        location.href = ROLE_META[selectedRole()]?.path || "/app?demo=1";
      }, 500);
    } catch (err) {
      if (status) {
        status.className = "welcome-status welcome-status-err";
        status.textContent = err.message || "Could not redeem invite";
      }
    }
  });
}

function bindDemoBypass() {
  $("#welcome-demo-bypass")?.addEventListener("click", () => {
    unlockArena();
    applyRoleToStorage(selectedRole());
    location.href = ROLE_META[selectedRole()]?.path || "/app?demo=1";
  });
}

function showTrialActiveHint() {
  if (!window.QoaInviteGate?.isInviteTrialValid?.()) return;
  const params = new URLSearchParams(location.search);
  if (params.get("code")) return;
  const shell = document.querySelector(".welcome-shell");
  if (!shell) return;
  const days = window.QoaInviteGate.inviteTrialDaysLeft?.() ?? 0;
  const hint = document.createElement("p");
  hint.className = "welcome-trial-hint";
  hint.innerHTML =
    `Trial active${days ? ` (${days} day${days === 1 ? "" : "s"} left)` : ""} — ` +
    `<a href="/app?demo=1">continue in Arena →</a>`;
  shell.insertBefore(hint, shell.querySelector(".welcome-foot-links"));
}

function bindWelcomeAiPrompt() {
  const form = $("#welcome-ai-form");
  if (!form) return;
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const text = $("#welcome-ai-input")?.value?.trim() || "";
    if (!text) {
      $("#welcome-ai-input")?.focus();
      return;
    }
    try {
      sessionStorage.setItem("qoa_draft_requirement", text);
      sessionStorage.setItem("qoa_open_planner", "1");
    } catch {
      /* ignore quota */
    }
    unlockArena();
    const meta = applyRoleToStorage(selectedRole());
    const base = meta.path.split("#")[0];
    if (selectedRole() === "client" || selectedRole() === "consultant") {
      location.href = `${base}${base.includes("?") ? "&" : "?"}planner=1`;
    } else {
      location.href = meta.path;
    }
  });
}

function bindEnterButtons() {
  $("#welcome-enter-arena")?.addEventListener("click", () => enterArena());
  $("#welcome-enter-role")?.addEventListener("click", () => enterArena());
}

bindAvatars();
prefillCodeFromUrl();
bindInviteForm();
bindDemoBypass();
bindWelcomeAiPrompt();
bindEnterButtons();
showTrialActiveHint();
