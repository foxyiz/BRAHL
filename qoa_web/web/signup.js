/* Two-step signup: Google/email → profile → BRAHL */
const $ = (s) => document.querySelector(s);
const $$ = (s) => Array.from(document.querySelectorAll(s));

const state = {
  mode: "email", // email | social
  provider: "",
  email: "",
  password: "",
  token: "",
  user: null,
  googleReady: false,
  authRequired: false,
};

function showError(id, msg) {
  const el = $(id);
  if (!el) return;
  el.hidden = !msg;
  el.textContent = msg || "";
}

function goStep(step) {
  const s1 = $("#signup-step-1");
  const s2 = $("#signup-step-2");
  if (s1) s1.hidden = step !== 1;
  if (s2) s2.hidden = step !== 2;
  $("#step-indicator-1")?.classList.toggle("active", step === 1);
  $("#step-indicator-1")?.classList.toggle("done", step > 1);
  $("#step-indicator-2")?.classList.toggle("active", step === 2);
}

function selectedRoles() {
  return $$('input[name="roles"]:checked').map((el) => el.value);
}

function syncConditional() {
  const roles = selectedRoles();
  const creatorExtra = $("#creator-extra");
  const hunterExtra = $("#hunter-extra");
  if (creatorExtra) creatorExtra.hidden = !roles.includes("creator");
  if (hunterExtra) hunterExtra.hidden = !roles.includes("qa_hunter");
}

function storeAuth(user, token) {
  localStorage.setItem("qoa_auth_token", token);
  localStorage.setItem("qoa_auth_user", JSON.stringify(user));
  state.token = token;
  state.user = user;
}

function enterBrahl() {
  const draft = sessionStorage.getItem("qoa_draft_requirement");
  location.href = draft ? "/app?restore_draft=1" : "/app";
}

function enterGuest() {
  window.QoaInviteGate?.enableDemoBypass?.();
  const draft = sessionStorage.getItem("qoa_draft_requirement");
  location.href = draft ? "/app?demo=1&restore_draft=1" : "/app?demo=1";
}

function syncGuestUi() {
  const showGuest = !state.authRequired;
  const panel = $("#guest-continue");
  if (panel) panel.hidden = !showGuest;
}

function takeAuthTokenFromUrl() {
  const u = new URL(location.href);
  const token = u.searchParams.get("auth_token");
  if (!token) return null;
  u.searchParams.delete("auth_token");
  history.replaceState({}, "", u.pathname + u.search + u.hash);
  return token;
}

async function apiJson(path, opts = {}) {
  const headers = { ...(opts.headers || {}) };
  if (opts.body && !(opts.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }
  if (state.token) headers.Authorization = `Bearer ${state.token}`;
  const res = await fetch(path, { ...opts, headers });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = data.detail;
    const msg = typeof detail === "string" ? detail : Array.isArray(detail) ? detail[0]?.msg : res.statusText;
    throw new Error(msg || res.statusText);
  }
  return data;
}

async function loadProviders() {
  try {
    const [prov, cfg] = await Promise.all([
      apiJson("/api/auth/providers"),
      fetch("/api/config").then((r) => r.json()),
    ]);
    state.googleReady = !!prov.providers?.google;
    state.authRequired = !!cfg.auth_required;
  } catch {
    state.googleReady = false;
    state.authRequired = false;
  }
  syncGuestUi();
}

$("#btn-guest-continue")?.addEventListener("click", enterGuest);
$("#footer-guest")?.addEventListener("click", (e) => {
  e.preventDefault();
  enterGuest();
});
$("#nav-guest-start")?.addEventListener("click", (e) => {
  if (state.authRequired) return;
  e.preventDefault();
  enterGuest();
});

$("#btn-google")?.addEventListener("click", async () => {
  showError("#signup-error-1", "");
  if (!state.googleReady) {
    showError(
      "#signup-error-1",
      "Google sign-in is not configured yet. Use Continue to BRAHL without account above, or email below."
    );
    return;
  }
  location.href = "/api/auth/google/start?next=/signup";
});

