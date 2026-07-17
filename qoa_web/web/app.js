const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

const STORAGE_AVATAR = "qoa_web_avatar";
const STORAGE_PROJECT = "qoa_web_project_id";
const STORAGE_SUITE = "qoa_web_suite";
const STORAGE_AUTH_TOKEN = "qoa_auth_token";
const STORAGE_AUTH_USER = "qoa_auth_user";
const STORAGE_DRAFT_REQUIREMENT = "qoa_draft_requirement";

let pendingBrahlPlan = null;

function maybeResetFromQuery() {
  const params = new URLSearchParams(location.search);
  if (params.get("reset") === "1") {
    localStorage.removeItem(STORAGE_AVATAR);
    localStorage.removeItem(STORAGE_PROJECT);
    localStorage.removeItem(STORAGE_SUITE);
    if (typeof clearStoredProfile === "function") clearStoredProfile();
    return true;
  }
  return false;
}
const didReset = maybeResetFromQuery();

function maybeApplyProfileFromQuery() {
  if (typeof getProfileById !== "function") return;
  const params = new URLSearchParams(location.search);
  let pid = params.get("profile");
  if (pid) {
    pid = pid.toLowerCase();
    if (!pid.startsWith("p")) pid = `p${pid}`;
    const profile = getProfileById(pid);
    if (profile) {
      saveProfile(profile.id);
      localStorage.setItem(STORAGE_AVATAR, profile.defaultAvatar);
      if (profile.role === "new-user" || profile.landing === "signin") {
        if (!params.get("suite")) {
          localStorage.removeItem(STORAGE_SUITE);
          localStorage.removeItem(STORAGE_PROJECT);
        }
      }
    }
  }
  const suite = params.get("suite");
  if (suite) localStorage.setItem(STORAGE_SUITE, suite);
}

maybeApplyProfileFromQuery();

(function enableDemoFromQuery() {
  const params = new URLSearchParams(location.search);
  if (params.get("demo") === "1" && window.QoaInviteGate?.enableDemoBypass) {
    window.QoaInviteGate.enableDemoBypass();
  }
})();

(function redirectIfNoAccess() {
  const path = location.pathname.replace(/\/$/, "") || "/";
  if (path !== "/app" && path !== "/index.html") return;
  if (window.QoaInviteGate && !window.QoaInviteGate.isInviteTrialValid()) {
    location.replace("/welcome");
  }
})();

let pollTimer = null;
let selectedRun = null;
let selectedBrahlRun = null;
let selectedBrahlReportId = null;
let activeProject = null;
let lastAnalyzeMarkdown = "";
let lastHealPatches = [];
let lastHealMarkdown = "";

const state = {
  profile: typeof getActiveProfile === "function" ? getActiveProfile() : null,
  avatar: localStorage.getItem(STORAGE_AVATAR) || null,
  projectId: localStorage.getItem(STORAGE_PROJECT) || null,
  suiteName: localStorage.getItem(STORAGE_SUITE) || null,
  suites: [],
  projects: [],
  phase: "build",
  consultantFilter: "",
  consultantSort: "name",
  consultantCompact: false,
};

const ypadState = {
  tab: "plans",
  data: null,
  editMode: false,
  filter: "",
  selectedIndex: -1,
  insights: null,
  designColumnMode: "all",
  designGroupFilter: "",
  coverageFilter: "all",
  /** Explicit CSV source path for multi-file suites (gate vs journey). */
  source: "",
  sourceKind: "",
  showTable: false,
  page: 0,
  pageSize: 50,
  versions: [],
  selectedVersionId: "",
};

async function api(path, opts = {}) {
  const headers = { "Content-Type": "application/json", ...(opts.headers || {}) };
  const token = localStorage.getItem(STORAGE_AUTH_TOKEN);
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(path, {
    headers,
    ...opts,
  });
  if (!res.ok) throw new Error((await res.text()) || res.statusText);
  const ct = res.headers.get("content-type") || "";
  return ct.includes("application/json") ? res.json() : res.text();
}

