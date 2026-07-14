/* Two-step signup: social/email → profile with multi-role checkboxes */
const $ = (s) => document.querySelector(s);
const $$ = (s) => Array.from(document.querySelectorAll(s));

const state = {
  mode: "email", // email | social
  provider: "",
  email: "",
  password: "",
  token: "",
  user: null,
};

function showError(id, msg) {
  const el = $(id);
  if (!el) return;
  el.hidden = !msg;
  el.textContent = msg || "";
}

function goStep(step) {
  $("#signup-step-1").hidden = step !== 1;
  $("#signup-step-2").hidden = step !== 2;
  $("#step-indicator-1").classList.toggle("active", step === 1);
  $("#step-indicator-1").classList.toggle("done", step > 1);
  $("#step-indicator-2").classList.toggle("active", step === 2);
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

function enterArena() {
  const draft = sessionStorage.getItem("qoa_draft_requirement");
  location.href = draft ? "/app?restore_draft=1" : "/app";
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

$$("[data-provider]").forEach((btn) => {
  btn.addEventListener("click", () => {
    state.provider = btn.dataset.provider;
    $("#social-provider-label").textContent = state.provider;
    $("#social-email-panel").hidden = false;
    $("#social-email").focus();
  });
});

$("#social-continue")?.addEventListener("click", async () => {
  showError("#signup-error-1", "");
  const email = $("#social-email").value.trim();
  const name = $("#social-name").value.trim();
  if (!email) {
    showError("#signup-error-1", "Email is required for social continue (local OAuth stub).");
    return;
  }
  try {
    const data = await apiJson("/api/auth/social", {
      method: "POST",
      body: JSON.stringify({ provider: state.provider, email, name }),
    });
    storeAuth(data.user, data.token);
    state.mode = "social";
    state.email = email;
    if (data.user.first_name) $("#signup-first").value = data.user.first_name;
    if (data.user.last_name) $("#signup-last").value = data.user.last_name;
    goStep(2);
    syncConditional();
  } catch (e) {
    showError("#signup-error-1", e.message);
  }
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
    showError("#signup-error-2", "Select at least one role / avatar.");
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
    enterArena();
  } catch (e) {
    showError("#signup-error-2", e.message);
  }
});

syncConditional();

(async function resumeIncompleteProfile() {
  const token = localStorage.getItem("qoa_auth_token");
  if (!token) return;
  try {
    const res = await fetch("/api/auth/me", { headers: { Authorization: `Bearer ${token}` } });
    if (!res.ok) return;
    const data = await res.json();
    if (data.user && data.user.profile_complete === false) {
      state.token = token;
      state.user = data.user;
      state.mode = data.user.social_provider ? "social" : "email";
      state.email = data.user.email || "";
      if (data.user.first_name) $("#signup-first").value = data.user.first_name;
      if (data.user.last_name) $("#signup-last").value = data.user.last_name;
      if (data.user.country) $("#signup-country").value = data.user.country;
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