$("#signup-email-form")?.addEventListener("submit", (ev) => {
  ev.preventDefault();
  showError("#signup-error-1", "");
  const email = $("#signup-email").value.trim();
  const password = $("#signup-password").value;
  if (password.length < 8) {
    showError("#signup-error-1", "Password must be at least 8 characters.");
    return;
  }
  state.mode = "email";
  state.email = email;
  state.password = password;
  goStep(2);
  syncConditional();
});

$("#signup-back")?.addEventListener("click", () => goStep(1));

$$('input[name="roles"]').forEach((el) => el.addEventListener("change", syncConditional));

$("#signup-profile-form")?.addEventListener("submit", async (ev) => {
  ev.preventDefault();
  showError("#signup-error-2", "");
  const roles = selectedRoles();
  if (!roles.length) {
    showError("#signup-error-2", "Select at least one role.");
    return;
  }
  const first = $("#signup-first").value.trim();
  const last = $("#signup-last").value.trim();
  if (!first || !last) {
    showError("#signup-error-2", "First and last name are required.");
    return;
  }
  const payload = {
    first_name: first,
    last_name: last,
    country: $("#signup-country").value.trim(),
    city: $("#signup-city").value.trim(),
    phone: $("#signup-phone").value.trim(),
    roles,
    app_url: roles.includes("creator") ? $("#signup-app-url").value.trim() : "",
    profile_complete: true,
  };

  try {
    if (state.mode === "email" && !state.token) {
      const data = await apiJson("/api/auth/register", {
        method: "POST",
        body: JSON.stringify({
          email: state.email,
          password: state.password,
          name: `${first} ${last}`,
          ...payload,
        }),
      });
      storeAuth(data.user, data.token);
    } else {
      const data = await apiJson("/api/auth/me", {
        method: "PATCH",
        body: JSON.stringify(payload),
      });
      storeAuth(data.user, data.token || state.token);
    }

    const file = $("#signup-profile-file")?.files?.[0];
    if (file && roles.includes("qa_hunter") && state.token) {
      const fd = new FormData();
      fd.append("file", file);
      await apiJson("/api/auth/me/profile-upload", { method: "POST", body: fd });
    }
    enterBrahl();
  } catch (e) {
    showError("#signup-error-2", e.message);
  }
});

syncConditional();
goStep(1);

(async function boot() {
  await loadProviders();

  const prefill = sessionStorage.getItem("qoa_signup_email");
  if (prefill && $("#signup-email")) {
    $("#signup-email").value = prefill;
    sessionStorage.removeItem("qoa_signup_email");
  }

  const oauthToken = takeAuthTokenFromUrl();
  if (oauthToken) {
    try {
      state.token = oauthToken;
      const data = await apiJson("/api/auth/me");
      storeAuth(data.user, oauthToken);
      state.mode = "social";
      state.email = data.user.email || "";
      if (data.user.first_name) $("#signup-first").value = data.user.first_name;
      if (data.user.last_name) $("#signup-last").value = data.user.last_name;
      if (data.user.country) $("#signup-country").value = data.user.country;
      if (data.user.city) $("#signup-city").value = data.user.city;
      if (data.user.phone) $("#signup-phone").value = data.user.phone;
      if (data.user.profile_complete) {
        enterBrahl();
        return;
      }
      goStep(2);
      syncConditional();
      return;
    } catch (e) {
      showError("#signup-error-1", e.message || "Google sign-in failed.");
    }
  }

  const token = localStorage.getItem("qoa_auth_token");
  if (!token) return;
  try {
    state.token = token;
    const data = await apiJson("/api/auth/me");
    if (data.user && data.user.profile_complete === false) {
      state.user = data.user;
      state.mode = data.user.social_provider ? "social" : "email";
      state.email = data.user.email || "";
      if (data.user.first_name) $("#signup-first").value = data.user.first_name;
      if (data.user.last_name) $("#signup-last").value = data.user.last_name;
      if (data.user.country) $("#signup-country").value = data.user.country;
      if (data.user.city) $("#signup-city").value = data.user.city;
      if (data.user.phone) $("#signup-phone").value = data.user.phone;
      if (data.user.app_url) $("#signup-app-url").value = data.user.app_url;
      (data.user.roles || []).forEach((r) => {
        const box = document.querySelector(`input[name="roles"][value="${r}"]`);
        if (box) box.checked = true;
      });
      goStep(2);
      syncConditional();
    }
  } catch {
    /* ignore */
  }
})();