function escapeHtml(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function setStatus(msg) {
  $("#status-bar").textContent = msg;
}

function hasScope() {
  return !!state.suiteName;
}

function isNetworker() {
  return state.avatar === "networker";
}

function isNalanda() {
  return isNetworker();
}

function applyAvatarModeNav() {
  document.body.classList.toggle("mode-networker", isNetworker());
  const brahlPhases = ["build", "run", "analyze", "heal", "loop", "brahl"];
  const utilityPhases = new Set(["nalanda", "atomic77", "promoter", "cost"]);
  $$(".phase-btn").forEach((btn) => {
    const ph = btn.dataset.phase;
    if (ph === "nalanda") {
      // Visible in phase nav for Nalanda avatar; others open it from the user menu
      btn.hidden = !isNetworker();
    } else if (ph === "atomic77" || ph === "cost" || ph === "promoter") {
      btn.hidden = true; // menu / deep-link surfaces
    } else if (brahlPhases.includes(ph)) {
      btn.hidden = isNetworker();
    }
    const item = btn.closest(".phase-nav-item");
    if (item) item.hidden = !!btn.hidden;
  });
  // Don't yank users off Promoter / A77 / Wallet / menu-opened Nalanda
  if (utilityPhases.has(state.phase)) return;
  if (isNetworker() && brahlPhases.includes(state.phase)) showPhase("nalanda");
}

function showPhase(name) {
  state.phase = name;
  $$(".phase-btn").forEach((b) => b.classList.toggle("active", b.dataset.phase === name));
  $$(".panel").forEach((p) => p.classList.toggle("active", p.dataset.panel === name));
  updatePhaseLock();
  const utility = ["nalanda", "atomic77", "promoter", "cost"].includes(name);
  if (!hasScope() && name !== "build" && !utility) {
    setStatus(state.avatar && !state.suites.length ? "Add your first challenge to the arena" : "Select a challenge in the top bar");
  } else {
    syncProjectStatus();
  }
  if (name === "brahl" && state.suiteName) loadBrahlPanel();
  if (name === "atomic77") loadAtomic77Panel();
  if (name === "cost") loadCostPanel();
  if (name === "nalanda") window.QoaNalanda?.loadPanel?.();
  if (name === "promoter") loadPromoterPanel();
  if (name === "heal") {
    applyAiMode();
    refreshHealFailures();
  }
  if (name === "loop") {
    refreshLoopBuiltSummary();
    loadSchedules();
  }
  if (name === "analyze" && selectedRun && isAiOn()) {
    /* user can click AI analyze or we leave prior result visible */
  }
  if (["nalanda", "atomic77", "promoter", "cost"].includes(name)) {
    try {
      history.replaceState(null, "", `#${name}`);
    } catch {
      /* ignore */
    }
  } else if (/^#(nalanda|atomic77|promoter|cost)$/i.test(location.hash || "")) {
    try {
      history.replaceState(null, "", `${location.pathname}${location.search}`);
    } catch {
      /* ignore */
    }
  }
  // Keep phase nav stable: never scrollIntoView the panel (jumps header / consultant locks).
  // Land at page top so each phase starts under the same menu position.
  try {
    window.scrollTo({ top: 0, left: 0, behavior: "auto" });
  } catch {
    window.scrollTo(0, 0);
  }
  renderPhaseProgress();
  updateVisualRewardRail();
  syncTopbarRoleSelect();
  if (name === "promoter") setStatus("Promoter — share invites · earn XP & wallet credits");
}

function updateLockedPhaseActions() {
  const showAdd = state.avatar && !state.suites.length;
  const showBuild = state.avatar && !state.suiteName && state.suites.length;
  $$(".phase-locked-add").forEach((btn) => {
    btn.hidden = !showAdd;
  });
  $$(".phase-locked-build").forEach((btn) => {
    btn.hidden = !showBuild;
  });
}

function updatePhaseLock() {
  const locked = !hasScope();
  ["run", "analyze", "heal", "loop", "brahl"].forEach((phase) => {
    const el = $(`#${phase}-locked`);
    const content = $(`#${phase}-content`);
    if (el) el.hidden = !locked;
    if (content) content.hidden = locked;
  });
  const costLocked =
    state.avatar === "consultant" || state.avatar === "networker" ? false : locked;
  if ($("#cost-locked")) $("#cost-locked").hidden = !costLocked;
  if ($("#cost-content")) $("#cost-content").hidden = costLocked;
  updateLockedPhaseActions();
  $$(".phase-btn").forEach((btn) => {
    if (btn.dataset.phase === "build") return;
    btn.disabled = !state.avatar;
    btn.title = locked ? "Open to see next steps" : "";
  });
}

async function setAvatar(avatar) {
  const profile = state.profile || getActiveProfile();
  if (profile && !profileAllowsAvatar(profile, avatar)) return;
  state.avatar = avatar;
  localStorage.setItem(STORAGE_AVATAR, avatar);
  syncAvatarButtons(profile, avatar);
  applyAvatarLabelsToDom();
  updateTopbarProjectLabel();
  $("#avatar-gate").hidden = true;
  $("#build-no-avatar").hidden = !!avatar;
  $("#build-client").hidden = !avatar;
  $$(".phase-btn").forEach((btn) => {
    if (btn.dataset.phase !== "build") btn.disabled = !avatar;
  });
  await loadYpadProjects();
  if (avatar === "consultant") await loadConsultantProjects();
  syncAvatarSections();
  applyAvatarModeNav();
  renderGoNoGo(null);
  applyProfileUI();
  setStatus(`Viewing as ${avatarLabel(avatar).short}`);
  syncProjectStatus();
  updateVisualRewardRail();
  syncTopbarRoleSelect();
}

function updateTopbarProjectLabel() {
  const labelEl = $(".topbar-project-label");
  if (!labelEl) return;
  labelEl.textContent = "Projects";
}

function syncTopbarRoleSelect() {
  const wrap = $("#topbar-role");
  const sel = $("#topbar-role-select");
  if (!wrap || !sel) return;
  if (!state.avatar) {
    wrap.hidden = true;
    return;
  }
  wrap.hidden = false;
  const profile = state.profile || (typeof getActiveProfile === "function" ? getActiveProfile() : null);
  const hunterOpt = sel.querySelector('option[value="consultant"]');
  if (hunterOpt) {
    const allowed = !profile || profileAllowsAvatar(profile, "consultant");
    hunterOpt.disabled = !allowed;
    hunterOpt.title = allowed
      ? "QA Hunter — join open challenges"
      : "QA Hunter — switch profile at Sign-in for dual-role access";
  }
  const creatorOpt = sel.querySelector('option[value="client"]');
  if (creatorOpt) {
    const allowed = !profile || profileAllowsAvatar(profile, "client");
    creatorOpt.disabled = !allowed;
  }
  const value = state.phase === "promoter" ? "promoter" : state.avatar === "consultant" ? "consultant" : "client";
  // networker maps to Creator slot visually unless on Promoter phase
  if (state.phase !== "promoter" && state.avatar === "networker") {
    sel.value = "client";
  } else if ([...sel.options].some((o) => o.value === value && !o.disabled)) {
    sel.value = value;
  } else if (state.avatar && [...sel.options].some((o) => o.value === state.avatar && !o.disabled)) {
    sel.value = state.avatar;
  }
}

function bindTopbarRoleSelect() {
  const sel = $("#topbar-role-select");
  if (!sel || sel.dataset.bound) return;
  sel.dataset.bound = "1";
  sel.addEventListener("change", async () => {
    const v = sel.value;
    if (v === "promoter") {
      showPhase("promoter");
      return;
    }
    if (v === "client" || v === "consultant") {
      const leavingUtility = ["promoter", "nalanda", "atomic77", "cost"].includes(state.phase);
      if (leavingUtility) showPhase("build");
      await setAvatar(v);
      if (state.avatar !== v) {
        syncTopbarRoleSelect();
        return;
      }
      syncTopbarRoleSelect();
    }
  });
}

function syncAvatarButtons(profile, activeAvatar) {
  $$(".avatar-btn").forEach((b) => {
    const allowed = !profile || profileAllowsAvatar(profile, b.dataset.avatar);
    b.classList.toggle("active", b.dataset.avatar === activeAvatar);
    b.classList.toggle("avatar-btn-restricted", !allowed);
    b.disabled = !allowed;
    b.setAttribute("aria-disabled", allowed ? "false" : "true");
    if (!allowed) {
      b.title = `${avatarLabel(b.dataset.avatar).short} — switch profile at Sign-in for dual-role access`;
    }
  });
  syncTopbarRoleSelect();
}

function bindAvatarControls() {
  $$(".avatar-btn, .avatar-choice").forEach((btn) => {
    if (btn.dataset.avatarBound) return;
    btn.dataset.avatarBound = "1";
    btn.addEventListener("click", async () => {
      const next = btn.dataset.avatar;
      if (!next) return;
      const profile = state.profile || getActiveProfile();
      if (profile && !profileAllowsAvatar(profile, next)) {
        setStatus(`This profile (${profile.code}) cannot use the ${avatarLabel(next).short} avatar`);
        return;
      }
      await setAvatar(next);
    });
  });
}

function syncAvatarSections() {
  const isClient = state.avatar === "client";
  const isConsultant = state.avatar === "consultant";
  const isNet = isNetworker();
  $$(".avatar-client-only").forEach((el) => {
    el.hidden = !isClient;
  });
  $$(".avatar-consultant-only").forEach((el) => {
    el.hidden = !isConsultant;
  });
  const aiWrap = $("#ai-toggle-wrap");
  if (aiWrap) aiWrap.hidden = isNet || !state.suiteName;
  const editBtn = $("#ypad-toggle-edit");
  const saveBtn = $("#ypad-save");
  if (editBtn) editBtn.hidden = !isClient;
  if (saveBtn) saveBtn.hidden = !isClient || !ypadState.editMode;
}

async function loadConsultantProjects() {
  try {
    const { projects } = await api("/api/projects?role=consultant");
    state.projects = projects || [];
  } catch {
    state.projects = [];
  }
}

async function loadPersonaTasks() {
  const profile = state.profile || getActiveProfile();
  const strip = $("#persona-tasks-strip");
  const list = $("#persona-tasks-list");
  const roleEl = $("#persona-tasks-role");
  const label = $("#persona-tasks-label");
  const codeEl = $("#persona-tasks-code");
  const details = $("#persona-tasks-details");
  const expandBtn = $("#persona-tasks-expand");
  const docLink = $("#persona-tasks-doc-link");
  const reopen = $("#persona-tips-reopen");
  if (!strip || !list || !profile?.id) {
    if (strip) strip.hidden = true;
    if (reopen) reopen.hidden = true;
    return;
  }
  if (sessionStorage.getItem("qoa_web_persona_badge_dismissed") === "1") {
    strip.hidden = true;
    if (reopen) reopen.hidden = false;
    return;
  }
  if (reopen) reopen.hidden = true;
  const avatar = state.avatar || profile.defaultAvatar || "client";
  try {
    const { tasks, fictional } = await api(
      `/api/test-users/${encodeURIComponent(profile.id)}/tasks?avatar=${encodeURIComponent(avatar)}`
    );
    if (!tasks?.length) {
      strip.hidden = true;
      return;
    }
    strip.hidden = false;
    if (codeEl) codeEl.textContent = profile.code;
    if (label) label.textContent = profile.name;
    if (roleEl) {
      const roleMap = { client: "Creator", consultant: "QA Hunter", networker: "Nalanda" };
      roleEl.textContent = roleMap[avatar] || "Creator";
    }
    list.innerHTML = tasks
      .map(
        (t) =>
          `<li class="persona-task-item">` +
          `<span class="persona-task-phase">${escapeHtml(t.phase || "—")}</span> ` +
          `<strong>${escapeHtml(t.title || "")}</strong>` +
          (t.detail ? `<span class="persona-task-detail">${escapeHtml(t.detail)}</span>` : "") +
          `</li>`
      )
      .join("");
    if (details) details.hidden = true;
    if (expandBtn) {
      expandBtn.setAttribute("aria-expanded", "false");
      expandBtn.textContent = "Tips";
    }
    if (docLink) {
      if (fictional) {
        docLink.hidden = true;
        docLink.href = "#";
        docLink.onclick = async (e) => {
          e.preventDefault();
          if (typeof openAiDocsModal === "function") openAiDocsModal();
          if (typeof selectAiDoc === "function") await selectAiDoc("test-user-data");
        };
      } else {
        docLink.hidden = true;
      }
    }
    const fixture = await api(`/api/test-users/${encodeURIComponent(profile.id)}/fixture`);
    if (fixture?.fixture) {
      sessionStorage.setItem("qoa_web_persona_fixture", JSON.stringify(fixture.fixture));
    }
  } catch {
    strip.hidden = true;
  }
}

function bindPersonaBadge() {
  const dismissBtn = $("#persona-tasks-dismiss");
  const expandBtn = $("#persona-tasks-expand");
  const details = $("#persona-tasks-details");
  const docLink = $("#persona-tasks-doc-link");
  const reopen = $("#persona-tips-reopen");
  const strip = $("#persona-tasks-strip");

  dismissBtn?.addEventListener("click", () => {
    sessionStorage.setItem("qoa_web_persona_badge_dismissed", "1");
    if (strip) strip.hidden = true;
    if (reopen) reopen.hidden = false;
  });

  expandBtn?.addEventListener("click", () => {
    if (!details) return;
    const open = details.hidden;
    details.hidden = !open;
    expandBtn.setAttribute("aria-expanded", open ? "true" : "false");
    expandBtn.textContent = open ? "Hide" : "Tips";
    if (docLink && open) docLink.hidden = false;
    else if (docLink && !open) docLink.hidden = true;
  });

  reopen?.addEventListener("click", () => {
    sessionStorage.removeItem("qoa_web_persona_badge_dismissed");
    if (reopen) reopen.hidden = true;
    loadPersonaTasks();
  });
}

function applyProfileUI() {
  const profile = state.profile || (typeof getActiveProfile === "function" ? getActiveProfile() : null);
  state.profile = profile;
  const chip = $("#user-menu-btn");
  const codeEl = $("#profile-chip-code");
  const nameEl = $("#profile-chip-name");
  const authUser = getAuthUser();
  if (chip) {
    chip.hidden = false;
    if (authUser) {
      if (codeEl) codeEl.textContent = (authUser.role || "user").replace(/_/g, " ").slice(0, 12);
      if (nameEl) nameEl.textContent = authUser.name || authUser.email?.split("@")[0] || "Account";
      chip.title = `${authUser.email || "Account"} — menu`;
      const so = $("#user-menu-signout");
      const li = $("#user-menu-login");
      const su = $("#user-menu-signup");
      if (so) so.hidden = false;
      if (li) li.hidden = true;
      if (su) su.hidden = true;
    } else {
      if (codeEl) codeEl.textContent = "Guest";
      if (nameEl) nameEl.textContent = "Sign in";
      chip.title = "Account menu";
      const so = $("#user-menu-signout");
      const li = $("#user-menu-login");
      const su = $("#user-menu-signup");
      if (so) so.hidden = true;
      if (li) li.hidden = false;
      if (su) su.hidden = false;
    }
  }

  const role = (authUser?.role || "").toLowerCase();
  const isPlatformAdmin = role === "admin" || role === "super_admin" || !!authUser?.is_super_admin;
  const isProjectAdmin =
    isPlatformAdmin ||
    (!!authUser &&
      state.avatar === "client" &&
      !!state.projectId &&
      ["creator", "both", "admin", "super_admin"].includes(role));

  const adminLink = $("#footer-admin-link");
  const adminMenu = $("#user-menu-admin");
  const projAdminMenu = $("#user-menu-project-admin");
  if (adminLink) {
    adminLink.href = "/admin";
    adminLink.hidden = !isPlatformAdmin && !isProjectAdmin;
    adminLink.classList.toggle("footer-admin-link-active", isPlatformAdmin || isProjectAdmin);
  }
  if (adminMenu) {
    adminMenu.hidden = !isPlatformAdmin;
    adminMenu.href = "/admin";
  }
  if (projAdminMenu) {
    projAdminMenu.hidden = !isProjectAdmin;
    projAdminMenu.href = state.projectId
      ? `/admin?project=${encodeURIComponent(state.projectId)}`
      : "/admin?scope=project";
  }

  $$(".avatar-btn").forEach(() => {
    syncAvatarButtons(null, state.avatar);
  });

  const tierBanner = $("#consultant-tier-banner");
  if (tierBanner) {
    tierBanner.hidden = true;
    tierBanner.textContent = "";
  }

  const demoBanner = $("#demo-banner");
  if (demoBanner) demoBanner.hidden = true;

  document.body.classList.toggle("profile-admin", isPlatformAdmin);
  document.body.classList.remove("profile-ai-locked", "profile-power-client");
}

const PRESENCE_SESSION_KEY = "qoa_presence_session";
let presenceGeoConsent = undefined; // undefined=not asked, false=denied, object={lat,lng}

function presenceSessionKey() {
  let k = sessionStorage.getItem(PRESENCE_SESSION_KEY);
  if (!k) {
    k = `s:${Date.now()}:${Math.random().toString(36).slice(2, 10)}`;
    sessionStorage.setItem(PRESENCE_SESSION_KEY, k);
  }
  return k;
}

function askPresenceGeoOnce() {
  if (presenceGeoConsent !== undefined) return;
  if (!navigator.geolocation) {
    presenceGeoConsent = false;
    return;
  }
  presenceGeoConsent = null; // in flight
  navigator.geolocation.getCurrentPosition(
    (pos) => {
      presenceGeoConsent = { lat: pos.coords.latitude, lng: pos.coords.longitude };
    },
    () => {
      presenceGeoConsent = false;
    },
    { maximumAge: 600_000, timeout: 5000 }
  );
}

async function sendPresenceHeartbeat() {
  try {
    const authUser = getAuthUser();
    const profile = state.profile || getActiveProfile();
    const body = {
      session_key: presenceSessionKey(),
      project_id: state.projectId || null,
      path: `${location.pathname}${location.hash || ""}`,
      avatar: state.avatar === "consultant" ? "qa_hunter" : "creator",
      display_name: authUser?.name || profile?.name || "Arena guest",
    };
    if (presenceGeoConsent && presenceGeoConsent.lat != null) {
      body.lat = presenceGeoConsent.lat;
      body.lng = presenceGeoConsent.lng;
    }
    await api("/api/presence/heartbeat", {
      method: "POST",
      body: JSON.stringify(body),
    });
  } catch {
    /* soft-fail — presence is best-effort */
  }
}

function initPresenceHeartbeat() {
  askPresenceGeoOnce();
  sendPresenceHeartbeat();
  setInterval(sendPresenceHeartbeat, 15000);
}

async function enforceProfileAiPolicy() {
  const profile = state.profile;
  if (!profile || !state.projectId || !activeProject) return;
  const mustOff = profile.aiLocked || profile.aiDefault === false;
  if (mustOff && activeProject.ai_enabled !== false) {
    try {
      const { project } = await api(`/api/projects/${state.projectId}`, {
        method: "PATCH",
        body: JSON.stringify({ ai_enabled: false }),
      });
      activeProject = project;
    } catch {
      /* ignore */
    }
  }
}

/** ?ai=1 forces AI on (smoke / deep-links). Soft aiDefault=false is overridden; hard aiLocked is not. */
async function ensureAiFromQuery() {
  const params = new URLSearchParams(location.search);
  if (params.get("ai") !== "1") return;
  if (!state.projectId || !activeProject) return;
  if (state.profile?.aiLocked) return;
  // Optimistic local enable so Heal/Analyze AI controls appear even if PATCH is slow/denied.
  activeProject = { ...activeProject, ai_enabled: true };
  const toggle = $("#ai-toggle");
  if (toggle) toggle.checked = true;
  if (activeProject.ai_enabled !== false) {
    /* still PATCH below when server still has it off — use prior server flag */
  }
  try {
    const { project } = await api(`/api/projects/${state.projectId}`, {
      method: "PATCH",
      body: JSON.stringify({ ai_enabled: true }),
    });
    activeProject = project;
  } catch {
    /* keep optimistic local enable for smoke / guest */
  }
}

async function loadYpadProjects() {
  if (!state.avatar) return;
  await loadSuites();
  renderTopbarProjectSelect();
  if (state.suiteName && state.suites.some((s) => s.name === state.suiteName)) {
    await selectYpadProject(state.suiteName);
  } else if (
    state.suites.length &&
    state.profile?.role !== "new-user" &&
    !state.profile?.firstVisit
  ) {
    await selectYpadProject(state.suites[0].name);
  } else {
    activeProject = null;
    state.projectId = null;
    localStorage.removeItem(STORAGE_PROJECT);
    renderClientWorkspace();
    updatePhaseLock();
    syncAvatarSections();
    syncProjectStatus();
  }
}

let projectSwitchToken = 0;

function setProjectSwitching(on) {
  const wrap = $("#topbar-project");
  const badge = $("#topbar-project-switching");
  if (wrap) wrap.classList.toggle("switching", on);
  if (badge) badge.hidden = !on;
}

/**
 * Project switch — sequenced + cancellable. Every await checks whether a
 * newer switch has already started; if so, this stale call stops updating
 * shared state/UI so an older Math/Nalanda response can never win a race
 * against a faster, more recent switch.
 */
async function selectYpadProject(suiteName) {
  if (!suiteName) return;
  const myToken = ++projectSwitchToken;
  const stale = () => myToken !== projectSwitchToken;
  state.suiteName = suiteName;
  localStorage.setItem(STORAGE_SUITE, suiteName);
  selectedBrahlRun = null;
  selectedRun = null;
  setProjectSwitching(true);
  try {
    const data = await api(`/api/ypad-projects/${encodeURIComponent(suiteName)}`);
    if (stale()) return;
    activeProject = data.project;
    state.projectId = activeProject?.id || null;
    if (state.projectId) localStorage.setItem(STORAGE_PROJECT, state.projectId);
    else localStorage.removeItem(STORAGE_PROJECT);
    const projAdminMenu = $("#user-menu-project-admin");
    if (projAdminMenu && !projAdminMenu.hidden) {
      projAdminMenu.href = state.projectId
        ? `/admin?project=${encodeURIComponent(state.projectId)}`
        : "/admin?scope=project";
    }
    updateProjectBanner(data.payout_preview);
  } catch {
    if (stale()) return;
    activeProject = null;
    state.projectId = null;
    localStorage.removeItem(STORAGE_PROJECT);
    updateProjectBanner();
  }
  if (stale()) return;
  syncRunSuiteDisplay();
  syncScopeLabels();
  await loadConfigsForSuite();
  if (stale()) return;
  renderTopbarProjectSelect();
  syncAvatarSections();
  renderClientWorkspace();
  updatePhaseLock();
  syncProjectToUI();
  renderBuildChecklist();
  renderCycleHistory();
  renderPhaseProgress();
  updateHealHint();
  renderBrahlChat();
  renderAtomic77Chat();
  await enforceProfileAiPolicy();
  if (stale()) return;
  await ensureAiFromQuery();
  applyAiMode();
  await loadRuns();
  if (stale()) return;
  await loadYpadInsights();
  loadBuildDocs();
  if (stale()) return;
  if ($("#panel-brahl")?.classList.contains("active")) await loadBrahlPanel();
  if (!stale()) setProjectSwitching(false);
}

async function refreshActiveProject() {
  if (!state.projectId) {
    activeProject = null;
    updateProjectBanner();
    return;
  }
  try {
    const data = await api(`/api/projects/${state.projectId}`);
    activeProject = data.project;
    const idx = state.projects.findIndex((p) => p.id === state.projectId);
    if (idx >= 0) state.projects[idx] = activeProject;
    updateProjectBanner(data.payout_preview);
    syncScopeLabels();
    syncProjectToUI();
    renderClientWorkspace();
    renderBrahlChat();
    renderAtomic77Chat();
    renderCycleHistory();
    renderPhaseProgress();
    updateHealHint();
    updateVisualRewardRail();
    refreshArenaCostWidget();
  } catch {
    state.projectId = null;
    localStorage.removeItem(STORAGE_PROJECT);
    activeProject = null;
    updateProjectBanner();
    refreshArenaCostWidget();
  }
}

function inferSuiteFromProject(project) {
  if (!project) return null;
  if (project.suite_name) return project.suite_name;
  if (project.suite_config) {
    const s = state.suites.find((x) => x.path === project.suite_config);
    if (s) return s.name;
  }
  const n = (project.name || "").toLowerCase();
  for (const s of state.suites) {
    if (n.includes(s.name.toLowerCase())) return s.name;
  }
  return state.suites.find((s) => s.name === "qoa_web")?.name || state.suites[0]?.name || null;
}

function syncSuiteFromProject() {
  const name = inferSuiteFromProject(activeProject);
  if (!name) return;
  state.suiteName = name;
  localStorage.setItem(STORAGE_SUITE, name);
  syncRunSuiteDisplay();
  syncScopeLabels();
}

async function applySuiteScope(suiteName) {
  if (!suiteName) return;
  state.suiteName = suiteName;
  localStorage.setItem(STORAGE_SUITE, suiteName);
  selectedBrahlRun = null;
  selectedRun = null;
  syncRunSuiteDisplay();
  syncScopeLabels();
  await loadRuns();
}

function uniqueProjects() {
  const seen = new Set();
  return state.projects.filter((p) => {
    if (!p.id || seen.has(p.id)) return false;
    seen.add(p.id);
    return true;
  });
}

function renderTopbarProjectSelect() {
  const topbarSel = $("#topbar-project-select");
  const topbarWrap = $("#topbar-project");
  if (!topbarSel || !state.avatar) return;
  if (topbarWrap) topbarWrap.hidden = false;
  updateTopbarProjectLabel();

  const hasSuites = state.suites.length > 0;
  const ph = avatarLabel(state.avatar).projectPlaceholder;
  if (hasSuites) {
    topbarSel.innerHTML = state.suites
      .map(
        (s) =>
          `<option value="${escapeHtml(s.name)}">${escapeHtml(s.name)}${s.url ? ` — ${escapeHtml(s.url)}` : ""}</option>`
      )
      .join("");
    if (state.suiteName && state.suites.some((s) => s.name === state.suiteName)) {
      topbarSel.value = state.suiteName;
    } else if (state.suites.length) {
      topbarSel.value = state.suites[0].name;
    }
  } else {
    topbarSel.innerHTML = '<option value="">No challenges in y/</option>';
  }
  topbarSel.disabled = !hasSuites;
}

function syncRunSuiteDisplay() {
  const suite = state.suites.find((s) => s.name === state.suiteName);
  const el = $("#run-suite-display");
  if (!el) return;
  if (suite) {
    el.textContent = suite.url ? `${suite.name} — ${suite.url}` : suite.name;
  } else if (state.suiteName) {
    el.textContent = state.suiteName;
  } else {
    el.textContent = "—";
  }
}

function syncScopeLabels() {
  const suite = state.suites.find((s) => s.name === state.suiteName);
  let label = "";
  if (suite) {
    label = `Scoped to: ${suite.name}${suite.url ? ` (${suite.url})` : ""}`;
  } else if (activeProject) {
    label = `Scoped to: ${activeProject.name}`;
  }
  ["run-project-scope", "analyze-project-scope", "heal-project-scope"].forEach((id) => {
    const el = $(`#${id}`);
    if (el) el.textContent = label;
  });
}

async function selectProject(projectId) {
  if (!projectId) return;
  let project = activeProject?.id === projectId ? activeProject : null;
  if (!project) {
    try {
      const data = await api(`/api/projects/${projectId}`);
      project = data.project;
    } catch {
      return;
    }
  }
  const suiteName = project?.suite_name || inferSuiteFromProject(project);
  if (suiteName) await selectYpadProject(suiteName);
}

function suiteConfigPath() {
  if (activeProject?.suite_config) return activeProject.suite_config;
  if (state.suiteName) return `y/${state.suiteName}/${state.suiteName}.json`;
  return "y/Math/Math.json";
}

function renderAiMarkdown(el, markdown) {
  if (!el) return;
  if (!markdown) {
    el.hidden = true;
    el.textContent = "";
    el.innerHTML = "";
    return;
  }
  el.hidden = false;
  el.classList.remove("ai-loading");
  el.innerHTML = renderMarkdown(markdown);
}

function isAiOn() {
  if (!activeProject) return false;
  const el = $("#ai-toggle");
  if (el && !$("#ai-toggle-wrap")?.hidden) return !!el.checked;
  return activeProject.ai_enabled !== false;
}

function applyAiMode() {
  const hasProject = !!activeProject;
  const profile = state.profile;
  const aiLocked = !!profile?.aiLocked;
  $("#ai-toggle-wrap").hidden = !hasProject;
  renderProjectSelectors();
  if (hasProject) {
    $("#ai-toggle").checked = activeProject.ai_enabled !== false;
    $("#ai-toggle").disabled = aiLocked;
  }
  const on = isAiOn();
  $("#ai-toggle-label").textContent = aiLocked ? "AI off (profile)" : on ? "AI on" : "AI off";
  $("#ai-toggle-wrap")?.classList.toggle("ai-off", !on);
  const aiDocsBtn = $("#btn-ai-docs");
  if (aiDocsBtn) aiDocsBtn.hidden = !on || !hasProject;
  const aiDocsLinkWrap = $("#build-ai-docs-link-wrap");
  if (aiDocsLinkWrap) aiDocsLinkWrap.hidden = !on;
  syncProjectStatus();

  $("#client-ai-build").hidden = !on;
  $("#client-manual-build").hidden = on;
  if (!on && activeProject) {
    $("#manual-purpose").value = activeProject.purpose || activeProject.prompt || "";
  }

  $("#brahl-ai-chat").hidden = !on;
  $("#brahl-ai-off-hint").hidden = on;

  const analyzeAiBtn = $("#btn-analyze-ai");
  const analyzeAiOff = $("#analyze-ai-off-hint");
  const healAiBtn = $("#btn-heal-ai");
  const healAiOff = $("#heal-ai-off-hint");
  if (analyzeAiBtn) analyzeAiBtn.hidden = !on || !hasProject;
  if (analyzeAiOff) analyzeAiOff.hidden = on || !hasProject;
  if (healAiBtn) healAiBtn.hidden = !on || !hasProject;
  if (healAiOff) healAiOff.hidden = on || !hasProject;
  if (!on) {
    renderAiMarkdown($("#analyze-ai-result"), "");
    renderAiMarkdown($("#heal-ai-result"), "");
    lastAnalyzeMarkdown = "";
  }

  const hitlHint = $("#consultant-hitl-hint");
  if (hitlHint) hitlHint.hidden = on;
  const submitBtn = $("#btn-hitl-submit");
  if (submitBtn) {
    submitBtn.textContent = on
      ? "Submit QA Hunter report"
      : "Upload Automation + AI report";
  }
}

function syncProjectStatus() {
  const strip = $("#context-strip");
  const profile = state.profile;
  if (!state.avatar) {
    strip?.classList.remove("has-project");
    setStatus(
      profile
        ? `${profileLabel(profile)} — choose avatar to start the QA agent`
        : "Choose an avatar to start the QA agent"
    );
    return;
  }
  if (!hasScope()) {
    strip?.classList.remove("has-project");
    setStatus(
      !state.suites.length
        ? "Add your first project — the QA agent needs a yPAD suite"
        : "Select a project in the top bar"
    );
    return;
  }
  strip?.classList.add("has-project");
  const phaseHints = {
    build: "QA agent · Build — set challenge, edit yPAD (plans · steps · data)",
    run: "QA agent · Run — FoXYiZ executes automated plans (no AI)",
    analyze: isAiOn()
      ? "QA agent · Analyze — failures from z/ · optional AI root-cause"
      : "QA agent · Analyze — failures from z/ (Input · Expected · Output)",
    heal: isAiOn()
      ? "QA agent · Heal — fix yPAD · Rerun · optional AI auto-heal"
      : "QA agent · Heal — fix yPAD · Rerun (no AI required)",
    loop: "QA agent · Loop — retry fails up to 3× · optional full Verify · then BRAHL Go/No-Go",
    brahl: "QA agent · BRAHL — Go/No-Go report from your latest runs",
    cost: state.avatar === "consultant" ? "QA Hunter wallet · earnings by project" : "Budget meter · AI vs QA Hunter vs local/cloud",
    nalanda: "Learn · teach · discuss · invite — free knowledge community",
    promoter: "Grow the arena — share invites · earn XP & wallet credits",
    atomic77: "Atomic 77 — idea-to-launch assistant",
  };
  setStatus(phaseHints[state.phase] || "QA agent ready");
}

function renderPhaseProgress() {
  const nav = $("#phase-nav");
  const markers = $$(".phase-marker");
  if (!markers.length) return;
  const show = !!(state.suiteName && activeProject);
  nav?.classList.toggle("has-markers", show);
  const userMsgs = (activeProject?.chat_messages || []).filter((m) => m.role === "user");
  const hasPurpose =
    !!(activeProject?.purpose || activeProject?.prompt || "").trim() || userMsgs.length > 0;
  const hasRun = !!(activeProject?.latest_run || "").trim();
  const hasContext = !!(activeProject?.brahl_context_path || "").trim();
  const hasReports = !!(activeProject?.reports || []).length;
  const done = {
    build: hasPurpose,
    run: hasRun,
    analyze: hasRun,
    heal: hasRun,
    loop: hasContext || hasRun,
    brahl: hasReports,
  };
  markers.forEach((el) => {
    const ph = el.dataset.phase;
    el.hidden = !show;
    el.classList.toggle("done", !!(show && done[ph]));
    el.classList.toggle("current", show && ph === state.phase);
  });
}

let runPickerMode = "link";
let runPickerResolve = null;

async function populateRunSelect(sel) {
  const suite = state.suiteName || "qoa_web";
  const { runs } = await api(`/api/runs?suite=${encodeURIComponent(suite)}`);
  if (!runs.length) {
    sel.innerHTML = '<option value="">No runs yet</option>';
    return;
  }
  sel.innerHTML = runs
    .map((r) => `<option value="${escapeHtml(r.name)}">${escapeHtml(r.name)}</option>`)
    .join("");
}

function closeLinkReportModal() {
  $("#link-report-modal").hidden = true;
  if (runPickerResolve) {
    runPickerResolve(null);
    runPickerResolve = null;
  }
}

async function openLinkReportModal() {
  if (!state.projectId) return;
  runPickerMode = "link";
  await populateRunSelect($("#link-report-run"));
  $("#link-report-source-row").hidden = false;
  $("#link-report-title").textContent = "Link verify run";
  $("#link-report-form button[type=submit]").textContent = "Link report";
  $("#link-report-source").value = isAiOn() ? "automation" : "automation_ai";
  $("#link-report-modal").hidden = false;
  $("#link-report-run").focus();
}

function pickRunViaModal() {
  return new Promise(async (resolve) => {
    runPickerResolve = resolve;
    runPickerMode = "hitl";
    await populateRunSelect($("#link-report-run"));
    $("#link-report-source-row").hidden = true;
    $("#link-report-title").textContent = "Choose verify run";
    $("#link-report-form button[type=submit]").textContent = "Use run";
    $("#link-report-modal").hidden = false;
    $("#link-report-run").focus();
  });
}

async function renderBatchRunRows(runNames, batchDashboard) {
  const wrap = $("#run-batch-rows");
  if (!wrap) return;
  if (!runNames?.length) {
    wrap.hidden = true;
    wrap.innerHTML = "";
    return;
  }
  const rows = await Promise.all(
    runNames.map(async (name) => {
      let href = null;
      try {
        const stats = await api(`/api/runs/${encodeURIComponent(name)}/stats`);
        href = zDashHref(stats.dashboard);
      } catch {
        /* stats not ready yet */
      }
      const link = href
        ? `<a href="${escapeHtml(href)}" target="_blank" class="secondary link-btn sm">View zDash</a>`
        : `<span class="hint">zDash generating…</span>`;
      return `<div class="run-batch-row"><span class="run-batch-name">${escapeHtml(name)}</span>${link}</div>`;
    })
  );
  let batchLinkHtml = "";
  if (batchDashboard) {
    const path = String(batchDashboard).replace(/\\/g, "/");
    const name = path.split("/").pop();
    batchLinkHtml = `<a href="/api/files/z-root/${encodeURIComponent(name)}" target="_blank" class="secondary link-btn">View combined batch zDash</a>`;
  }
  wrap.innerHTML =
    `<h4 class="section-sub">Batch jobs (${runNames.length})</h4>` + rows.join("") + batchLinkHtml;
  wrap.hidden = false;
}

function zDashHref(dashboardRelPath) {
  if (!dashboardRelPath) return null;
  const parts = dashboardRelPath.replace(/\\/g, "/").split("/");
  if (parts[0] === "z" && parts.length >= 3) {
    return `/api/files/z/${encodeURIComponent(parts[1])}/${parts.slice(2).join("/")}`;
  }
  return null;
}

async function showRunPostActions(runName, batchDashboard) {
  const wrap = $("#run-post-actions");
  if (!wrap) return;
  const hasBatch = Boolean(batchDashboard);
  const hasRun = Boolean(runName) && !String(runName).includes("zDash_batch_");
  if (!hasBatch && !hasRun) {
    wrap.hidden = true;
    return;
  }
  wrap.hidden = false;
  const link = $("#run-zdash-link");
  const batchLink = $("#run-batch-zdash-link");
  if (batchLink) {
    if (hasBatch) {
      const path = String(batchDashboard).replace(/\\/g, "/");
      const name = path.split("/").pop();
      batchLink.href = `/api/files/z-root/${encodeURIComponent(name)}`;
      batchLink.hidden = false;
    } else {
      batchLink.hidden = true;
    }
  }
  if (link) {
    if (hasRun) {
      let href = null;
      try {
        const stats = await api(`/api/runs/${encodeURIComponent(runName)}/stats`);
        href = zDashHref(stats.dashboard);
      } catch {
        /* stats not ready */
      }
      if (href) {
        link.href = href;
        link.hidden = false;
      } else {
        link.hidden = true;
      }
    } else {
      link.hidden = true;
    }
  }
}

let fstartSelected = new Set();
let fstartPrimary = null;
const fstartMetaCache = {};
const RUN_PROFILE_DEFAULT = ["Smoke", "UI", "API", "Performance", "Security", "Manual"];
let runProfileOrder = [...RUN_PROFILE_DEFAULT];
let runProfilesSelected = new Set(["Smoke"]);

function fstartChipLabel(path) {
  return (path || "")
    .replace(/^f\/fStart\//, "")
    .replace(/^f\//, "")
    .replace(/\.json$/i, "");
}

function selectedFstartPaths() {
  return [...fstartSelected];
}

function selectedRunProfiles() {
  return runProfileOrder.filter((p) => runProfilesSelected.has(p));
}

function runThreadCount() {
  const el = $("#run-thread-count");
  const n = Number(el?.value || 1);
  return Number.isFinite(n) && n >= 1 ? Math.min(8, Math.floor(n)) : 1;
}

function syncConfigSelectFromChips() {
  const sel = $("#config-select");
  if (!sel) return;
  const primary = fstartPrimary || selectedFstartPaths()[0] || "";
  if (primary && [...sel.options].some((o) => o.value === primary)) {
    sel.value = primary;
  }
  updateRunParallelEnabled();
  const runBtn = $("#btn-run");
  if (runBtn) runBtn.disabled = selectedFstartPaths().length < 1 || selectedRunProfiles().length < 1;
}

/** Parallel execution is derived only from Threads > 1 + 2+ profiles — no separate control. */
function updateRunParallelEnabled() {
  refreshFstartFanoutHint();
}

async function refreshFstartFanoutHint() {
  const hint = $("#fstart-fanout-hint");
  if (!hint) return;
  const profiles = selectedRunProfiles();
  const threads = runThreadCount();
  if (!profiles.length) {
    hint.hidden = true;
    return;
  }
  if (threads > 1 && profiles.length >= 2) {
    const workers = Math.min(threads, profiles.length);
    hint.textContent = `${threads} threads · ${profiles.join("+")} → ${profiles.length} jobs, ${workers} at a time`;
    hint.hidden = false;
  } else {
    hint.textContent = `thread_count ${threads} · profiles: ${profiles.join(", ")} (OR filter when threads=1)`;
    hint.hidden = false;
  }
}

function renderRunProfileChips() {
  const row = $("#run-profile-row");
  if (!row) return;
  row.innerHTML = runProfileOrder
    .map(
      (p) =>
        `<button type="button" class="fstart-chip run-profile-chip${runProfilesSelected.has(p) ? " selected" : ""}" data-profile="${escapeHtml(p)}">${escapeHtml(p)}</button>`
    )
    .join("");
  row.querySelectorAll(".run-profile-chip").forEach((btn) => {
    btn.addEventListener("click", () => {
      const name = btn.dataset.profile;
      if (runProfilesSelected.has(name)) {
        if (runProfilesSelected.size > 1) runProfilesSelected.delete(name);
      } else {
        runProfilesSelected.add(name);
      }
      row.querySelectorAll(".run-profile-chip").forEach((b) => {
        b.classList.toggle("selected", runProfilesSelected.has(b.dataset.profile));
      });
      syncConfigSelectFromChips();
    });
  });
  const thr = $("#run-thread-count");
  if (thr && !thr.dataset.bound) {
    thr.dataset.bound = "1";
    thr.addEventListener("change", () => syncConfigSelectFromChips());
    thr.addEventListener("input", () => syncConfigSelectFromChips());
  }
}

async function loadRunProfiles() {
  try {
    const data = await api("/api/run-profiles");
    if (Array.isArray(data.order) && data.order.length) runProfileOrder = data.order;
  } catch {
    /* keep defaults */
  }
  renderRunProfileChips();
}

function renderFstartChips(configs, preferred) {
  const row = $("#fstart-chip-row");
  if (!row) return;
  const prev = new Set(fstartSelected);
  fstartSelected = new Set();
  row.innerHTML = (configs || [])
    .map((c) => {
      const short = escapeHtml(fstartChipLabel(c));
      return `<button type="button" class="fstart-chip" data-path="${escapeHtml(c)}" title="${escapeHtml(c)}">${short}</button>`;
    })
    .join("");
  row.querySelectorAll(".fstart-chip").forEach((btn) => {
    const path = btn.dataset.path;
    btn.addEventListener("click", () => {
      fstartSelected = new Set([path]);
      fstartPrimary = path;
      row.querySelectorAll(".fstart-chip").forEach((b) => {
        b.classList.toggle("selected", fstartSelected.has(b.dataset.path));
        b.classList.toggle("active-primary", b.dataset.path === fstartPrimary);
      });
      syncConfigSelectFromChips();
    });
    if (prev.has(path) || path === preferred || (!preferred && prev.size === 0 && path === configs[0])) {
      fstartSelected.add(path);
    }
  });
  if (!fstartSelected.size && configs?.length) {
    fstartSelected.add(preferred && configs.includes(preferred) ? preferred : configs[0]);
  }
  fstartPrimary = preferred && fstartSelected.has(preferred) ? preferred : selectedFstartPaths()[0] || null;
  row.querySelectorAll(".fstart-chip").forEach((b) => {
    b.classList.toggle("selected", fstartSelected.has(b.dataset.path));
    b.classList.toggle("active-primary", b.dataset.path === fstartPrimary);
  });
  syncConfigSelectFromChips();
}

async function loadAppVersion() {
  try {
    const d = await api("/api/version");
    const foot = $("#footer-version");
    if (foot) foot.textContent = `qoa_web v${d.version} · Arena`;
  } catch {
    /* keep static footer */
  }
}

function renderCycleHistory() {
  const el = $("#cycle-history");
  if (!el) return;
  const items = activeProject?.cycle_history || [];
  const peakFails = items.reduce((m, e) => Math.max(m, Number(e.stats?.fails ?? 0)), 0);
  el.innerHTML = items.length
    ? items
        .map((e) => {
          const s = e.stats;
          let statPill = "";
          let badge = "";
          if (s && (s.total_plans || s.passes || s.fails)) {
            statPill = ` <span class="cycle-stat">${s.passes ?? 0}/${s.total_plans ?? 0} pass · ${s.fails ?? 0} fail</span>`;
            const isLoopStep = /^(verify|loop)/i.test(e.step || "");
            if (peakFails > 0 && Number(s.fails) === 0 && isLoopStep) {
              badge = ' <span class="cycle-badge cycle-recovered">Recovered</span>';
            }
          }
          return (
            `<li><strong>${escapeHtml(e.step)}</strong> ${escapeHtml(e.detail || "")}${statPill}${badge} ` +
            `<span class="meta">${escapeHtml((e.at || "").replace("T", " ").slice(0, 19))}</span></li>`
          );
        })
        .join("")
    : '<li class="empty-hint">No cycle steps yet — run Loop from this tab.</li>';
}

function updateHealHint() {
  const hint = $("#heal-run-hint");
  if (!hint) return;
  if (!activeProject?.latest_run) {
    hint.textContent =
      "Select a run in Analyze. AI Apply edits Input/Expected/locators only — never Run flags. Shrink (below) is for Loop prep.";
    return;
  }
  hint.textContent = `Last run: ${activeProject.latest_run} — Apply = CSV field patches · Shrink = Run=Y on failures only (Restore undoes it).`;
}

async function recordCycleEvent(step, detail, runName) {
  if (!state.projectId) return;
  try {
    await api(`/api/projects/${state.projectId}/cycle`, {
      method: "POST",
      body: JSON.stringify({ step, detail, run_name: runName || undefined }),
    });
    await refreshActiveProject();
    renderCycleHistory();
  } catch {
    /* non-fatal */
  }
}

function refreshProjectBannerMeta() {
  const meta = $("#project-banner-meta");
  if (!meta) return;
  const suite = state.suites.find((s) => s.name === state.suiteName);
  if (!activeProject && !suite) {
    meta.hidden = true;
    return;
  }
  meta.hidden = false;
  const name = suite?.name || activeProject?.name || state.suiteName || "—";
  const ins = ypadState.insights;
  const auto = ins?.automated ?? suite?.plan_run_y ?? "—";
  const total = ins?.totalPlans ?? suite?.plan_total ?? "—";
  const aiLabel = isAiOn() ? "AI on" : "AI off";
  const parts = [`yPAD ${name}`, `${total} plans`];
  if (ins?.actionSteps != null) parts.push(`${ins.actionSteps} steps`);
  if (ins?.designRows != null) parts.push(`${ins.designRows} data`);
  parts.push(`${auto} automated`, aiLabel);
  meta.textContent = parts.join(" · ");
  meta.title =
    "yPAD = Plans (what) · Actions (steps) · Designs (data). Automated = Run=Y. Open the yPAD widget (above Wallet) for details.";
}

function updateProjectBanner(payoutPreview) {
  applyAiMode();
  updateInviteButtonState();
  const meta = $("#project-banner-meta");
  const strip = $("#context-strip");
  const suite = state.suites.find((s) => s.name === state.suiteName);
  if (!activeProject && !suite) {
    if (meta) meta.hidden = true;
    strip?.classList.remove("has-project");
    const hitlEl = $("#project-banner-hitl");
    if (hitlEl) hitlEl.hidden = true;
    return;
  }
  strip?.classList.add("has-project");
  refreshProjectBannerMeta();
  const hitlEl = $("#project-banner-hitl");
  const hitlCount = activeProject ? (activeProject.hitl_consultants || []).length : 0;
  if (activeProject && hitlCount > 0 && payoutPreview?.length) {
    hitlEl.hidden = false;
    hitlEl.innerHTML = payoutPreview
      .map(
        (p) =>
          `<span class="hitl-chip">${escapeHtml(p.name)}: $${p.payout_usd} ` +
          `(${p.deliverables?.critical_issues || 0} issues, ${p.deliverables?.reports_submitted || 0} reports)</span>`
      )
      .join("");
  } else if (hitlEl) {
    hitlEl.hidden = true;
  }
  syncProjectStatus();
}

function syncProjectToUI() {
  if (!activeProject) return;
  const purpose = activeProject.purpose || activeProject.prompt || "";
  const cyclePrompt = $("#cycle-prompt");
  if (cyclePrompt) cyclePrompt.value = purpose;
  const paths = (activeProject.context_items || []).map((c) => c.value).filter(Boolean);
  (activeProject.documents || []).forEach((d) => paths.push(d.path));
  const cycleDocs = $("#cycle-docs");
  if (cycleDocs) cycleDocs.value = [...new Set(paths)].join("\n");
  refreshLoopBuiltSummary();
  const scope = `Scoped to: ${activeProject.name}`;
  const runScope = $("#run-project-scope");
  const analyzeScope = $("#analyze-project-scope");
  const healScope = $("#heal-project-scope");
  if (runScope) runScope.textContent = scope;
  if (analyzeScope) analyzeScope.textContent = scope;
  if (healScope) healScope.textContent = scope;
}

function renderMarkdown(md) {
  let html = escapeHtml(md);
  html = html.replace(/^#### (.+)$/gm, "<h5>$1</h5>");
  html = html.replace(/^### (.+)$/gm, "<h4>$1</h4>");
  html = html.replace(/^## (.+)$/gm, "<h3>$1</h3>");
  html = html.replace(/^# (.+)$/gm, "<h2>$1</h2>");
  html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  html = html.replace(/`([^`]+)`/g, "<code>$1</code>");
  html = html.replace(/^- (.+)$/gm, "<li>$1</li>");
  html = html.replace(/(<li>.*<\/li>)/gs, "<ul>$1</ul>");
  html = html.replace(/\n/g, "<br>");
  // Simple GFM tables (after newlines → <br>)
  html = html.replace(/(?:^|<br>)(\|.+\|(?:<br>\|.+\|)+)/g, (block) => {
    const rows = block
      .replace(/^<br>/, "")
      .split("<br>")
      .map((r) => r.trim())
      .filter((r) => r.startsWith("|"));
    if (rows.length < 2) return block;
    const parse = (row) =>
      row
        .replace(/^\|/, "")
        .replace(/\|$/, "")
        .split("|")
        .map((c) => c.trim());
    const head = parse(rows[0]);
    const bodyRows = rows.slice(1).filter((r) => !/^\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)*\|?$/.test(r));
    let out = '<table class="ai-md-table"><thead><tr>' + head.map((c) => `<th>${c}</th>`).join("") + "</tr></thead><tbody>";
    bodyRows.forEach((r) => {
      out += "<tr>" + parse(r).map((c) => `<td>${c}</td>`).join("") + "</tr>";
    });
    return out + "</tbody></table>";
  });
  return html;
}

function renderBrahlChat() {
  const el = $("#brahl-chat-thread");
  if (!el || !activeProject) return;
  const msgs = activeProject.brahl_chat_messages || [];
  el.innerHTML = msgs
    .map(
      (m) =>
        `<div class="chat-msg chat-${m.role}"><span class="chat-role">${m.role === "assistant" ? "BRAHL" : "You"}</span>${m.role === "assistant" ? renderMarkdown(m.text) : escapeHtml(m.text)}</div>`
    )
    .join("");
  el.scrollTop = el.scrollHeight;
}

function teamAuthorMeta() {
  const profile = state.profile;
  const isHunter = state.avatar === "consultant";
  const name =
    profile?.name ||
    (isHunter ? "QA Hunter" : state.avatar === "client" ? "Creator" : "Teammate");
  return {
    author: name,
    author_role: isHunter ? "hunter" : "creator",
    created_by: name,
  };
}

function renderBrahlTeamRoster(project) {
  const el = $("#brahl-team-roster");
  if (!el) return;
  const owner = project?.name ? `Creator · ${project.name}` : "Creator";
  const team = project?.hitl_consultants || [];
  const pending = (project?.hitl_invites || []).filter((i) => (i.status || "pending") === "pending");
  const rows = [
    `<div class="brahl-team-member"><strong>Creator</strong> — project owner</div>`,
    ...team.map((c) => {
      const d = c.deliverables || {};
      return `<div class="brahl-team-member"><strong>${escapeHtml(c.name || "QA Hunter")}</strong> — ${d.critical_issues || 0} critical · ${d.reports_submitted || 0} reports</div>`;
    }),
  ];
  if (pending.length) {
    rows.push(
      ...pending.map(
        (i) =>
          `<div class="brahl-team-member"><em>Pending invite</em> — ${escapeHtml(i.consultant_name || i.email || "QA Hunter")}</div>`
      )
    );
  }
  if (!team.length && !pending.length) {
    rows.push(`<p class="empty-hint">No QA Hunters yet — invite from here or Build.</p>`);
  }
  el.innerHTML = rows.join("");
  void owner;
}

function renderBrahlTeamChat(messages) {
  const el = $("#brahl-team-chat-thread");
  if (!el) return;
  const msgs = messages || [];
  if (!msgs.length) {
    el.innerHTML =
      '<p class="empty-hint">Start the conversation — scope, bugs, and next BRAHL loops live here.</p>';
    return;
  }
  el.innerHTML = msgs
    .map((m) => {
      const roleLabel =
        m.author_role === "hunter" ? "QA Hunter" : m.author_role === "system" ? "System" : "Creator";
      return `<div class="chat-msg chat-user"><span class="chat-role">${escapeHtml(m.author || roleLabel)} · ${roleLabel}</span>${escapeHtml(m.text || "")}</div>`;
    })
    .join("");
  el.scrollTop = el.scrollHeight;
}

function renderBrahlTeamTasks(tasks) {
  const el = $("#brahl-team-tasks");
  if (!el) return;
  const list = tasks || [];
  if (!list.length) {
    el.innerHTML = '<li class="empty-hint">No tasks yet — Creator can assign work for payouts later.</li>';
    return;
  }
  el.innerHTML = list
    .map((t) => {
      const done = t.status === "done";
      return `<li class="brahl-team-task${done ? " done" : ""}" data-task-id="${escapeHtml(t.id)}">
        <strong>${escapeHtml(t.title || "")}</strong>
        ${t.assignee ? ` · ${escapeHtml(t.assignee)}` : ""}
        <button type="button" class="secondary brahl-task-toggle" data-task-id="${escapeHtml(t.id)}" data-next="${done ? "open" : "done"}">${done ? "Reopen" : "Done"}</button>
      </li>`;
    })
    .join("");
}

async function loadBrahlTeamWorkspace() {
  if (!state.projectId) return;
  let project = activeProject;
  try {
    const data = await api(`/api/projects/${state.projectId}/team`);
    if (activeProject) {
      activeProject.team_messages = data.team_messages || [];
      activeProject.team_tasks = data.team_tasks || [];
      activeProject.hitl_consultants = data.hitl_consultants || activeProject.hitl_consultants;
      activeProject.hitl_invites = data.hitl_invites || activeProject.hitl_invites;
      activeProject.context_items = data.context_items || activeProject.context_items;
      activeProject.documents = data.documents || activeProject.documents;
      project = activeProject;
    } else {
      project = {
        hitl_consultants: data.hitl_consultants,
        hitl_invites: data.hitl_invites,
        team_messages: data.team_messages,
        team_tasks: data.team_tasks,
        context_items: data.context_items,
        documents: data.documents,
      };
    }
  } catch {
    /* keep local project snapshot */
  }
  if (!project) return;
  renderBrahlTeamRoster(project);
  renderBrahlTeamChat(project.team_messages || []);
  renderBrahlTeamTasks(project.team_tasks || []);
  await renderEvidenceLibraries();
}

async function sendBrahlTeamChat(ev) {
  ev.preventDefault();
  if (!state.projectId) return;
  const input = $("#brahl-team-chat-input");
  const text = input?.value?.trim();
  if (!text) return;
  input.value = "";
  const meta = teamAuthorMeta();
  try {
    const data = await api(`/api/projects/${state.projectId}/team/chat`, {
      method: "POST",
      body: JSON.stringify({ text, author: meta.author, author_role: meta.author_role }),
    });
    if (data.project) activeProject = data.project;
    renderBrahlTeamChat(data.team_messages || activeProject?.team_messages || []);
    setStatus("Team message sent");
  } catch (err) {
    input.value = text;
    setStatus(`Team chat failed: ${err.message}`);
  }
}

async function addBrahlTeamTask(ev) {
  ev.preventDefault();
  if (!state.projectId) return;
  const input = $("#brahl-team-task-title");
  const title = input?.value?.trim();
  if (!title) return;
  input.value = "";
  const meta = teamAuthorMeta();
  try {
    const data = await api(`/api/projects/${state.projectId}/team/tasks`, {
      method: "POST",
      body: JSON.stringify({ title, created_by: meta.created_by }),
    });
    if (data.project) activeProject = data.project;
    renderBrahlTeamTasks(data.team_tasks || []);
    setStatus("Task added");
  } catch (err) {
    input.value = title;
    setStatus(`Task failed: ${err.message}`);
  }
}

async function toggleBrahlTeamTask(taskId, nextStatus) {
  if (!state.projectId || !taskId) return;
  try {
    const data = await api(`/api/projects/${state.projectId}/team/tasks/${encodeURIComponent(taskId)}`, {
      method: "PATCH",
      body: JSON.stringify({ status: nextStatus }),
    });
    if (data.project) activeProject = data.project;
    renderBrahlTeamTasks(data.team_tasks || []);
  } catch (err) {
    setStatus(`Task update failed: ${err.message}`);
  }
}

async function addBrahlTeamLibraryLink(ev) {
  ev.preventDefault();
  if (!state.projectId) return;
  const label = $("#brahl-team-lib-label")?.value?.trim() || "";
  const value = $("#brahl-team-lib-url")?.value?.trim() || "";
  if (!value) return;
  try {
    const data = await api(`/api/projects/${state.projectId}/context`, {
      method: "POST",
      body: JSON.stringify({ kind: "url", label: label || "Link", value }),
    });
    activeProject = data.project;
    if ($("#brahl-team-lib-label")) $("#brahl-team-lib-label").value = "";
    if ($("#brahl-team-lib-url")) $("#brahl-team-lib-url").value = "";
    await registerEvidence("url", { url: value, title: label || value });
    setStatus("Library link added");
  } catch (err) {
    setStatus(`Library failed: ${err.message}`);
  }
}

async function uploadBrahlTeamFile(ev) {
  const file = ev.target?.files?.[0];
  if (!file || !state.projectId) return;
  const fd = new FormData();
  fd.append("file", file);
  try {
    const res = await fetch(`/api/projects/${state.projectId}/documents`, { method: "POST", body: fd });
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();
    if (data.project) activeProject = data.project;
    else await refreshActiveProject();
    const path = data.document?.path;
    if (path) await registerEvidence("document", { path, title: file.name });
    else await renderEvidenceLibraries();
    setStatus(`Uploaded ${file.name}`);
  } catch (err) {
    setStatus(`Upload failed: ${err.message}`);
  } finally {
    ev.target.value = "";
  }
}

function bindBrahlTeamWorkspace() {
  if (bindBrahlTeamWorkspace._bound) return;
  bindBrahlTeamWorkspace._bound = true;
  $("#brahl-team-chat-form")?.addEventListener("submit", sendBrahlTeamChat);
  $("#brahl-team-task-form")?.addEventListener("submit", addBrahlTeamTask);
  $("#brahl-team-library-form")?.addEventListener("submit", addBrahlTeamLibraryLink);
  $("#brahl-team-file")?.addEventListener("change", uploadBrahlTeamFile);
  $("#brahl-team-invite")?.addEventListener("click", () => openInviteHitlModal());
  $("#brahl-team-tasks")?.addEventListener("click", (e) => {
    const btn = e.target.closest(".brahl-task-toggle");
    if (!btn) return;
    toggleBrahlTeamTask(btn.dataset.taskId, btn.dataset.next);
  });
}

function loadAtomic77LocalMessages() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_A77_LOCAL) || "[]");
  } catch {
    return [];
  }
}

function saveAtomic77LocalMessage(role, text) {
  const msgs = loadAtomic77LocalMessages();
  msgs.push({ id: String(Date.now()), role, text, at: new Date().toISOString() });
  if (msgs.length > 40) msgs.splice(0, msgs.length - 40);
  localStorage.setItem(STORAGE_A77_LOCAL, JSON.stringify(msgs));
}

function atomic77Messages() {
  if (activeProject?.atomic77_chat_messages?.length) return activeProject.atomic77_chat_messages;
  const local = loadAtomic77LocalMessages();
  if (local.length) return local;
  return [
    {
      id: "a77-welcome",
      role: "assistant",
      text:
        "I'm **Atomic 77** — idea to launch inside QA on Air. Pick an FAQ chip or ask anything. " +
        "Select a challenge in the top bar to tie answers to your project budget on **$**.",
    },
  ];
}

function renderAtomic77Chat() {
  const el = $("#atomic77-chat-thread");
  if (!el) return;
  const msgs = atomic77Messages();
  el.innerHTML = msgs
    .map(
      (m) =>
        `<div class="chat-msg chat-${m.role}"><span class="chat-role">${m.role === "assistant" ? "A77" : "You"}</span>${m.role === "assistant" ? renderMarkdown(m.text) : escapeHtml(m.text)}</div>`
    )
    .join("");
  el.scrollTop = el.scrollHeight;
}

function renderAtomic77Usage() {
  const wrap = $("#atomic77-usage");
  const textEl = $("#atomic77-usage-text");
  if (!wrap || !textEl) return;
  const usage = activeProject?.atomic77_usage;
  if (!usage || !state.projectId) {
    wrap.hidden = true;
    return;
  }
  wrap.hidden = false;
  const tokens = usage.tokens_est || 0;
  const users = usage.user_messages || 0;
  textEl.textContent = `${users} prompts · ~${tokens.toLocaleString()} tokens est. · tracked on $ tab`;
}

function loadAtomic77Panel() {
  renderAtomic77Chat();
  renderAtomic77Usage();
  const blurb = $("#atomic77-blurb");
  if (blurb && state.avatar) {
    const who = avatarLabel(state.avatar).short;
    blurb.innerHTML =
      `Idea → Build → BRAHL → launch — helping <strong>${escapeHtml(who)}</strong> with FAQ, scope, and launch. ` +
      `Respects <strong>AI on/off</strong>; usage flows to the <strong>$</strong> tab and admin analytics.`;
  }
}

async function sendAtomic77Chat(ev, faqKey) {
  ev?.preventDefault?.();
  const input = $("#atomic77-chat-input");
  const faqLabels = {
    idea: "How do I turn my idea into a BRAHL project?",
    brahl: "Explain BRAHL for my app",
    launch: "What's the launch checklist?",
    cost: "How do membership, $5/mo, QA wallet from $50, and $100 payouts work?",
    hunter: "How do I hunt and get paid?",
  };
  const text = faqKey ? faqLabels[faqKey] || faqKey : input?.value?.trim();
  if (!text) return;
  if (!faqKey && input) input.value = "";
  if (!state.avatar) {
    setStatus("Choose an avatar first");
    return;
  }
  if (!faqKey && !isAiOn()) {
    const lower = text.toLowerCase();
    const keywordMap = {
      idea: ["idea", "project", "ypad", "start"],
      brahl: ["brahl", "loop", "verify"],
      launch: ["launch", "go/no", "gonogo", "ship"],
      cost: ["cost", "wallet", "budget", "$", "price", "payout"],
      hunter: ["hunt", "hunter", "paid", "earn"],
    };
    for (const [key, words] of Object.entries(keywordMap)) {
      if (words.some((w) => lower.includes(w))) {
        faqKey = key;
        break;
      }
    }
    if (!faqKey) {
      setStatus("AI is off — use FAQ chips or mention idea/BRAHL/launch/cost/hunter");
      return;
    }
  }
  try {
    let data;
    if (state.projectId) {
      data = await api(`/api/projects/${state.projectId}/atomic77/chat`, {
        method: "POST",
        body: JSON.stringify({ text, faq_key: faqKey || null, avatar: state.avatar }),
      });
      activeProject = data.project;
    } else {
      saveAtomic77LocalMessage("user", text);
      data = await api("/api/atomic77/chat", {
        method: "POST",
        body: JSON.stringify({
          text,
          faq_key: faqKey || null,
          avatar: state.avatar,
        }),
      });
      saveAtomic77LocalMessage("assistant", data.assistant_message?.text || "");
    }
    addXp("atomic77_activity", 8);
    if (data.tokens_est) addXp("atomic77_tokens", Math.max(1, Math.round(data.tokens_est / 100)));
    renderAtomic77Chat();
    renderAtomic77Usage();
    if (state.phase === "cost") loadCostPanel();
  } catch (e) {
    setStatus(e.message || "Atomic 77 chat failed");
  }
}

let brahlReportTab = "automation";
const brahlReportsCache = { runs: [], huntReports: [] };

function renderBrahlReportTabs() {
  $$(".brahl-report-tab").forEach((btn) => {
    const active = btn.dataset.tab === brahlReportTab;
    btn.classList.toggle("active", active);
    btn.setAttribute("aria-selected", active ? "true" : "false");
  });
}

function renderBrahlReportListFromCache() {
  const list = $("#brahl-report-list");
  if (!list) return;
  renderBrahlReportTabs();
  const { runs, huntReports } = brahlReportsCache;
  list.innerHTML = "";
  if (brahlReportTab === "human") {
    if (!huntReports.length) {
      list.innerHTML =
        '<li class="empty-hint">No QA Hunter reports yet — submit one from the QA Hunter workspace.</li>';
      return;
    }
    huntReports.forEach((r) => {
      const li = document.createElement("li");
      const label = PathBasename(r.report_path) || r.run_name;
      const isSel = selectedBrahlReportId ? r.id === selectedBrahlReportId : false;
      if (isSel) li.classList.add("selected");
      li.innerHTML =
        `<span class="source-badge sm source-${escapeHtml(r.source || "human_in_the_loop")}">${escapeHtml(r.source_label || "QA Hunter")}</span>` +
        `<span>${escapeHtml(label)}</span>` +
        `<span class="meta">${escapeHtml(r.run_name)}</span>`;
      li.onclick = () =>
        selectBrahlReport(r.run_name, {
          source: r.source || "human_in_the_loop",
          source_label: r.source_label || "QA Hunter",
          report_id: r.id,
          is_hunt: true,
          report_path: r.report_path,
          archived: Boolean(r.archived),
        });
      list.appendChild(li);
    });
  } else {
    if (!runs.length) {
      list.innerHTML = '<li class="empty-hint">No automation verify runs yet — Run on the Run tab.</li>';
      return;
    }
    runs.forEach((r, i) => {
      const li = document.createElement("li");
      const isSel = !selectedBrahlReportId && (selectedBrahlRun ? r.name === selectedBrahlRun : i === 0);
      if (isSel) li.classList.add("selected");
      li.innerHTML =
        `<span class="source-badge sm">Run</span><span>${escapeHtml(r.name)}</span>` +
        `<span class="meta">${r.passes} pass · ${r.fails} fail</span>`;
      li.onclick = () =>
        selectBrahlReport(r.name, { source: "automation", source_label: "Automation", report_id: null, is_hunt: false });
      list.appendChild(li);
    });
  }
}

function bindBrahlReportTabs() {
  if (bindBrahlReportTabs._bound) return;
  bindBrahlReportTabs._bound = true;
  $("#brahl-report-tabs")?.addEventListener("click", (e) => {
    const btn = e.target.closest(".brahl-report-tab");
    if (!btn || btn.dataset.tab === brahlReportTab) return;
    brahlReportTab = btn.dataset.tab;
    renderBrahlReportListFromCache();
  });
}

async function loadBrahlPanel() {
  if (!state.projectId || !state.suiteName) return;
  bindBrahlTeamWorkspace();
  bindBrahlReportTabs();
  await loadBrahlTeamWorkspace();

  let projectReports = [];
  try {
    const pr = await api(`/api/projects/${state.projectId}/brahl/reports`);
    projectReports = pr.reports || [];
  } catch {
    projectReports = [];
  }

  const data = await api(`/api/suites/${encodeURIComponent(state.suiteName)}/brahl/reports`);
  const runs = data.runs || [];
  const huntReports = projectReports.filter(
    (r) => r.is_hunt_report || (r.source || "").includes("human")
  );
  brahlReportsCache.runs = runs;
  brahlReportsCache.huntReports = huntReports;
  // Default the tab to wherever the latest activity is, without fighting a user's explicit choice.
  if (!runs.length && huntReports.length) brahlReportTab = "human";
  else if (runs.length && brahlReportTab === "human" && !huntReports.length) brahlReportTab = "automation";

  if (!runs.length && !huntReports.length) {
    renderBrahlReportListFromCache();
    $("#brahl-report-body").innerHTML =
      `<p class="empty-hint">No BRAHL report for <strong>${escapeHtml(state.suiteName)}</strong> yet. Run from the <strong>Run</strong> tab (Smoke profile) or Verify on Loop, then return here.</p>` +
      (data.suite?.description ? `<p class="hint">${escapeHtml(data.suite.description)}</p>` : "");
    $("#brahl-report-summary").hidden = true;
    $("#brahl-hunt-artifacts").hidden = true;
    $("#brahl-report-title").textContent = state.suiteName;
    $("#brahl-report-source").textContent = "y/ suite";
    $("#brahl-report-status-badge").hidden = true;
    $("#brahl-zdash-embed-wrap").hidden = true;
    $("#brahl-evidence-wrap").hidden = true;
    renderGoNoGo(null);
    renderVersionCompare(null);
    renderBrahlChat();
    return;
  }

  renderBrahlReportListFromCache();

  const pickHunt = huntReports.find((r) => r.id === selectedBrahlReportId) || huntReports[0];
  const pickRun = selectedBrahlRun || data.latest_run_name || runs[0]?.name;
  if (pickHunt && selectedBrahlReportId) {
    await selectBrahlReport(pickHunt.run_name, {
      source: pickHunt.source,
      source_label: pickHunt.source_label,
      report_id: pickHunt.id,
      is_hunt: true,
      report_path: pickHunt.report_path,
      archived: Boolean(pickHunt.archived),
    });
  } else if (brahlReportTab === "human" && pickHunt) {
    await selectBrahlReport(pickHunt.run_name, {
      source: pickHunt.source,
      source_label: pickHunt.source_label,
      report_id: pickHunt.id,
      is_hunt: true,
      report_path: pickHunt.report_path,
      archived: Boolean(pickHunt.archived),
    });
  } else if (pickRun) {
    await selectBrahlReport(pickRun, { source: "automation", source_label: "Automation", report_id: null, is_hunt: false });
  }
  renderBrahlChat();
}

function PathBasename(path) {
  if (!path) return "";
  const parts = String(path).replace(/\\/g, "/").split("/");
  return parts[parts.length - 1] || "";
}

function renderBrahlHuntArtifacts(artifacts) {
  const wrap = $("#brahl-hunt-artifacts");
  if (!wrap) return;
  if (!artifacts?.length || !state.projectId) {
    wrap.hidden = true;
    wrap.innerHTML = "";
    return;
  }
  const uploadUrl = (path) => {
    const name = PathBasename(path);
    return name ? `/api/projects/${encodeURIComponent(state.projectId)}/uploads/${encodeURIComponent(name)}` : "#";
  };
  const videos = artifacts.filter((a) => String(a).toLowerCase().endsWith(".webm"));
  const others = artifacts.filter((a) => !String(a).toLowerCase().endsWith(".webm"));
  let html = "<h4>Hunt recordings &amp; artifacts</h4>";
  if (videos.length) {
    html += videos
      .map(
        (v) =>
          `<video controls playsinline preload="metadata" src="${escapeHtml(uploadUrl(v))}" title="${escapeHtml(PathBasename(v))}"></video>`
      )
      .join("");
  }
  if (others.length) {
    html +=
      `<ul class="brahl-hunt-artifact-list">` +
      others
        .map(
          (a) =>
            `<li><a href="${escapeHtml(uploadUrl(a))}" target="_blank" rel="noopener">${escapeHtml(PathBasename(a))}</a></li>`
        )
        .join("") +
      `</ul>`;
  }
  wrap.innerHTML = html;
  wrap.hidden = false;
}

let lastVersionCompare = null;

function renderGoNoGo(stats) {
  const block = $("#gonogo-block");
  const label = $("#gonogo-label");
  const cb = $("#gonogo-launch-ready");
  const scorecard = $("#scorecard");
  const stamp = $("#scorecard-stamp");
  const pctEl = $("#scorecard-pct");
  const ring = $("#scorecard-ring-fg");
  const obs = $("#scorecard-observations");
  if (!block) return;
  if (state.avatar !== "client") {
    block.hidden = true;
    return;
  }
  block.hidden = false;
  const total = stats?.total_plans || 0;
  if (!total) {
    if (label) label.textContent = "Run Verify on Loop for a Go / No-Go opinion";
    if (cb) cb.checked = false;
    if (scorecard) {
      scorecard.className = "scorecard scorecard-pending";
    }
    if (stamp) stamp.textContent = "PENDING";
    if (pctEl) pctEl.textContent = "—";
    if (ring) ring.style.strokeDashoffset = String(2 * Math.PI * 52);
    if (obs) {
      obs.hidden = true;
      obs.innerHTML = "";
    }
    $("#sc-pass").textContent = "0";
    $("#sc-fail").textContent = "0";
    $("#sc-total").textContent = "0";
    $("#sc-time").textContent = "—";
    return;
  }
  const passes = stats.passes ?? 0;
  const fails = stats.fails ?? 0;
  const go =
    fails === 0 &&
    passes > 0 &&
    !(lastVersionCompare?.regression_count > 0);
  const pct = Math.round((passes / total) * 100);
  if (cb) cb.checked = go;
  if (label) {
    if (lastVersionCompare?.regression_count > 0) {
      label.textContent = `${lastVersionCompare.regression_count} regression(s) vs baseline — hold launch`;
    } else {
      label.textContent = go
        ? "Verify clean — launch approved for this scope"
        : "Failures remaining — not launch-ready for this scope";
    }
  }
  if (stamp) stamp.textContent = go ? "GO" : "NO-GO";
  if (pctEl) pctEl.textContent = `${pct}%`;
  if (scorecard) {
    scorecard.className = `scorecard ${go ? "scorecard-go" : "scorecard-nogo"}`;
  }
  if (ring) {
    const c = 2 * Math.PI * 52;
    ring.style.strokeDasharray = String(c);
    ring.style.strokeDashoffset = String(c * (1 - pct / 100));
  }
  $("#sc-pass").textContent = String(passes);
  $("#sc-fail").textContent = String(fails);
  $("#sc-total").textContent = String(total);
  $("#sc-time").textContent = stats.duration_sec > 0 ? `${stats.duration_sec}s` : "—";
  if (obs) {
    const failures = stats.failures || [];
    if (failures.length) {
      obs.hidden = false;
      obs.innerHTML =
        `<h4>Key observations</h4><ul>` +
        failures
          .slice(0, 6)
          .map((f) => {
            const pid = f.planId || f.PlanId || "plan";
            const info = f.stepInfo || f.StepInfo || f.message || "failed step";
            return `<li><strong>${escapeHtml(pid)}</strong> — ${escapeHtml(String(info).slice(0, 120))}</li>`;
          })
          .join("") +
        `</ul>`;
    } else {
      obs.hidden = false;
      obs.innerHTML = `<h4>Key observations</h4><p>All automated plans in scope passed. Review zDash for timing and evidence before production cutover.</p>`;
    }
  }
}

// Best-effort live status for the run currently being polled by startRun(), so a
// report the user is looking at can show "running" instead of looking stale/broken.
const liveRunStatus = { runName: null, status: null };

function reportStatusFor(runName, meta, stats) {
  if (meta?.archived) return "archived";
  if (runName && liveRunStatus.runName === runName && liveRunStatus.status === "running") return "running";
  if (!stats || !stats.total_plans) return meta?.is_hunt ? "completed" : null;
  if (!meta?.is_hunt && !stats.dashboard) return "generating";
  if (stats.fails > 0) return "failed";
  return "completed";
}

const REPORT_STATUS_LABELS = {
  running: "Running…",
  generating: "Generating zDash…",
  completed: "Completed",
  failed: "Failed",
  archived: "Archived",
};

function renderReportStatusBadge(runName, meta, stats) {
  const badge = $("#brahl-report-status-badge");
  if (!badge) return;
  const status = reportStatusFor(runName, meta, stats);
  if (!status) {
    badge.hidden = true;
    return;
  }
  badge.hidden = false;
  badge.textContent = REPORT_STATUS_LABELS[status] || status;
  badge.className = `report-status-badge status-${status}`;
}

function renderZdashEmbed(stats) {
  const wrap = $("#brahl-zdash-embed-wrap");
  const frame = $("#brahl-zdash-embed");
  if (!wrap || !frame) return;
  const href = zDashHref(stats?.dashboard);
  if (href) {
    wrap.hidden = false;
    if (frame.src !== location.origin + href) frame.src = href;
  } else {
    wrap.hidden = true;
    frame.src = "about:blank";
  }
}

async function renderReportEvidence(reportId) {
  const wrap = $("#brahl-evidence-wrap");
  const list = $("#brahl-report-evidence-list");
  if (!wrap || !list) return;
  if (!reportId || !state.projectId) {
    wrap.hidden = true;
    list.innerHTML = "";
    return;
  }
  try {
    const { items } = await api(`/api/projects/${state.projectId}/evidence?report_id=${encodeURIComponent(reportId)}`);
    wrap.hidden = false;
    list.innerHTML = (items || []).length
      ? items.map(evidenceItemHtml).join("")
      : '<li class="empty-hint">No evidence linked to this report yet.</li>';
  } catch {
    wrap.hidden = true;
  }
}

function renderBrahlSummaryStats(stats, runName) {
  const wrap = $("#brahl-report-summary");
  if (!wrap || !stats?.total_plans) {
    if (wrap) wrap.hidden = true;
    renderGoNoGo(stats?.total_plans ? stats : null);
    renderZdashEmbed(stats);
    return;
  }
  wrap.hidden = false;
  const badge = $("#brahl-health-badge");
  const health = stats.health || "unknown";
  if (badge) {
    badge.textContent = health === "green" ? "Healthy" : health === "amber" ? "Needs attention" : "Unknown";
    badge.className = `health-badge health-${health}`;
  }
  $("#brahl-stat-pass").textContent = stats.passes ?? 0;
  $("#brahl-stat-fail").textContent = stats.fails ?? 0;
  $("#brahl-stat-total").textContent = stats.total_plans ?? 0;
  const timeWrap = $("#brahl-stat-time-wrap");
  if (stats.duration_sec > 0) {
    timeWrap.hidden = false;
    $("#brahl-stat-time").textContent = stats.duration_sec;
  } else if (timeWrap) {
    timeWrap.hidden = true;
  }
  const zdash = $("#brahl-zdash-link");
  if (zdash) {
    const href = zDashHref(stats.dashboard);
    if (href) {
      zdash.href = href;
      zdash.hidden = false;
    } else {
      zdash.hidden = true;
    }
  }
  renderZdashEmbed(stats);
  renderGoNoGo(stats);
}

let currentBrahlReportRef = { id: null, archived: false };

function bindBrahlArchiveToggle() {
  if (bindBrahlArchiveToggle._bound) return;
  bindBrahlArchiveToggle._bound = true;
  $("#brahl-report-archive-toggle")?.addEventListener("click", async () => {
    if (!state.projectId || !currentBrahlReportRef.id) return;
    const next = !currentBrahlReportRef.archived;
    try {
      await api(`/api/projects/${state.projectId}/brahl/reports/${currentBrahlReportRef.id}/archive`, {
        method: "POST",
        body: JSON.stringify({ archived: next }),
      });
      currentBrahlReportRef.archived = next;
      const btn = $("#brahl-report-archive-toggle");
      if (btn) btn.textContent = next ? "Unarchive" : "Archive";
      renderReportStatusBadge(selectedBrahlRun, { archived: next }, null);
    } catch (e) {
      setStatus(`Could not update archive state: ${e.message}`);
    }
  });
}

async function selectBrahlReport(runName, meta) {
  if (!state.suiteName) return;
  bindBrahlArchiveToggle();
  selectedBrahlRun = runName;
  selectedBrahlReportId = meta?.report_id || null;
  $$("#brahl-report-list li").forEach((li) => li.classList.remove("selected"));
  $$("#brahl-report-list li").forEach((li) => {
    if (meta?.report_id && li.textContent.includes(PathBasename(meta.report_path))) li.classList.add("selected");
    else if (!meta?.report_id && li.textContent.includes(runName)) li.classList.add("selected");
  });
  $("#brahl-report-title").textContent = meta?.is_hunt ? PathBasename(meta.report_path) || runName : runName;
  const srcEl = $("#brahl-report-source");
  srcEl.textContent = meta?.source_label || "BRAHL";
  srcEl.className = `source-badge source-${meta?.source || "automation"}`;
  try {
    let data;
    if (state.projectId && meta?.is_hunt) {
      const q = meta.report_id ? `?report_id=${encodeURIComponent(meta.report_id)}` : "";
      data = await api(
        `/api/projects/${state.projectId}/brahl/reports/${encodeURIComponent(runName)}/content${q}`
      );
    } else {
      const q = state.projectId ? `?project_id=${encodeURIComponent(state.projectId)}` : "";
      data = await api(
        `/api/suites/${encodeURIComponent(state.suiteName)}/brahl/reports/${encodeURIComponent(runName)}/content${q}`
      );
    }
    $("#brahl-report-body").innerHTML = renderMarkdown(data.markdown);
    renderBrahlHuntArtifacts(data.artifacts);
    const archiveBtn = $("#brahl-report-archive-toggle");
    if (meta?.is_hunt) {
      $("#brahl-report-summary").hidden = true;
      $("#brahl-zdash-link").hidden = true;
      renderZdashEmbed(null);
      renderGoNoGo(null);
      renderVersionCompare(null);
      currentBrahlReportRef = { id: meta.report_id || null, archived: Boolean(meta.archived) };
      renderReportStatusBadge(runName, meta, null);
      await renderReportEvidence(meta.report_id);
      const open = $("#brahl-report-open");
      if (open && data.artifacts?.length) {
        const md = data.artifacts.find((a) => String(a).includes("hunt-report") && String(a).endsWith(".md"));
        if (md) {
          open.href = `/api/projects/${encodeURIComponent(state.projectId)}/uploads/${encodeURIComponent(PathBasename(md))}`;
          open.hidden = false;
        } else open.hidden = true;
      }
    } else {
      const archived = Boolean(data.archived);
      const effMeta = { ...meta, report_id: data.report_id || meta?.report_id, archived };
      renderBrahlSummaryStats(data.stats, runName);
      renderVersionCompare(data.version_compare);
      currentBrahlReportRef = { id: data.report_id || null, archived };
      renderReportStatusBadge(runName, effMeta, data.stats);
      await renderReportEvidence(data.report_id || null);
      const open = $("#brahl-report-open");
      open.href = `/api/files/z/${encodeURIComponent(runName)}/brahl_report.md`;
      open.hidden = false;
    }
    if (archiveBtn) {
      archiveBtn.hidden = !currentBrahlReportRef.id;
      archiveBtn.textContent = currentBrahlReportRef.archived ? "Unarchive" : "Archive";
    }
  } catch {
    $("#brahl-report-body").innerHTML =
      '<p class="empty-hint">No zResults for this run yet. Run Verify on the Loop tab, or pick a run with results.</p>';
    $("#brahl-report-summary").hidden = true;
    $("#brahl-hunt-artifacts").hidden = true;
    $("#brahl-zdash-link").hidden = true;
    $("#brahl-report-open").hidden = true;
    $("#brahl-report-archive-toggle").hidden = true;
    renderZdashEmbed(null);
    renderReportStatusBadge(runName, meta, null);
    renderReportEvidence(null);
    renderVersionCompare(null);
  }
}

async function sendBrahlChat(ev) {
  ev.preventDefault();
  if (!isAiOn()) return;
  const input = $("#brahl-chat-input");
  const text = input.value.trim();
  if (!text || !state.projectId) return;
  input.value = "";
  const data = await api(`/api/projects/${state.projectId}/brahl/chat`, {
    method: "POST",
    body: JSON.stringify({ text, run_name: selectedBrahlRun }),
  });
  activeProject = data.project;
  renderBrahlChat();
}

async function autoEnsureBrahlReport(runName, stepLabel) {
  if (!state.projectId || !runName) return;
  try {
    await api(`/api/projects/${state.projectId}/brahl/reports`, {
      method: "POST",
      body: JSON.stringify({ run_name: runName, source: isAiOn() ? "automation" : "automation_ai" }),
    });
    if ($("#panel-brahl")?.classList.contains("active")) await loadBrahlPanel();
  } catch {
    /* non-fatal */
  }
}

async function linkRunReport() {
  await openLinkReportModal();
}

async function submitLinkReportForm(ev) {
  ev.preventDefault();
  const runName = $("#link-report-run").value?.trim();
  if (!runName) return;
  if (runPickerMode === "hitl") {
    $("#link-report-modal").hidden = true;
    if (runPickerResolve) {
      runPickerResolve(runName);
      runPickerResolve = null;
    }
    return;
  }
  if (!state.projectId) return;
  const source = $("#link-report-source").value || "automation";
  await api(`/api/projects/${state.projectId}/brahl/reports`, {
    method: "POST",
    body: JSON.stringify({ run_name: runName, source }),
  });
  closeLinkReportModal();
  await refreshActiveProject();
  await loadBrahlPanel();
}

function projectOptionsHtml(includePlaceholder = false) {
  const ph = state.avatar
    ? avatarLabel(state.avatar).projectPlaceholder
    : "Select a challenge…";
  const placeholder = includePlaceholder
    ? `<option value="">${escapeHtml(ph)}</option>`
    : "";
  return (
    placeholder +
    uniqueProjects().map((p) => `<option value="${p.id}">${escapeHtml(p.name)}</option>`).join("")
  );
}

function renderProjectSelectors() {
  const topbarWrap = $("#topbar-project");
  const roleWrap = $("#topbar-role");
  if (!state.avatar) {
    if (topbarWrap) topbarWrap.hidden = true;
    if (roleWrap) roleWrap.hidden = true;
    return;
  }
  renderTopbarProjectSelect();
  syncTopbarRoleSelect();
}

function renderBuildChecklist() {
  const el = $("#build-checklist");
  if (!el) return;
  const hasProject = hasScope() && !!activeProject;
  el.hidden = !hasProject;
  if (!hasProject) return;

  const userMsgs = (activeProject.chat_messages || []).filter((m) => m.role === "user");
  const hasPurpose =
    !!(activeProject.purpose || activeProject.prompt || "").trim() || userMsgs.length > 0;
  const hasVerify =
    !!(activeProject.reports || []).length || !!(activeProject.latest_run || "").trim();

  const setStep = (step, done, index) => {
    const item = el.querySelector(`[data-step="${step}"]`);
    if (!item) return;
    item.classList.toggle("done", done);
    item.classList.toggle("current", !done && index === nextStep);
    const marker = item.querySelector(".checklist-marker");
    if (marker) marker.textContent = done ? "✓" : String(index);
  };
  let nextStep = 1;
  if (hasPurpose) nextStep = 3;
  else if (true) nextStep = 2;
  setStep("project", true, 1);
  setStep("purpose", hasPurpose, 2);
  setStep("verify", hasVerify, 3);
}

let plannerDraft = null;
let plannerHistory = [];
let plannerBrahlPlan = null;
let plannerRecognition = null;

function openAddProjectModal() {
  const modal = $("#add-project-modal");
  if (!modal) return;
  plannerDraft = null;
  plannerHistory = [];
  plannerBrahlPlan = null;
  const log = $("#planner-chat-log");
  if (log) log.innerHTML = "";
  const draftReq =
    sessionStorage.getItem(STORAGE_DRAFT_REQUIREMENT) ||
    $("#brahl-plan-requirement")?.value.trim() ||
    "";
  const input = $("#planner-input");
  if (input) input.value = draftReq;
  updatePlannerDraftUI(null);
  const preview = $("#planner-plan-preview");
  if (preview) {
    preview.hidden = true;
    preview.innerHTML = "";
  }
  const statusEl = $("#planner-status");
  if (statusEl) statusEl.hidden = true;
  modal.hidden = false;
  modal.style.display = "flex";
  appendPlannerMessage(
    "assistant",
    "Hi — I’m the BRAHL planner. Paste your **app URL** and what you want covered (or tap 🎤 to speak). I’ll draft a lean strategy and yPAD white pads, then we can run a quick BRAHL for Go/No-Go."
  );
  input?.focus();
}

function closeAddProjectModal() {
  const modal = $("#add-project-modal");
  if (modal) {
    modal.hidden = true;
    modal.style.display = "";
  }
  stopPlannerMic();
}

function appendPlannerMessage(role, text) {
  const log = $("#planner-chat-log");
  if (!log) return;
  const div = document.createElement("div");
  div.className = `planner-msg planner-msg-${role}`;
  div.innerHTML = renderMarkdown(String(text || "").replace(/\n/g, "  \n"));
  log.appendChild(div);
  log.scrollTop = log.scrollHeight;
}

function updatePlannerDraftUI(draft) {
  plannerDraft = draft;
  const ready = !!draft?.ready;
  const nameEl = $("#planner-draft-name");
  const urlEl = $("#planner-draft-url");
  const purposeEl = $("#planner-draft-purpose");
  if (nameEl) nameEl.textContent = draft?.name || "—";
  if (urlEl) urlEl.textContent = draft?.app_url || "—";
  const purpose = (draft?.purpose || "").trim();
  if (purposeEl) {
    purposeEl.textContent = purpose
      ? purpose.slice(0, 220) + (purpose.length > 220 ? "…" : "")
      : "—";
  }
  const createBtn = $("#planner-create");
  const brahlBtn = $("#planner-create-brahl");
  if (createBtn) createBtn.disabled = !ready;
  if (brahlBtn) brahlBtn.disabled = !ready;
  const hint = $("#planner-ready-hint");
  if (hint) {
    hint.textContent = ready
      ? "Draft ready — create yPAD, or Create & quick BRAHL for a scorecard."
      : `Share ${(draft?.missing || ["name", "app_url", "purpose"]).join(", ")} to unlock create.`;
  }
}

function showPlannerPlanPreview(preview) {
  const el = $("#planner-plan-preview");
  if (!el) return;
  if (!preview) {
    el.hidden = true;
    el.innerHTML = "";
    plannerBrahlPlan = null;
    return;
  }
  plannerBrahlPlan = preview.brahl_plan || null;
  el.hidden = false;
  el.innerHTML =
    `<strong>Strategy preview</strong> · ${preview.automated_count ?? 0} automated · ${preview.manual_count ?? 0} manual` +
    (preview.summary ? `<p>${escapeHtml(preview.summary)}</p>` : "");
}

async function sendPlannerChat(ev) {
  ev?.preventDefault?.();
  const input = $("#planner-input");
  const message = input?.value.trim();
  if (!message) return;
  input.value = "";
  appendPlannerMessage("user", message);
  plannerHistory.push({ role: "user", text: message });
  try {
    const data = await api("/api/planner/chat", {
      method: "POST",
      body: JSON.stringify({ message, draft: plannerDraft, history: plannerHistory.slice(-8) }),
    });
    appendPlannerMessage("assistant", data.reply);
    plannerHistory.push({ role: "assistant", text: data.reply });
    updatePlannerDraftUI(data.draft);
    showPlannerPlanPreview(data.plan_preview);
  } catch (e) {
    appendPlannerMessage("assistant", `Could not reach planner: ${e.message}`);
    setStatus(`Planner error: ${e.message}`);
  }
}

function stopPlannerMic() {
  try {
    plannerRecognition?.stop?.();
  } catch {
    /* ignore */
  }
  plannerRecognition = null;
  $("#planner-mic")?.classList.remove("listening");
}

function togglePlannerMic() {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) {
    setStatus("Voice not supported in this browser — type instead");
    return;
  }
  if (plannerRecognition) {
    stopPlannerMic();
    return;
  }
  const rec = new SR();
  plannerRecognition = rec;
  rec.lang = "en-US";
  rec.interimResults = false;
  rec.continuous = false;
  $("#planner-mic")?.classList.add("listening");
  rec.onresult = (event) => {
    const text = Array.from(event.results)
      .map((r) => r[0]?.transcript || "")
      .join(" ")
      .trim();
    if (text) {
      const input = $("#planner-input");
      input.value = input.value ? `${input.value.trim()} ${text}` : text;
    }
  };
  rec.onerror = () => stopPlannerMic();
  rec.onend = () => {
    $("#planner-mic")?.classList.remove("listening");
    plannerRecognition = null;
  };
  rec.start();
}

async function pollQuickBrahlJob(jobId, projectId) {
  const statusEl = $("#planner-status");
  if (statusEl) {
    statusEl.hidden = false;
    statusEl.textContent = "Quick BRAHL running…";
  }
  for (let i = 0; i < 90; i++) {
    await new Promise((r) => setTimeout(r, 1000));
    const j = await api(`/api/jobs/${jobId}`);
    if (j.status === "completed" || j.status === "failed") {
      if (j.output_dir && projectId) {
        const runName = j.output_dir.replace(/\\/g, "/").split("/").pop();
        await api(`/api/projects/${projectId}`, {
          method: "PATCH",
          body: JSON.stringify({ latest_run: runName }),
        });
        try {
          await api(`/api/projects/${projectId}/brahl/reports`, {
            method: "POST",
            body: JSON.stringify({ run_name: runName, source: "automation" }),
          });
        } catch {
          /* report may auto-ensure on load */
        }
        selectedBrahlRun = runName;
      }
      return j;
    }
  }
  throw new Error("Quick BRAHL timed out");
}

async function finishPlannerCreate(quickBrahl) {
  if (!plannerDraft?.ready) {
    setStatus("Draft not ready — keep chatting");
    return;
  }
  const statusEl = $("#planner-status");
  if (statusEl) {
    statusEl.hidden = false;
    statusEl.textContent = quickBrahl ? "Creating suite + starting BRAHL…" : "Creating yPAD suite…";
  }
  $("#planner-create").disabled = true;
  $("#planner-create-brahl").disabled = true;
  try {
    const data = await api("/api/planner/create", {
      method: "POST",
      body: JSON.stringify({
        draft: plannerDraft,
        brahl_plan: plannerBrahlPlan,
        quick_brahl: !!quickBrahl,
      }),
    });
    await loadSuites();
    await selectYpadProject(data.suite.name);
    if (quickBrahl && data.quick_brahl_job?.job_id) {
      const job = await pollQuickBrahlJob(data.quick_brahl_job.job_id, data.project.id);
      closeAddProjectModal();
      showPhase("brahl");
      await loadBrahlPanel();
      setStatus(
        job.status === "completed"
          ? `Quick BRAHL done for ${data.suite.name} — see scorecard`
          : `Quick BRAHL finished with status ${job.status}`
      );
    } else {
      closeAddProjectModal();
      showPhase("build");
      setStatus(`Created ${data.suite.name} — lean yPAD ready on Build`);
      if (data.quick_brahl_error) setStatus(`Created, but quick BRAHL failed: ${data.quick_brahl_error}`);
    }
  } catch (e) {
    appendPlannerMessage("assistant", `Create failed: ${e.message}`);
    setStatus(`Create failed: ${e.message}`);
    updatePlannerDraftUI(plannerDraft);
  }
}

async function submitAddProjectForm(ev) {
  // Legacy form removed — planner chat handles create
  ev?.preventDefault?.();
  await sendPlannerChat(ev);
}

function openRoleSwitchModal(nextAvatar) {
  pendingAvatar = nextAvatar;
  const modal = $("#role-switch-modal");
  if (modal) modal.hidden = false;
}

function closeRoleSwitchModal() {
  pendingAvatar = null;
  const modal = $("#role-switch-modal");
  if (modal) modal.hidden = true;
}

let pendingAvatar = null;

function renderBuildWorkspace() {
  const has = hasScope() && !!activeProject;
  $("#client-no-project").hidden = has;
  $("#client-workspace").hidden = !has;
  if (!has) {
    renderBuildChecklist();
    return;
  }
  const title = $("#build-panel-title");
  const label = state.suiteName || activeProject.name;
  if (title) {
    if (state.avatar === "consultant") {
      title.textContent = `Build — ${label} (QA Hunter)`;
    } else {
      title.textContent = isAiOn() ? `Build — ${label}` : `Build — ${label} (manual)`;
    }
  }
  const hunterTag = $("#hunter-hero-tagline");
  if (hunterTag) hunterTag.hidden = state.avatar !== "consultant";
  const hitlLabel = $("#hitl-project-label");
  if (hitlLabel) hitlLabel.textContent = state.suiteName || activeProject.name || "this project";
  renderBuildChecklist();
  if (state.avatar === "client") {
    renderChat($("#chat-thread"), activeProject.chat_messages || []);
    renderContextList(activeProject.context_items || []);
    $("#budget-usd").value = activeProject.budget_usd || "";
    const auto = activeProject.budget_split?.automation_pct ?? 50;
    $("#budget-split").value = auto;
    $("#auto-pct").textContent = auto;
    $("#human-pct").textContent = 100 - auto;
    renderHitlRoster(activeProject);
    $("#add-context-panel").hidden = true;
  }
  loadBuildAiStatus();
  applyAiMode();
  loadBuildAiStatus();
  loadBuildBoard();
  if (state.avatar === "consultant") renderConsultantWorkspace();
}

function ypadDesignColumns(headers) {
  return (headers || []).filter((h) => /^D\d+$/.test(h)).sort((a, b) => parseInt(a.slice(1), 10) - parseInt(b.slice(1), 10));
}

function ypadDesignColumnLabels(data) {
  const cols = ypadDesignColumns(data?.headers);
  const labels = {};
  const personaRow = (data?.rows || []).find((r) => (r.DataName || "").trim() === "persona_name");
  cols.forEach((col) => {
    const name = (personaRow?.[col] || "").trim();
    labels[col] = name ? `${name} (${col})` : col;
  });
  return labels;
}

function ypadDesignGroupMatch(dataName, group) {
  const n = (dataName || "").toLowerCase();
  if (!group) return true;
  if (group === "locator") return n.includes("_locator") || n.endsWith("locator");
  if (group === "url") return n.includes("_url") || n.endsWith("url") || n.includes("endpoint");
  if (group === "expected") return n.includes("_expected") || n.endsWith("expected");
  if (group === "credential") return n.includes("password") || n.includes("email") || n.includes("credential") || n.includes("login_");
  return true;
}

function ypadPrimaryColumns(tab) {
  if (tab === "plans") return ["PlanId", "PlanName", "Run", "Tags"];
  if (tab === "actions") return ["PlanId", "StepId", "ActionName", "Input"];
  if (tab === "designs") return ["Type", "DataName"];
  return [];
}

function ypadDisplayColumnsForTab(tab, data) {
  const headers = data?.headers || [];
  const base = ypadPrimaryColumns(tab).filter((c) => headers.includes(c));
  if (tab !== "designs") {
    const primary = base.length ? base : headers.slice(0, 6);
    return { cols: primary, labels: {} };
  }
  let dCols = ypadDesignColumns(headers);
  if (ypadState.designColumnMode === "active") {
    /* persona design columns retired — show all */
  }
  const labels = ypadDesignColumnLabels(data);
  const cols = [...base, ...dCols];
  return { cols: cols.length ? cols : headers.slice(0, 6), labels };
}

function ypadRowMatchesFilter(row, filter) {
  if (!filter) return true;
  const q = String(filter).trim().toLowerCase();
  if (!q) return true;
  // Exact tag match first (semicolon-separated Tags), then substring fallback on other fields
  const tags = String(row.Tags || "")
    .split(";")
    .map((t) => t.trim().toLowerCase())
    .filter(Boolean);
  if (tags.includes(q)) return true;
  return Object.entries(row).some(([k, v]) => {
    if (k === "Tags" || String(k).startsWith("_")) return false;
    return String(v || "").toLowerCase().includes(q);
  });
}

function rowsToCsv(headers, rows) {
  const esc = (v) => {
    const s = String(v ?? "");
    if (/[",\n\r]/.test(s)) return `"${s.replace(/"/g, '""')}"`;
    return s;
  };
  const lines = [headers.map(esc).join(",")];
  for (const row of rows) {
    lines.push(headers.map((h) => esc(row[h] ?? "")).join(","));
  }
  return lines.join("\n");
}

function csvToRows(text) {
  const lines = text.replace(/\r\n/g, "\n").replace(/\r/g, "\n").split("\n").filter((l) => l.length);
  if (!lines.length) return { headers: [], rows: [] };
  const parseLine = (line) => {
    const out = [];
    let cur = "";
    let inQ = false;
    for (let i = 0; i < line.length; i++) {
      const c = line[i];
      if (inQ) {
        if (c === '"' && line[i + 1] === '"') {
          cur += '"';
          i++;
        } else if (c === '"') inQ = false;
        else cur += c;
      } else if (c === '"') inQ = true;
      else if (c === ",") {
        out.push(cur);
        cur = "";
      } else cur += c;
    }
    out.push(cur);
    return out;
  };
  const headers = parseLine(lines[0]);
  const rows = lines.slice(1).map((line) => {
    const vals = parseLine(line);
    const row = {};
    headers.forEach((h, i) => {
      row[h] = vals[i] ?? "";
    });
    return row;
  });
  return { headers, rows };
}

async function loadYpadSheet(tab = ypadState.tab) {
  if (!state.suiteName) return;
  ypadState.tab = tab;
  ypadState.editMode = false;
  ypadState.selectedIndex = -1;
  closeYpadDrawer(false);
  try {
    const qs = new URLSearchParams();
    if (ypadState.source) qs.set("source", ypadState.source);
    else if (ypadState.sourceKind) qs.set("source_kind", ypadState.sourceKind);
    const q = qs.toString() ? `?${qs}` : "";
    ypadState.data = await api(`/api/suites/${encodeURIComponent(state.suiteName)}/ypad/${tab}${q}`);
  } catch {
    ypadState.data = { headers: [], rows: [], row_count: 0, env_example: "" };
  }
  renderYpadExplorer();
  if (tab === "plans") {
    ypadState.insights = computeYpadInsights(ypadState.data);
    renderYpadInsights();
  }
  loadYpadVersions();
}

function computeYpadInsights(plansData) {
  const rows = plansData?.rows || [];
  let automated = 0;
  let skipped = 0;
  const tagCounts = {};
  for (const r of rows) {
    const pid = (r.PlanId || "").trim();
    if (!pid || pid.startsWith("PReuse_")) continue;
    const run = (r.Run || "").trim().toUpperCase();
    if (run === "Y") automated += 1;
    else if (run === "N") skipped += 1;
    if (run !== "Y") continue;
    for (const part of (r.Tags || "").split(";")) {
      const tag = part.trim();
      if (tag) tagCounts[tag] = (tagCounts[tag] || 0) + 1;
    }
  }
  const tags = Object.entries(tagCounts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 12);
  return {
    totalPlans: rows.filter((r) => (r.PlanId || "").trim() && !(r.PlanId || "").startsWith("PReuse_")).length,
    automated,
    skipped,
    tags,
    tagCount: Object.keys(tagCounts).length,
  };
}

async function loadYpadInsights() {
  // Guard against a slower request for a since-abandoned suite winning the race
  // and overwriting the floating yPAD widget with stale Math/Nalanda numbers.
  const requestedSuite = state.suiteName;
  if (!requestedSuite) return;
  try {
    const [plans, actions, designs] = await Promise.all([
      api(`/api/suites/${encodeURIComponent(requestedSuite)}/ypad/plans`),
      api(`/api/suites/${encodeURIComponent(requestedSuite)}/ypad/actions`),
      api(`/api/suites/${encodeURIComponent(requestedSuite)}/ypad/designs`),
    ]);
    if (state.suiteName !== requestedSuite) return; // superseded — a newer switch already won
    ypadState.insights = {
      ...computeYpadInsights(plans),
      actionSteps: actions.row_count ?? actions.rows?.length ?? 0,
      designRows: designs.row_count ?? designs.rows?.length ?? 0,
    };
  } catch {
    if (state.suiteName !== requestedSuite) return;
    ypadState.insights = null;
  }
  if (state.suiteName !== requestedSuite) return;
  renderYpadInsights();
  refreshArenaYpadWidget();
  refreshProjectBannerMeta();
}

function renderYpadInsights() {
  const el = $("#ypad-insights-stats");
  const cloud = $("#ypad-tag-cloud");
  if (!el) return;
  const ins = ypadState.insights;
  const suite = state.suites.find((s) => s.name === state.suiteName);
  if (!ins && !suite) {
    el.innerHTML = `<span class="meta">Select a project to see automation summary.</span>`;
    if (cloud) cloud.hidden = true;
    return;
  }
  const auto = ins?.automated ?? suite?.plan_run_y ?? "—";
  const total = ins?.totalPlans ?? suite?.plan_total ?? "—";
  const actions = ins?.actionSteps ?? "—";
  const designs = ins?.designRows ?? "—";
  const tagN = ins?.tagCount ?? 0;
  el.innerHTML =
    `<span class="ypad-stat-pill"><strong>${auto}</strong> automated tests</span>` +
    `<span class="ypad-stat-pill"><strong>${total}</strong> total tests</span>` +
    `<span class="ypad-stat-pill"><strong>${actions}</strong> steps</span>` +
    `<span class="ypad-stat-pill"><strong>${designs}</strong> test data rows</span>` +
    `<span class="ypad-stat-pill"><strong>${tagN}</strong> tags</span>`;
  if (cloud) {
    if (ins?.tags?.length) {
      cloud.hidden = false;
      cloud.innerHTML = ins.tags
        .map(
          ([tag, n]) =>
            `<button type="button" class="ypad-tag-chip" data-tag="${escapeHtml(tag)}" title="${n} plan(s)">${escapeHtml(tag)} (${n})</button>`
        )
        .join("");
      cloud.querySelectorAll(".ypad-tag-chip").forEach((btn) => {
        btn.addEventListener("click", () => {
          const tag = btn.dataset.tag;
          const filter = $("#ypad-filter");
          if (filter) filter.value = tag;
          ypadState.filter = tag;
          if (ypadState.tab !== "plans") loadYpadSheet("plans");
          else renderYpadExplorer();
        });
      });
    } else {
      cloud.hidden = true;
      cloud.innerHTML = "";
    }
  }
}

const COST_TYPE_LABELS = { ai: "AI", local: "Local · free", cloud: "Cloud", human: "Human" };

function getAuthUser() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_AUTH_USER) || "null");
  } catch {
    return null;
  }
}

