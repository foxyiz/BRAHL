const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

const STORAGE_AVATAR = "qoa_web_avatar";
const STORAGE_PROJECT = "qoa_web_project_id";
const STORAGE_SUITE = "qoa_web_suite";

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

(function redirectIfNoProfile() {
  const path = location.pathname.replace(/\/$/, "") || "/";
  if (path !== "/app" && path !== "/index.html") return;
  if (window.QoaInviteGate && !window.QoaInviteGate.isInviteTrialValid()) {
    location.replace("/welcome");
    return;
  }
  const params = new URLSearchParams(location.search);
  if (!localStorage.getItem(STORAGE_PROFILE) && !params.get("profile")) {
    location.replace("/signin");
  }
})();

let pollTimer = null;
let selectedRun = null;
let selectedBrahlRun = null;
let selectedBrahlReportId = null;
let activeProject = null;
let lastAnalyzeMarkdown = "";

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
};

async function api(path, opts = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(opts.headers || {}) },
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
  $$(".phase-btn").forEach((btn) => {
    const ph = btn.dataset.phase;
    if (ph === "nalanda") btn.hidden = !isNetworker();
    else if (ph === "atomic77" || ph === "cost") btn.hidden = isNetworker();
    else if (brahlPhases.includes(ph)) btn.hidden = isNetworker();
  });
  if (isNetworker() && state.phase !== "nalanda") showPhase("nalanda");
  if (!isNetworker() && state.phase === "nalanda") showPhase("build");
}

function showPhase(name) {
  state.phase = name;
  $$(".phase-btn").forEach((b) => b.classList.toggle("active", b.dataset.phase === name));
  $$(".panel").forEach((p) => p.classList.toggle("active", p.dataset.panel === name));
  updatePhaseLock();
  if (!hasScope() && name !== "build") {
    setStatus(state.avatar && !state.suites.length ? "Add your first challenge to the arena" : "Select a challenge in the top bar");
  } else {
    syncProjectStatus();
  }
  if (name === "brahl" && state.suiteName) loadBrahlPanel();
  if (name === "atomic77") loadAtomic77Panel();
  if (name === "cost") loadCostPanel();
  if (name === "nalanda") window.QoaNalanda?.loadPanel?.();
  if (name === "analyze" && selectedRun && isAiOn()) {
    /* user can click AI analyze or we leave prior result visible */
  }
  renderPhaseProgress();
  updateVisualRewardRail();
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
}

function updateTopbarProjectLabel() {
  const labelEl = $(".topbar-project-label");
  if (!labelEl || !state.avatar) return;
  labelEl.textContent = avatarLabel(state.avatar).projectLabel;
}

function syncAvatarButtons(profile, activeAvatar) {
  $$(".avatar-btn").forEach((b) => {
    const allowed = profileAllowsAvatar(profile, b.dataset.avatar);
    b.classList.toggle("active", b.dataset.avatar === activeAvatar);
    b.classList.toggle("avatar-btn-restricted", false);
    b.disabled = false;
    b.setAttribute("aria-disabled", "false");
  });
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
  const profile = state.profile || getActiveProfile();
  state.profile = profile;
  const chip = $("#profile-chip");
  const codeEl = $("#profile-chip-code");
  const nameEl = $("#profile-chip-name");
  if (chip && profile) {
    chip.hidden = false;
    if (codeEl) codeEl.textContent = profile.code;
    if (nameEl) nameEl.textContent = profile.name;
    chip.title = `${profile.code} · ${profile.title} — click to switch profile`;
  }
  const adminLink = $("#footer-admin-link");
  if (adminLink) adminLink.classList.toggle("footer-admin-link-active", !!profile?.admin);

  $$(".avatar-btn").forEach((b) => {
    syncAvatarButtons(profile, state.avatar);
  });

  const tierBanner = $("#consultant-tier-banner");
  if (tierBanner) {
    if (profile?.consultantTier === "senior") {
      tierBanner.hidden = false;
      tierBanner.textContent =
        "Senior QA Hunter — mentor-level deliverables, hybrid Automation + AI reports, yPAD shrink/restore guidance.";
      tierBanner.className = "consultant-tier-banner consultant-tier-senior";
    } else if (profile?.consultantTier === "bounty") {
      tierBanner.hidden = false;
      tierBanner.textContent =
        "Bug-bounty QA Hunter — focus on critical issues, tagged invites, enriched report uploads.";
      tierBanner.className = "consultant-tier-banner consultant-tier-bounty";
    } else {
      tierBanner.hidden = true;
      tierBanner.textContent = "";
    }
  }

  const demoBanner = $("#demo-banner");
  if (demoBanner && window.QoaInviteGate?.isInviteTrialValid?.()) {
    const days = window.QoaInviteGate.inviteTrialDaysLeft();
    const trial = window.QoaInviteGate.getInviteTrial();
    const batch = trial?.batch_label ? ` · ${trial.batch_label}` : "";
    const span = demoBanner.querySelector("span");
    if (span) span.textContent = `GTM trial — ${days} day(s) left${batch} · earn XP · BRAHL small projects`;
  }

  document.body.classList.toggle("profile-admin", !!profile?.admin);
  document.body.classList.toggle("profile-ai-locked", !!profile?.aiLocked);
  document.body.classList.toggle("profile-power-client", profile?.techLevel === "engineer");
  loadPersonaTasks();
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

async function selectYpadProject(suiteName) {
  if (!suiteName) return;
  state.suiteName = suiteName;
  localStorage.setItem(STORAGE_SUITE, suiteName);
  selectedBrahlRun = null;
  selectedRun = null;
  try {
    const data = await api(`/api/ypad-projects/${encodeURIComponent(suiteName)}`);
    activeProject = data.project;
    state.projectId = activeProject?.id || null;
    if (state.projectId) localStorage.setItem(STORAGE_PROJECT, state.projectId);
    else localStorage.removeItem(STORAGE_PROJECT);
    updateProjectBanner(data.payout_preview);
  } catch {
    activeProject = null;
    state.projectId = null;
    localStorage.removeItem(STORAGE_PROJECT);
    updateProjectBanner();
  }
  syncRunSuiteDisplay();
  syncScopeLabels();
  await loadConfigsForSuite();
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
  applyAiMode();
  await loadRuns();
  if ($("#panel-brahl")?.classList.contains("active")) await loadBrahlPanel();
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
  } catch {
    state.projectId = null;
    localStorage.removeItem(STORAGE_PROJECT);
    activeProject = null;
    updateProjectBanner();
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
  return "y/qoa_web/qoa_web.json";
}

function renderAiMarkdown(el, markdown) {
  if (!el) return;
  if (!markdown) {
    el.hidden = true;
    el.textContent = "";
    return;
  }
  el.hidden = false;
  el.classList.remove("ai-loading");
  el.textContent = markdown;
}

function isAiOn() {
  return activeProject?.ai_enabled !== false;
}

function applyAiMode() {
  const on = isAiOn();
  const hasProject = !!activeProject;
  const profile = state.profile;
  const aiLocked = !!profile?.aiLocked;
  $("#ai-toggle-wrap").hidden = !hasProject;
  renderProjectSelectors();
  if (hasProject) {
    $("#ai-toggle").checked = on;
    $("#ai-toggle").disabled = aiLocked;
  }
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
    setStatus(profile ? `${profileLabel(profile)} — choose avatar` : "Choose an avatar to start");
    return;
  }
  if (!hasScope()) {
    strip?.classList.remove("has-project");
    setStatus(
      !state.suites.length ? "Add your first project" : "Select a project in the top bar"
    );
    return;
  }
  strip?.classList.add("has-project");
  const phaseHints = {
    build: "Describe purpose · set budget · add context (AI chat when on)",
    run: "FoXYiZ fEngine2 — Run yPAD (no AI)",
    analyze: isAiOn() ? "Refresh runs · AI root-cause or manual RCA" : "Refresh runs · classify T1/T2/T3/A1 manually",
    heal: isAiOn() ? "AI heal suggestions · shrink/restore y1Plans" : "Edit yPAD · shrink/restore for Loop",
    loop: "Step 0 context · Loop 1–3 + Verify via fEngine2",
    brahl: "Review reports · chat with model",
    cost: state.avatar === "consultant" ? "QA Hunter wallet · earnings by project" : "Budget meter · AI vs QA Hunter vs local/cloud",
    nalanda: "Learn · teach · discuss · invite — free knowledge community",
  };
  setStatus(phaseHints[state.phase] || "Project active");
}

