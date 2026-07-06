const $ = (sel) => document.querySelector(sel);

(function gateInviteTrial() {
  if (window.QoaInviteGate?.requireInviteTrialOrRedirect("/welcome")) {
    /* ok */
  }
})();

function showTrialBadge() {
  const el = $("#signin-trial-badge");
  if (!el || !window.QoaInviteGate?.isInviteTrialValid()) return;
  const trial = window.QoaInviteGate.getInviteTrial();
  const days = window.QoaInviteGate.inviteTrialDaysLeft();
  const label = trial?.batch_label ? ` · ${trial.batch_label}` : "";
  el.hidden = false;
  el.textContent = `Trial: ${days} day(s) left${label}`;
}

function roleBadgeClass(profile) {
  if (profile.role === "new-user") return "signin-badge-newcomer";
  if (profile.admin) return "signin-badge-admin";
  if (profile.role.startsWith("consultant")) return "signin-badge-hitl";
  if (profile.dualRole) return "signin-badge-dual";
  return "signin-badge-client";
}

function roleBadgeText(profile) {
  if (profile.role === "new-user") return "New user";
  if (profile.admin) return "Admin";
  if (profile.consultantTier === "senior") return "Senior QA Hunter";
  if (profile.consultantTier === "bounty") return "Bug bounty";
  if (profile.role.startsWith("consultant")) return "QA Hunter";
  if (profile.dualRole) return "Creator + QA Hunter";
  if (profile.aiLocked) return "Manual only";
  if (profile.techLevel === "engineer") return "Power user";
  return "Creator";
}

function renderProfiles() {
  const grid = $("#signin-grid");
  if (!grid) return;
  const activeId = localStorage.getItem(STORAGE_PROFILE);

  grid.innerHTML = TEST_PROFILES.map((p) => {
    return (
      `<article class="signin-card signin-accent-${p.accent}${p.id === activeId ? " signin-card-active" : ""}" data-profile-id="${p.id}">` +
      `<div class="signin-card-head">` +
      `<span class="signin-code">${p.code}</span>` +
      `<span class="signin-badge ${roleBadgeClass(p)}">${roleBadgeText(p)}</span>` +
      `</div>` +
      `<h2 class="signin-name">${p.name}</h2>` +
      `<p class="signin-title">${p.title}</p>` +
      `<div class="signin-blurb-wrap" hidden>` +
      `<p class="signin-blurb">${p.blurb}</p>` +
      `</div>` +
      `<button type="button" class="signin-more linkish" data-profile-id="${p.id}" aria-expanded="false">More…</button>` +
      `<button type="button" class="signin-select primary" data-profile-id="${p.id}">` +
      (p.id === activeId ? "Continue as this profile" : "Sign in") +
      `</button>` +
      `</article>`
    );
  }).join("");

  grid.querySelectorAll(".signin-select").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      selectProfile(btn.dataset.profileId);
    });
  });

  grid.querySelectorAll(".signin-card").forEach((card) => {
    card.addEventListener("click", (e) => {
      if (e.target.closest(".signin-more, .signin-select")) return;
      selectProfile(card.dataset.profileId);
    });
  });

  grid.querySelectorAll(".signin-more").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      const card = btn.closest(".signin-card");
      const wrap = card?.querySelector(".signin-blurb-wrap");
      if (!wrap) return;
      const open = wrap.hidden;
      wrap.hidden = !open;
      btn.setAttribute("aria-expanded", open ? "true" : "false");
      btn.textContent = open ? "Less" : "More…";
    });
  });
}

function selectProfile(id) {
  const profile = getProfileById(id);
  if (!profile) return;
  saveProfile(id);
  localStorage.setItem("qoa_web_avatar", profile.defaultAvatar);
  const params = new URLSearchParams(location.search);
  const suite = params.get("suite");
  if (profile.landing === "signin" || profile.role === "new-user") {
    localStorage.removeItem("qoa_web_suite");
    localStorage.removeItem("qoa_web_project_id");
  } else if (suite) {
    localStorage.setItem("qoa_web_suite", suite);
  }
  if (profile.landing === "admin") {
    location.href = "/admin";
    return;
  }
  location.href = suite && profile.landing !== "signin" ? `/app?suite=${encodeURIComponent(suite)}` : "/app";
}

function bindReset() {
  $("#signin-reset")?.addEventListener("click", () => {
    localStorage.removeItem(STORAGE_PROFILE);
    localStorage.removeItem("qoa_web_avatar");
    localStorage.removeItem("qoa_web_project_id");
    localStorage.removeItem("qoa_web_suite");
    renderProfiles();
  });
}

renderProfiles();
bindReset();
showTrialBadge();

(function autoProfileFromQuery() {
  const params = new URLSearchParams(location.search);
  let pid = params.get("profile");
  if (!pid) return;
  pid = pid.toLowerCase();
  if (!pid.startsWith("p")) pid = `p${pid}`;
  if (getProfileById(pid)) selectProfile(pid);
})();