function initUserMenu() {
  const btn = $("#user-menu-btn");
  const menu = $("#user-menu-dropdown");
  if (!btn || !menu) return;
  btn.addEventListener("click", (e) => {
    e.stopPropagation();
    const open = menu.hidden;
    menu.hidden = !open;
    btn.setAttribute("aria-expanded", open ? "true" : "false");
  });
  document.addEventListener("click", () => {
    menu.hidden = true;
    btn.setAttribute("aria-expanded", "false");
  });
  menu.querySelectorAll("[data-user-action]").forEach((el) => {
    el.addEventListener("click", async (e) => {
      e.stopPropagation();
      menu.hidden = true;
      const action = el.dataset.userAction;
      if (action === "upcoming") {
        setStatus("Coming soon — Nalanda & Atomic 77 are on the roadmap");
        return;
      }
      if (action === "account-roles") {
        const copy = window.ROLE_COPY || {};
        const lines = ["creator", "hunter", "promoter", "nalanda", "account"]
          .map((k) => copy[k])
          .filter(Boolean)
          .map((r) => `• ${r.title}: ${r.pitch}`)
          .join("\n\n");
        alert(lines || "Role guide unavailable.");
        return;
      }
      if (action === "promoter") showPhase("promoter");
      else if (action === "cost") showPhase("cost");
      else if (action === "theme-pro") window.QoaTheme?.setTheme?.("pro");
      else if (action === "signout") {
        localStorage.removeItem(STORAGE_AUTH_TOKEN);
        localStorage.removeItem(STORAGE_AUTH_USER);
        location.href = "/login";
      }
    });
  });
}