function renderPhaseProgress() {
  const bar = $("#phase-progress");
  if (!bar) return;
  if (!state.suiteName || !activeProject) {
    bar.hidden = true;
    return;
  }
  bar.hidden = false;
  const userMsgs = (activeProject.chat_messages || []).filter((m) => m.role === "user");
  const hasPurpose =
    !!(activeProject.purpose || activeProject.prompt || "").trim() || userMsgs.length > 0;
  const hasRun = !!(activeProject.latest_run || "").trim();
  const hasContext = !!(activeProject.brahl_context_path || "").trim();
  const hasReports = !!(activeProject.reports || []).length;
  const done = {
    build: hasPurpose,
    run: hasRun,
    analyze: hasRun,
    heal: hasRun,
    loop: hasContext || hasRun,
    brahl: hasReports,
    cost: (Number(activeProject.budget_usd) || 0) > 0,
  };
  $$(".phase-progress-dot").forEach((el) => {
    const ph = el.dataset.phase;
    el.classList.toggle("done", !!done[ph]);
    el.classList.toggle("current", ph === state.phase);
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

function showRunPostActions(runName) {
  const wrap = $("#run-post-actions");
  if (!wrap || !runName) {
    if (wrap) wrap.hidden = true;
    return;
  }
  wrap.hidden = false;
  const zdash = `/api/files/z/${encodeURIComponent(runName)}/qoa_web_zDash.html`;
  const link = $("#run-zdash-link");
  if (link) link.href = zdash;
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
  el.innerHTML = items.length
    ? items
        .map(
          (e) =>
            `<li><strong>${escapeHtml(e.step)}</strong> ${escapeHtml(e.detail || "")} ` +
            `<span class="meta">${escapeHtml((e.at || "").replace("T", " ").slice(0, 19))}</span></li>`
        )
        .join("")
    : '<li class="empty-hint">No cycle steps yet — Capture Step 0 or Run Loop 1.</li>';
}

function updateHealHint() {
  const hint = $("#heal-run-hint");
  if (!hint) return;
  if (!activeProject?.latest_run) {
    hint.textContent = "Select a run in Analyze to shrink to failures.";
    return;
  }
  hint.textContent = `Last run: ${activeProject.latest_run} — shrink uses its failures.`;
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

function updateProjectBanner(payoutPreview) {
  applyAiMode();
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
  if (meta) {
    meta.hidden = false;
    if (activeProject) {
      const aiLabel = isAiOn() ? "AI on" : "AI off";
      const budget = Number(activeProject.budget_usd) || 0;
      const split = activeProject.budget_split || { automation_pct: 50, human_pct: 50 };
      const parts = [activeProject.name, aiLabel];
      if (suite) parts.push(`y/${suite.name}`);
      if (suite?.plan_run_y != null) parts.push(`${suite.plan_run_y} Run=Y`);
      if (budget > 0) parts.push(`$${budget}`, `${split.automation_pct}% auto`);
      meta.textContent = parts.join(" · ");
    } else if (suite) {
      meta.textContent = [suite.name, suite.url, suite.plan_run_y != null ? `${suite.plan_run_y} Run=Y` : ""]
        .filter(Boolean)
        .join(" · ");
    }
  }
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
  $("#cycle-prompt").value = purpose;
  const paths = (activeProject.context_items || []).map((c) => c.value).filter(Boolean);
  (activeProject.documents || []).forEach((d) => paths.push(d.path));
  $("#cycle-docs").value = [...new Set(paths)].join("\n");
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
  html = html.replace(/^### (.+)$/gm, "<h4>$1</h4>");
  html = html.replace(/^## (.+)$/gm, "<h3>$1</h3>");
  html = html.replace(/^# (.+)$/gm, "<h2>$1</h2>");
  html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  html = html.replace(/^- (.+)$/gm, "<li>$1</li>");
  html = html.replace(/(<li>.*<\/li>)/gs, "<ul>$1</ul>");
  html = html.replace(/\n/g, "<br>");
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
    setStatus("AI is off — use FAQ chips or turn AI on");
    return;
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

async function loadBrahlPanel() {
  if (!state.projectId || !state.suiteName) return;
  const list = $("#brahl-report-list");
  list.innerHTML = "";

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

  if (!runs.length && !huntReports.length) {
    list.innerHTML = "<li class=\"empty-hint\">No verify runs for this suite yet.</li>";
    $("#brahl-report-body").innerHTML =
      `<p class="empty-hint">No BRAHL report for <strong>${escapeHtml(state.suiteName)}</strong> yet. Run Verify on the Loop tab, or submit a QA Hunter hunt report from Build.</p>` +
      (data.suite?.description ? `<p class="hint">${escapeHtml(data.suite.description)}</p>` : "");
    $("#brahl-report-summary").hidden = true;
    $("#brahl-hunt-artifacts").hidden = true;
    $("#brahl-report-title").textContent = state.suiteName;
    $("#brahl-report-source").textContent = "y/ suite";
    renderGoNoGo(null);
    renderVersionCompare(null);
    renderBrahlChat();
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
      });
    list.appendChild(li);
  });

  runs.forEach((r, i) => {
    const li = document.createElement("li");
    const isSel = !selectedBrahlReportId && (selectedBrahlRun ? r.name === selectedBrahlRun : i === 0 && !huntReports.length);
    if (isSel) li.classList.add("selected");
    li.innerHTML =
      `<span class="source-badge sm">Verify</span><span>${escapeHtml(r.name)}</span>` +
      `<span class="meta">${r.passes} pass · ${r.fails} fail</span>`;
    li.onclick = () =>
      selectBrahlReport(r.name, { source: "automation", source_label: "Automation", report_id: null, is_hunt: false });
    list.appendChild(li);
  });

  const pickHunt = huntReports.find((r) => r.id === selectedBrahlReportId) || huntReports[0];
  const pickRun = selectedBrahlRun || data.latest_run_name || runs[0]?.name;
  if (pickHunt && selectedBrahlReportId) {
    await selectBrahlReport(pickHunt.run_name, {
      source: pickHunt.source,
      source_label: pickHunt.source_label,
      report_id: pickHunt.id,
      is_hunt: true,
      report_path: pickHunt.report_path,
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
  const verdict = $("#gonogo-verdict");
  if (!block) return;
  if (state.avatar !== "client") {
    block.hidden = true;
    return;
  }
  block.hidden = false;
  if (!stats?.total_plans) {
    if (label) label.textContent = "Run Verify on Loop for a Go / No-Go opinion";
    if (cb) cb.checked = false;
    if (verdict) {
      verdict.classList.remove("gonogo-go", "gonogo-nogo");
      verdict.classList.add("gonogo-pending");
    }
    return;
  }
  const go =
    (stats.fails ?? 0) === 0 &&
    (stats.passes ?? 0) > 0 &&
    !(lastVersionCompare?.regression_count > 0);
  if (cb) cb.checked = go;
  if (label) {
    if (lastVersionCompare?.regression_count > 0) {
      label.textContent = `NO-GO — ${lastVersionCompare.regression_count} regression(s) vs baseline`;
    } else {
      label.textContent = go ? "GO — Launch approved" : "NO-GO — Not launch-ready";
    }
  }
  if (verdict) {
    verdict.classList.toggle("gonogo-go", go);
    verdict.classList.toggle("gonogo-nogo", !go);
    verdict.classList.remove("gonogo-pending");
  }
}

function renderBrahlSummaryStats(stats, runName) {
  const wrap = $("#brahl-report-summary");
  if (!wrap || !stats?.total_plans) {
    if (wrap) wrap.hidden = true;
    renderGoNoGo(stats?.total_plans ? stats : null);
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
  if (zdash && runName) {
    if (stats.dashboard) {
      const parts = stats.dashboard.replace(/\\/g, "/").split("/");
      if (parts[0] === "z" && parts.length >= 3) {
        zdash.href = `/api/files/z/${encodeURIComponent(parts[1])}/${parts.slice(2).join("/")}`;
      } else {
        zdash.href = `/api/files/z/${encodeURIComponent(runName)}/qoa_web_zDash.html`;
      }
    } else {
      zdash.href = `/api/files/z/${encodeURIComponent(runName)}/qoa_web_zDash.html`;
    }
    zdash.hidden = false;
  }
  renderGoNoGo(stats);
}

async function selectBrahlReport(runName, meta) {
  if (!state.suiteName) return;
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
    if (meta?.is_hunt) {
      $("#brahl-report-summary").hidden = true;
      $("#brahl-zdash-link").hidden = true;
      renderGoNoGo(null);
      renderVersionCompare(null);
      const open = $("#brahl-report-open");
      if (open && data.artifacts?.length) {
        const md = data.artifacts.find((a) => String(a).includes("hunt-report") && String(a).endsWith(".md"));
        if (md) {
          open.href = `/api/projects/${encodeURIComponent(state.projectId)}/uploads/${encodeURIComponent(PathBasename(md))}`;
          open.hidden = false;
        } else open.hidden = true;
      }
    } else {
      renderBrahlSummaryStats(data.stats, runName);
      renderVersionCompare(data.version_compare);
      const open = $("#brahl-report-open");
      open.href = `/api/files/z/${encodeURIComponent(runName)}/brahl_report.md`;
      open.hidden = false;
    }
  } catch {
    $("#brahl-report-body").innerHTML =
      '<p class="empty-hint">No zResults for this run yet. Run Verify on the Loop tab, or pick a run with results.</p>';
    $("#brahl-report-summary").hidden = true;
    $("#brahl-hunt-artifacts").hidden = true;
    $("#brahl-zdash-link").hidden = true;
    $("#brahl-report-open").hidden = true;
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
  const placeholder = includePlaceholder
    ? `<option value="">${ph}</option>`
    : "";
  return (
    placeholder +
    uniqueProjects().map((p) => `<option value="${p.id}">${escapeHtml(p.name)}</option>`).join("")
  );
}

function renderProjectSelectors() {
  const topbarWrap = $("#topbar-project");
  if (!state.avatar) {
    if (topbarWrap) topbarWrap.hidden = true;
    return;
  }
  renderTopbarProjectSelect();
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

function openAddProjectModal() {
  const modal = $("#add-project-modal");
  if (!modal) return;
  $("#new-project-name").value = "";
  $("#new-project-purpose").value = "";
  $("#new-project-url").value = "";
  $("#new-project-budget").value = "";
  $("#new-project-connector").value = "";
  $("#new-project-connector-url").value = "";
  $("#new-project-ai").checked = true;
  modal.hidden = false;
  $("#new-project-name").focus();
}

function closeAddProjectModal() {
  const modal = $("#add-project-modal");
  if (modal) modal.hidden = true;
}

async function submitAddProjectForm(ev) {
  ev.preventDefault();
  const name = $("#new-project-name")?.value.trim();
  const purpose = $("#new-project-purpose")?.value.trim() || "";
  const appUrl = $("#new-project-url")?.value.trim() || "";
  const budget = parseFloat($("#new-project-budget")?.value) || 0;
  const aiEnabled = $("#new-project-ai")?.checked !== false;
  if (!name) return;

  const context_items = [];
  if (appUrl) {
    context_items.push({ kind: "url", label: "App URL", value: appUrl });
  }
  const connLabel = $("#new-project-connector")?.value.trim();
  const connUrl = $("#new-project-connector-url")?.value.trim();
  if (connLabel && connUrl) {
    context_items.push({ kind: "connector", label: connLabel, value: connUrl });
  }

  const body = {
    name,
    purpose,
    app_url: appUrl,
    budget_usd: budget,
    ai_enabled: aiEnabled,
    context_items,
  };
  const data = await api("/api/ypad-projects", {
    method: "POST",
    body: JSON.stringify(body),
  });
  closeAddProjectModal();
  await loadSuites();
  await selectYpadProject(data.suite.name);
  setStatus(`Created: ${data.suite.name}`);
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
  const suite = state.suites.find((s) => s.name === state.suiteName);
  const title = $("#build-panel-title");
  const blurb = $("#build-panel-blurb");
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
  if (blurb && suite) {
    blurb.textContent =
      `${suite.description || "FoXYiZ + BRAHL cycle."} · ${suite.plan_run_y ?? "—"} automated plans in y/${suite.name}/`;
  }
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
    const profileCol = typeof getActiveProfile === "function" ? getActiveProfile()?.ypadDesignColumn : null;
    if (profileCol && dCols.includes(profileCol)) dCols = [profileCol];
  }
  const labels = ypadDesignColumnLabels(data);
  const cols = [...base, ...dCols];
  return { cols: cols.length ? cols : headers.slice(0, 6), labels };
}

function ypadRowMatchesFilter(row, filter) {
  if (!filter) return true;
  const q = filter.toLowerCase();
  return Object.values(row).some((v) => String(v || "").toLowerCase().includes(q));
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
    ypadState.data = await api(`/api/suites/${encodeURIComponent(state.suiteName)}/ypad/${tab}`);
  } catch {
    ypadState.data = { headers: [], rows: [], row_count: 0, env_example: "" };
  }
  renderYpadExplorer();
  if (tab === "plans") {
    ypadState.insights = computeYpadInsights(ypadState.data);
    renderYpadInsights();
  }
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
  if (!state.suiteName) return;
  try {
    const [plans, actions, designs] = await Promise.all([
      api(`/api/suites/${encodeURIComponent(state.suiteName)}/ypad/plans`),
      api(`/api/suites/${encodeURIComponent(state.suiteName)}/ypad/actions`),
      api(`/api/suites/${encodeURIComponent(state.suiteName)}/ypad/designs`),
    ]);
    ypadState.insights = {
      ...computeYpadInsights(plans),
      actionSteps: actions.row_count ?? actions.rows?.length ?? 0,
      designRows: designs.row_count ?? designs.rows?.length ?? 0,
    };
  } catch {
    ypadState.insights = null;
  }
  renderYpadInsights();
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
    `<span class="ypad-stat-pill"><strong>${auto}</strong> automated plans (Run=Y)</span>` +
    `<span class="ypad-stat-pill"><strong>${total}</strong> total plans</span>` +
    `<span class="ypad-stat-pill"><strong>${actions}</strong> action steps</span>` +
    `<span class="ypad-stat-pill"><strong>${designs}</strong> design rows</span>` +
    `<span class="ypad-stat-pill"><strong>${tagN}</strong> tags · filter by tag below</span>`;
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

async function renderBuildCostTeaser() {
  const wrap = $("#build-cost-teaser");
  const body = $("#build-cost-teaser-body");
  if (!wrap || !body || !state.projectId || state.avatar === "consultant") {
    if (wrap) wrap.hidden = true;
    return;
  }
  try {
    const { cost_meter: m } = await api(`/api/projects/${state.projectId}/cost-meter`);
    if (!m.budget_usd) {
      wrap.hidden = true;
      return;
    }
    wrap.hidden = false;
    body.innerHTML =
      `<span class="ypad-stat-pill">Budget <strong>$${m.budget_usd}</strong></span>` +
      `<span class="ypad-stat-pill">Spent ~<strong>$${m.spent_total_usd}</strong></span>` +
      `<span class="ypad-stat-pill">AI/auto <strong>$${m.spent_automation_usd}</strong></span>` +
      `<span class="ypad-stat-pill">QA Hunter <strong>$${m.spent_human_usd}</strong></span>` +
      `<span class="meta">${m.runtime_mode === "local" ? "Local Run/Loop free" : "Cloud mode"}</span>`;
  } catch {
    wrap.hidden = true;
  }
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
  if (ypadState.tab === "plans" && $("#ypad-run-y-only")?.checked) {
    rows = rows.filter((r) => {
      const pid = (r.PlanId || "").trim();
      if (pid.startsWith("PReuse_")) return false;
      return (r.Run || "").trim().toUpperCase() === "Y";
    });
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
  $("#ypad-table-wrap").hidden = isEnv || ypadState.editMode;
  $("#ypad-env-panel").hidden = !isEnv || ypadState.editMode;
  $("#ypad-csv-editor").hidden = !ypadState.editMode || isEnv;
  $("#ypad-run-y-wrap").hidden = tab !== "plans" || ypadState.editMode;
  const designsToolbar = $("#ypad-designs-toolbar");
  if (designsToolbar) designsToolbar.hidden = tab !== "designs" || ypadState.editMode;
  $("#ypad-toggle-edit").hidden = isEnv;
  $("#ypad-save").hidden = !ypadState.editMode || isEnv;
  $("#ypad-filter").hidden = ypadState.editMode;
  if (tab === "designs" && !ypadState.editMode) {
    const modeSel = $("#ypad-design-col-mode");
    if (modeSel) modeSel.value = ypadState.designColumnMode;
    $$(".ypad-design-group-chip").forEach((chip) => {
      chip.classList.toggle("active", chip.dataset.designGroup === ypadState.designGroupFilter);
    });
  }

  if (data?.paths?.length) {
    $("#ypad-meta").textContent = `${data.row_count ?? data.rows?.length ?? 0} rows · ${data.paths[0]}`;
  } else {
    $("#ypad-meta").textContent = "";
  }

  if (isEnv) {
    $("#ypad-env-example").textContent = data?.env_example || "# No ENV defined";
    return;
  }

  if (ypadState.editMode && data) {
    $("#ypad-csv-editor").value = rowsToCsv(data.headers || [], data.rows || []);
    return;
  }

  const rows = getYpadDisplayRows();
  const { cols, labels } = ypadDisplayColumnsForTab(tab, data);
  const tableWrap = $("#ypad-table-wrap");
  if (tableWrap) tableWrap.classList.toggle("ypad-table-wide", tab === "designs" && cols.length > 4);

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
  body.innerHTML = Object.entries(row)
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

function toggleYpadEdit() {
  if (ypadState.tab === "env") return;
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
  await api(`/api/suites/${encodeURIComponent(state.suiteName)}/ypad/${ypadState.tab}`, {
    method: "PUT",
    body: JSON.stringify({ headers: parsed.headers, rows: parsed.rows }),
  });
  ypadState.editMode = false;
  await loadYpadSheet(ypadState.tab);
  setStatus(`Saved y${ypadState.tab === "plans" ? "1Plans" : ypadState.tab === "actions" ? "2Actions" : "3Designs"}.csv`);
}

function openInviteHitlModal() {
  if (!state.projectId) return;
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
  const reqEl = $("#build-requirement-text");
  if (reqEl) {
    reqEl.textContent = data.requirement || "No requirement captured yet — use Refine with AI below.";
  }
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
      : `<li class="empty-hint">No manual user stories yet — add scenarios for QA Hunters below.</li>`;
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
        `<div class="chat-msg chat-${m.role}"><span class="chat-role">${m.role === "assistant" ? "BRAHL AI" : "You"}</span>${escapeHtml(m.text)}</div>`
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
    const st = await api("/api/ai/status");
    const docHint = st.reference_doc_count
      ? ` · ${st.context_doc_count} in prompt · click .md in top bar for all docs`
      : "";
    el.textContent = st.available
      ? `BRAHL AI active (${st.model || "OpenAI"})${docHint}`
      : `AI on — guided replies (OPENAI_API_KEY in f/.env)${docHint}`;
  } catch {
    el.textContent = "BRAHL AI — describe changes in chat below · .md for context docs";
  }
}

let aiDocsCache = null;

async function openAiDocsModal() {
  const modal = $("#ai-docs-modal");
  if (!modal) return;
  modal.hidden = false;
  try {
    const data = await api("/api/ai/docs");
    aiDocsCache = data.docs || [];
    renderAiDocsList();
    const firstPrompt = aiDocsCache.find((d) => d.in_prompt) || aiDocsCache[0];
    if (firstPrompt) await selectAiDoc(firstPrompt.id);
  } catch {
    $("#ai-docs-list").innerHTML = `<li class="empty-hint">Could not load AI docs.</li>`;
  }
}

function closeAiDocsModal() {
  const modal = $("#ai-docs-modal");
  if (modal) modal.hidden = true;
}

function renderAiDocsList(selectedId) {
  const list = $("#ai-docs-list");
  if (!list) return;
  list.innerHTML = (aiDocsCache || [])
    .map(
      (d) =>
        `<li class="ai-docs-list-item${d.id === selectedId ? " active" : ""}">` +
        `<button type="button" data-doc-id="${escapeHtml(d.id)}">` +
        `<strong>${escapeHtml(d.title)}</strong>` +
        (d.in_prompt ? ` <span class="ai-docs-prompt-badge">in AI prompt</span>` : "") +
        `<span class="doc-sub">${escapeHtml(d.subtitle || d.path)}</span>` +
        `</button></li>`
    )
    .join("");
  list.querySelectorAll("button[data-doc-id]").forEach((btn) => {
    btn.addEventListener("click", () => selectAiDoc(btn.dataset.docId));
  });
}

async function selectAiDoc(docId) {
  renderAiDocsList(docId);
  const title = $("#ai-docs-doc-title");
  const meta = $("#ai-docs-doc-meta");
  const body = $("#ai-docs-doc-body");
  if (body) body.textContent = "Loading…";
  try {
    const { doc } = await api(`/api/ai/docs/${encodeURIComponent(docId)}`);
    if (title) title.textContent = doc.title;
    if (meta) {
      meta.textContent = `${doc.path}${doc.in_prompt ? " · loaded into AI when AI is on" : " · reference"}`;
    }
    if (body) body.textContent = doc.content || "(empty)";
  } catch {
    if (body) body.textContent = "Failed to load document.";
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
        : "Ready — record your session or log findings"
  );
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
    recorder.onstop = () => {
      const blob = new Blob(chunks, { type: mime });
      const stamp = new Date().toISOString().replace(/[:.]/g, "-");
      huntSession.blobs.push({ blob, name: `hunt-screen-${stamp}.webm`, type: mime, kind: "screen" });
      const preview = $("#hunt-preview");
      if (preview) {
        preview.src = URL.createObjectURL(blob);
        preview.hidden = false;
      }
      stopHuntStreams();
      setHuntRecStatus(`Screen recording saved (${Math.round(blob.size / 1024)} KB)`);
      $("#btn-hunt-start")?.classList.remove("recording");
      persistHuntSession();
    };
    display.getVideoTracks()[0]?.addEventListener("ended", () => stopHuntRecording());
    recorder.start(1000);
    huntSession.mediaRecorder = recorder;
    $("#btn-hunt-start")?.classList.add("recording");
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
    recorder.onstop = () => {
      stream.getTracks().forEach((t) => t.stop());
      const blob = new Blob(chunks, { type: mime });
      const stamp = new Date().toISOString().replace(/[:.]/g, "-");
      huntSession.blobs.push({ blob, name: `hunt-audio-${stamp}.webm`, type: mime, kind: "audio" });
      setHuntRecStatus(`Audio note saved (${Math.round(blob.size / 1024)} KB)`);
      persistHuntSession();
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
  const { project } = await api(`/api/projects/${state.projectId}`, {
    method: "PATCH",
    body: JSON.stringify({ ai_enabled }),
  });
  activeProject = project;
  applyAiMode();
  loadBuildAiStatus();
  setStatus(ai_enabled ? "AI assistant enabled" : "AI off — manual Build mode");
  renderClientWorkspace();
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
  if (!isAiOn()) {
    setStatus("AI is off — turn on AI in the top bar or use manual purpose");
    return;
  }
  const input = $("#chat-input");
  const sendBtn = $("#chat-send-btn");
  const text = input.value.trim();
  if (!text || !state.projectId) return;
  input.value = "";
  input.placeholder = "Describe what you want BRAHL to test…";
  if (sendBtn) sendBtn.disabled = true;
  try {
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
    renderAiMarkdown(el, data.markdown || "");
    setStatus(data.ai ? "Heal: AI suggestions ready — review before editing CSVs" : "Heal: manual guide (no API key)");
  } catch (e) {
    renderAiMarkdown(el, `Error: ${e.message}`);
  }
}

async function shrinkPlans() {
  const runName = selectedRun || activeProject?.latest_run;
  const logEl = $("#heal-log");
  if (!runName) {
    logEl.textContent = "Select a run in Analyze first.";
    return;
  }
  try {
    const res = await api("/api/ypad/shrink", {
      method: "POST",
      body: JSON.stringify({ run_name: runName, suite_config: suiteConfigPath() }),
    });
    logEl.textContent = res.ok
      ? `Shrunk: Run=Y on ${res.run_y} failure(s), Run=N on ${res.run_n} pass(es). ${res.changed} row(s) updated.`
      : res.error || "No failures to shrink.";
    if (res.ok) await recordCycleEvent("Shrink", `Run=Y on ${res.run_y} plans`, runName);
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
    logEl.textContent = `Restored Run=Y on ${res.run_y} plan(s). ${res.changed} row(s) updated.`;
    await recordCycleEvent("Restore", "All Run=Y restored");
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
    $("#loop-log").textContent = `[Report] Written: ${res.report_path}\n`;
    if (state.projectId) {
      await api(`/api/projects/${state.projectId}/brahl/reports`, {
        method: "POST",
        body: JSON.stringify({ run_name: runName, source: "automation" }),
      });
      await recordCycleEvent("Report", res.report_path, runName);
      if ($("#panel-brahl")?.classList.contains("active")) await loadBrahlPanel();
    }
  } catch (e) {
    $("#loop-log").textContent = `[Report] Error: ${e.message}\n`;
  }
}

async function runLoopStep(stepLabel, options = {}) {
  const logEl = $("#loop-log");
  if (!state.projectId) {
    alert("Select a project on Build first.");
    return;
  }
  if (options.restoreFirst) {
    try {
      const res = await api("/api/ypad/restore", {
        method: "POST",
        body: JSON.stringify({ suite_config: suiteConfigPath() }),
      });
      logEl.textContent = `[${stepLabel}] Restored Run=Y on ${res.run_y} plan(s).\n`;
      await recordCycleEvent("Restore", "Verify prep — all Run=Y");
    } catch (e) {
      logEl.textContent = `[${stepLabel}] Restore error: ${e.message}\n`;
      return;
    }
  }
  if (options.shrinkFirst) {
    const runName = selectedRun || activeProject?.latest_run;
    if (!runName) {
      logEl.textContent += `[${stepLabel}] Select a run in Analyze for shrink.\n`;
      return;
    }
    try {
      const res = await api("/api/ypad/shrink", {
        method: "POST",
        body: JSON.stringify({ run_name: runName, suite_config: suiteConfigPath() }),
      });
      if (res.ok) {
        logEl.textContent += `[${stepLabel}] Shrunk to ${res.run_y} failure(s).\n`;
        await recordCycleEvent("Shrink", `Loop prep — ${res.run_y} plans`, runName);
      } else {
        logEl.textContent += `[${stepLabel}] ${res.error || "Shrink skipped"}\n`;
      }
    } catch (e) {
      logEl.textContent += `[${stepLabel}] Shrink error: ${e.message}\n`;
      return;
    }
  }
  await startRun(stepLabel);
}

async function captureContext() {
  if (!state.projectId || !activeProject) {
    alert("Select a project first.");
    return;
  }
  const prompt = activeProject.purpose || activeProject.prompt || "";
  const documents = (activeProject.context_items || [])
    .filter((c) => c.kind === "document" || c.kind === "connector")
    .map((c) => ({ name: c.label, path: c.value }));
  const config_path = $("#config-select").value;
  const logEl = $("#loop-log");
  try {
    const res = await api("/api/context", {
      method: "POST",
      body: JSON.stringify({ prompt, config_path, documents, project_id: state.projectId }),
    });
    logEl.textContent = `[Step 0] Context saved: ${res.context_path}\n`;
    await recordCycleEvent("Step 0", res.context_path);
    await refreshActiveProject();
  } catch (e) {
    logEl.textContent = `[Step 0] Error: ${e.message}\n`;
  }
}

async function loadRuns() {
  const suite = state.suiteName || "qoa_web";
  const { runs } = await api(`/api/runs?suite=${encodeURIComponent(suite)}`);
  const list = $("#runs-list");
  if (!list) return;
  list.innerHTML = runs.length ? "" : `<li>No ${escapeHtml(suite)} runs yet</li>`;
  runs.forEach((r, i) => {
    const li = document.createElement("li");
    li.innerHTML = `${escapeHtml(r.name)}<span class="meta">${r.passes} pass · ${r.fails} fail</span>`;
    li.onclick = () => selectRun(r.name, li);
    list.appendChild(li);
    if (i === 0) selectRun(r.name, li);
  });
}

async function selectRun(name, li) {
  selectedRun = name;
  lastAnalyzeMarkdown = "";
  renderAiMarkdown($("#analyze-ai-result"), "");
  renderAiMarkdown($("#heal-ai-result"), "");
  $$("#runs-list li").forEach((el) => el.classList.remove("selected"));
  if (li) li.classList.add("selected");
  const { failures } = await api(`/api/runs/${encodeURIComponent(name)}/failures`);
  const tbody = $("#failures-body");
  tbody.innerHTML = failures.length
    ? failures
        .map(
          (f) =>
            `<tr><td>${escapeHtml(f.planId)}</td><td>${escapeHtml(f.stepId)}</td><td>${escapeHtml(f.output)}</td></tr>`
        )
        .join("")
    : "<tr><td colspan='3'>No failures</td></tr>";
  const suite = state.suiteName || name.split("_").slice(2).join("_") || "qoa_web";
  $("#dash-link").innerHTML = `<a href="/api/files/z/${encodeURIComponent(name)}/${encodeURIComponent(suite)}_zDash.html" target="_blank">Open zDash</a>`;
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
      /* report file may not exist yet */
    }
  }
}

async function startRun(stepLabel) {
  if (!state.projectId) {
    alert("Select a project on Build first.");
    return;
  }
  const configPath = $("#config-select")?.value;
  if (!configPath) {
    alert("No fStart config for this project — click New to create one.");
    return;
  }
  const logEl = stepLabel.startsWith("Loop") || stepLabel === "Verify" ? $("#loop-log") : $("#run-log");
  if (stepLabel === "Run") {
    logEl.textContent = "";
    const post = $("#run-post-actions");
    if (post) post.hidden = true;
  }
  $("#btn-run").disabled = true;
  $("#progress-bar").style.width = "10%";
  const job = await api("/api/jobs", {
    method: "POST",
    body: JSON.stringify({ config_path: configPath, step_label: stepLabel }),
  });
  if (pollTimer) clearInterval(pollTimer);
  pollTimer = setInterval(async () => {
    const j = await api(`/api/jobs/${job.job_id}`);
    logEl.textContent = j.log_lines.join("\n");
    if (j.status === "completed" || j.status === "failed") {
      clearInterval(pollTimer);
      $("#btn-run").disabled = false;
      $("#progress-bar").style.width = j.status === "completed" ? "100%" : "60%";
      if (j.output_dir && state.projectId) {
        const runName = j.output_dir.replace(/\\/g, "/").split("/").pop();
        await api(`/api/projects/${state.projectId}`, {
          method: "PATCH",
          body: JSON.stringify({ latest_run: runName }),
        });
        await recordCycleEvent(stepLabel, j.status === "completed" ? "completed" : "failed", runName);
        selectedRun = runName;
      }
      loadRuns();
      await refreshActiveProject();
      if (stepLabel === "Run" && j.status === "completed" && j.output_dir) {
        const runName = j.output_dir.replace(/\\/g, "/").split("/").pop();
        showRunPostActions(runName);
        setStatus(`Run complete — review in Analyze or open zDash`);
      }
      if (j.status === "completed" && j.output_dir) {
        const runName = j.output_dir.replace(/\\/g, "/").split("/").pop();
        if (stepLabel === "Verify" || stepLabel.startsWith("Loop")) {
          await autoEnsureBrahlReport(runName, stepLabel);
          if ($("#panel-brahl")?.classList.contains("active")) await loadBrahlPanel();
        }
      }
    }
  }, 800);
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

async function openFstartNew() {
  const suite = state.suiteName;
  if (!suite) return;
  let data;
  try {
    data = await api(`/api/configs?suite=${encodeURIComponent(suite)}`);
  } catch {
    return;
  }
  if (!data.configs?.length) {
    try {
      const created = await api("/api/configs", {
        method: "POST",
        body: JSON.stringify({ suite_name: suite, variant: "verify" }),
      });
      await loadConfigsForSuite();
      fstartEditorPath = created.path;
      $("#fstart-modal-title").textContent = "New fStart config";
      $("#fstart-modal-path").textContent = created.path;
      $("#fstart-json-editor").value = JSON.stringify(created.content, null, 2);
      $("#fstart-delete").hidden = false;
      $("#fstart-json-error").hidden = true;
      $("#fstart-modal").hidden = false;
      return;
    } catch (e) {
      setStatus(e.message);
      return;
    }
  }
  const hasSmoke = data.configs.some((c) => c.toLowerCase().includes("smoke"));
  const suffix = hasSmoke ? "custom" : "smoke";
  fstartEditorPath = `f/fStart_${suite}_${suffix}.json`;
  const template = data.template || {
    configs: [`y/${suite}/${suite}.json`],
    thread_count: 1,
    timeout: 10,
    headless: false,
    debug: false,
    tags: [],
  };
  $("#fstart-modal-title").textContent = "New fStart config";
  $("#fstart-modal-path").textContent = fstartEditorPath;
  $("#fstart-json-editor").value = JSON.stringify(template, null, 2);
  $("#fstart-delete").hidden = true;
  $("#fstart-json-error").hidden = true;
  $("#fstart-modal").hidden = false;
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
    const data = await api(`/api/configs?suite=${encodeURIComponent(suite)}`);
    const configs = data.configs || [];
    if (configs.length) {
      sel.innerHTML = configs.map((c) => `<option value="${escapeHtml(c)}">${escapeHtml(c)}</option>`).join("");
      sel.value = data.default && configs.includes(data.default) ? data.default : configs[0];
      if (hint) hint.hidden = true;
      if (runBtn) runBtn.disabled = false;
    } else {
      sel.innerHTML = '<option value="">— none —</option>';
      if (hint) hint.hidden = false;
      if (runBtn) runBtn.disabled = true;
    }
  } catch {
    sel.innerHTML = '<option value="">— error —</option>';
    if (runBtn) runBtn.disabled = true;
  }
}

function initAvatarGate() {
  state.profile = getActiveProfile();
  applyProfileUI();
  bindAvatarControls();
  const profile = state.profile;
  let avatar = state.avatar;
  if (profile) {
    if (!avatar || !profileAllowsAvatar(profile, avatar)) {
      avatar = profile.defaultAvatar;
    }
    setAvatar(avatar);
    return;
  }
  if (!avatar) $("#avatar-gate").hidden = false;
  else setAvatar(avatar);
}

$$(".phase-btn").forEach((btn) => {
  btn.addEventListener("click", () => showPhase(btn.dataset.phase));
});

$("#topbar-project-select")?.addEventListener("change", (e) => {
  selectYpadProject(e.target.value);
});
$("#client-empty-add")?.addEventListener("click", createNewProject);
$("#btn-fstart-edit")?.addEventListener("click", openFstartEditor);
$("#btn-fstart-new")?.addEventListener("click", openFstartNew);
$("#fstart-save")?.addEventListener("click", saveFstartEditor);
$("#fstart-delete")?.addEventListener("click", deleteFstartEditor);
$("#fstart-cancel")?.addEventListener("click", closeFstartModal);
$("#add-project-form")?.addEventListener("submit", submitAddProjectForm);
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
  $("#add-context-panel").hidden = false;
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
$("#build-goto-cost")?.addEventListener("click", () => showPhase("cost"));
$("#cost-runtime-local")?.addEventListener("change", () => saveCostRuntimeMode("local"));
$("#cost-runtime-cloud")?.addEventListener("change", () => saveCostRuntimeMode("cloud"));
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && !$("#ypad-detail-drawer")?.hidden) closeYpadDrawer();
});
$("#btn-join-hitl")?.addEventListener("click", joinHitl);
$("#btn-hitl-submit")?.addEventListener("click", submitHitlReport);
$("#btn-hunt-start")?.addEventListener("click", startHuntRecording);
$("#btn-hunt-stop")?.addEventListener("click", stopHuntRecording);
$("#btn-hunt-audio")?.addEventListener("click", startHuntAudioNote);
$("#btn-hunt-add-issue")?.addEventListener("click", addHuntIssueFromForm);
$("#btn-hunt-screenshot")?.addEventListener("click", () => $("#hunt-screenshot-file")?.click());
$("#hunt-screenshot-file")?.addEventListener("change", (e) => {
  const f = e.target.files?.[0];
  if (f) attachHuntScreenshot(f);
  e.target.value = "";
});
$("#btn-run")?.addEventListener("click", () => startRun("Run"));
$("#btn-loop1")?.addEventListener("click", () => runLoopStep("Loop 1"));
$("#btn-loop2")?.addEventListener("click", () => runLoopStep("Loop 2", { shrinkFirst: true }));
$("#btn-loop3")?.addEventListener("click", () => runLoopStep("Loop 3", { shrinkFirst: true }));
$("#btn-verify")?.addEventListener("click", () => runLoopStep("Verify", { restoreFirst: true }));
$("#btn-gen-report")?.addEventListener("click", generateReport);
$("#btn-shrink-plans")?.addEventListener("click", shrinkPlans);
$("#btn-restore-plans")?.addEventListener("click", restorePlans);
$("#btn-context")?.addEventListener("click", captureContext);
$("#btn-refresh-runs")?.addEventListener("click", loadRuns);
$("#btn-analyze-ai")?.addEventListener("click", runAnalyzeAi);
$("#btn-heal-ai")?.addEventListener("click", runHealAi);
$("#brahl-chat-form")?.addEventListener("submit", sendBrahlChat);
$("#atomic77-chat-form")?.addEventListener("submit", (ev) => sendAtomic77Chat(ev));
$$(".atomic77-faq-chip").forEach((chip) => {
  chip.addEventListener("click", () => sendAtomic77Chat({ preventDefault: () => {} }, chip.dataset.faq));
});
$("#btn-link-run-report")?.addEventListener("click", linkRunReport);
$("#link-report-form")?.addEventListener("submit", submitLinkReportForm);
$("#link-report-cancel")?.addEventListener("click", closeLinkReportModal);
$("#btn-goto-analyze")?.addEventListener("click", () => showPhase("analyze"));
$$(".phase-progress-dot").forEach((dot) => {
  dot.addEventListener("click", () => showPhase(dot.dataset.phase));
});

initAvatarGate();
bindPersonaBadge();
window.QoaTheme?.initTheme?.();
window.addEventListener("qoa-theme-change", (ev) => {
  updateVisualRewardRail();
  if (state.phase === "cost") loadCostPanel();
  const title = $("#app-title");
  if (title) {
    title.textContent =
      ev.detail?.theme === "arena" && state.avatar ? "BRAHL Arena" : "BRAHL Web — f(x,y)=z";
  }
});
applyAvatarLabelsToDom();
applyAvatarModeNav();
loadAppVersion();
checkHealth();
loadSuites();
loadConfigsForSuite();
loadRuns();
setInterval(checkHealth, 15000);