const PROMOTER_SHARES_KEY = "qoa_promoter_shares";
let promoterChannel = "linkedin";
let promoterInvite = { code: "", url: "" };

function promoterShareCount() {
  return Number(sessionStorage.getItem(PROMOTER_SHARES_KEY) || "0") || 0;
}

function bumpPromoterShare() {
  const n = promoterShareCount() + 1;
  sessionStorage.setItem(PROMOTER_SHARES_KEY, String(n));
  return n;
}

function promoterReferralUrl(code) {
  const c = code || promoterInvite.code || "";
  return `${location.origin}/welcome?code=${encodeURIComponent(c)}`;
}

function promoterTemplates(code, url, name) {
  const who = name || "a QA teammate";
  const c = code || "YOUR-CODE";
  const link = url || promoterReferralUrl(c);
  return {
    linkedin:
      `Creators and QA Hunters: stop guessing launch readiness.\n\n` +
      `QA on Air is an invite-only arena where you BRAHL apps with FoXYiZ — Build → Run → Analyze → Heal → Loop — then get a clear Go/No-Go.\n\n` +
      `I'm sharing my referral for a 7-day trial:\n` +
      `Code: ${c}\n${link}\n\n` +
      `#QualityEngineering #QA #ProductLaunch #QAonAir #BRAHL`,
    instagram:
      `Arena mode ON. \n` +
      `Creators post. QA Hunters break. BRAHL decides Go/No-Go.\n\n` +
      `7-day trial with my code:\n${c}\n${link}\n\n` +
      `#QAonAir #BRAHL #QAHunters #BuildInPublic`,
    whatsapp:
      `Hey — try QA on Air with me.\n` +
      `7-day invite trial → build a small challenge and BRAHL it.\n\n` +
      `Code: ${c}\n${link}`,
    blog:
      `Title: Why I'm promoting QA on Air (and how to join with my referral)\n\n` +
      `${who} here. Launch decisions shouldn't wait for heroics — they need evidence.\n\n` +
      `QA on Air pairs Creators with QA Hunters inside a BRAHL loop (Build, Run, Analyze, Heal, Loop) powered by FoXYiZ. ` +
      `The output is a standardized Go/No-Go on whether an app is production-ready.\n\n` +
      `If you want a 7-day trial, use my referral code **${c}** or open:\n${link}\n\n` +
      `Once inside: try Promoter to share your own code, Atomic 77 for idea-to-launch help, and Wallet for XP.\n`,
  };
}

function defaultPromoterDraft(code) {
  return promoterTemplates(code, promoterReferralUrl(code)).linkedin;
}

function applyPromoterTemplate(channel) {
  const templates = promoterTemplates(
    promoterInvite.code,
    promoterInvite.url,
    getAuthUser()?.name || state.profile?.name
  );
  const draft = $("#promoter-share-text");
  if (draft) draft.value = templates[channel] || templates.linkedin;
  const label = $("#promoter-channel-label");
  const titles = {
    linkedin: "LinkedIn post",
    instagram: "Instagram caption",
    whatsapp: "WhatsApp message",
    blog: "Blog draft",
  };
  if (label) label.textContent = titles[channel] || "Post";
}

function refreshPromoterStats() {
  const n = promoterShareCount();
  if ($("#promoter-shares")) $("#promoter-shares").textContent = String(n);
  if ($("#promoter-xp")) $("#promoter-xp").textContent = String(40 + n * 15);
  if ($("#promoter-credits")) $("#promoter-credits").textContent = `$${(n * 2.5).toFixed(1)}`;
}

function setPromoterStatus(msg) {
  const status = $("#promoter-status");
  if (!status) return;
  status.hidden = !msg;
  status.textContent = msg || "";
}

async function copyText(text) {
  await navigator.clipboard.writeText(text);
}

async function publishPromoterPost() {
  const text = $("#promoter-share-text")?.value?.trim() || "";
  if (!text) {
    setPromoterStatus("Add some post text first.");
    return;
  }
  const url = promoterInvite.url || promoterReferralUrl(promoterInvite.code);
  let opened = false;
  try {
    if (promoterChannel === "whatsapp") {
      window.open(`https://wa.me/?text=${encodeURIComponent(text)}`, "_blank", "noopener");
      opened = true;
    } else if (promoterChannel === "linkedin") {
      window.open(
        `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(url)}`,
        "_blank",
        "noopener"
      );
      await copyText(text);
      opened = true;
      setPromoterStatus("LinkedIn opened — post text copied; paste into your update.");
    } else if (promoterChannel === "instagram") {
      await copyText(text);
      window.open("https://www.instagram.com/", "_blank", "noopener");
      opened = true;
      setPromoterStatus("Instagram opened — caption copied; paste into your post.");
    } else if (promoterChannel === "blog") {
      await copyText(text);
      setPromoterStatus("Blog draft copied — paste into your CMS / Notion / Medium.");
    }
  } catch (e) {
    setPromoterStatus(e.message || "Publish failed — try Copy post.");
    return;
  }
  bumpPromoterShare();
  refreshPromoterStats();
  if (opened && promoterChannel === "whatsapp") {
    setPromoterStatus("WhatsApp opened with your invite message.");
  }
  setStatus("Promoter publish counted");
}

async function loadPromoterPanel() {
  const profile = state.profile || (typeof getActiveProfile === "function" ? getActiveProfile() : null);
  const auth = getAuthUser();
  const profileId = profile?.id || (auth?.id ? `u${String(auth.id).slice(0, 6)}` : "p1");
  const authorName = profile?.name || auth?.name || [auth?.first_name, auth?.last_name].filter(Boolean).join(" ") || "Promoter";
  refreshPromoterStats();
  setPromoterStatus("");
  try {
    const data = await api(
      `/api/nalanda/invite?profile_id=${encodeURIComponent(profileId)}&author_name=${encodeURIComponent(authorName)}`
    );
    const code = data.code || "QOA-CR5-001-001-DEMO";
    const path = data.invite_path || `/welcome?code=${encodeURIComponent(code)}`;
    const abs = path.startsWith("http") ? path : `${location.origin}${path.startsWith("/") ? path : `/${path}`}`;
    promoterInvite = { code, url: abs };
    if ($("#promoter-invite-code")) $("#promoter-invite-code").textContent = code;
    if ($("#promoter-invite-link")) {
      $("#promoter-invite-link").href = path.startsWith("http") ? path : path;
      $("#promoter-invite-link").textContent = abs;
    }
  } catch {
    const code = "QOA-CR5-001-001-DEMO";
    const abs = promoterReferralUrl(code);
    promoterInvite = { code, url: abs };
    if ($("#promoter-invite-code")) $("#promoter-invite-code").textContent = code;
    if ($("#promoter-invite-link")) {
      $("#promoter-invite-link").href = `/welcome?code=${encodeURIComponent(code)}`;
      $("#promoter-invite-link").textContent = abs;
    }
  }
  applyPromoterTemplate(promoterChannel);
  $$(".promoter-channel").forEach((btn) => {
    const on = btn.dataset.channel === promoterChannel;
    btn.classList.toggle("active", on);
    btn.setAttribute("aria-selected", on ? "true" : "false");
  });
}

function initPromoterPanel() {
  $$(".promoter-channel").forEach((btn) => {
    btn.addEventListener("click", () => {
      promoterChannel = btn.dataset.channel || "linkedin";
      $$(".promoter-channel").forEach((b) => {
        const on = b === btn;
        b.classList.toggle("active", on);
        b.setAttribute("aria-selected", on ? "true" : "false");
      });
      applyPromoterTemplate(promoterChannel);
      setPromoterStatus("");
    });
  });
  $("#btn-promoter-copy")?.addEventListener("click", async () => {
    try {
      await copyText($("#promoter-share-text")?.value || "");
      bumpPromoterShare();
      refreshPromoterStats();
      setPromoterStatus("Post copied.");
    } catch {
      setPromoterStatus("Could not copy — select the text manually.");
    }
  });
  $("#btn-promoter-copy-code")?.addEventListener("click", async () => {
    try {
      await copyText(promoterInvite.code || $("#promoter-invite-code")?.textContent || "");
      setPromoterStatus("Referral code copied.");
    } catch {
      setPromoterStatus("Could not copy code.");
    }
  });
  $("#btn-promoter-copy-link")?.addEventListener("click", async () => {
    try {
      await copyText(promoterInvite.url || promoterReferralUrl(promoterInvite.code));
      setPromoterStatus("Referral link copied.");
    } catch {
      setPromoterStatus("Could not copy link.");
    }
  });
  $("#btn-promoter-publish")?.addEventListener("click", () => publishPromoterPost());
  $("#btn-promoter-draft")?.addEventListener("click", () => {
    applyPromoterTemplate(promoterChannel);
    setPromoterStatus("Template reset.");
  });
  $("#btn-promoter-wallet")?.addEventListener("click", () => showPhase("cost"));
}

let costWidgetTimer = null;

function refreshArenaYpadWidget() {
  const dock = $("#arena-dock");
  const el = $("#arena-ypad-widget");
  if (!dock || !el) return;
  if (!state.suiteName) {
    dock.hidden = !state.projectId;
    el.hidden = true;
    return;
  }
  dock.hidden = false;
  el.hidden = false;
  const suite = state.suites.find((s) => s.name === state.suiteName);
  const ins = ypadState.insights;
  const auto = ins?.automated ?? suite?.plan_run_y ?? 0;
  const total = ins?.totalPlans ?? suite?.plan_total ?? 0;
  const steps = ins?.actionSteps ?? "—";
  const dataRows = ins?.designRows ?? "—";
  const manual = Math.max(0, Number(total) - Number(auto) || 0);
  const title = $("#arena-ypad-title");
  const plansEl = $("#arena-ypad-plans");
  const autoEl = $("#arena-ypad-auto");
  const stepsEl = $("#arena-ypad-steps");
  const dataEl = $("#arena-ypad-data");
  const manualChip = $("#arena-ypad-manual-chip");
  const autoChip = $("#arena-ypad-auto-chip");
  if (title) title.textContent = suite?.name || state.suiteName;
  if (plansEl) plansEl.textContent = String(total);
  if (autoEl) autoEl.textContent = String(auto);
  if (stepsEl) stepsEl.textContent = String(steps);
  if (dataEl) dataEl.textContent = String(dataRows);
  if (manualChip) {
    manualChip.classList.toggle("has-coverage", manual > 0 || Number(total) === 0);
    manualChip.title = `${manual} plan(s) not marked automated (Run=N / manual)`;
  }
  if (autoChip) {
    autoChip.classList.toggle("has-coverage", Number(auto) > 0);
    autoChip.title = `${auto} automated plan(s) (Run=Y)`;
  }
}

async function refreshArenaCostWidget() {
  const dock = $("#arena-dock");
  const el = $("#arena-cost-widget");
  if (!el) return;
  if (!state.projectId) {
    if (dock && !state.suiteName) dock.hidden = true;
    el.hidden = true;
    refreshArenaYpadWidget();
    return;
  }
  if (dock) dock.hidden = false;
  el.hidden = false;
  refreshArenaYpadWidget();
  try {
    const [{ cost_meter: m }, status] = await Promise.all([
      api(`/api/projects/${state.projectId}/cost-meter`),
      api(`/api/ai/status?project_id=${encodeURIComponent(state.projectId)}`).catch(() => null),
    ]);
    const budget = Number(m.budget_usd) || 0;
    const remaining = Number(m.remaining_usd) || 0;
    const spentAi = Number(m.spent_automation_usd) || 0;
    const spentHuman = Number(m.spent_human_usd) || 0;
    const aiUsd = Number(m.ai_usage?.usd_est) || 0;
    const autoPool = Number(m.automation_pool_usd) || 0;
    const usedPct = Math.min(100, Math.max(0, Number(m.budget_used_pct) || 0));
    const remEl = $("#arena-cost-remaining");
    const aiEl = $("#arena-cost-ai");
    const humanEl = $("#arena-cost-human");
    const fill = $("#arena-cost-fill");
    const hint = $("#arena-cost-ai-hint");
    if (remEl) remEl.textContent = budget ? `$${remaining.toFixed(0)}` : "No budget";
    if (aiEl) {
      aiEl.textContent = autoPool
        ? `$${spentAi.toFixed(0)}/$${autoPool.toFixed(0)}`
        : `$${aiUsd.toFixed(2)}`;
    }
    if (humanEl) {
      const humanPool = Number(m.human_pool_usd) || 0;
      humanEl.textContent = humanPool
        ? `$${spentHuman.toFixed(0)}/$${humanPool.toFixed(0)}`
        : `$${spentHuman.toFixed(0)}`;
    }
    if (fill) fill.style.width = `${usedPct}%`;
    if (hint) {
      const available = Boolean(status?.available);
      hint.textContent = available
        ? `AI metered · ${(m.ai_usage?.total_tokens || 0).toLocaleString()} tok`
        : "AI scripted / no key";
    }
  } catch {
    const remEl = $("#arena-cost-remaining");
    if (remEl) remEl.textContent = "—";
    const hint = $("#arena-cost-ai-hint");
    if (hint) hint.textContent = "Cost unavailable";
  }
}

function startArenaCostWidgetPoll() {
  if (costWidgetTimer) clearInterval(costWidgetTimer);
  costWidgetTimer = setInterval(() => {
    refreshArenaCostWidget();
  }, 60000);
  refreshArenaCostWidget();
}

async function renderBuildCostRail() {
  /* Cost rail removed — Wallet dock + Budget & AI cover project cost. */
  refreshArenaCostWidget();
}


async function generateBrahlPlan() {
  if (!state.projectId) {
    setStatus("Select or create a project first.");
    return;
  }
  const req = $("#brahl-plan-requirement")?.value.trim();
  if (!req) {
    setStatus("Enter a requirement to generate a BRAHL Plan.");
    return;
  }
  sessionStorage.setItem(STORAGE_DRAFT_REQUIREMENT, req);
  const btn = $("#btn-generate-brahl-plan");
  if (btn) btn.disabled = true;
  try {
    const data = await api(`/api/projects/${state.projectId}/brahl-plan/generate`, {
      method: "POST",
      body: JSON.stringify({ requirement: req }),
    });
    pendingBrahlPlan = data.brahl_plan;
    const review = $("#brahl-plan-review");
    const stats = $("#brahl-plan-stats");
    const body = $("#brahl-plan-body");
    const accept = $("#btn-accept-brahl-plan");
    if (review) review.hidden = false;
    if (stats) {
      const p = data.brahl_plan || {};
      stats.innerHTML =
        `<span class="brahl-plan-stat">${(p.user_stories || []).length} user stories</span>` +
        `<span class="brahl-plan-stat">${(p.test_cases || []).length} test cases</span>` +
        `<span class="brahl-plan-stat">${p.automated_count ?? 0} automated</span>` +
        `<span class="brahl-plan-stat">${p.manual_count ?? 0} manual</span>`;
    }
    if (body) body.textContent = data.preview_markdown || "";
    if (accept) accept.hidden = false;
    setStatus(data.ai ? "BRAHL Plan ready — review and accept" : "BRAHL Plan (offline template) — review and accept");
  } catch (e) {
    setStatus(`BRAHL Plan error: ${e.message}`);
  } finally {
    if (btn) btn.disabled = false;
  }
}

async function acceptBrahlPlan() {
  if (!state.projectId || !pendingBrahlPlan) return;
  try {
    const data = await api(`/api/projects/${state.projectId}/brahl-plan/accept`, {
      method: "POST",
      body: JSON.stringify({ brahl_plan: pendingBrahlPlan }),
    });
    activeProject = data.project;
    sessionStorage.removeItem(STORAGE_DRAFT_REQUIREMENT);
    pendingBrahlPlan = null;
    $("#btn-accept-brahl-plan").hidden = true;
    await loadBuildBoard();
    setStatus("BRAHL Plan accepted — white pads + stories updated on disk.");
  } catch (e) {
    setStatus(`Accept failed: ${e.message}`);
  }
}

function restoreDraftRequirementIfNeeded() {
  const params = new URLSearchParams(location.search);
  const draft = sessionStorage.getItem(STORAGE_DRAFT_REQUIREMENT);
  const ta = $("#brahl-plan-requirement");
  if (draft && ta) ta.value = draft;
  const openPlanner =
    params.get("planner") === "1" ||
    params.get("restore_draft") === "1" ||
    sessionStorage.getItem("qoa_open_planner") === "1";
  if (openPlanner) {
    sessionStorage.removeItem("qoa_open_planner");
    params.delete("planner");
    params.delete("restore_draft");
    const qs = params.toString();
    history.replaceState({}, "", qs ? `${location.pathname}?${qs}` : location.pathname);
    setTimeout(() => {
      if (state.avatar) openAddProjectModal();
    }, 400);
    return;
  }
  if (params.has("restore_draft") || params.has("planner")) {
    params.delete("restore_draft");
    params.delete("planner");
    const qs = params.toString();
    history.replaceState({}, "", qs ? `${location.pathname}?${qs}` : location.pathname);
  }
}

async function renderBuildCostTeaser() {
  await renderBuildCostRail();
  const wrap = $("#build-cost-teaser");
  if (wrap) wrap.hidden = true;
}

function renderCostMeter(m) {
  $("#cost-project-name").textContent = activeProject?.name || state.suiteName || "project";
  $("#cost-philosophy").textContent = m.philosophy || "";
  const split = m.deposit_split;
  const minNote = m.budget_min_usd ? ` (min $${m.budget_min_usd})` : "";
  const cards = $("#cost-summary-cards");
  if (cards) {
    let html =
      `<div class="cost-card"><span class="cost-card-label">QA wallet${minNote}</span><span class="cost-card-value">$${m.budget_usd}</span></div>`;
    if (split) {
      html +=
        `<div class="cost-card"><span class="cost-card-label">QAonAIR (${split.platform_fee_pct}%)</span><span class="cost-card-value">$${split.platform_fee_usd}</span></div>` +
        `<div class="cost-card"><span class="cost-card-label">AI cost</span><span class="cost-card-value">$${split.ai_cost_usd}</span></div>` +
        `<div class="cost-card"><span class="cost-card-label">Human payouts</span><span class="cost-card-value">$${split.human_payout_usd}</span></div>` +
        `<div class="cost-card"><span class="cost-card-label">Admin / ops</span><span class="cost-card-value">$${split.admin_ops_usd}</span></div>`;
    } else {
      html +=
        `<div class="cost-card"><span class="cost-card-label">Automation pool (${m.automation_pct}%)</span><span class="cost-card-value">$${m.automation_pool_usd}</span></div>` +
        `<div class="cost-card"><span class="cost-card-label">Human pool (${m.human_pct}%)</span><span class="cost-card-value">$${m.human_pool_usd}</span></div>`;
    }
    html +=
      `<div class="cost-card"><span class="cost-card-label">Est. spent</span><span class="cost-card-value cost-spent">$${m.spent_total_usd}</span></div>` +
      `<div class="cost-card"><span class="cost-card-label">Remaining</span><span class="cost-card-value">$${m.remaining_usd}</span></div>`;
    cards.innerHTML = html;
  }
  const pct = m.budget_used_pct || 0;
  const usedLabel = $("#cost-used-label");
  if (usedLabel) usedLabel.textContent = `${pct}% · $${m.spent_total_usd} of $${m.budget_usd}`;
  const fill = $("#cost-meter-fill");
  if (fill) fill.style.width = `${Math.min(100, pct)}%`;
  const tbody = $("#cost-phase-tbody");
  if (tbody) {
    tbody.innerHTML = (m.phases || [])
      .map(
        (p) =>
          `<tr>` +
          `<td><strong>${escapeHtml(p.label)}</strong></td>` +
          `<td><span class="cost-type cost-type-${p.cost_type}">${escapeHtml(COST_TYPE_LABELS[p.cost_type] || p.cost_type)}</span></td>` +
          `<td>$${p.allocated_usd}</td>` +
          `<td>$${p.spent_usd}</td>` +
          `<td class="meta">${escapeHtml(p.note)}</td>` +
          `</tr>`
      )
      .join("");
  }
  const localRadio = $("#cost-runtime-local");
  const cloudRadio = $("#cost-runtime-cloud");
  if (localRadio) localRadio.checked = m.runtime_mode === "local";
  if (cloudRadio) cloudRadio.checked = m.runtime_mode === "cloud";
}

function renderConsultantWallet(w) {
  const phil = $("#cost-hitl-philosophy");
  if (phil) phil.textContent = w.philosophy || "";
  const pricing = w.pricing || {};
  const threshold = pricing.payout_threshold_usd || 100;
  const balance = Number(w.total_earned_usd) || 0;
  const cards = $("#cost-wallet-summary");
  if (cards) {
    cards.innerHTML =
      `<div class="cost-card cost-card-wallet"><span class="cost-card-label">Total wallet (est.)</span><span class="cost-card-value cost-earned">$${balance}</span></div>` +
      `<div class="cost-card"><span class="cost-card-label">Projects joined</span><span class="cost-card-value">${(w.projects || []).length}</span></div>` +
      `<div class="cost-card"><span class="cost-card-label">Payout at</span><span class="cost-card-value">$${threshold}</span></div>` +
      `<div class="cost-card"><span class="cost-card-label">Status</span><span class="cost-card-value ${pricing.payout_eligible ? "cost-earned" : ""}">${pricing.payout_eligible ? "Eligible" : `$${pricing.payout_remaining_usd ?? Math.max(0, threshold - balance).toFixed(0)} to go`}</span></div>`;
  }
  const progressWrap = $("#wallet-payout-progress");
  const progressLabel = $("#wallet-payout-label");
  const progressFill = $("#wallet-payout-fill");
  if (progressWrap) {
    progressWrap.hidden = false;
    const pct = Math.min(100, Math.round((100 * balance) / threshold));
    if (progressLabel) {
      progressLabel.textContent = pricing.payout_eligible
        ? `$${balance} — cash out or apply to QA your apps`
        : `$${balance} / $${threshold}`;
    }
    if (progressFill) progressFill.style.width = `${pct}%`;
  }
  const tbody = $("#cost-wallet-tbody");
  if (tbody) {
    const rows = w.projects || [];
    tbody.innerHTML = rows.length
      ? rows
          .map((p) => {
            const d = p.deliverables || {};
            const del =
              `${d.reports_submitted || 0} reports · ${d.critical_issues || 0} critical · ${d.time_hours || 0}h`;
            return (
              `<tr>` +
              `<td><strong>${escapeHtml(p.project_name)}</strong><br /><span class="meta">${escapeHtml(p.suite_name || "")}</span></td>` +
              `<td>$${p.human_pool_usd}</td>` +
              `<td class="cost-earned">$${p.earned_usd}</td>` +
              `<td class="meta">${escapeHtml(del)}</td>` +
              `</tr>`
            );
          })
          .join("")
      : `<tr><td colspan="4" class="empty-hint">Join open challenges from Build (QA Hunter avatar) to earn from the human pool.</td></tr>`;
  }
}

const STORAGE_XP = "qoa_web_xp";
const STORAGE_A77_LOCAL = "qoa_web_atomic77_local";
const XP_WEIGHTS = {
  creator_activity: { label: "Creator — budget, chat, BRAHL cycles", weight: "1.2×", base: 40 },
  hunter_activity: { label: "QA Hunter — joins, reports, deliverables", weight: "1.5×", base: 35 },
  networker_activity: { label: "Nalanda — community contribution", weight: "1.0×", base: 15 },
  atomic77_activity: { label: "Atomic 77 — idea-to-launch assistant", weight: "0.8×", base: 12 },
  passion_time: { label: "Time & passion in the arena", weight: "0.3× / 10 min", base: 10 },
};

function loadXpLedger() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_XP) || "{}");
  } catch {
    return {};
  }
}

function saveXpLedger(led) {
  const sum = Object.entries(led)
    .filter(([k]) => !k.startsWith("_"))
    .reduce((s, [, v]) => s + (Number(v) || 0), 0);
  led._total = sum;
  localStorage.setItem(STORAGE_XP, JSON.stringify(led));
  return led;
}

function addXp(category, amount) {
  const led = loadXpLedger();
  led[category] = (led[category] || 0) + amount;
  saveXpLedger(led);
  if (state.phase === "cost") loadCostPanel();
  updateVisualRewardRail();
}

function updateVisualRewardRail() {
  if (window.QoaTheme?.getTheme?.() !== "arena") return;
  const { total } = computeXpBreakdown();
  const led = loadXpLedger();
  const mins = sessionMinutesEstimate();
  const xpEl = $("#rail-xp");
  if (xpEl) xpEl.textContent = String(total);
  const payEl = $("#rail-pay");
  if (payEl) {
    const budget = activeProject?.budget_usd;
    payEl.textContent = budget != null && budget > 0 ? `$${Math.round(budget * 0.45)}` : "$—";
  }
  const launchEl = $("#rail-launch");
  if (launchEl) {
    const go = activeProject?.latest_run ? "Go?" : "—";
    launchEl.textContent = go;
  }
  const huntIcon = $("#rail-icon-hunt");
  const huntLabel = $("#rail-label-hunt");
  const huntStep = $("#rail-step-hunt");
  if (state.avatar === "client") {
    if (huntIcon) huntIcon.textContent = "🥊";
    if (huntLabel) huntLabel.textContent = "Build";
  } else if (state.avatar === "consultant") {
    if (huntIcon) huntIcon.textContent = "🎯";
    if (huntLabel) huntLabel.textContent = "Hunt";
  } else if (state.avatar === "networker") {
    if (huntIcon) huntIcon.textContent = "📚";
    if (huntLabel) huntLabel.textContent = "Nalanda";
  }
  $$(".reward-step").forEach((s) => s.classList.remove("reward-step-current"));
  const phaseMap = {
    build: "rail-step-hunt",
    run: "rail-step-hunt",
    analyze: "rail-step-hunt",
    heal: "rail-step-hunt",
    loop: "rail-step-hunt",
    brahl: "rail-step-launch",
    atomic77: "rail-step-hunt",
    cost: "rail-step-pay",
    nalanda: "rail-step-xp",
  };
  const stepId = phaseMap[state.phase] || "rail-step-hunt";
  $(`#${stepId}`)?.classList.add("reward-step-current");
  const vXp = $("#visual-xp-total");
  if (vXp) vXp.textContent = String(total);
  const vMin = $("#visual-session-min");
  if (vMin) vMin.textContent = String(mins);
  const vShares = $("#visual-shares");
  if (vShares) vShares.textContent = String(led.promote_shares || 0);
  const vBudget = $("#visual-budget");
  if (vBudget) {
    const b = activeProject?.budget_usd;
    vBudget.textContent = b != null && b > 0 ? `$${b}` : "—";
  }
  if (title && window.QoaTheme?.getTheme?.() === "arena" && state.avatar) title.textContent = "BRAHL Arena";
  else if (title && window.QoaTheme?.getTheme?.() !== "arena") title.textContent = "BRAHL Web — f(x,y)=z";
}

function sessionMinutesEstimate() {
  const key = "qoa_web_session_start";
  let start = sessionStorage.getItem(key);
  if (!start) {
    start = String(Date.now());
    sessionStorage.setItem(key, start);
  }
  return Math.max(1, Math.floor((Date.now() - Number(start)) / 60000));
}

function computeXpBreakdown() {
  const led = loadXpLedger();
  const avatar = state.avatar || "client";
  const mins = sessionMinutesEstimate();
  const rows = [
    {
      key: "creator_activity",
      xp: Math.round((led.creator_activity || 0) + (avatar === "client" ? XP_WEIGHTS.creator_activity.base : 0)),
    },
    {
      key: "hunter_activity",
      xp: Math.round((led.hunter_activity || 0) + (avatar === "consultant" ? XP_WEIGHTS.hunter_activity.base : 0)),
    },
    {
      key: "networker_activity",
      xp: Math.round(
        (led.promote_drafts || 0) +
          (led.promote_shares || 0) * 25 +
          (avatar === "networker" ? XP_WEIGHTS.networker_activity.base : 0)
      ),
    },
    {
      key: "atomic77_activity",
      xp: Math.round((led.atomic77_activity || 0) + (led.atomic77_tokens || 0) * 0.02),
    },
    {
      key: "passion_time",
      xp: Math.round((led.passion_time || 0) + mins * 3),
    },
  ];
  const total = rows.reduce((s, r) => s + r.xp, 0);
  return { rows, total, led };
}

function renderDepositSplitBar(split, blurb) {
  const budget = split.budget_usd || 0;
  const pct = (usd) => (budget > 0 ? (100 * usd) / budget : 0);
  const segments = [
    { cls: "xp-pool-platform", usd: split.platform_fee_usd, label: `QAonAIR ${split.platform_fee_pct}%`, title: "Platform fee retained by QAonAIR" },
    { cls: "xp-pool-admin", usd: split.admin_ops_usd, label: `Ops ${split.admin_ops_pct}%`, title: "Admin & operations" },
    { cls: "xp-pool-ai", usd: split.ai_cost_usd, label: `AI $${split.ai_cost_usd}`, title: "AI & automation costs" },
    { cls: "xp-pool-human", usd: split.human_payout_usd, label: `Humans $${split.human_payout_usd}`, title: "QA Hunter & contributor payouts" },
  ];
  const bar = segments
    .filter((s) => s.usd > 0)
    .map(
      (s) =>
        `<span class="xp-pool-seg ${s.cls}" style="width:${Math.max(pct(s.usd), 8).toFixed(1)}%" title="${escapeHtml(s.title)}">${escapeHtml(s.label)}</span>`
    )
    .join("");
  const legend = segments
    .map((s) => `<span class="pricing-legend-item"><strong>${escapeHtml(s.label)}</strong> · $${s.usd}</span>`)
    .join("");
  return `<p class="blurb">${blurb}</p><div class="xp-pool-bar">${bar}</div><div class="pricing-split-legend">${legend}</div>`;
}

async function fetchPricingForPanel(meter, wallet) {
  const budget = meter?.budget_usd || 0;
  const autoPct = meter?.automation_pct ?? 50;
  const humanPct = meter?.human_pct ?? 50;
  const walletBalance = wallet?.total_earned_usd ?? 0;
  const params = new URLSearchParams({
    automation_pct: String(autoPct),
    human_pct: String(humanPct),
    wallet_balance_usd: String(walletBalance),
  });
  if (budget > 0) params.set("budget_usd", String(budget));
  const data = await api(`/api/pricing?${params}`);
  return data.pricing;
}

function renderPricingRules(p) {
  const el = $("#pricing-rules");
  if (!el || !p) return;
  const tasks = (p.earn_tasks || [])
    .map((t) => `<li><strong>${escapeHtml(t.title)}</strong> — ${escapeHtml(t.description)}</li>`)
    .join("");
  const payouts = (p.payout_options || []).map((o) => `<li>${escapeHtml(o)}</li>`).join("");
  const example = p.example_deposit_split;
  el.innerHTML =
    `<p class="blurb pricing-summary">${escapeHtml(p.summary || "")}</p>` +
    `<div class="pricing-grid">` +
    `<div class="pricing-card"><span class="pricing-card-label">Membership</span><span class="pricing-card-value">~$${p.membership_usd_per_month}/mo</span><span class="meta">Every member</span></div>` +
    `<div class="pricing-card"><span class="pricing-card-label">Creator QA wallet</span><span class="pricing-card-value">$${p.creator_wallet_min_usd}+</span><span class="meta">Minimum top-up</span></div>` +
    `<div class="pricing-card"><span class="pricing-card-label">QAonAIR fee</span><span class="pricing-card-value">${p.platform_fee_pct}%</span><span class="meta">Retained on deposits</span></div>` +
    `<div class="pricing-card"><span class="pricing-card-label">Payout threshold</span><span class="pricing-card-value">$${p.payout_threshold_usd}</span><span class="meta">Or spend on your QA</span></div>` +
    `</div>` +
    `<div class="pricing-two-col">` +
    `<div><h4 class="pricing-sub">Earn wallet credits</h4><ul class="about-bullet-list">${tasks}</ul></div>` +
    `<div><h4 class="pricing-sub">Payout options</h4><ul class="about-bullet-list">${payouts}</ul></div>` +
    `</div>` +
    (example
      ? `<h4 class="pricing-sub">Example — $${example.budget_usd} Creator deposit</h4>${renderDepositSplitBar(example, "After QAonAIR and ops fees, the net pool splits between AI and human payouts per your Build slider.")}`
      : "");
}

function renderXpPoolSplit(m, pricing) {
  const el = $("#xp-pool-split");
  if (!el) return;
  const split = m?.deposit_split || pricing?.project_deposit_split;
  if (split?.budget_usd) {
    el.innerHTML = renderDepositSplitBar(
      split,
      `Challenge QA wallet <strong>$${split.budget_usd}</strong> — QAonAIR keeps <strong>${split.platform_fee_pct}%</strong>; ` +
        `net <strong>$${split.net_pool_usd}</strong> splits AI vs human per your Build slider (${split.automation_pct}% / ${split.human_pct}%).`
    );
    return;
  }
  const example = pricing?.example_deposit_split;
  if (example) {
    el.innerHTML = renderDepositSplitBar(
      example,
      `Set a QA wallet on <strong>Build</strong> (Creator, from <strong>$${pricing.creator_wallet_min_usd}</strong>). ` +
        `Example <strong>$${example.budget_usd}</strong> deposit split below.`
    );
    return;
  }
  el.innerHTML =
    `<p class="blurb">Creators fund QA wallets from <strong>$50+</strong>. QAonAIR retains <strong>5%</strong>; ` +
    `deposits split across <strong>AI</strong>, <strong>human payouts</strong>, and <strong>admin/ops</strong>.</p>` +
    `<div class="xp-pool-bar xp-pool-placeholder">` +
    `<span class="xp-pool-seg xp-pool-platform" style="width:5%">QAonAIR 5%</span>` +
    `<span class="xp-pool-seg xp-pool-admin" style="width:10%">Ops 10%</span>` +
    `<span class="xp-pool-seg xp-pool-ai" style="width:38%">AI ~38%</span>` +
    `<span class="xp-pool-seg xp-pool-human" style="width:47%">Humans ~47%</span>` +
    `</div>`;
}

function renderXpPanel(m, pricing) {
  const { rows, total } = computeXpBreakdown();
  const label = $("#xp-avatar-label");
  if (label) label.textContent = state.avatar ? avatarLabel(state.avatar).short : "your arena";
  const cards = $("#xp-summary-cards");
  if (cards) {
    cards.innerHTML =
      `<div class="cost-card xp-card"><span class="cost-card-label">Total XP</span><span class="cost-card-value xp-value">${total}</span></div>` +
      `<div class="cost-card xp-card"><span class="cost-card-label">Avatar</span><span class="cost-card-value">${escapeHtml(avatarLabel(state.avatar || "client").short)}</span></div>` +
      `<div class="cost-card xp-card"><span class="cost-card-label">Session</span><span class="cost-card-value">${sessionMinutesEstimate()} min</span></div>` +
      `<div class="cost-card xp-card"><span class="cost-card-label">Shares</span><span class="cost-card-value">${loadXpLedger().promote_shares || 0}</span></div>`;
  }
  const tbody = $("#xp-breakdown-tbody");
  if (tbody) {
    tbody.innerHTML = rows
      .map((r) => {
        const meta = XP_WEIGHTS[r.key] || { label: r.key, weight: "—" };
        return `<tr><td>${escapeHtml(meta.label)}</td><td>${escapeHtml(meta.weight)}</td><td><strong>${r.xp}</strong></td></tr>`;
      })
      .join("");
  }
  renderXpPoolSplit(m, pricing);
  updateVisualRewardRail();
}

async function sendAtomic77Faq(faqKey) {
  if (!state.avatar) {
    setStatus("Choose an avatar first");
    return;
  }
  const faqLabels = {
    idea: "How do I turn my idea into a BRAHL project?",
    brahl: "Explain BRAHL for my app",
    launch: "What's the launch checklist?",
    cost: "How do membership, wallet, and payouts work?",
    hunter: "How do I hunt and get paid?",
  };
  const text = faqLabels[faqKey] || faqKey;
  try {
    const data = await api("/api/atomic77/chat", {
      method: "POST",
      body: JSON.stringify({
        text,
        faq_key: faqKey,
        avatar: state.avatar,
        project_id: state.projectId || null,
      }),
    });
    const answer = data.assistant_message?.text || "";
    const el = $("#nalanda-faq-answer");
    if (el) {
      el.hidden = false;
      el.innerHTML = answer.replace(/\*\*/g, "");
    }
    setStatus("FAQ answer loaded");
  } catch (e) {
    setStatus(e.message || "FAQ failed");
  }
}

window.QoaXp = { add: addXp, ledger: loadXpLedger };
window.sendAtomic77Faq = sendAtomic77Faq;

async function loadCostPanel() {
  let meter = null;
  let wallet = null;
  if (state.projectId && state.avatar !== "networker") {
    try {
      const runtime = $("#cost-runtime-cloud")?.checked ? "cloud" : "local";
      const data = await api(
        `/api/projects/${state.projectId}/cost-meter?runtime=${encodeURIComponent(runtime)}`
      );
      meter = data.cost_meter;
    } catch {
      /* XP still renders */
    }
  }
  if (state.avatar === "consultant") {
    try {
      wallet = (await api("/api/consultant/wallet")).wallet;
    } catch {
      /* pricing still loads */
    }
  }
  let pricing = null;
  try {
    pricing = await fetchPricingForPanel(meter, wallet);
  } catch {
    /* rules section shows loading fallback */
  }
  renderXpPanel(meter, pricing);
  renderPricingRules(pricing);

  const clientView = $("#cost-client-view");
  const hitlView = $("#cost-hitl-view");
  if (state.avatar === "networker") {
    if (clientView) clientView.hidden = true;
    if (hitlView) hitlView.hidden = true;
    return;
  }
  if (state.avatar === "consultant") {
    if (clientView) clientView.hidden = true;
    if (hitlView) hitlView.hidden = false;
    if (wallet) renderConsultantWallet(wallet);
    else renderConsultantWallet({ total_earned_usd: 0, projects: [], philosophy: "", pricing: pricing || {} });
    return;
  }
  if (clientView) clientView.hidden = false;
  if (hitlView) hitlView.hidden = true;
  if (!state.projectId) return;
  if (meter) {
    renderCostMeter(meter);
    return;
  }
  const runtime = $("#cost-runtime-cloud")?.checked ? "cloud" : "local";
  try {
    const { cost_meter: m } = await api(
      `/api/projects/${state.projectId}/cost-meter?runtime=${encodeURIComponent(runtime)}`
    );
    renderCostMeter(m);
  } catch {
    setStatus("Could not load cost meter");
  }
}

async function saveCostRuntimeMode(mode) {
  if (!state.projectId) return;
  await api(`/api/projects/${state.projectId}`, {
    method: "PATCH",
    body: JSON.stringify({ runtime_mode: mode }),
  });
  if (activeProject) activeProject.runtime_mode = mode;
  loadCostPanel();
  renderBuildCostTeaser();
}

function getYpadDisplayRows() {
  const data = ypadState.data;
  if (!data) return [];
  let rows = data.rows || [];
  if (ypadState.tab === "plans") {
    const cov = ypadState.coverageFilter || "all";
    if (cov === "auto" || $("#ypad-run-y-only")?.checked) {
      rows = rows.filter((r) => {
        const pid = (r.PlanId || "").trim();
        if (pid.startsWith("PReuse_")) return false;
        return (r.Run || "").trim().toUpperCase() === "Y";
      });
    } else if (cov === "manual") {
      rows = rows.filter((r) => {
        const pid = (r.PlanId || "").trim();
        if (pid.startsWith("PReuse_")) return false;
        const tags = (r.Tags || "").toLowerCase();
        const run = (r.Run || "").trim().toUpperCase();
        return tags.split(/[;,\s]+/).includes("manual") || run === "N";
      });
    }
  }
  if (ypadState.tab === "designs" && ypadState.designGroupFilter) {
    rows = rows.filter((r) => ypadDesignGroupMatch(r.DataName, ypadState.designGroupFilter));
  }
  if (ypadState.filter) {
    rows = rows.filter((r) => ypadRowMatchesFilter(r, ypadState.filter));
  }
  return rows;
}

function renderYpadExplorer() {
  const data = ypadState.data;
  const tab = ypadState.tab;
  $$(".ypad-tab").forEach((btn) => {
    const on = btn.dataset.ypadTab === tab;
    btn.classList.toggle("active", on);
    btn.setAttribute("aria-selected", on ? "true" : "false");
  });
  const isEnv = tab === "env";
  $("#ypad-env-panel").hidden = !isEnv || ypadState.editMode;
  $("#ypad-csv-editor").hidden = !ypadState.editMode || isEnv;
  $("#ypad-run-y-wrap").hidden = true;
  const covChips = $("#ypad-coverage-chips");
  if (covChips) covChips.hidden = tab !== "plans" || ypadState.editMode;
  const designsToolbar = $("#ypad-designs-toolbar");
  if (designsToolbar) designsToolbar.hidden = true;
  $("#ypad-toggle-edit").hidden = isEnv;
  $("#ypad-save").hidden = !ypadState.editMode || isEnv;
  $("#ypad-filter").hidden = ypadState.editMode;

  if (data?.paths?.length) {
    const srcHint =
      ypadState.source ||
      (data.multi_file ? `${data.paths.length} files (pick source to edit)` : data.paths[0]);
    $("#ypad-meta").textContent = `${data.row_count ?? data.rows?.length ?? 0} rows · ${srcHint}`;
  } else {
    $("#ypad-meta").textContent = "";
  }
  renderYpadSourceChips(data);

  if (isEnv) {
    $("#ypad-env-example").textContent = data?.env_example || "# No ENV defined";
    return;
  }

  if (ypadState.editMode && data) {
    $("#ypad-csv-editor").value = rowsToCsv(data.headers || [], data.rows || []);
    return;
  }

  const rowsAll = getYpadDisplayRows();
  const pageSize = ypadState.pageSize || 50;
  const maxPage = Math.max(0, Math.ceil(rowsAll.length / pageSize) - 1);
  if (ypadState.page > maxPage) ypadState.page = maxPage;
  const start = ypadState.page * pageSize;
  const rows = rowsAll.slice(start, start + pageSize);
  const { cols, labels } = ypadDisplayColumnsForTab(tab, data);
  const tableWrap = $("#ypad-table-wrap");
  const showTable = ypadState.showTable || ypadState.editMode;
  if (tableWrap) {
    tableWrap.hidden = isEnv || ypadState.editMode ? (isEnv || false) : !showTable;
    if (ypadState.editMode) tableWrap.hidden = true;
    tableWrap.classList.toggle("ypad-table-wide", tab === "designs" && cols.length > 4);
  }
  const showBtn = $("#ypad-show-table");
  if (showBtn) {
    showBtn.hidden = isEnv || ypadState.editMode;
    showBtn.textContent = ypadState.showTable ? "Hide table" : "Show table";
  }
  const pageMeta = $("#ypad-page-meta");
  if (pageMeta) {
    pageMeta.textContent = rowsAll.length
      ? `${start + 1}–${Math.min(start + pageSize, rowsAll.length)} of ${rowsAll.length}`
      : "0 rows";
  }
  const prevBtn = $("#ypad-page-prev");
  const nextBtn = $("#ypad-page-next");
  if (prevBtn) {
    prevBtn.hidden = !ypadState.showTable || ypadState.page <= 0;
  }
  if (nextBtn) {
    nextBtn.hidden = !ypadState.showTable || ypadState.page >= maxPage;
  }

  const thead = $("#ypad-thead");
  const tbody = $("#ypad-tbody");
  thead.innerHTML = `<tr>${cols
    .map((c) => `<th title="${escapeHtml(c)}">${escapeHtml(labels[c] || c)}</th>`)
    .join("")}</tr>`;
  tbody.innerHTML = rows
    .map((row, idx) => {
      const run = (row.Run || "").trim().toUpperCase();
      const cls = tab === "plans" ? (run === "Y" ? "run-y" : run === "N" ? "run-n" : "") : "";
      const sel = idx === ypadState.selectedIndex ? " selected" : "";
      return `<tr class="${cls}${sel}" data-idx="${idx}">${cols
        .map((c) => `<td title="${escapeHtml(row[c] || "")}">${escapeHtml(row[c] || "")}</td>`)
        .join("")}</tr>`;
    })
    .join("");
  $("#ypad-empty").hidden = rows.length > 0;
  tbody.querySelectorAll("tr").forEach((tr) => {
    tr.addEventListener("click", () => {
      ypadState.selectedIndex = parseInt(tr.dataset.idx, 10);
      openYpadDrawer(rows[ypadState.selectedIndex]);
      renderYpadExplorer();
    });
  });
}

function openYpadDrawer(row) {
  if (!row) return;
  const drawer = $("#ypad-detail-drawer");
  const backdrop = $("#ypad-drawer-backdrop");
  const title = $("#ypad-drawer-title");
  const body = $("#ypad-drawer-body");
  const label =
    row.PlanName || row.PlanId || row.DataName || row.ActionName || row.StepInfo || "Row details";
  title.textContent = label;
  const preferred = ["PlanId", "PlanName", "Tags", "Run", "CreatedBy", "CreatedAt", "StepId", "DataName"];
  const entries = Object.entries(row).sort(([a], [b]) => {
    const ia = preferred.indexOf(a);
    const ib = preferred.indexOf(b);
    if (ia >= 0 || ib >= 0) return (ia < 0 ? 999 : ia) - (ib < 0 ? 999 : ib);
    return a.localeCompare(b);
  });
  body.innerHTML = entries
    .map(([k, v]) => `<dt>${escapeHtml(k)}</dt><dd>${escapeHtml(v || "—")}</dd>`)
    .join("");
  if (backdrop) backdrop.hidden = false;
  drawer.hidden = false;
}

function closeYpadDrawer(rerender = true) {
  const drawer = $("#ypad-detail-drawer");
  const backdrop = $("#ypad-drawer-backdrop");
  if (drawer) drawer.hidden = true;
  if (backdrop) backdrop.hidden = true;
  ypadState.selectedIndex = -1;
  if (rerender) renderYpadExplorer();
}

function renderYpadSourceChips(data) {
  let host = $("#ypad-source-chips");
  if (!host) {
    const toolbar = $(".ypad-toolbar");
    if (!toolbar) return;
    host = document.createElement("div");
    host.id = "ypad-source-chips";
    host.className = "ypad-source-chips";
    host.setAttribute("role", "group");
    host.setAttribute("aria-label", "yPAD source file");
    toolbar.insertBefore(host, toolbar.firstChild);
  }
  const sources = data?.sources || [];
  if (!data?.multi_file && sources.length <= 1) {
    host.hidden = true;
    host.innerHTML = "";
    return;
  }
  host.hidden = false;
  const chips = [
    { kind: "", source: "", label: "All files" },
    { kind: "gate", source: "", label: "Gate" },
    { kind: "journey", source: "", label: "Journey" },
    ...sources.map((s) => ({
      kind: "",
      source: s.path,
      label: `${s.kind}: ${String(s.path).split("/").pop()}`,
    })),
  ];
  host.innerHTML = chips
    .map((c) => {
      const active =
        (c.source && ypadState.source === c.source) ||
        (!c.source && !ypadState.source && (ypadState.sourceKind || "") === (c.kind || ""));
      return `<button type="button" class="ypad-source-chip${active ? " active" : ""}" data-source="${escapeHtml(c.source)}" data-kind="${escapeHtml(c.kind)}">${escapeHtml(c.label)}</button>`;
    })
    .join("");
  host.querySelectorAll(".ypad-source-chip").forEach((btn) => {
    btn.addEventListener("click", () => {
      ypadState.source = btn.dataset.source || "";
      ypadState.sourceKind = btn.dataset.kind || "";
      loadYpadSheet(ypadState.tab);
    });
  });
}

function toggleYpadEdit() {
  if (ypadState.tab === "env") return;
  const paths = ypadState.data?.paths || [];
  const multi = !!ypadState.data?.multi_file || paths.length > 1;
  if (!ypadState.editMode && multi && !ypadState.source && paths.length !== 1) {
    setStatus("Pick a Gate or Journey source chip before editing multi-file yPAD sheets.");
    return;
  }
  ypadState.editMode = !ypadState.editMode;
  renderYpadExplorer();
}

async function saveYpadSheet() {
  if (!state.suiteName || ypadState.tab === "env") return;
  const parsed = csvToRows($("#ypad-csv-editor").value);
  if (!parsed.headers.length) {
    setStatus("CSV must have a header row");
    return;
  }
  const paths = ypadState.data?.paths || [];
  const multi = !!ypadState.data?.multi_file || paths.length > 1;
  const source =
    ypadState.source ||
    (paths.length === 1 ? paths[0] : "") ||
    (ypadState.data?.sources?.length === 1 ? ypadState.data.sources[0].path : "");
  if (multi && !source) {
    setStatus("Pick a source file (gate or journey) before saving — merged writes are blocked.");
    return;
  }
  try {
    await api(`/api/suites/${encodeURIComponent(state.suiteName)}/ypad/${ypadState.tab}`, {
      method: "PUT",
      body: JSON.stringify({
        headers: parsed.headers,
        rows: parsed.rows,
        ...(source ? { source } : {}),
      }),
    });
  } catch (err) {
    setStatus(String(err.message || err));
    return;
  }
  ypadState.editMode = false;
  await loadYpadSheet(ypadState.tab);
  const label = ypadState.tab === "plans" ? "1Plans" : ypadState.tab === "actions" ? "2Actions" : "3Designs";
  setStatus(`Saved y${label}.csv${source ? ` → ${source}` : ""}`);
}

async function loadYpadVersions() {
  const list = $("#ypad-versions-list");
  if (!list || !state.suiteName) return;
  try {
    const data = await api(`/api/suites/${encodeURIComponent(state.suiteName)}/ypad-versions`);
    ypadState.versions = data.versions || [];
  } catch {
    ypadState.versions = [];
  }
  list.innerHTML = ypadState.versions.length
    ? ypadState.versions
        .map((v) => {
          const active = v.id === ypadState.selectedVersionId ? " active" : "";
          return `<li class="ypad-version-item${active}" data-vid="${escapeHtml(v.id)}">
            <div><strong>${escapeHtml(v.label || v.id)}</strong>
            <span class="meta">${escapeHtml(v.author || "—")} · ${escapeHtml(v.created_at || "")}</span></div>
            <div class="ypad-version-actions">
              <button type="button" class="linkish" data-act="diff">Diff</button>
              <button type="button" class="linkish" data-act="merge">Merge missing</button>
              <button type="button" class="linkish" data-act="restore">Restore</button>
            </div>
          </li>`;
        })
        .join("")
    : `<li class="meta">No snapshots yet — Snapshot before a big rebuild.</li>`;
  list.querySelectorAll(".ypad-version-item").forEach((li) => {
    const vid = li.dataset.vid;
    li.querySelectorAll("button[data-act]").forEach((btn) => {
      btn.addEventListener("click", (ev) => {
        ev.stopPropagation();
        handleYpadVersionAction(vid, btn.dataset.act);
      });
    });
    li.addEventListener("click", () => {
      ypadState.selectedVersionId = vid;
      loadYpadVersions();
    });
  });
}

async function handleYpadVersionAction(versionId, act) {
  if (!state.suiteName || !versionId) return;
  const base = `/api/suites/${encodeURIComponent(state.suiteName)}/ypad-versions/${encodeURIComponent(versionId)}`;
  try {
    if (act === "diff") {
      const diff = await api(`${base}/diff?sheet=plans`);
      const el = $("#ypad-version-diff");
      if (el) {
        el.hidden = false;
        el.innerHTML =
          `<strong>Diff vs current</strong> — +${diff.counts?.added || 0} / −${diff.counts?.removed || 0} / ~${diff.counts?.changed || 0}` +
          `<pre class="ypad-version-diff-pre">${escapeHtml(
            JSON.stringify(
              {
                added: (diff.added || []).slice(0, 8).map((r) => r.PlanId || r.DataName),
                removed: (diff.removed || []).slice(0, 8).map((r) => r.PlanId || r.DataName),
                changed: (diff.changed || []).slice(0, 8).map((c) => c.key),
              },
              null,
              2
            )
          )}</pre>`;
      }
      setStatus(`Compared version ${versionId}`);
      return;
    }
    if (act === "merge") {
      const res = await api(`${base}/merge`, {
        method: "POST",
        body: JSON.stringify({ sheet: "plans" }),
      });
      setStatus(`Merged ${res.merged || 0} missing plan(s) from ${versionId}`);
      await loadYpadSheet(ypadState.tab);
      return;
    }
    if (act === "restore") {
      if (!confirm(`Restore yPAD files from snapshot ${versionId}? Current CSVs will be overwritten.`)) return;
      await api(`${base}/restore`, { method: "POST", body: "{}" });
      setStatus(`Restored yPAD from ${versionId}`);
      await loadYpadSheet(ypadState.tab);
      await loadYpadVersions();
    }
  } catch (err) {
    setStatus(String(err.message || err));
  }
}

async function createYpadSnapshot() {
  if (!state.suiteName) return;
  const label = prompt("Snapshot label (optional)", "before-rebuild") || "";
  const author =
    getAuthUser()?.name || getAuthUser()?.email || localStorage.getItem("qoa_profile_name") || "arena";
  try {
    const snap = await api(`/api/suites/${encodeURIComponent(state.suiteName)}/ypad-versions`, {
      method: "POST",
      body: JSON.stringify({
        label,
        author,
        source_build: state.projectId || state.suiteName || "",
      }),
    });
    ypadState.selectedVersionId = snap.id;
    setStatus(`Snapshot saved: ${snap.label || snap.id}`);
    await loadYpadVersions();
  } catch (err) {
    setStatus(String(err.message || err));
  }
}

function updateInviteButtonState() {
  const btn = $("#btn-invite-hitl");
  if (!btn) return;
  const enabled = !!state.projectId;
  btn.disabled = !enabled;
  btn.title = enabled ? "" : "Select or create a challenge first";
}

function openInviteHitlModal() {
  if (!state.projectId) {
    setStatus("Select or create a challenge before inviting QA Hunters.");
    return;
  }
  $("#invite-consultant-name").value = "";
  $("#invite-email").value = "";
  $("#invite-tag").value = "";
  $("#invite-note").value = "";
  $("#invite-bug-bounty").checked = false;
  $("#invite-hitl-modal").hidden = false;
}

function closeInviteHitlModal() {
  $("#invite-hitl-modal").hidden = true;
}

function openChangeRequestModal() {
  if (!state.projectId) return;
  $("#change-request-note").value = "";
  $("#change-request-modal").hidden = false;
}

function closeChangeRequestModal() {
  $("#change-request-modal").hidden = true;
}

async function loadBuildBoard() {
  if (!state.projectId) return;
  try {
    const data = await api(`/api/projects/${state.projectId}/build-board`);
    if (data.project) activeProject = data.project;
    renderBuildBoard(data);
  } catch {
    renderBuildBoard({ automation_plans: [], hitl_stories: [], requirement: activeProject?.purpose || "" });
  }
}

function renderBuildBoard(data) {
  const brahlReq = $("#brahl-plan-requirement");
  if (brahlReq && !brahlReq.value.trim()) {
    brahlReq.value = data.requirement || activeProject?.purpose || "";
  }
  renderBuildStrategySummary(data);
  loadBuildDocs();
  renderHunterManualList(data);
  refreshLoopBuiltSummary();
  const verifyEl = $("#build-verify-summary");
  if (verifyEl) {
    const st = data.report_stats;
    if (st && data.latest_run) {
      verifyEl.hidden = false;
      verifyEl.textContent = `Latest verify: ${st.passes}/${st.total_plans} pass · run ${data.latest_run} · full BRAHL report on the BRAHL tab`;
    } else {
      verifyEl.hidden = true;
    }
  }
  loadYpadSheet(ypadState.tab);
  loadYpadInsights();
  renderBuildCostTeaser();
  const storyList = $("#hitl-story-list");
  if (storyList) {
    const stories = data.hitl_stories || [];
    storyList.innerHTML = stories.length
      ? stories
          .map(
            (s) =>
              `<li class="hitl-story-item">` +
              `<span class="story-status">${escapeHtml(s.status || "open")}</span> ` +
              `<strong>${escapeHtml(s.title)}</strong>` +
              (s.description ? `<br /><span class="meta">${escapeHtml(s.description)}</span>` : "") +
              `</li>`
          )
          .join("")
      : "";
  }
  const invitesEl = $("#hitl-invites");
  if (invitesEl) {
    const pending = (data.hitl_invites || []).filter((i) => i.status === "pending");
    invitesEl.innerHTML = pending.length
      ? pending
          .map(
            (i) =>
              `<div class="hitl-invite-item">` +
              `<strong>${escapeHtml(i.consultant_name || i.team_name || "Consultant")}</strong>` +
              (i.consultant_tag ? ` <span class="ypad-tag-chip" style="cursor:default">${escapeHtml(i.consultant_tag)}</span>` : "") +
              (i.email ? ` · ${escapeHtml(i.email)}` : "") +
              (i.bug_bounty ? `<span class="bug-bounty-tag">bug bounty</span>` : "") +
              (i.note ? `<br /><span class="meta">${escapeHtml(i.note)}</span>` : "") +
              `</div>`
          )
          .join("")
      : "";
  }
  const changeList = $("#change-request-list");
  if (changeList) {
    const changes = data.change_requests || [];
    changeList.innerHTML = changes.length
      ? changes
          .slice(0, 5)
          .map(
            (c) =>
              `<li><strong>${escapeHtml((c.requested_at || "").slice(0, 10))}</strong> — ${escapeHtml(c.note || "")}</li>`
          )
          .join("")
      : "";
  }
  if (data.project) {
    renderHitlRoster(data.project);
  }
  renderVersionLaunchPanel(data);
}

function renderBuildStrategySummary(data) {
  const empty = $("#build-strategy-empty");
  const body = $("#build-strategy-body");
  if (!body) return;
  const draft = activeProject?.brahl_plan_draft || data?.brahl_plan_draft;
  const purpose = (data?.requirement || activeProject?.purpose || activeProject?.prompt || "").trim();
  if (!draft && !purpose) {
    if (empty) empty.hidden = false;
    body.hidden = true;
    body.innerHTML = "";
    return;
  }
  if (empty) empty.hidden = true;
  body.hidden = false;
  const stories = draft?.user_stories || [];
  const cases = draft?.test_cases || [];
  const auto = draft?.automated_count ?? cases.filter((c) => c.automated !== false).length;
  const manual = draft?.manual_count ?? cases.filter((c) => c.automated === false).length;
  const summary = (draft?.summary || purpose || "").trim();
  const bullets = (draft?.strategy_bullets || draft?.strategy || [])
    .slice(0, 6)
    .map((b) => (typeof b === "string" ? b : b?.text || b?.title || ""))
    .filter(Boolean);
  body.innerHTML =
    (summary ? `<p class="build-strategy-purpose">${escapeHtml(summary)}</p>` : "") +
    `<p class="meta">${stories.length} stories · ${auto} automated · ${manual} manual</p>` +
    (bullets.length
      ? `<ul class="build-strategy-bullets">${bullets.map((b) => `<li>${escapeHtml(b)}</li>`).join("")}</ul>`
      : "");
}

let buildDocsCache = { suite: "", docs: [] };
let buildDocModalState = { docId: null, view: "synopsis", doc: null };

async function loadBuildDocs() {
  const strip = $("#build-docs-strip");
  if (!strip) return;
  if (!state.suiteName) {
    strip.hidden = true;
    buildDocsCache = { suite: "", docs: [] };
    return;
  }
  strip.hidden = false;
  try {
    const q = state.projectId ? `?project_id=${encodeURIComponent(state.projectId)}` : "";
    const data = await api(`/api/suites/${encodeURIComponent(state.suiteName)}/docs${q}`);
    buildDocsCache = { suite: state.suiteName, docs: data.docs || [] };
  } catch {
    buildDocsCache = { suite: state.suiteName, docs: [] };
  }
  const byId = Object.fromEntries((buildDocsCache.docs || []).map((d) => [d.id, d]));
  for (const id of ["strategy", "plan"]) {
    const hint = $(`#build-doc-${id}-hint`);
    const doc = byId[id];
    if (!hint) continue;
    if (!doc) {
      hint.textContent = "Open synopsis";
      continue;
    }
    const oneLine = (doc.synopsis || doc.blurb || "").replace(/\s+/g, " ").trim();
    hint.textContent = oneLine ? oneLine.slice(0, 72) + (oneLine.length > 72 ? "…" : "") : doc.blurb || "Open synopsis";
    hint.title = doc.synopsis || doc.blurb || "";
  }
}

function setBuildDocModalView(view) {
  buildDocModalState.view = view === "full" ? "full" : "synopsis";
  const syn = $("#build-doc-modal-synopsis");
  const full = $("#build-doc-modal-full");
  const btnSyn = $("#build-doc-view-synopsis");
  const btnFull = $("#build-doc-view-full");
  if (syn) syn.hidden = buildDocModalState.view !== "synopsis";
  if (full) full.hidden = buildDocModalState.view !== "full";
  btnSyn?.classList.toggle("active", buildDocModalState.view === "synopsis");
  btnFull?.classList.toggle("active", buildDocModalState.view === "full");
}

function closeBuildDocModal() {
  const modal = $("#build-doc-modal");
  if (modal) modal.hidden = true;
  buildDocModalState = { docId: null, view: "synopsis", doc: null };
}

async function openBuildDoc(docId, view = "synopsis") {
  if (!state.suiteName || !docId) return;
  const modal = $("#build-doc-modal");
  if (!modal) return;
  modal.hidden = false;
  setBuildDocModalView(view);
  const title = $("#build-doc-modal-title");
  const meta = $("#build-doc-modal-meta");
  const syn = $("#build-doc-modal-synopsis");
  const full = $("#build-doc-modal-full");
  if (title) title.textContent = docId === "plan" ? "test plan.md" : "test strategy.md";
  if (meta) meta.textContent = "Loading…";
  if (syn) syn.innerHTML = `<p class="meta">Loading…</p>`;
  if (full) full.innerHTML = "";
  try {
    const q = state.projectId ? `?project_id=${encodeURIComponent(state.projectId)}` : "";
    const data = await api(
      `/api/suites/${encodeURIComponent(state.suiteName)}/docs/${encodeURIComponent(docId)}${q}`
    );
    const doc = data.doc || {};
    buildDocModalState = { docId, view: buildDocModalState.view, doc };
    if (title) title.textContent = doc.label || title.textContent;
    if (meta) {
      meta.textContent =
        `${doc.path || ""} · ${doc.source === "file" ? "on disk" : "generated from yPAD / purpose"}` +
        (doc.blurb ? ` — ${doc.blurb}` : "");
    }
    if (syn) {
      const synText = doc.synopsis || "No synopsis available.";
      syn.innerHTML =
        `<p>${escapeHtml(synText).replace(/\n/g, "<br>")}</p>` +
        `<p class="meta"><button type="button" class="linkish" id="build-doc-open-full-inline">Open full document →</button></p>`;
      $("#build-doc-open-full-inline")?.addEventListener("click", () => setBuildDocModalView("full"));
    }
    if (full) full.innerHTML = renderMarkdown(doc.markdown || "_Empty document._");
  } catch (e) {
    if (meta) meta.textContent = e.message || "Failed to load document";
    if (syn) syn.innerHTML = `<p class="empty-hint">${escapeHtml(e.message || "Failed to load")}</p>`;
  }
}

function renderHunterManualList(data) {
  const list = $("#hunter-manual-list");
  if (!list) return;
  const fromDraft = (activeProject?.brahl_plan_draft?.test_cases || []).filter((c) => c.automated === false);
  const fromStories = (data?.hitl_stories || activeProject?.hitl_stories || []).map((s) => ({
    title: s.title,
    id: s.id,
  }));
  const rows = fromDraft.length
    ? fromDraft.map((c) => ({ title: c.title || c.id, id: c.id }))
    : fromStories;
  list.innerHTML = rows.length
    ? rows
        .map(
          (r) =>
            `<li><strong>${escapeHtml(r.title || "Manual case")}</strong>` +
            (r.id ? ` <span class="meta">${escapeHtml(r.id)}</span>` : "") +
            `</li>`
        )
        .join("")
    : `<li class="empty-hint">No Manual cases yet — accept a BRAHL plan with manual tests, or filter Manual in Test coverage.</li>`;
}

function renderVersionLaunchPanel(data) {
  const p = data.project || activeProject || {};
  const baseIn = $("#baseline-version-input");
  const appIn = $("#app-version-input");
  const summary = $("#version-baseline-summary");
  if (baseIn && document.activeElement !== baseIn) baseIn.value = p.baseline_version || "";
  if (appIn && document.activeElement !== appIn) appIn.value = p.app_version || "";
  if (summary) {
    const br = p.baseline_run;
    if (br) {
      const bs = data.version_compare?.baseline_stats;
      summary.textContent = bs
        ? `Baseline ${p.baseline_version || "old"}: ${bs.passes}/${bs.total_plans} pass, ${bs.fails} fail · run ${br}`
        : `Baseline saved · run ${br}${p.baseline_version ? ` (${p.baseline_version})` : ""}`;
    } else {
      summary.textContent =
        "No baseline yet — Verify the old app, then Save latest Verify as baseline (captures all failures).";
    }
  }
}

function renderVersionCompare(cmp) {
  lastVersionCompare = cmp || null;
  const block = $("#version-compare-block");
  const cards = $("#version-compare-cards");
  const regList = $("#version-regression-list");
  if (!block || !cards) return;
  if (state.avatar !== "client" || !cmp?.baseline_run) {
    block.hidden = true;
    return;
  }
  block.hidden = false;
  const bs = cmp.baseline_stats || {};
  const cs = cmp.current_stats || {};
  const oldLabel = cmp.baseline_version || "Old version";
  const newLabel = cmp.app_version || "New version";
  cards.innerHTML =
    `<article class="version-compare-card old">` +
    `<h4>${escapeHtml(oldLabel)}</h4>` +
    `<div class="version-compare-stat">${bs.passes ?? 0}/${bs.total_plans ?? 0} pass · ${bs.fails ?? 0} fail</div>` +
    `<span class="meta">Health: ${escapeHtml(bs.health || "—")} · <code>${escapeHtml(cmp.baseline_run)}</code></span>` +
    `</article>` +
    `<article class="version-compare-card new${cmp.regression_count ? " regression" : ""}">` +
    `<h4>${escapeHtml(newLabel)}</h4>` +
    `<div class="version-compare-stat">${cs.passes ?? 0}/${cs.total_plans ?? 0} pass · ${cs.fails ?? 0} fail</div>` +
    `<span class="meta">Health: ${escapeHtml(cs.health || "—")} · ${cmp.regression_count || 0} regression(s) · ${cmp.fixed_count || 0} fixed</span>` +
    `</article>`;
  if (regList) {
    const regs = cmp.regressions || [];
    if (regs.length) {
      regList.hidden = false;
      regList.innerHTML = regs
        .map((planId) => `<li><code>${escapeHtml(planId)}</code> — passed on old, fails on new</li>`)
        .join("");
    } else {
      regList.hidden = true;
      regList.innerHTML = "";
    }
  }
}

async function saveVersionLabels() {
  if (!state.projectId) return;
  const data = await api(`/api/projects/${state.projectId}`, {
    method: "PATCH",
    body: JSON.stringify({
      baseline_version: $("#baseline-version-input")?.value?.trim() || "",
      app_version: $("#app-version-input")?.value?.trim() || "",
    }),
  });
  activeProject = data.project;
  await loadBuildBoard();
  setStatus("Version labels saved");
}

async function snapshotVersionBaseline() {
  if (!state.projectId) return;
  const label =
    $("#baseline-version-input")?.value?.trim() ||
    $("#app-version-input")?.value?.trim() ||
    "";
  try {
    const data = await api(`/api/projects/${state.projectId}/version-baseline`, {
      method: "POST",
      body: JSON.stringify({ version_label: label }),
    });
    activeProject = data.project;
    await loadBuildBoard();
    if ($("#panel-brahl")?.classList.contains("active")) await loadBrahlPanel();
    setStatus("Baseline saved — old-version verify pinned for launch compare");
  } catch (e) {
    alert(e.message || "Could not save baseline — run Verify on the old app first.");
  }
}

async function submitHitlStoryForm(ev) {
  ev.preventDefault();
  if (!state.projectId) return;
  const title = $("#hitl-story-title")?.value.trim();
  const description = $("#hitl-story-desc")?.value.trim() || "";
  if (!title) return;
  const { project } = await api(`/api/projects/${state.projectId}/hitl-stories`, {
    method: "POST",
    body: JSON.stringify({ title, description }),
  });
  activeProject = project;
  $("#hitl-story-title").value = "";
  $("#hitl-story-desc").value = "";
  await loadBuildBoard();
  setStatus("User story added for QA Hunters");
}

async function inviteHitlFromBuild(ev) {
  if (ev?.preventDefault) ev.preventDefault();
  if (!state.projectId) return;
  const consultant_name = $("#invite-consultant-name")?.value.trim() || "";
  const email = $("#invite-email")?.value.trim() || "";
  const consultant_tag = $("#invite-tag")?.value.trim() || "";
  const note = $("#invite-note")?.value.trim() || "";
  const bug_bounty = !!$("#invite-bug-bounty")?.checked;
  const { project } = await api(`/api/projects/${state.projectId}/invite-hitl`, {
    method: "POST",
    body: JSON.stringify({ note, consultant_name, email, consultant_tag, bug_bounty }),
  });
  activeProject = project;
  closeInviteHitlModal();
  await refreshActiveProject();
  await loadBuildBoard();
  setStatus("QA Hunter invited — teams can join from the QA Hunter avatar");
}

async function requestProjectChange(ev) {
  if (ev?.preventDefault) ev.preventDefault();
  if (!state.projectId) return;
  const note =
    $("#change-request-note")?.value.trim() ||
    "Project has changed — need assistance again.";
  const data = await api(`/api/projects/${state.projectId}/request-change`, {
    method: "POST",
    body: JSON.stringify({ note }),
  });
  activeProject = data.project;
  closeChangeRequestModal();
  const refine = $("#build-refine-details");
  if (refine) refine.open = true;
  renderChat($("#chat-thread"), activeProject.chat_messages || []);
  renderContextList(activeProject.context_items || []);
  renderBuildChecklist();
  loadBuildBoard();
  const chatInput = $("#chat-input");
  if (chatInput) {
    chatInput.value = "";
    chatInput.placeholder = "Add detail to the change request, or describe new test scope…";
  }
  chatInput?.focus();
  setStatus("Change request sent — BRAHL AI replied in chat below");
}

function scrollChatToBottom() {
  const el = $("#chat-thread");
  if (el) el.scrollTop = el.scrollHeight;
}

function renderChat(el, messages) {
  if (!el) return;
  el.innerHTML = (messages || [])
    .map(
      (m) =>
        `<div class="chat-msg chat-${m.role}"><span class="chat-role">${m.role === "assistant" ? "BRAHL AI" : "You"}</span>${
          m.role === "assistant" ? renderMarkdown(m.text) : escapeHtml(m.text)
        }</div>`
    )
    .join("");
  scrollChatToBottom();
}

const CONTEXT_KIND_LABELS = {
  connector: "Connector",
  url: "App URL",
  api_docs: "API docs",
  github: "GitHub",
  jira: "JIRA",
  screenshot: "Screenshot",
  figma: "Figma",
  note: "Note",
  document: "Document",
};

function renderContextList(items) {
  const list = $("#context-list");
  const empty = $("#context-empty");
  const chips = $("#context-chips");
  if (!list) return;
  const arr = items || [];
  if (empty) empty.hidden = arr.length > 0;
  list.innerHTML = arr.length
    ? arr
        .map((c) => {
          const kind = CONTEXT_KIND_LABELS[c.kind] || c.kind || "Context";
          const val = c.value || "";
          const link =
            val.startsWith("http://") || val.startsWith("https://")
              ? `<a href="${escapeHtml(val)}" target="_blank" rel="noopener">${escapeHtml(val)}</a>`
              : escapeHtml(val);
          return (
            `<li class="context-list-item">` +
            `<span class="context-kind-badge">${escapeHtml(kind)}</span> ` +
            `<strong>${escapeHtml(c.label || kind)}</strong>` +
            `<div class="context-list-value">${link}</div>` +
            `</li>`
          );
        })
        .join("")
    : "";
  if (chips) {
    chips.innerHTML = arr
      .map(
        (c) =>
          `<span class="ctx-chip" title="${escapeHtml(c.value)}">${escapeHtml(c.label || c.kind)}</span>`
      )
      .join("");
  }
}

async function loadBuildAiStatus() {
  const el = $("#build-ai-status");
  if (!el) return;
  if (!isAiOn()) {
    el.textContent = "AI off — use manual purpose above or turn AI on in the top bar.";
    return;
  }
  try {
    const q = state.projectId ? `?project_id=${encodeURIComponent(state.projectId)}` : "";
    const st = await api(`/api/ai/status${q}`);
    const journeyHint = st.journey_in_prompt ? " · journey ON" : "";
    const docHint = st.reference_doc_count
      ? ` · ${st.context_doc_count} in prompt${journeyHint} · click .md for Master + Journey`
      : "";
    el.textContent = st.available
      ? `BRAHL AI active (${st.model || "OpenAI"})${docHint}`
      : `AI on — guided replies (OPENAI_API_KEY in FoXYiZ/f/.env)${docHint}`;
  } catch {
    el.textContent = "BRAHL AI — describe changes in chat below · .md for Master + Journey context";
  }
}

let aiDocsCache = null;
let aiDocsBudget = null;
let aiDocsSelectedId = null;
let aiDocsExpanded = false;

function updateAiDocsBudget(budget) {
  aiDocsBudget = budget || null;
  const el = $("#ai-docs-budget");
  if (!el) return;
  if (!budget) {
    el.hidden = true;
    return;
  }
  el.hidden = false;
  el.classList.toggle("warn", Boolean(budget.over_budget));
  el.textContent =
    `My docs in prompt: ${budget.used_chars}/${budget.max_chars} chars · ` +
    `${budget.doc_count}/${budget.max_docs} files · max ${Math.round(budget.max_file_bytes / 1024)}KB each`;
}

function aiDocsProjectQuery() {
  return state.projectId ? `?project_id=${encodeURIComponent(state.projectId)}` : "";
}

async function openAiDocsModal() {
  const modal = $("#ai-docs-modal");
  if (!modal) return;
  modal.hidden = false;
  setAiDocsExpanded(true);
  try {
    const data = await api(`/api/ai/docs${aiDocsProjectQuery()}`);
    aiDocsCache = data.docs || [];
    updateAiDocsBudget(data.budget);
    renderAiDocsList();
    const firstPrompt =
      aiDocsCache.find((d) => d.source === "journey") ||
      aiDocsCache.find((d) => d.in_prompt && d.master) ||
      aiDocsCache.find((d) => d.in_prompt) ||
      aiDocsCache[0];
    if (firstPrompt) await selectAiDoc(firstPrompt.id);
  } catch {
    const promptList = $("#ai-docs-list-prompt");
    if (promptList) promptList.innerHTML = `<li class="empty-hint">Could not load AI docs.</li>`;
  }
}

function closeAiDocsModal() {
  const modal = $("#ai-docs-modal");
  if (modal) modal.hidden = true;
  setAiDocsExpanded(false);
  document.body.classList.remove("ai-docs-open");
}

function setAiDocsExpanded(on) {
  aiDocsExpanded = Boolean(on);
  const modal = $("#ai-docs-modal");
  const card = $("#ai-docs-modal-card");
  const btn = $("#ai-docs-expand");
  if (modal) modal.classList.toggle("is-expanded", aiDocsExpanded);
  if (card) card.classList.toggle("expanded", aiDocsExpanded);
  if (btn) btn.textContent = aiDocsExpanded ? "Collapse" : "Expand";
  document.body.classList.toggle("ai-docs-open", !modal?.hidden);
}

function toggleAiDocsExpand() {
  setAiDocsExpanded(!aiDocsExpanded);
}

function renderAiDocsList(selectedId) {
  const selected = selectedId ?? aiDocsSelectedId;
  const promptDocs = (aiDocsCache || []).filter(
    (d) => d.source === "journey" || d.master || (d.in_prompt && d.source !== "user")
  );
  const promptIds = new Set(promptDocs.map((d) => d.id));
  const builtins = (aiDocsCache || []).filter(
    (d) => d.source === "builtin" && !promptIds.has(d.id)
  );
  const users = (aiDocsCache || []).filter((d) => d.source === "user");
  const fill = (listEl, docs) => {
    if (!listEl) return;
    if (!docs.length) {
      listEl.innerHTML = `<li class="empty-hint" style="padding:0.5rem 0.75rem;font-size:0.75rem;color:var(--muted)">None yet</li>`;
      return;
    }
    listEl.innerHTML = docs
      .map(
        (d) =>
          `<li class="ai-docs-list-item${d.id === selected ? " active" : ""}">` +
          `<button type="button" data-doc-id="${escapeHtml(d.id)}">` +
          `<strong>${escapeHtml(d.title)}</strong>` +
          (d.in_prompt ? ` <span class="ai-docs-prompt-badge">in AI prompt</span>` : "") +
          `<span class="doc-sub">${escapeHtml(d.subtitle || d.path)}</span>` +
          `</button></li>`
      )
      .join("");
    listEl.querySelectorAll("button[data-doc-id]").forEach((btn) => {
      btn.addEventListener("click", () => selectAiDoc(btn.dataset.docId));
    });
  };
  fill($("#ai-docs-list-prompt"), promptDocs);
  fill($("#ai-docs-list-builtin"), builtins);
  fill($("#ai-docs-list-user"), users);
}

async function selectAiDoc(docId) {
  aiDocsSelectedId = docId;
  renderAiDocsList(docId);
  const title = $("#ai-docs-doc-title");
  const meta = $("#ai-docs-doc-meta");
  const body = $("#ai-docs-doc-body");
  const editor = $("#ai-docs-doc-editor");
  const toolbar = $("#ai-docs-edit-toolbar");
  const inPrompt = $("#ai-docs-in-prompt");
  if (body) {
    body.hidden = false;
    body.textContent = "Loading…";
  }
  if (editor) editor.hidden = true;
  if (toolbar) toolbar.hidden = true;
  try {
    const data = await api(`/api/ai/docs/${encodeURIComponent(docId)}${aiDocsProjectQuery()}`);
    const doc = data.doc;
    updateAiDocsBudget(data.budget);
    if (title) title.textContent = doc.title;
    const editable = Boolean(doc.editable || doc.source === "user");
    if (meta) {
      meta.textContent = editable
        ? `${doc.path}${doc.in_prompt ? " · in AI prompt (capped)" : " · not in prompt"}`
        : `${doc.path}${doc.in_prompt ? " · loaded into AI when a key is set" : " · reference (not packed)"}`;
    }
    if (editable) {
      if (body) body.hidden = true;
      if (editor) {
        editor.hidden = false;
        editor.value = doc.content || "";
      }
      if (toolbar) toolbar.hidden = false;
      if (inPrompt) inPrompt.checked = Boolean(doc.in_prompt);
    } else {
      if (editor) editor.hidden = true;
      if (body) {
        body.hidden = false;
        body.textContent = doc.content || "(empty)";
      }
      if (toolbar) toolbar.hidden = true;
    }
  } catch {
    if (body) {
      body.hidden = false;
      body.textContent = "Failed to load document.";
    }
  }
}

async function createUserAiDoc() {
  const title = window.prompt("Title for your markdown doc", "My notes");
  if (title == null) return;
  try {
    const data = await api("/api/ai/docs/user", {
      method: "POST",
      body: JSON.stringify({
        title: title.trim() || "My notes",
        content: `# ${title.trim() || "My notes"}\n\n`,
        in_prompt: false,
      }),
    });
    const list = await api("/api/ai/docs");
    aiDocsCache = list.docs || [];
    updateAiDocsBudget(data.budget || list.budget);
    renderAiDocsList();
    if (data.doc?.id) await selectAiDoc(data.doc.id);
    setStatus("Created My doc");
  } catch (e) {
    setStatus(`Create doc failed: ${e.message}`);
  }
}

async function saveUserAiDoc() {
  if (!aiDocsSelectedId) return;
  const meta = (aiDocsCache || []).find((d) => d.id === aiDocsSelectedId);
  if (!meta || meta.source !== "user") return;
  const editor = $("#ai-docs-doc-editor");
  const inPrompt = $("#ai-docs-in-prompt");
  try {
    const data = await api(`/api/ai/docs/user/${encodeURIComponent(aiDocsSelectedId)}`, {
      method: "PUT",
      body: JSON.stringify({
        content: editor?.value ?? "",
        in_prompt: Boolean(inPrompt?.checked),
        title: meta.title,
      }),
    });
    const list = await api("/api/ai/docs");
    aiDocsCache = list.docs || [];
    updateAiDocsBudget(data.budget || list.budget);
    renderAiDocsList(aiDocsSelectedId);
    if (data.doc && $("#ai-docs-doc-meta")) {
      $("#ai-docs-doc-meta").textContent =
        `${data.doc.path}${data.doc.in_prompt ? " · in AI prompt (capped)" : " · not in prompt"}`;
    }
    setStatus("Saved My doc");
  } catch (e) {
    setStatus(`Save failed: ${e.message}`);
  }
}

async function deleteUserAiDoc() {
  if (!aiDocsSelectedId) return;
  const meta = (aiDocsCache || []).find((d) => d.id === aiDocsSelectedId);
  if (!meta || meta.source !== "user") return;
  if (!window.confirm(`Delete “${meta.title}”?`)) return;
  try {
    await api(`/api/ai/docs/user/${encodeURIComponent(aiDocsSelectedId)}`, { method: "DELETE" });
    const list = await api("/api/ai/docs");
    aiDocsCache = list.docs || [];
    updateAiDocsBudget(list.budget);
    aiDocsSelectedId = null;
    renderAiDocsList();
    const title = $("#ai-docs-doc-title");
    const body = $("#ai-docs-doc-body");
    const editor = $("#ai-docs-doc-editor");
    const toolbar = $("#ai-docs-edit-toolbar");
    if (title) title.textContent = "Select a document";
    if (editor) {
      editor.hidden = true;
      editor.value = "";
    }
    if (toolbar) toolbar.hidden = true;
    if (body) {
      body.hidden = false;
      body.textContent = "Choose a .md file from the list.";
    }
    setStatus("Deleted My doc");
  } catch (e) {
    setStatus(`Delete failed: ${e.message}`);
  }
}

function renderContextChips(el, items) {
  if (el?.id === "context-chips") {
    renderContextList(items);
    return;
  }
  if (!el) return;
  el.innerHTML = (items || [])
    .map(
      (c) =>
        `<span class="ctx-chip" title="${escapeHtml(c.value)}">${escapeHtml(c.label || c.kind)}</span>`
    )
    .join("");
}

function renderClientWorkspace() {
  syncAvatarSections();
  renderBuildWorkspace();
}

async function renderConsultantWorkspace() {
  const panel = $("#build-consultant-panel");
  if (!panel || state.avatar !== "consultant") return;
  if (!activeProject || !hasScope()) {
    panel.hidden = true;
    return;
  }
  panel.hidden = false;
  renderChat($("#consultant-client-chat"), activeProject.chat_messages || []);
  renderContextChips($("#consultant-context"), activeProject.context_items || []);
  const joined = (activeProject.hitl_consultants || []).some((c) => c.id === "local-hitl-consultant");
  $("#btn-join-hitl").hidden = joined;
  $("#consultant-deliver").hidden = !joined;
  applyAiMode();
  await loadHuntSessionForProject();
  renderHuntIssueList();
}

/** QA Hunter hunt evidence — screen/audio capture + structured findings (v1, browser APIs). */
const huntSession = {
  issues: [],
  blobs: [],
  evidenceIds: [],
  timerId: null,
  startedAt: null,
  mediaRecorder: null,
  recordStream: null,
};

const HUNT_IDB_NAME = "qoa_hunt_blobs";
const HUNT_IDB_STORE = "blobs";

function huntIdbOpen() {
  return new Promise((resolve, reject) => {
    if (!window.indexedDB) {
      reject(new Error("IndexedDB unavailable"));
      return;
    }
    const req = indexedDB.open(HUNT_IDB_NAME, 1);
    req.onupgradeneeded = () => {
      if (!req.result.objectStoreNames.contains(HUNT_IDB_STORE)) {
        req.result.createObjectStore(HUNT_IDB_STORE);
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

async function huntIdbSaveBlobs(projectId) {
  if (!projectId || !huntSession.blobs.length) return;
  try {
    const db = await huntIdbOpen();
    const tx = db.transaction(HUNT_IDB_STORE, "readwrite");
    const store = tx.objectStore(HUNT_IDB_STORE);
    const keys = await new Promise((res, rej) => {
      const req = store.getAllKeys();
      req.onsuccess = () => res(req.result || []);
      req.onerror = () => rej(req.error);
    });
    const prefix = `${projectId}:`;
    for (const key of keys) {
      if (String(key).startsWith(prefix)) store.delete(key);
    }
    for (const b of huntSession.blobs) {
      store.put({ name: b.name, type: b.type, kind: b.kind, blob: b.blob }, `${projectId}:${b.name}`);
    }
    await new Promise((res, rej) => {
      tx.oncomplete = res;
      tx.onerror = () => rej(tx.error);
    });
    db.close();
  } catch {
    /* storage quota or private mode */
  }
}

async function huntIdbLoadBlobs(projectId) {
  if (!projectId || !window.indexedDB) return [];
  try {
    const db = await huntIdbOpen();
    const tx = db.transaction(HUNT_IDB_STORE, "readonly");
    const store = tx.objectStore(HUNT_IDB_STORE);
    const keys = await new Promise((res, rej) => {
      const req = store.getAllKeys();
      req.onsuccess = () => res(req.result || []);
      req.onerror = () => rej(req.error);
    });
    const prefix = `${projectId}:`;
    const projectKeys = keys.filter((k) => String(k).startsWith(prefix));
    const rows = await Promise.all(
      projectKeys.map(
        (key) =>
          new Promise((res, rej) => {
            const req = store.get(key);
            req.onsuccess = () => res(req.result);
            req.onerror = () => rej(req.error);
          })
      )
    );
    db.close();
    return rows
      .filter((row) => row?.name && row?.blob)
      .map((row) => ({ name: row.name, type: row.type, kind: row.kind, blob: row.blob }));
  } catch {
    return [];
  }
}

async function huntIdbClear(projectId) {
  if (!projectId || !window.indexedDB) return;
  try {
    const db = await huntIdbOpen();
    const tx = db.transaction(HUNT_IDB_STORE, "readwrite");
    const store = tx.objectStore(HUNT_IDB_STORE);
    const all = await new Promise((res, rej) => {
      const req = store.getAllKeys();
      req.onsuccess = () => res(req.result || []);
      req.onerror = () => rej(req.error);
    });
    for (const key of all) {
      if (String(key).startsWith(`${projectId}:`)) store.delete(key);
    }
    await new Promise((res, rej) => {
      tx.oncomplete = res;
      tx.onerror = () => rej(tx.error);
    });
    db.close();
  } catch {
    /* ignore */
  }
}

function huntStorageKey() {
  return state.projectId ? `qoa_hunt_${state.projectId}` : null;
}

function persistHuntSession() {
  const key = huntStorageKey();
  if (!key) return;
  const payload = {
    issues: huntSession.issues,
    blobMeta: huntSession.blobs.map((b) => ({ name: b.name, type: b.type, kind: b.kind, size: b.blob.size })),
  };
  try {
    sessionStorage.setItem(key, JSON.stringify(payload));
  } catch {
    /* quota */
  }
  void huntIdbSaveBlobs(state.projectId);
}

async function loadHuntSessionForProject() {
  huntSession.issues = [];
  huntSession.blobs = [];
  huntSession.evidenceIds = [];
  stopHuntTimer();
  const preview = $("#hunt-preview");
  if (preview) {
    preview.hidden = true;
    preview.removeAttribute("src");
  }
  const key = huntStorageKey();
  if (!key) return;
  try {
    const raw = sessionStorage.getItem(key);
    if (raw) {
      const data = JSON.parse(raw);
      huntSession.issues = Array.isArray(data.issues) ? data.issues : [];
    }
  } catch {
    huntSession.issues = [];
  }
  if (state.projectId) {
    const blobs = await huntIdbLoadBlobs(state.projectId);
    if (blobs.length) {
      huntSession.blobs = blobs;
      const screen = blobs.find((b) => b.kind === "screen");
      if (screen && preview) {
        preview.src = URL.createObjectURL(screen.blob);
        preview.hidden = false;
      }
    }
  }
  const blobNote = huntSession.blobs.length ? ` · ${huntSession.blobs.length} artifact(s) restored` : "";
  setHuntRecStatus(
    huntSession.issues.length
      ? `${huntSession.issues.length} finding(s) in this hunt log${blobNote}`
      : huntSession.blobs.length
        ? `${huntSession.blobs.length} recording(s) restored — add findings or submit`
        : "Ready — use + Add evidence or log findings"
  );
  await renderEvidenceLibraries();
}

function setHuntRecStatus(msg) {
  const el = $("#hunt-rec-status");
  if (el) el.textContent = msg || "";
}

function formatHuntTimer(ms) {
  const s = Math.floor(ms / 1000);
  const m = Math.floor(s / 60);
  return `${String(m).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
}

function startHuntTimer() {
  stopHuntTimer();
  huntSession.startedAt = Date.now();
  const timerEl = $("#hunt-timer");
  if (timerEl) timerEl.hidden = false;
  huntSession.timerId = setInterval(() => {
    if (timerEl && huntSession.startedAt) {
      timerEl.textContent = formatHuntTimer(Date.now() - huntSession.startedAt);
    }
  }, 500);
}

function stopHuntTimer() {
  if (huntSession.timerId) clearInterval(huntSession.timerId);
  huntSession.timerId = null;
  huntSession.startedAt = null;
  const timerEl = $("#hunt-timer");
  if (timerEl) timerEl.hidden = true;
}

function stopHuntStreams() {
  if (huntSession.recordStream) {
    huntSession.recordStream.getTracks().forEach((t) => t.stop());
    huntSession.recordStream = null;
  }
}

async function startHuntRecording() {
  if (huntSession.mediaRecorder?.state === "recording") return;
  if (!navigator.mediaDevices?.getDisplayMedia) {
    alert("Screen recording is not supported in this browser. Log findings manually or upload screenshots.");
    return;
  }
  try {
    const display = await navigator.mediaDevices.getDisplayMedia({ video: true, audio: true });
    let mic = null;
    try {
      mic = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch {
      /* optional narration */
    }
    const tracks = [...display.getVideoTracks(), ...display.getAudioTracks()];
    if (mic) tracks.push(...mic.getAudioTracks());
    const stream = new MediaStream(tracks);
    huntSession.recordStream = stream;
    const mime = MediaRecorder.isTypeSupported("video/webm;codecs=vp9")
      ? "video/webm;codecs=vp9"
      : "video/webm";
    const recorder = new MediaRecorder(stream, { mimeType: mime });
    const chunks = [];
    recorder.ondataavailable = (e) => {
      if (e.data?.size) chunks.push(e.data);
    };
    recorder.onstop = async () => {
      const blob = new Blob(chunks, { type: mime });
      const stamp = new Date().toISOString().replace(/[:.]/g, "-");
      const name = `hunt-screen-${stamp}.webm`;
      huntSession.blobs.push({ blob, name, type: mime, kind: "screen" });
      const preview = $("#hunt-preview");
      if (preview) {
        preview.src = URL.createObjectURL(blob);
        preview.hidden = false;
      }
      stopHuntStreams();
      setHuntRecStatus(`Screen recording saved (${Math.round(blob.size / 1024)} KB) — uploading…`);
      persistHuntSession();
      const path = await uploadEvidenceBlob(blob, name);
      if (path) {
        await registerEvidence("screen_recording", { path, title: "Screen recording" });
        setHuntRecStatus(`Screen recording added to evidence library (${Math.round(blob.size / 1024)} KB)`);
      }
    };
    display.getVideoTracks()[0]?.addEventListener("ended", () => stopHuntRecording());
    recorder.start(1000);
    huntSession.mediaRecorder = recorder;
    $("#btn-hunt-stop").hidden = false;
    startHuntTimer();
    setHuntRecStatus("Recording — share the app window or tab you are testing");
    setStatus("Hunt recording started");
  } catch (e) {
    setHuntRecStatus("Recording cancelled or blocked");
    stopHuntStreams();
  }
}

function stopHuntRecording() {
  if (huntSession.mediaRecorder?.state === "recording") {
    huntSession.mediaRecorder.stop();
  }
  huntSession.mediaRecorder = null;
  stopHuntTimer();
  $("#btn-hunt-stop").hidden = true;
  setStatus("Hunt recording stopped");
}

async function startHuntAudioNote() {
  if (!navigator.mediaDevices?.getUserMedia) {
    alert("Audio notes are not supported in this browser.");
    return;
  }
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const mime = MediaRecorder.isTypeSupported("audio/webm") ? "audio/webm" : "audio/mp4";
    const recorder = new MediaRecorder(stream, { mimeType: mime });
    const chunks = [];
    recorder.ondataavailable = (e) => {
      if (e.data?.size) chunks.push(e.data);
    };
    recorder.onstop = async () => {
      stream.getTracks().forEach((t) => t.stop());
      const blob = new Blob(chunks, { type: mime });
      const stamp = new Date().toISOString().replace(/[:.]/g, "-");
      const name = `hunt-audio-${stamp}.webm`;
      huntSession.blobs.push({ blob, name, type: mime, kind: "audio" });
      setHuntRecStatus(`Audio note saved (${Math.round(blob.size / 1024)} KB) — uploading…`);
      persistHuntSession();
      const path = await uploadEvidenceBlob(blob, name);
      if (path) {
        await registerEvidence("audio_note", { path, title: "Audio note" });
        setHuntRecStatus(`Audio note added to evidence library (${Math.round(blob.size / 1024)} KB)`);
      }
    };
    setHuntRecStatus("Recording audio… (auto-stops after 60s)");
    recorder.start();
    setTimeout(() => {
      if (recorder.state === "recording") recorder.stop();
    }, 60000);
  } catch {
    setHuntRecStatus("Microphone access denied");
  }
}

function addHuntIssueFromForm() {
  const title = $("#hunt-issue-title")?.value?.trim();
  if (!title) {
    alert("Add a title for this finding.");
    return;
  }
  const issue = {
    id: crypto.randomUUID?.() || String(Date.now()),
    title,
    type: $("#hunt-issue-type")?.value || "bug",
    severity: $("#hunt-issue-severity")?.value || "major",
    repro: $("#hunt-issue-repro")?.value?.trim() || "",
    at: new Date().toISOString(),
  };
  huntSession.issues.push(issue);
  if ($("#hunt-issue-title")) $("#hunt-issue-title").value = "";
  if ($("#hunt-issue-repro")) $("#hunt-issue-repro").value = "";
  persistHuntSession();
  renderHuntIssueList();
  setHuntRecStatus(`${huntSession.issues.length} finding(s) in hunt log`);
}

function renderHuntIssueList() {
  const list = $("#hunt-issue-list");
  if (!list) return;
  if (!huntSession.issues.length) {
    list.innerHTML = '<li class="empty-hint">No findings yet — record, screenshot, or log issues above.</li>';
    return;
  }
  list.innerHTML = huntSession.issues
    .map(
      (i) =>
        `<li class="hunt-issue-item">` +
        `<div class="hunt-issue-item-head">` +
        `<strong>${escapeHtml(i.title)}</strong>` +
        `<span class="hunt-issue-badge">${escapeHtml(i.type)}</span>` +
        `<span class="hunt-issue-badge sev-${escapeHtml(i.severity)}">${escapeHtml(i.severity)}</span>` +
        `</div>` +
        (i.repro ? `<pre class="hunt-repro">${escapeHtml(i.repro)}</pre>` : "") +
        `</li>`
    )
    .join("");
}

function attachHuntScreenshot(file) {
  if (!file?.type?.startsWith("image/")) return;
  const stamp = new Date().toISOString().replace(/[:.]/g, "-");
  const ext = file.name.split(".").pop() || "png";
  huntSession.blobs.push({
    blob: file,
    name: `hunt-screenshot-${stamp}.${ext}`,
    type: file.type,
    kind: "screenshot",
  });
  setHuntRecStatus(`Screenshot attached: ${file.name}`);
  persistHuntSession();
}

/** Add evidence — one menu → screen/audio/screenshot/file/URL/note, all land in the project evidence library. */
async function uploadEvidenceBlob(blob, filename) {
  if (!state.projectId) return null;
  try {
    const fd = new FormData();
    fd.append("file", blob, filename);
    const res = await fetch(`/api/projects/${state.projectId}/documents`, { method: "POST", body: fd });
    if (!res.ok) return null;
    const data = await res.json();
    return data.document?.path || null;
  } catch {
    return null;
  }
}

async function registerEvidence(kind, opts = {}) {
  if (!state.projectId) return null;
  try {
    const author = teamAuthorMeta().author;
    const { item } = await api(`/api/projects/${state.projectId}/evidence`, {
      method: "POST",
      body: JSON.stringify({ kind, author, ...opts }),
    });
    if (item?.id) huntSession.evidenceIds.push(item.id);
    await renderEvidenceLibraries();
    return item;
  } catch (e) {
    setStatus(`Evidence save failed: ${e.message}`);
    return null;
  }
}

function closeEvidenceMenu() {
  const menu = $("#evidence-menu");
  if (menu) menu.hidden = true;
  $("#btn-add-evidence")?.setAttribute("aria-expanded", "false");
}

function openEvidenceAction(kind) {
  closeEvidenceMenu();
  $("#evidence-url-form")?.setAttribute("hidden", "");
  $("#evidence-note-form")?.setAttribute("hidden", "");
  if (kind === "screen") startHuntRecording();
  else if (kind === "audio") startHuntAudioNote();
  else if (kind === "screenshot") $("#hunt-screenshot-file")?.click();
  else if (kind === "file") $("#hunt-file-upload")?.click();
  else if (kind === "url") $("#evidence-url-form")?.removeAttribute("hidden");
  else if (kind === "note") $("#evidence-note-form")?.removeAttribute("hidden");
}

function bindEvidenceMenu() {
  if (bindEvidenceMenu._bound) return;
  bindEvidenceMenu._bound = true;
  const btn = $("#btn-add-evidence");
  const menu = $("#evidence-menu");
  btn?.addEventListener("click", (e) => {
    e.stopPropagation();
    const willOpen = menu?.hidden;
    if (menu) menu.hidden = !willOpen;
    btn.setAttribute("aria-expanded", willOpen ? "true" : "false");
  });
  menu?.addEventListener("click", (e) => {
    const item = e.target.closest("[data-eve]");
    if (item) openEvidenceAction(item.dataset.eve);
  });
  document.addEventListener("click", (e) => {
    if (menu && !menu.hidden && !menu.contains(e.target) && e.target !== btn) closeEvidenceMenu();
  });
  $("#hunt-screenshot-file")?.addEventListener("change", async (e) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    attachHuntScreenshot(file);
    setHuntRecStatus(`Uploading screenshot ${file.name}…`);
    const path = await uploadEvidenceBlob(file, file.name);
    if (path) {
      await registerEvidence("screenshot", { path, title: file.name });
      setHuntRecStatus(`Screenshot added to evidence library: ${file.name}`);
    }
  });
  $("#hunt-file-upload")?.addEventListener("change", async (e) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    setHuntRecStatus(`Uploading ${file.name}…`);
    const path = await uploadEvidenceBlob(file, file.name);
    if (path) {
      const kind = file.type?.startsWith("video/") ? "video" : "document";
      await registerEvidence(kind, { path, title: file.name });
      setHuntRecStatus(`${file.name} added to evidence library`);
    } else {
      setHuntRecStatus(`Upload failed for ${file.name}`);
    }
  });
  $("#evidence-url-save")?.addEventListener("click", async () => {
    const url = $("#evidence-url-input")?.value?.trim();
    if (!url) return;
    const title = $("#evidence-url-title")?.value?.trim() || url;
    const item = await registerEvidence("url", { url, title });
    if (item) {
      if ($("#evidence-url-input")) $("#evidence-url-input").value = "";
      if ($("#evidence-url-title")) $("#evidence-url-title").value = "";
      $("#evidence-url-form").hidden = true;
      setHuntRecStatus(`Link added to evidence library: ${title}`);
    }
  });
  $("#evidence-url-cancel")?.addEventListener("click", () => {
    if ($("#evidence-url-form")) $("#evidence-url-form").hidden = true;
  });
  $("#evidence-note-save")?.addEventListener("click", async () => {
    const note = $("#evidence-note-input")?.value?.trim();
    if (!note) return;
    const item = await registerEvidence("note", { note, title: note.slice(0, 60) });
    if (item) {
      if ($("#evidence-note-input")) $("#evidence-note-input").value = "";
      $("#evidence-note-form").hidden = true;
      setHuntRecStatus("Text note added to evidence library");
    }
  });
  $("#evidence-note-cancel")?.addEventListener("click", () => {
    if ($("#evidence-note-form")) $("#evidence-note-form").hidden = true;
  });
  $("#hunt-evidence-search")?.addEventListener("input", () => renderEvidenceLibraries());
  $("#brahl-team-lib-search")?.addEventListener("input", () => renderEvidenceLibraries());
}

const EVIDENCE_KIND_LABELS = {
  screen_recording: "Screen recording",
  audio_note: "Audio note",
  screenshot: "Screenshot",
  video: "Video",
  file: "File",
  document: "Document",
  url: "Link",
  note: "Note",
};

function evidenceItemHtml(item) {
  const kindLabel = EVIDENCE_KIND_LABELS[item.kind] || item.kind || "Evidence";
  const when = item.created_at ? new Date(item.created_at).toLocaleString() : "";
  let body = "";
  if (item.url) {
    body = `<a href="${escapeHtml(item.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(item.title || item.url)}</a>`;
  } else if (item.path && state.projectId) {
    const name = PathBasename(item.path);
    const href = `/api/projects/${encodeURIComponent(state.projectId)}/uploads/${encodeURIComponent(name)}`;
    body = `<a href="${escapeHtml(href)}" target="_blank" rel="noopener noreferrer">${escapeHtml(item.title || name)}</a>`;
  } else {
    body = escapeHtml(item.title || item.note || "Evidence");
  }
  return (
    `<li class="evidence-item" data-evidence-id="${escapeHtml(item.id || "")}">` +
    `<span class="evidence-kind">${escapeHtml(kindLabel)}</span>` +
    `<span>${body}</span>` +
    `<span class="evidence-meta">${escapeHtml(item.author || "")}${when ? " · " + escapeHtml(when) : ""}</span>` +
    `</li>`
  );
}

async function fetchEvidenceLibrary(query) {
  if (!state.projectId) return [];
  try {
    const q = query ? `?q=${encodeURIComponent(query)}` : "";
    const { items } = await api(`/api/projects/${state.projectId}/evidence${q}`);
    return items || [];
  } catch {
    return [];
  }
}

async function renderEvidenceLibraries() {
  if (!state.projectId) return;
  const huntList = $("#hunt-evidence-list");
  const teamList = $("#brahl-team-library");
  if (!huntList && !teamList) return;
  const query = ($("#hunt-evidence-search")?.value || $("#brahl-team-lib-search")?.value || "").trim();
  const items = await fetchEvidenceLibrary(query);
  const html = items.length
    ? items.map(evidenceItemHtml).join("")
    : '<li class="empty-hint">No evidence yet — use + Add evidence above or link a source on BRAHL.</li>';
  if (huntList) huntList.innerHTML = html;
  if (teamList) teamList.innerHTML = html || renderBrahlTeamLibraryFallbackHtml();
}

function renderBrahlTeamLibraryFallbackHtml() {
  return '<li class="empty-hint">No evidence yet — add links or upload docs the team can reference.</li>';
}

function buildHuntReportMarkdown() {
  const lines = [
    "# QA Hunter — Hunt evidence report",
    "",
    `Project: ${activeProject?.name || state.suiteName || "—"}`,
    `Recorded: ${new Date().toISOString()}`,
    "",
    "## Findings",
    "",
  ];
  if (!huntSession.issues.length) {
    lines.push("_No structured findings — see attached recordings/screenshots._", "");
  } else {
    huntSession.issues.forEach((i, n) => {
      lines.push(`### ${n + 1}. ${i.title}`, "", `- **Type:** ${i.type}`, `- **Severity:** ${i.severity}`, "");
      if (i.repro) lines.push("**Steps to reproduce:**", "", i.repro, "");
    });
  }
  lines.push("## Artifacts", "");
  huntSession.blobs.forEach((b) => lines.push(`- ${b.kind}: \`${b.name}\` (${Math.round(b.blob.size / 1024)} KB)`));
  return lines.join("\n");
}

async function uploadHuntEvidence() {
  if (!state.projectId) return null;
  if (!huntSession.issues.length && !huntSession.blobs.length) return null;
  const stamp = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 15);
  const md = buildHuntReportMarkdown();
  const json = JSON.stringify({ issues: huntSession.issues, artifacts: huntSession.blobs.map((b) => b.name) }, null, 2);
  const uploads = [
    { name: `hunt-report-${stamp}.md`, blob: new Blob([md], { type: "text/markdown" }) },
    { name: `hunt-report-${stamp}.json`, blob: new Blob([json], { type: "application/json" }) },
    ...huntSession.blobs.map((b) => ({ name: b.name, blob: b.blob })),
  ];
  const artifactPaths = [];
  let huntReportPath = null;
  for (const u of uploads) {
    const fd = new FormData();
    fd.append("file", u.blob, u.name);
    const res = await fetch(`/api/projects/${state.projectId}/documents`, { method: "POST", body: fd });
    if (!res.ok) continue;
    const data = await res.json();
    const path = data.document?.path;
    if (path) {
      artifactPaths.push(path);
      if (u.name.startsWith("hunt-report-") && u.name.endsWith(".md")) huntReportPath = path;
    }
  }
  const critical = huntSession.issues.filter((i) => i.severity === "critical").length;
  if (critical && $("#hitl-critical")) {
    const cur = parseInt($("#hitl-critical").value, 10) || 0;
    if (cur < critical) $("#hitl-critical").value = String(critical);
  }
  return { huntReportPath, artifactPaths };
}

async function clearHuntSessionAfterSubmit() {
  huntSession.issues = [];
  huntSession.blobs = [];
  huntSession.evidenceIds = [];
  const key = huntStorageKey();
  if (key) sessionStorage.removeItem(key);
  if (state.projectId) await huntIdbClear(state.projectId);
  const preview = $("#hunt-preview");
  if (preview) {
    preview.hidden = true;
    preview.removeAttribute("src");
  }
  renderHuntIssueList();
  setHuntRecStatus("Hunt evidence submitted — ready for next session");
}

function goToBuildPanel() {
  showPhase("build");
}

function renderHitlRoster(project) {
  const el = $("#hitl-roster");
  const team = project.hitl_consultants || [];
  if (!team.length) {
    el.innerHTML =
      '<p class="empty-hint">No QA Hunters joined yet — click <strong>Invite QA Hunter</strong> above.</p>';
    return;
  }
  el.innerHTML =
    "<h4>QA Hunter team</h4>" +
    team
      .map((c) => {
        const d = c.deliverables || {};
        return `<div class="hitl-member">${escapeHtml(c.name)} — ${d.critical_issues || 0} critical, ${d.reports_submitted || 0} reports, ${d.time_hours || 0}h</div>`;
      })
      .join("");
}

async function createNewProject() {
  openAddProjectModal();
}

async function toggleAiMode() {
  if (!state.projectId) return;
  if (state.profile?.aiLocked) {
    setStatus("AI is disabled for this test profile (non-technical user)");
    applyAiMode();
    return;
  }
  const ai_enabled = $("#ai-toggle").checked;
  if (activeProject) activeProject.ai_enabled = ai_enabled;
  applyAiMode();
  try {
    const { project } = await api(`/api/projects/${state.projectId}`, {
      method: "PATCH",
      body: JSON.stringify({ ai_enabled }),
    });
    activeProject = project;
    applyAiMode();
    loadBuildAiStatus();
    setStatus(ai_enabled ? "AI assistant enabled" : "AI off — manual Build mode");
    renderClientWorkspace();
  } catch (err) {
    if (activeProject) activeProject.ai_enabled = !ai_enabled;
    $("#ai-toggle").checked = !ai_enabled;
    applyAiMode();
    setStatus(`AI toggle failed: ${err.message || err}`);
  }
}

async function saveManualPurpose() {
  if (!state.projectId) return;
  const purpose = $("#manual-purpose").value.trim();
  const { project } = await api(`/api/projects/${state.projectId}`, {
    method: "PATCH",
    body: JSON.stringify({ purpose }),
  });
  activeProject = project;
  syncProjectToUI();
  setStatus("Purpose saved");
}

async function sendChat(ev) {
  ev.preventDefault();
  const input = $("#chat-input");
  const sendBtn = $("#chat-send-btn");
  const text = input.value.trim();
  if (!text || !state.projectId) return;
  input.value = "";
  input.placeholder = "Describe what you want BRAHL to test…";
  if (sendBtn) sendBtn.disabled = true;
  try {
    // When AI is off, still accept a Build note (comment) so chat is never dead
    if (!isAiOn()) {
      const data = await api(`/api/projects/${state.projectId}/chat`, {
        method: "POST",
        body: JSON.stringify({ text, note_only: true }),
      });
      activeProject = data.project;
      renderChat($("#chat-thread"), activeProject.chat_messages || []);
      setStatus("Note saved (AI off — turn AI on for BRAHL replies)");
      return;
    }
    const data = await api(`/api/projects/${state.projectId}/chat`, {
      method: "POST",
      body: JSON.stringify({ text }),
    });
    activeProject = data.project;
    renderChat($("#chat-thread"), activeProject.chat_messages || []);
    renderBuildChecklist();
    syncProjectToUI();
    setStatus("BRAHL AI replied");
  } catch (err) {
    input.value = text;
    setStatus(`Chat failed: ${err.message}`);
  } finally {
    if (sendBtn) sendBtn.disabled = false;
  }
}

async function saveContextItem() {
  const kind = $("#ctx-kind").value;
  const label = $("#ctx-label").value.trim();
  const value = $("#ctx-value").value.trim();
  if (!value || !state.projectId) return;
  const data = await api(`/api/projects/${state.projectId}/context`, {
    method: "POST",
    body: JSON.stringify({ kind, label: label || kind, value }),
  });
  activeProject = data.project;
  $("#ctx-label").value = "";
  $("#ctx-value").value = "";
  $("#add-context-panel").hidden = true;
  renderContextList(activeProject.context_items || []);
  syncProjectToUI();
  setStatus(`Added ${label || kind} to project context`);
  if (kind === "url") {
    await api(`/api/projects/${state.projectId}`, {
      method: "PATCH",
      body: JSON.stringify({ app_url: value }),
    });
    await refreshActiveProject();
  }
}

function openContextPanel(kind, label, value) {
  $("#add-context-panel").hidden = false;
  if (kind) $("#ctx-kind").value = kind;
  if (label) $("#ctx-label").value = label;
  if (value) $("#ctx-value").value = value;
  $("#ctx-value")?.focus();
}

async function saveBudget() {
  if (!state.projectId) return;
  const budget_usd = parseFloat($("#budget-usd").value) || 0;
  const automation_pct = parseInt($("#budget-split").value, 10);
  if (budget_usd > 0 && budget_usd < 50) {
    setStatus("Creator QA wallet minimum is $50");
    return;
  }
  const { project } = await api(`/api/projects/${state.projectId}`, {
    method: "PATCH",
    body: JSON.stringify({
      budget_usd,
      budget_split: { automation_pct, human_pct: 100 - automation_pct },
    }),
  });
  activeProject = project;
  if (isAiOn()) {
    try {
      const data = await api(`/api/projects/${state.projectId}/chat`, {
        method: "POST",
        body: JSON.stringify({
          text: `Updated budget to $${budget_usd} (${automation_pct}% automation / ${100 - automation_pct}% QA Hunter)`,
        }),
      });
      activeProject = data.project;
      renderChat($("#chat-thread"), activeProject.chat_messages || []);
    } catch {
      /* budget saved even if chat ack fails */
    }
  }
  await refreshActiveProject();
  renderBuildCostTeaser();
  setStatus(`Budget $${budget_usd} saved`);
}

async function joinHitl() {
  if (!state.projectId) return;
  const data = await api(`/api/projects/${state.projectId}/join-hitl`, { method: "POST" });
  activeProject = data.project;
  await refreshActiveProject();
  renderConsultantWorkspace();
  setStatus("Joined as QA Hunter");
}

async function submitHitlReport() {
  if (!state.projectId) return;
  let runName = selectedRun;
  if (!runName?.trim()) {
    runName = await pickRunViaModal();
    if (!runName?.trim()) return;
  }
  const huntUpload = await uploadHuntEvidence();
  const data = await api(`/api/projects/${state.projectId}/submit-hitl-report`, {
    method: "POST",
    body: JSON.stringify({
      run_name: runName.trim(),
      report_path: huntUpload?.huntReportPath || `z/${runName.trim()}/brahl_report.md`,
      critical_issues: parseInt($("#hitl-critical").value, 10) || 0,
      time_hours: parseFloat($("#hitl-hours").value) || 0,
      features_found: parseInt($("#hitl-features").value, 10) || 0,
      hunt_report_path: huntUpload?.huntReportPath || null,
      artifact_paths: huntUpload?.artifactPaths?.length ? huntUpload.artifactPaths : null,
      evidence_ids: huntSession.evidenceIds.length ? huntSession.evidenceIds : null,
    }),
  });
  if (huntUpload) await clearHuntSessionAfterSubmit();
  if (data.report?.id) selectedBrahlReportId = data.report.id;
  const file = $("#hitl-ypad").files[0];
  if (file) {
    const fd = new FormData();
    fd.append("file", file);
    await fetch(`/api/projects/${state.projectId}/documents`, { method: "POST", body: fd });
  }
  await refreshActiveProject();
  renderConsultantWorkspace();
  if ($("#panel-brahl")?.classList.contains("active")) await loadBrahlPanel();
  setStatus("QA Hunter report submitted");
}

async function runAnalyzeAi() {
  if (!state.projectId || !selectedRun || !isAiOn()) return;
  const el = $("#analyze-ai-result");
  if (el) {
    el.hidden = false;
    el.classList.add("ai-loading");
    el.textContent = "Analyzing z/ failures (BRAHL T1/T2/T3/A1 classification)…";
  }
  try {
    const data = await api(
      `/api/projects/${state.projectId}/runs/${encodeURIComponent(selectedRun)}/analyze-ai`,
      { method: "POST", body: "{}" }
    );
    lastAnalyzeMarkdown = data.markdown || "";
    renderAiMarkdown(el, lastAnalyzeMarkdown);
    if (data.fallback) setStatus("Analyze: manual RCA (set OPENAI_API_KEY in f/.env for AI)");
    else setStatus("Analyze: AI root-cause complete");
  } catch (e) {
    renderAiMarkdown(el, `Error: ${e.message}`);
  }
}

async function runHealAi() {
  if (!state.projectId || !selectedRun || !isAiOn()) return;
  const el = $("#heal-ai-result");
  const applyBtn = $("#btn-heal-apply");
  const applyHint = $("#heal-apply-hint");
  lastHealPatches = [];
  if (applyBtn) applyBtn.hidden = true;
  if (applyHint) {
    applyHint.hidden = true;
    applyHint.textContent = "";
  }
  if (el) {
    el.hidden = false;
    el.classList.add("ai-loading");
    el.textContent = "Generating yPAD heal suggestions per BRAHL.md…";
  }
  try {
    const data = await api(
      `/api/projects/${state.projectId}/runs/${encodeURIComponent(selectedRun)}/heal-suggest`,
      {
        method: "POST",
        body: JSON.stringify({ rca_markdown: lastAnalyzeMarkdown }),
      }
    );
    lastHealMarkdown = data.markdown || "";
    lastHealPatches = Array.isArray(data.patches) ? data.patches : [];
    renderAiMarkdown(el, lastHealMarkdown);
    if (lastHealPatches.length && applyBtn) {
      applyBtn.hidden = false;
      applyBtn.textContent = `Apply to yPAD (${lastHealPatches.length})`;
      if (applyHint) {
        applyHint.hidden = false;
        applyHint.textContent =
          `${lastHealPatches.length} structured patch(es) ready — review the heal plan, then Apply to write CSV changes.`;
      }
      setStatus(`Heal: ${lastHealPatches.length} patch(es) ready to Apply`);
    } else {
      setStatus(
        data.ai
          ? "Heal: AI suggestions ready — no auto-apply patches parsed"
          : "Heal: manual guide (no API key)"
      );
    }
  } catch (e) {
    renderAiMarkdown(el, `Error: ${e.message}`);
  }
}

async function applyHealPatches() {
  if (!state.projectId || !lastHealPatches.length) {
    alert("Run AI auto-heal first so there are patches to apply.");
    return;
  }
  const logEl = $("#heal-log");
  const applyHint = $("#heal-apply-hint");
  const applyBtn = $("#btn-heal-apply");
  const suite = suiteConfigPath();
  if (applyBtn) applyBtn.disabled = true;
  try {
    const preview = await api(`/api/projects/${state.projectId}/heal-apply`, {
      method: "POST",
      body: JSON.stringify({
        patches: lastHealPatches,
        suite_config: suite,
        dry_run: true,
      }),
    });
    const n = preview.applied || 0;
    if (!n) {
      const detail = [
        `Dry-run: nothing to apply for suite \`${suite}\`.`,
        preview.error || "",
        ...(preview.errors || []),
        "",
        JSON.stringify(preview.changes || [], null, 2),
      ]
        .filter(Boolean)
        .join("\n");
      if (logEl) logEl.textContent = detail;
      if (applyHint) {
        applyHint.hidden = false;
        applyHint.textContent =
          preview.error ||
          "No matching CSV rows — check PlanId/StepId and that the project suite_config points at the right yPAD.";
      }
      setStatus("Heal Apply: no matching CSV rows");
      return;
    }
    const ok = confirm(
      `Apply ${n} yPAD field change(s) from AI heal?\n\nSuite: ${suite}\nUpdates Input/Expected/locators only — never Run=Y/N.\nA1 defects are skipped.`
    );
    if (!ok) return;
    const res = await api(`/api/projects/${state.projectId}/heal-apply`, {
      method: "POST",
      body: JSON.stringify({
        patches: lastHealPatches,
        suite_config: suite,
        dry_run: false,
      }),
    });
    const lines = [
      res.ok
        ? `Applied ${res.applied} change(s); skipped ${res.skipped}.`
        : `Apply failed: ${res.error || "unknown"}`,
      res.written?.length ? `Wrote: ${res.written.join(", ")}` : "",
      "",
      ...(res.changes || []).slice(0, 20).map(
        (c) =>
          `[${c.status}] ${c.sheet || ""} ${JSON.stringify(c.match || {})} → ${JSON.stringify(c.after || c.reason || {})}`
      ),
    ];
    if (logEl) logEl.textContent = lines.filter(Boolean).join("\n");
    if (applyHint) {
      applyHint.hidden = false;
      applyHint.textContent = res.ok
        ? `Applied ${res.applied} change(s). Open Build → yPAD to review, then Rerun.`
        : res.error || "Apply failed";
    }
    if (res.ok) {
      lastHealPatches = [];
      if (applyBtn) applyBtn.hidden = true;
      setStatus("Heal Apply complete — review yPAD, then Rerun");
      await recordCycleEvent("Heal", `Applied ${res.applied} CSV patch(es)`, selectedRun);
      try {
        await loadYpadSheet(ypadState.tab || "actions");
      } catch {
        /* optional refresh */
      }
    }
  } catch (e) {
    if (logEl) logEl.textContent = `Apply error: ${e.message}`;
    if (applyHint) {
      applyHint.hidden = false;
      applyHint.textContent = e.message;
    }
  } finally {
    if (applyBtn) applyBtn.disabled = false;
  }
}

async function shrinkPlans() {
  const runName = selectedRun || activeProject?.latest_run;
  const logEl = $("#heal-log");
  if (!runName) {
    logEl.textContent = "Select a run in Analyze first.";
    return;
  }
  const ok = confirm(
    "Shrink sets Run=Y only on plans that failed in this run (others → Run=N).\n\n" +
      "This is Loop prep — not AI Heal Apply.\n" +
      "Use Restore all Run=Y when you want the full suite again."
  );
  if (!ok) return;
  try {
    const res = await api("/api/ypad/shrink", {
      method: "POST",
      body: JSON.stringify({ run_name: runName, suite_config: suiteConfigPath() }),
    });
    logEl.textContent = res.ok
      ? `Shrunk: Run=Y on ${res.run_y} failure(s), Run=N on ${res.run_n} pass(es). ${res.changed} row(s) updated.\n` +
        `Click “Restore all Run=Y” before a full Verify.`
      : res.error || "No failures to shrink.";
    if (res.ok) {
      await recordCycleEvent("Shrink", `Run=Y on ${res.run_y} plans`, runName);
      setStatus(`Shrunk to ${res.run_y} failing plan(s) — Restore before full Verify`);
    }
  } catch (e) {
    logEl.textContent = `Error: ${e.message}`;
  }
}

async function restorePlans() {
  const logEl = $("#heal-log");
  try {
    const res = await api("/api/ypad/restore", {
      method: "POST",
      body: JSON.stringify({ suite_config: suiteConfigPath() }),
    });
    logEl.textContent = `Restored Run=Y on ${res.run_y} plan(s). ${res.changed} row(s) updated.` +
      (res.from_baseline ? " (from pre-shrink baseline)" : "");
    await recordCycleEvent("Restore", "All Run=Y restored");
    setStatus(`Restored ${res.run_y} Run=Y plan(s)`);
  } catch (e) {
    logEl.textContent = `Error: ${e.message}`;
  }
}

async function generateReport() {
  const runName = selectedRun || activeProject?.latest_run;
  if (!runName) {
    alert("Select or run a verify first.");
    return;
  }
  const config_path = $("#config-select").value;
  try {
    const res = await api(`/api/runs/${encodeURIComponent(runName)}/report`, {
      method: "POST",
      body: JSON.stringify({
        run_name: runName,
        config_path,
        step_label: "Verify",
        project_id: state.projectId,
      }),
    });
    const logEl = $("#loop-log");
    if (logEl) logEl.textContent = `[Report] Written: ${res.report_path}\n`;
    if (state.projectId) {
      await api(`/api/projects/${state.projectId}/brahl/reports`, {
        method: "POST",
        body: JSON.stringify({ run_name: runName, source: "automation" }),
      });
      await recordCycleEvent("Report", res.report_path, runName);
      if ($("#panel-brahl")?.classList.contains("active")) await loadBrahlPanel();
    }
  } catch (e) {
    const logEl = $("#loop-log");
    if (logEl) logEl.textContent = `[Report] Error: ${e.message}\n`;
  }
}

function failureIssueLabel(f) {
  const info = (f.stepInfo || "").trim();
  const action = (f.actionName || "").trim();
  if (info && action && info.toLowerCase() !== action.toLowerCase()) return `${info} · ${action}`;
  return info || action || "—";
}

function failureRowsHtml(failures) {
  if (!failures.length) {
    return `<tr><td colspan="6">No failures</td></tr>`;
  }
  return failures
    .map(
      (f) =>
        `<tr>` +
        `<td>${escapeHtml(f.planId || "")}</td>` +
        `<td>${escapeHtml(f.stepId || "")}</td>` +
        `<td>${escapeHtml(failureIssueLabel(f))}</td>` +
        `<td class="fail-cell">${escapeHtml(f.input || "")}</td>` +
        `<td class="fail-cell">${escapeHtml(f.expected || "")}</td>` +
        `<td class="fail-cell">${escapeHtml(f.output || "")}</td>` +
        `</tr>`
    )
    .join("");
}

async function fetchRunFailures(runName) {
  if (!runName) return [];
  const { failures } = await api(`/api/runs/${encodeURIComponent(runName)}/failures`);
  return failures || [];
}

async function refreshHealFailures() {
  const tbody = $("#heal-failures-body");
  if (!tbody) return;
  const runName = selectedRun || activeProject?.latest_run;
  updateHealHint();
  if (!runName) {
    tbody.innerHTML = `<tr><td colspan="6">Select a run in Analyze first.</td></tr>`;
    return;
  }
  try {
    const failures = await fetchRunFailures(runName);
    tbody.innerHTML = failureRowsHtml(failures);
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="6">${escapeHtml(e.message)}</td></tr>`;
  }
}

function refreshLoopBuiltSummary() {
  const purposeEl = $("#loop-built-purpose");
  const metaEl = $("#loop-built-meta");
  if (!purposeEl) return;
  const purpose =
    (activeProject?.purpose || activeProject?.prompt || "").trim() ||
    ($("#brahl-plan-requirement")?.value || "").trim() ||
    "No purpose yet — set it on Build.";
  purposeEl.textContent = purpose;
  const suite = state.suiteName || activeProject?.suite_name || "—";
  const draft = activeProject?.brahl_plan_draft;
  const auto = draft?.automated_count ?? draft?.test_cases?.filter?.((c) => c.automated !== false)?.length;
  const manual = draft?.manual_count ?? draft?.test_cases?.filter?.((c) => c.automated === false)?.length;
  const parts = [`yPAD ${suite}`];
  if (activeProject?.app_version) parts.push(`version ${activeProject.app_version}`);
  if (activeProject?.latest_run) parts.push(`latest run ${activeProject.latest_run}`);
  if (auto != null || manual != null) parts.push(`${auto ?? "—"} automated · ${manual ?? "—"} manual`);
  if (metaEl) metaEl.textContent = parts.join(" · ");
  const promptEl = $("#cycle-prompt");
  const docsEl = $("#cycle-docs");
  if (promptEl) promptEl.value = purpose;
  if (docsEl) {
    const paths = (activeProject?.context_items || []).map((c) => c.value).filter(Boolean);
    docsEl.value = [...new Set(paths)].join("\n");
  }
}

let schedulesCache = [];
let scheduleProfilesSelected = new Set(["Smoke"]);

function renderScheduleProfileChips() {
  const row = $("#schedule-profile-row");
  if (!row) return;
  row.innerHTML = runProfileOrder
    .map(
      (p) =>
        `<button type="button" class="fstart-chip schedule-profile-chip${scheduleProfilesSelected.has(p) ? " selected" : ""}" data-profile="${escapeHtml(p)}">${escapeHtml(p)}</button>`
    )
    .join("");
  row.querySelectorAll(".schedule-profile-chip").forEach((btn) => {
    btn.addEventListener("click", () => {
      const name = btn.dataset.profile;
      if (scheduleProfilesSelected.has(name)) {
        if (scheduleProfilesSelected.size > 1) scheduleProfilesSelected.delete(name);
      } else {
        scheduleProfilesSelected.add(name);
      }
      row.querySelectorAll(".schedule-profile-chip").forEach((b) => {
        b.classList.toggle("selected", scheduleProfilesSelected.has(b.dataset.profile));
      });
      refreshScheduleCostEstimate();
    });
  });
}

async function refreshScheduleCostEstimate() {
  const el = $("#schedule-cost-estimate");
  if (!el) return;
  const runtime = $("#schedule-runtime")?.value || "local";
  if (runtime !== "cloud") {
    el.hidden = true;
    return;
  }
  const interval = $("#schedule-interval")?.value || "daily";
  const threads = Number($("#schedule-thread-count")?.value || 1);
  const profiles = runProfileOrder.filter((p) => scheduleProfilesSelected.has(p));
  try {
    const est = await api(
      `/api/schedules/cost-estimate?interval=${encodeURIComponent(interval)}&thread_count=${threads}&profiles=${encodeURIComponent(profiles.join(","))}`
    );
    el.hidden = false;
    el.textContent = `Estimated cloud runtime: ~$${est.per_run_usd}/run · ~$${est.monthly_usd_est}/mo at ${interval} cadence (${est.runs_per_month_est} runs). ${est.note}`;
  } catch {
    el.hidden = false;
    el.textContent = "Could not estimate cloud cost right now.";
  }
}

function scheduleItemHtml(s) {
  const runtimeBadge = `<span class="schedule-runtime-badge runtime-${escapeHtml(s.runtime)}">${escapeHtml(s.runtime)}</span>`;
  const next = s.next_run ? new Date(s.next_run).toLocaleString() : "—";
  const last = s.last_run_at ? new Date(s.last_run_at).toLocaleString() : "never";
  const profiles = (s.profiles || []).join("+") || "default";
  return (
    `<li class="schedule-item" data-schedule-id="${escapeHtml(s.id)}">` +
    `<strong>${escapeHtml(s.step_label || "Verify")}</strong>` +
    `<span class="meta">${escapeHtml(profiles)} · ${escapeHtml(s.interval)} · ${s.thread_count || 1} thread(s)</span>` +
    runtimeBadge +
    `<span class="meta">Next: ${escapeHtml(next)} · Last: ${escapeHtml(last)}</span>` +
    `<span class="schedule-item-spacer"></span>` +
    `<label class="checkbox-label sm">` +
    `<input type="checkbox" class="schedule-toggle" ${s.enabled ? "checked" : ""} /> Enabled</label>` +
    `<button type="button" class="link-btn sm schedule-delete">Delete</button>` +
    `</li>`
  );
}

async function loadSchedules() {
  const list = $("#schedules-list");
  if (!list || !state.projectId) return;
  renderScheduleProfileChips();
  try {
    const { schedules } = await api(`/api/projects/${state.projectId}/schedules`);
    schedulesCache = schedules || [];
  } catch {
    schedulesCache = [];
  }
  list.innerHTML = schedulesCache.length
    ? schedulesCache.map(scheduleItemHtml).join("")
    : '<li class="empty-hint">No schedules yet — automated Verify stays off until you add one.</li>';
  list.querySelectorAll(".schedule-item").forEach((li) => {
    const id = li.dataset.scheduleId;
    li.querySelector(".schedule-toggle")?.addEventListener("change", async (e) => {
      try {
        await api(`/api/schedules/${id}/toggle`, {
          method: "POST",
          body: JSON.stringify({ enabled: e.target.checked }),
        });
        setStatus(e.target.checked ? "Schedule enabled" : "Schedule disabled");
        loadSchedules();
      } catch (err) {
        setStatus(`Could not update schedule: ${err.message}`);
        e.target.checked = !e.target.checked;
      }
    });
    li.querySelector(".schedule-delete")?.addEventListener("click", async () => {
      try {
        await api(`/api/schedules/${id}`, { method: "DELETE" });
        loadSchedules();
      } catch (err) {
        setStatus(`Could not delete schedule: ${err.message}`);
      }
    });
  });
}

function bindScheduleForm() {
  const form = $("#schedule-create-form");
  if (!form || form.dataset.bound) return;
  form.dataset.bound = "1";
  $("#schedule-runtime")?.addEventListener("change", refreshScheduleCostEstimate);
  $("#schedule-interval")?.addEventListener("change", refreshScheduleCostEstimate);
  $("#schedule-thread-count")?.addEventListener("input", refreshScheduleCostEstimate);
  form.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    if (!state.projectId) return;
    const configPath = $("#config-select")?.value;
    if (!configPath) {
      setStatus("Pick an fStart config on Run first.");
      return;
    }
    const profiles = runProfileOrder.filter((p) => scheduleProfilesSelected.has(p));
    const body = {
      suite: state.suiteName || "",
      config_path: configPath,
      profiles,
      thread_count: Number($("#schedule-thread-count")?.value || 1),
      interval: $("#schedule-interval")?.value || "daily",
      runtime: $("#schedule-runtime")?.value || "local",
      step_label: "Verify",
      enabled: Boolean($("#schedule-enabled")?.checked),
    };
    try {
      await api(`/api/projects/${state.projectId}/schedules`, {
        method: "POST",
        body: JSON.stringify(body),
      });
      setStatus("Schedule saved");
      $("#schedule-enabled").checked = false;
      loadSchedules();
    } catch (err) {
      setStatus(`Could not save schedule: ${err.message}`);
    }
  });
}
bindScheduleForm();

async function runLoopStep(stepLabel, options = {}) {
  const logEl = $("#loop-log");
  if (!state.projectId) {
    alert("Select a project on Build first.");
    return null;
  }
  if (options.restoreFirst) {
    try {
      const res = await api("/api/ypad/restore", {
        method: "POST",
        body: JSON.stringify({ suite_config: suiteConfigPath() }),
      });
      if (logEl) logEl.textContent += `[${stepLabel}] Restored Run=Y on ${res.run_y} plan(s).\n`;
      await recordCycleEvent("Restore", "Verify prep — all Run=Y");
    } catch (e) {
      if (logEl) logEl.textContent += `[${stepLabel}] Restore error: ${e.message}\n`;
      return null;
    }
  }
  if (options.shrinkFirst) {
    const runName = selectedRun || activeProject?.latest_run;
    if (!runName) {
      if (logEl) logEl.textContent += `[${stepLabel}] Need a prior run to shrink to failures.\n`;
      return null;
    }
    try {
      const res = await api("/api/ypad/shrink", {
        method: "POST",
        body: JSON.stringify({ run_name: runName, suite_config: suiteConfigPath() }),
      });
      if (res.ok) {
        if (logEl) logEl.textContent += `[${stepLabel}] Shrunk to ${res.run_y} failure(s).\n`;
        await recordCycleEvent("Shrink", `Loop prep — ${res.run_y} plans`, runName);
      } else if (logEl) {
        logEl.textContent += `[${stepLabel}] ${res.error || "Shrink skipped"}\n`;
      }
    } catch (e) {
      if (logEl) logEl.textContent += `[${stepLabel}] Shrink error: ${e.message}\n`;
      return null;
    }
  }
  return startRun(stepLabel);
}

async function captureContextSilent() {
  if (!state.projectId || !activeProject) return null;
  const prompt =
    (activeProject.purpose || activeProject.prompt || "").trim() ||
    ($("#brahl-plan-requirement")?.value || "").trim() ||
    "BRAHL cycle — purpose not yet set in Build.";
  const documents = (activeProject.context_items || [])
    .filter((c) => c.kind === "document" || c.kind === "connector")
    .map((c) => ({ name: c.label, path: c.value }));
  const config_path = $("#config-select")?.value || "";
  try {
    const res = await api("/api/context", {
      method: "POST",
      body: JSON.stringify({ prompt, config_path, documents, project_id: state.projectId }),
    });
    await recordCycleEvent("Context", res.context_path);
    await refreshActiveProject();
    return res;
  } catch {
    return null;
  }
}

async function runBrahlCycle() {
  if (!state.projectId) {
    alert("Select a project on Build first.");
    return;
  }
  const times = Number($('input[name="loop-times"]:checked')?.value || 1);
  const verify = !!$("#loop-verify-full")?.checked;
  const logEl = $("#loop-log");
  const btn = $("#btn-loop-run");
  if (btn) btn.disabled = true;
  if (logEl) logEl.textContent = `Loop ×${times}${verify ? " + Verify full" : ""}…\n`;
  try {
    await captureContextSilent();
    if (logEl) logEl.textContent += `[Context] Snapshot from Build purpose.\n`;
    let lastRunName = null;
    let earlyGreen = false;
    for (let i = 1; i <= times; i++) {
      const label = `Loop ${i}`;
      const job = await runLoopStep(label, i === 1 ? {} : { shrinkFirst: true });
      if (!job || job.status === "failed") {
        if (logEl) logEl.textContent += `[${label}] Stopped (${job?.status || "error"}).\n`;
        setStatus(`${label} failed — see log`);
        return;
      }
      lastRunName = selectedRun || activeProject?.latest_run || lastRunName;
      // Early exit when the suite is already green — go straight to BRAHL Go/No-Go
      if (lastRunName) {
        try {
          const stats = await api(`/api/runs/${encodeURIComponent(lastRunName)}/stats`);
          const fails = Number(stats.fails || 0);
          const total = Number(stats.total_plans || 0);
          if (total > 0 && fails === 0) {
            earlyGreen = true;
            if (logEl) {
              logEl.textContent +=
                `[${label}] All ${total} plan(s) passed — stopping Loop early (no more shrink/rerun).\n`;
            }
            break;
          }
        } catch {
          /* continue remaining loops */
        }
      }
    }
    if (verify && !earlyGreen) {
      const job = await runLoopStep("Verify", { restoreFirst: true });
      if (!job || job.status === "failed") {
        setStatus("Verify failed — see log");
        return;
      }
      lastRunName = selectedRun || activeProject?.latest_run || lastRunName;
    } else if (verify && earlyGreen && lastRunName) {
      // Restore full Run=Y before Go/No-Go report so Verify scope is intact
      try {
        const res = await api("/api/ypad/restore", {
          method: "POST",
          body: JSON.stringify({ suite_config: suiteConfigPath() }),
        });
        if (logEl) logEl.textContent += `[Verify] Restored Run=Y on ${res.run_y} plan(s) (skipped re-run — already green).\n`;
        await recordCycleEvent("Restore", "Green early-exit — Run=Y restored", lastRunName);
      } catch (e) {
        if (logEl) logEl.textContent += `[Verify] Restore skipped: ${e.message}\n`;
      }
    }
    const runName = lastRunName || selectedRun || activeProject?.latest_run;
    if (runName) await autoEnsureBrahlReport(runName, earlyGreen ? "Loop (green)" : verify ? "Verify" : `Loop ${times}`);
    setStatus(earlyGreen ? "All green — opening BRAHL Go/No-Go" : "Loop complete — opening BRAHL");
    showPhase("brahl");
    await loadBrahlPanel();
  } catch (e) {
    if (logEl) logEl.textContent += `Error: ${e.message}\n`;
    setStatus(`Loop error: ${e.message}`);
  } finally {
    if (btn) btn.disabled = false;
  }
}

function formatRunTimestamp(ts) {
  if (!ts || !/^\d{8}_\d{6}$/.test(ts)) return ts || "";
  const y = ts.slice(0, 4);
  const mo = ts.slice(4, 6);
  const d = ts.slice(6, 8);
  const h = ts.slice(9, 11);
  const mi = ts.slice(11, 13);
  const s = ts.slice(13, 15);
  return `${y}-${mo}-${d} ${h}:${mi}:${s}`;
}

async function loadRuns() {
  const projectSuite = state.suiteName || activeProject?.suite_name || "";
  // Load all suites so history survives refresh; still highlight current suite first
  const { runs } = await api(`/api/runs?suite=all`);
  const list = $("#runs-list");
  if (!list) return;
  if (!runs.length) {
    list.innerHTML = `<li>No runs yet</li>`;
    return;
  }
  const bySuite = {};
  runs.forEach((r) => {
    const key = r.suite || "other";
    (bySuite[key] ||= []).push(r);
  });
  const suiteOrder = Object.keys(bySuite).sort((a, b) => {
    if (projectSuite && a === projectSuite) return -1;
    if (projectSuite && b === projectSuite) return 1;
    return a.localeCompare(b);
  });
  list.innerHTML = "";
  let firstLi = null;
  let firstRun = null;
  suiteOrder.forEach((suite, si) => {
    const group = document.createElement("li");
    group.className = "runs-suite-group";
    const open = !projectSuite || suite === projectSuite || si === 0;
    group.innerHTML = `<details ${open ? "open" : ""}><summary>${escapeHtml(suite)} <span class="meta">${bySuite[suite].length} run(s)</span></summary><ul class="runs-suite-children"></ul></details>`;
    const childUl = group.querySelector(".runs-suite-children");
    bySuite[suite].forEach((r) => {
      const li = document.createElement("li");
      const when = formatRunTimestamp(r.timestamp);
      li.innerHTML =
        `<span class="run-name">${escapeHtml(r.name)}</span>` +
        `<span class="meta">${when ? escapeHtml(when) + " · " : ""}${r.passes}/${r.total_plans ?? r.passes + r.fails} pass · ${r.fails} fail</span>`;
      li.onclick = (ev) => {
        ev.stopPropagation();
        selectRun(r.name, li, r);
      };
      childUl.appendChild(li);
      if (!firstLi) {
        firstLi = li;
        firstRun = r;
      }
    });
    list.appendChild(group);
  });
  // Prefer latest run for current project suite
  const preferred = projectSuite
    ? runs.find((r) => r.suite === projectSuite)
    : firstRun;
  if (preferred) {
    const preferLi =
      [...list.querySelectorAll(".runs-suite-children li")].find((el) =>
        el.textContent.includes(preferred.name)
      ) || firstLi;
    if (preferLi) selectRun(preferred.name, preferLi, preferred);
  } else if (firstLi && firstRun) {
    selectRun(firstRun.name, firstLi, firstRun);
  }
}

async function selectRun(name, li, run) {
  selectedRun = name;
  lastAnalyzeMarkdown = "";
  renderAiMarkdown($("#analyze-ai-result"), "");
  renderAiMarkdown($("#heal-ai-result"), "");
  $$("#runs-list .runs-suite-children li").forEach((el) => el.classList.remove("selected"));
  if (li) li.classList.add("selected");
  try {
    const failures = await fetchRunFailures(name);
    const tbody = $("#failures-body");
    if (tbody) tbody.innerHTML = failureRowsHtml(failures);
    const healBody = $("#heal-failures-body");
    if (healBody) healBody.innerHTML = failureRowsHtml(failures);
  } catch (e) {
    const tbody = $("#failures-body");
    if (tbody) tbody.innerHTML = `<tr><td colspan="6">${escapeHtml(e.message)}</td></tr>`;
  }
  const dashHref = zDashHref(run?.dashboard);
  $("#dash-link").innerHTML = dashHref
    ? `<a href="${dashHref}" target="_blank">Open zDash</a>`
    : '<span class="empty-hint">No zDash for this run yet.</span>';
  updateHealHint();
  if (state.projectId) {
    await api(`/api/projects/${state.projectId}`, {
      method: "PATCH",
      body: JSON.stringify({ latest_run: name }),
    });
    try {
      await api(`/api/projects/${state.projectId}/brahl/reports`, {
        method: "POST",
        body: JSON.stringify({
          run_name: name,
          source: isAiOn() ? "automation" : "automation_ai",
        }),
      });
    } catch {
      /* optional link */
    }
  }
}

async function startRun(stepLabel) {
  if (!state.projectId) {
    alert("Select a project on Build first.");
    return null;
  }
  const paths = selectedFstartPaths();
  const configPath = paths[0] || $("#config-select")?.value;
  if (!configPath) {
    alert("No fStart config for this project yet — one is created automatically once a suite exists.");
    return null;
  }
  const profiles = selectedRunProfiles();
  if (!profiles.length) {
    alert("Select at least one Run profile (Smoke, UI, API, …).");
    return null;
  }
  const threads = runThreadCount();
  const isCycle = stepLabel.startsWith("Loop") || stepLabel === "Verify";
  const logEl = isCycle ? $("#loop-log") : $("#run-log");
  if (stepLabel === "Run") {
    if (logEl) logEl.textContent = "";
    const post = $("#run-post-actions");
    if (post) post.hidden = true;
    const batchRows = $("#run-batch-rows");
    if (batchRows) {
      batchRows.hidden = true;
      batchRows.innerHTML = "";
    }
  }
  const runBtn = $("#btn-run");
  if (runBtn) runBtn.disabled = true;
  const progress = $("#progress-bar");
  if (progress) progress.style.width = "10%";
  // Parallel execution is derived only from Threads > 1 + 2+ profiles — never a separate control.
  const body = {
    config_path: configPath,
    step_label: stepLabel,
    profiles,
    thread_count: threads,
  };
  const job = await api("/api/jobs", {
    method: "POST",
    body: JSON.stringify(body),
  });
  if (pollTimer) clearInterval(pollTimer);
  return new Promise((resolve) => {
    pollTimer = setInterval(async () => {
      try {
        const j = await api(`/api/jobs/${job.job_id}`);
        const liveName = j.output_dir && !String(j.output_dir).includes("zDash_batch_")
          ? String(j.output_dir).replace(/\\/g, "/").split("/").pop()
          : (j.run_dirs || [])[0]?.replace(/\\/g, "/").split("/").pop();
        if (liveName) {
          liveRunStatus.runName = liveName;
          liveRunStatus.status = j.status;
        }
        if (logEl) {
          const engineLog = (j.log_lines || []).join("\n");
          if (isCycle) {
            const marker = `\n—— ${stepLabel} ——\n`;
            const prior = logEl.textContent.includes(marker)
              ? logEl.textContent.split(marker)[0] + marker
              : `${logEl.textContent}${marker}`;
            logEl.textContent = prior + engineLog;
          } else {
            logEl.textContent = engineLog;
          }
          logEl.scrollTop = logEl.scrollHeight;
        }
        if (j.status === "completed" || j.status === "failed") {
          clearInterval(pollTimer);
          pollTimer = null;
          if (runBtn) runBtn.disabled = false;
          syncConfigSelectFromChips();
          if (progress) progress.style.width = j.status === "completed" ? "100%" : "60%";
          const batchDash =
            j.batch_dashboard || (String(j.output_dir || "").includes("zDash_batch_") ? j.output_dir : null);
          const allRunDirs = (j.run_dirs || [])
            .map((d) => String(d).replace(/\\/g, "/").split("/").pop())
            .filter(Boolean);
          const isBatch = allRunDirs.length > 1 || Boolean(batchDash);
          let runName = null;
          if (j.output_dir && !String(j.output_dir).includes("zDash_batch_")) {
            runName = j.output_dir.replace(/\\/g, "/").split("/").pop();
          } else if (allRunDirs.length) {
            runName = allRunDirs[0];
          }
          if (runName && state.projectId) {
            await api(`/api/projects/${state.projectId}`, {
              method: "PATCH",
              body: JSON.stringify({ latest_run: runName }),
            });
            await recordCycleEvent(stepLabel, j.status === "completed" ? "completed" : "failed", runName);
            selectedRun = runName;
          }
          loadRuns();
          await refreshActiveProject();
          if (stepLabel === "Run" && j.status === "completed") {
            await showRunPostActions(runName, batchDash);
            if (isBatch) {
              await renderBatchRunRows(allRunDirs, batchDash);
              setStatus(`Batch complete — ${allRunDirs.length} job(s), one zDash each`);
            } else {
              setStatus("Run complete — review in Analyze or open zDash");
            }
          }
          if (j.status === "completed" && runName) {
            if (stepLabel === "Verify" || stepLabel.startsWith("Loop") || stepLabel === "Run") {
              if (isBatch && state.projectId && allRunDirs.length) {
                try {
                  await api(`/api/projects/${state.projectId}/brahl/reports/batch`, {
                    method: "POST",
                    body: JSON.stringify({
                      run_names: allRunDirs,
                      source: isAiOn() ? "automation" : "automation_ai",
                      batch_dashboard: batchDash || null,
                      job_id: j.job_id,
                    }),
                  });
                } catch {
                  /* non-fatal */
                }
              } else {
                await autoEnsureBrahlReport(runName, stepLabel);
              }
              if ($("#panel-brahl")?.classList.contains("active")) await loadBrahlPanel();
            }
          }
          resolve(j);
        }
      } catch (e) {
        clearInterval(pollTimer);
        pollTimer = null;
        if (runBtn) runBtn.disabled = false;
        syncConfigSelectFromChips();
        if (logEl) logEl.textContent += `\n[poll error] ${e.message}`;
        resolve({ status: "failed", error: e.message });
      }
    }, 400);
  });
}

async function checkHealth() {
  try {
    const d = await api("/api/health");
    $("#health-pill").textContent = d.status;
    $("#health-pill").className = "health-pill ok";
  } catch {
    $("#health-pill").textContent = "offline";
    $("#health-pill").className = "health-pill err";
  }
}

async function loadSuites() {
  const { suites } = await api("/api/suites");
  state.suites = suites || [];
  syncRunSuiteDisplay();
}

let fstartEditorPath = null;

function closeFstartModal() {
  $("#fstart-modal").hidden = true;
  fstartEditorPath = null;
  const err = $("#fstart-json-error");
  if (err) err.hidden = true;
}

async function openFstartEditor() {
  const path = $("#config-select")?.value;
  if (!path) return;
  try {
    const data = await api(`/api/configs/content?path=${encodeURIComponent(path)}`);
    fstartEditorPath = data.path;
    $("#fstart-modal-title").textContent = "Edit fStart config";
    $("#fstart-modal-path").textContent = data.path;
    $("#fstart-json-editor").value = JSON.stringify(data.content, null, 2);
    $("#fstart-delete").hidden = false;
    $("#fstart-json-error").hidden = true;
    $("#fstart-modal").hidden = false;
  } catch (e) {
    setStatus(`Cannot load config: ${e.message}`);
  }
}

async function saveFstartEditor() {
  const errEl = $("#fstart-json-error");
  const raw = $("#fstart-json-editor")?.value || "";
  let parsed;
  try {
    parsed = JSON.parse(raw);
  } catch (e) {
    if (errEl) {
      errEl.hidden = false;
      errEl.textContent = `Invalid JSON: ${e.message}`;
    }
    return;
  }
  const path = fstartEditorPath || $("#fstart-modal-path")?.textContent?.trim();
  if (!path) return;
  try {
    await api("/api/configs/content", {
      method: "PUT",
      body: JSON.stringify({ path, content: parsed }),
    });
    closeFstartModal();
    await loadConfigsForSuite();
    const sel = $("#config-select");
    if (sel) sel.value = path.replace(/\\/g, "/");
    setStatus(`Saved ${path}`);
  } catch (e) {
    if (errEl) {
      errEl.hidden = false;
      errEl.textContent = e.message;
    }
  }
}

async function deleteFstartEditor() {
  const path = fstartEditorPath || $("#config-select")?.value;
  if (!path || !confirm(`Delete ${path}?`)) return;
  try {
    await api(`/api/configs/content?path=${encodeURIComponent(path)}`, { method: "DELETE" });
    closeFstartModal();
    await loadConfigsForSuite();
    setStatus(`Deleted ${path}`);
  } catch (e) {
    setStatus(`Delete failed: ${e.message}`);
  }
}

async function loadConfigsForSuite() {
  const suite = state.suiteName;
  const sel = $("#config-select");
  const hint = $("#fstart-empty-hint");
  const runBtn = $("#btn-run");
  if (!suite || !sel) return;
  try {
    await loadRunProfiles();
    const data = await api(`/api/configs?suite=${encodeURIComponent(suite)}`);
    let configs = data.configs || [];
    let preferred = data.default && configs.includes(data.default) ? data.default : configs[0];
    if (!configs.length) {
      // One fStart per suite is expected — create it silently instead of a manual "New" step.
      try {
        const hasSmoke = false;
        const created = await api("/api/configs", {
          method: "POST",
          body: JSON.stringify({ suite_name: suite, variant: hasSmoke ? "custom" : "smoke" }),
        });
        const retry = await api(`/api/configs?suite=${encodeURIComponent(suite)}`);
        configs = retry.configs || [];
        preferred = created.path && configs.includes(created.path) ? created.path : configs[0];
      } catch {
        /* fall through to empty state */
      }
    }
    if (configs.length) {
      sel.innerHTML = configs.map((c) => `<option value="${escapeHtml(c)}">${escapeHtml(c)}</option>`).join("");
      sel.value = preferred;
      renderFstartChips(configs, preferred);
      if (hint) hint.hidden = true;
      if (runBtn) runBtn.disabled = false;
    } else {
      sel.innerHTML = '<option value="">— none —</option>';
      renderFstartChips([]);
      fstartSelected = new Set();
      fstartPrimary = null;
      if (hint) hint.hidden = false;
      if (runBtn) runBtn.disabled = true;
    }
  } catch {
    sel.innerHTML = '<option value="">— error —</option>';
    if (runBtn) runBtn.disabled = true;
  }
}

function initAvatarGate() {
  state.profile = typeof getActiveProfile === "function" ? getActiveProfile() : null;
  applyProfileUI();
  bindAvatarControls();
  bindTopbarRoleSelect();
  let avatar = state.avatar;
  const authUser = getAuthUser();
  if (!avatar && authUser?.role === "qa_hunter") avatar = "consultant";
  if (!avatar && authUser) avatar = "client";
  if (!avatar) {
    $("#avatar-gate").hidden = false;
    return;
  }
  setAvatar(avatar);
}

$$(".phase-btn").forEach((btn) => {
  btn.addEventListener("click", () => showPhase(btn.dataset.phase));
});

$("#topbar-project-select")?.addEventListener("change", (e) => {
  selectYpadProject(e.target.value);
});
$("#client-empty-add")?.addEventListener("click", createNewProject);
$("#btn-fstart-edit")?.addEventListener("click", openFstartEditor);
$("#fstart-save")?.addEventListener("click", saveFstartEditor);
$("#fstart-delete")?.addEventListener("click", deleteFstartEditor);
$("#fstart-cancel")?.addEventListener("click", closeFstartModal);
$("#planner-chat-form")?.addEventListener("submit", sendPlannerChat);
$("#planner-mic")?.addEventListener("click", togglePlannerMic);
$("#planner-create")?.addEventListener("click", () => finishPlannerCreate(false));
$("#planner-create-brahl")?.addEventListener("click", () => finishPlannerCreate(true));
$("#add-project-cancel")?.addEventListener("click", closeAddProjectModal);
$("#role-switch-confirm")?.addEventListener("click", async () => {
  const next = pendingAvatar;
  closeRoleSwitchModal();
  if (next) await setAvatar(next);
});
$("#role-switch-cancel")?.addEventListener("click", closeRoleSwitchModal);
$$(".phase-locked-add").forEach((btn) => btn.addEventListener("click", createNewProject));
$$(".phase-locked-build").forEach((btn) => btn.addEventListener("click", goToBuildPanel));
$("#chat-form")?.addEventListener("submit", sendChat);
$("#btn-add-context")?.addEventListener("click", () => {
  const panel = $("#add-context-panel");
  const section = $(".context-section");
  if (section) section.hidden = false;
  if (panel) panel.hidden = false;
});
$("#btn-build-add-context")?.addEventListener("click", openAddProjectModal);
$("#btn-topbar-add-project")?.addEventListener("click", openAddProjectModal);
$("#btn-generate-brahl-plan")?.addEventListener("click", generateBrahlPlan);
$("#btn-accept-brahl-plan")?.addEventListener("click", acceptBrahlPlan);
$("#ypad-foxyiz-help")?.addEventListener("click", () => {
  window.open("https://foxyiz.com", "_blank", "noopener");
});
$("#btn-save-context")?.addEventListener("click", saveContextItem);
$("#btn-cancel-context")?.addEventListener("click", () => {
  $("#add-context-panel").hidden = true;
});
$$(".ctx-example-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    openContextPanel(btn.dataset.kind, btn.dataset.label, btn.dataset.value);
  });
});
$("#budget-split")?.addEventListener("input", (e) => {
  const v = parseInt(e.target.value, 10);
  $("#auto-pct").textContent = v;
  $("#human-pct").textContent = 100 - v;
});
$("#btn-save-budget")?.addEventListener("click", saveBudget);
$("#ai-toggle")?.addEventListener("change", toggleAiMode);
$("#btn-ai-docs")?.addEventListener("click", openAiDocsModal);
$("#build-open-ai-docs")?.addEventListener("click", openAiDocsModal);
$("#ai-docs-close")?.addEventListener("click", closeAiDocsModal);
$("#ai-docs-expand")?.addEventListener("click", toggleAiDocsExpand);
$("#ai-docs-new")?.addEventListener("click", createUserAiDoc);
$("#ai-docs-save")?.addEventListener("click", saveUserAiDoc);
$("#ai-docs-delete")?.addEventListener("click", deleteUserAiDoc);
$("#ai-docs-in-prompt")?.addEventListener("change", async () => {
  if (!aiDocsSelectedId) return;
  const meta = (aiDocsCache || []).find((d) => d.id === aiDocsSelectedId);
  if (!meta || meta.source !== "user") return;
  const inPrompt = $("#ai-docs-in-prompt");
  try {
    const data = await api(`/api/ai/docs/user/${encodeURIComponent(aiDocsSelectedId)}`, {
      method: "PATCH",
      body: JSON.stringify({ in_prompt: Boolean(inPrompt?.checked) }),
    });
    const list = await api("/api/ai/docs");
    aiDocsCache = list.docs || [];
    updateAiDocsBudget(data.budget || list.budget);
    renderAiDocsList(aiDocsSelectedId);
    setStatus(inPrompt?.checked ? "Doc included in AI prompt" : "Doc removed from AI prompt");
  } catch (e) {
    if (inPrompt) inPrompt.checked = !inPrompt.checked;
    setStatus(`Prompt toggle failed: ${e.message}`);
  }
});
$("#arena-cost-widget")?.addEventListener("click", () => showPhase("cost"));
$("#arena-ypad-widget")?.addEventListener("click", () => {
  showPhase("build");
  requestAnimationFrame(() => {
    $("#build-automation")?.scrollIntoView({ behavior: "smooth", block: "start" });
  });
});
$$(".build-doc-chip").forEach((btn) => {
  btn.addEventListener("click", () => openBuildDoc(btn.dataset.doc || "strategy", "synopsis"));
});
$("#build-doc-modal-close")?.addEventListener("click", closeBuildDocModal);
$("#build-doc-modal")?.addEventListener("click", (e) => {
  if (e.target?.id === "build-doc-modal") closeBuildDocModal();
});
$("#build-doc-view-synopsis")?.addEventListener("click", () => setBuildDocModalView("synopsis"));
$("#build-doc-view-full")?.addEventListener("click", () => setBuildDocModalView("full"));
startArenaCostWidgetPoll();
$("#ai-docs-modal")?.addEventListener("click", (e) => {
  if (e.target.id === "ai-docs-modal") closeAiDocsModal();
});
$("#btn-save-manual-purpose")?.addEventListener("click", saveManualPurpose);
$("#btn-add-context-manual")?.addEventListener("click", () => {
  $("#add-context-panel").hidden = false;
});
$("#hitl-story-form")?.addEventListener("submit", submitHitlStoryForm);
$("#btn-invite-hitl")?.addEventListener("click", openInviteHitlModal);
$("#invite-hitl-form")?.addEventListener("submit", inviteHitlFromBuild);
$("#invite-hitl-cancel")?.addEventListener("click", closeInviteHitlModal);
$("#btn-request-change")?.addEventListener("click", openChangeRequestModal);
$("#change-request-form")?.addEventListener("submit", requestProjectChange);
$("#change-request-cancel")?.addEventListener("click", closeChangeRequestModal);
$("#btn-snapshot-baseline")?.addEventListener("click", snapshotVersionBaseline);
$("#btn-save-app-version")?.addEventListener("click", saveVersionLabels);
$$(".ypad-tab").forEach((btn) => {
  btn.addEventListener("click", () => loadYpadSheet(btn.dataset.ypadTab));
});
$("#ypad-filter")?.addEventListener("input", (e) => {
  ypadState.filter = e.target.value;
  renderYpadExplorer();
});
$("#ypad-run-y-only")?.addEventListener("change", renderYpadExplorer);
$$(".ypad-cov-chip").forEach((chip) => {
  chip.addEventListener("click", () => {
    ypadState.coverageFilter = chip.dataset.ypadCov || "all";
    $$(".ypad-cov-chip").forEach((c) => c.classList.toggle("active", c === chip));
    const runY = $("#ypad-run-y-only");
    if (runY) runY.checked = ypadState.coverageFilter === "auto";
    renderYpadExplorer();
  });
});
$("#ypad-design-col-mode")?.addEventListener("change", (e) => {
  ypadState.designColumnMode = e.target.value;
  renderYpadExplorer();
});
$$(".ypad-design-group-chip").forEach((chip) => {
  chip.addEventListener("click", () => {
    ypadState.designGroupFilter = chip.dataset.designGroup || "";
    renderYpadExplorer();
  });
});
$("#ypad-toggle-edit")?.addEventListener("click", toggleYpadEdit);
$("#ypad-save")?.addEventListener("click", saveYpadSheet);
$("#ypad-drawer-close")?.addEventListener("click", () => closeYpadDrawer());
$("#ypad-drawer-backdrop")?.addEventListener("click", () => closeYpadDrawer());
$("#ypad-goto-brahl")?.addEventListener("click", () => showPhase("brahl"));
$("#cost-runtime-local")?.addEventListener("change", () => saveCostRuntimeMode("local"));
$("#cost-runtime-cloud")?.addEventListener("change", () => saveCostRuntimeMode("cloud"));
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && !$("#ypad-detail-drawer")?.hidden) closeYpadDrawer();
});
$("#btn-join-hitl")?.addEventListener("click", joinHitl);
$("#btn-hitl-submit")?.addEventListener("click", submitHitlReport);
$("#btn-hunt-stop")?.addEventListener("click", stopHuntRecording);
$("#btn-hunt-add-issue")?.addEventListener("click", addHuntIssueFromForm);
bindEvidenceMenu();
$("#btn-heal-edit-ypad")?.addEventListener("click", () => {
  showPhase("build");
  const cov = $("#build-automation");
  cov?.scrollIntoView({ behavior: "smooth", block: "start" });
  if (!ypadState.editMode) toggleYpadEdit();
});
$("#btn-ypad-snapshot")?.addEventListener("click", createYpadSnapshot);
$("#ypad-show-table")?.addEventListener("click", () => {
  ypadState.showTable = !ypadState.showTable;
  renderYpadExplorer();
});
$("#ypad-page-prev")?.addEventListener("click", () => {
  ypadState.page = Math.max(0, ypadState.page - 1);
  renderYpadExplorer();
});
$("#ypad-page-next")?.addEventListener("click", () => {
  ypadState.page += 1;
  renderYpadExplorer();
});
$("#btn-heal-rerun")?.addEventListener("click", () => showPhase("run"));
$("#btn-loop-open-build")?.addEventListener("click", () => showPhase("build"));
$("#btn-loop-run")?.addEventListener("click", runBrahlCycle);
$("#btn-run")?.addEventListener("click", () => startRun("Run"));
$("#btn-shrink-plans")?.addEventListener("click", shrinkPlans);
$("#btn-restore-plans")?.addEventListener("click", restorePlans);
$("#btn-refresh-runs")?.addEventListener("click", loadRuns);
$("#btn-analyze-ai")?.addEventListener("click", runAnalyzeAi);
$("#btn-heal-ai")?.addEventListener("click", runHealAi);
$("#btn-heal-apply")?.addEventListener("click", applyHealPatches);
$("#brahl-chat-form")?.addEventListener("submit", sendBrahlChat);
$("#atomic77-chat-form")?.addEventListener("submit", (ev) => sendAtomic77Chat(ev));
$$(".atomic77-faq-chip").forEach((chip) => {
  chip.addEventListener("click", () => sendAtomic77Chat({ preventDefault: () => {} }, chip.dataset.faq));
});
$("#btn-link-run-report")?.addEventListener("click", linkRunReport);
$("#link-report-form")?.addEventListener("submit", submitLinkReportForm);
$("#link-report-cancel")?.addEventListener("click", closeLinkReportModal);
$$(".phase-marker").forEach((dot) => {
  dot.addEventListener("click", () => showPhase(dot.dataset.phase));
});

initAvatarGate();
initUserMenu();
initPresenceHeartbeat();
initPromoterPanel();
restoreDraftRequirementIfNeeded();
(function initAuthRole() {
  const u = getAuthUser();
  if (!u || state.avatar) return;
  if (u.role === "qa_hunter") setAvatar("consultant");
  else setAvatar("client");
})();
window.QoaTheme?.initTheme?.();
window.addEventListener("qoa-theme-change", () => {
  updateVisualRewardRail();
  if (state.phase === "cost") loadCostPanel();
  const title = $("#app-title");
  if (title) title.textContent = "BRAHL Web — f(x,y)=z";
});
applyAvatarLabelsToDom();
applyAvatarModeNav();
loadAppVersion();
checkHealth();
loadSuites();
loadConfigsForSuite();
loadRuns();
setInterval(checkHealth, 15000);

(function applyDeepLinkPhase() {
  const raw = (location.hash || "").replace(/^#/, "").trim().toLowerCase();
  if (!raw) return;
  const allowed = new Set(["build", "run", "analyze", "heal", "loop", "brahl", "nalanda", "atomic77", "promoter", "cost"]);
  if (!allowed.has(raw)) return;
  const go = () => showPhase(raw);
  // Wait a tick so suites/avatar init settle
  setTimeout(go, 200);
  window.addEventListener("hashchange", () => {
    const h = (location.hash || "").replace(/^#/, "").trim().toLowerCase();
    if (allowed.has(h)) showPhase(h);
  });
})();
