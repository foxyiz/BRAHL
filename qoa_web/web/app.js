const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

const STORAGE_AVATAR = "qoa_web_avatar";
const STORAGE_PROJECT = "qoa_web_project_id";

function maybeResetFromQuery() {
  if (new URLSearchParams(location.search).get("reset") === "1") {
    localStorage.removeItem(STORAGE_AVATAR);
    localStorage.removeItem(STORAGE_PROJECT);
    return true;
  }
  return false;
}
const didReset = maybeResetFromQuery();

let pollTimer = null;
let selectedRun = null;
let selectedBrahlRun = null;
let activeProject = null;

const state = {
  avatar: didReset ? null : localStorage.getItem(STORAGE_AVATAR) || null,
  projectId: didReset ? null : localStorage.getItem(STORAGE_PROJECT) || null,
  projects: [],
  phase: "build",
  consultantFilter: "",
  consultantSort: "name",
  consultantCompact: false,
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

function showPhase(name) {
  state.phase = name;
  $$(".phase-btn").forEach((b) => b.classList.toggle("active", b.dataset.phase === name));
  $$(".panel").forEach((p) => p.classList.toggle("active", p.dataset.panel === name));
  updatePhaseLock();
  if (!state.projectId && name !== "build") {
    setStatus(state.avatar === "client" && !state.projects.length ? "Add your first project" : "Select a project on Build first");
  } else {
    syncProjectStatus();
  }
  if (name === "brahl" && state.projectId) loadBrahlPanel();
  renderPhaseProgress();
}

function updateLockedPhaseActions() {
  const showAdd = state.avatar === "client" && !state.projects.length;
  const showBuild = state.avatar && !state.projectId && !showAdd;
  $$(".phase-locked-add").forEach((btn) => {
    btn.hidden = !showAdd;
  });
  $$(".phase-locked-build").forEach((btn) => {
    btn.hidden = !showBuild;
  });
}

function updatePhaseLock() {
  const locked = !state.projectId;
  ["run", "analyze", "heal", "loop", "brahl"].forEach((phase) => {
    const el = $(`#${phase}-locked`);
    const content = $(`#${phase}-content`);
    if (el) el.hidden = !locked;
    if (content) content.hidden = locked;
  });
  updateLockedPhaseActions();
  $$(".phase-btn").forEach((btn) => {
    if (btn.dataset.phase === "build") return;
    btn.disabled = !state.avatar;
    btn.title = locked ? "Open to see next steps" : "";
  });
}

async function setAvatar(avatar) {
  state.avatar = avatar;
  localStorage.setItem(STORAGE_AVATAR, avatar);
  $$(".avatar-btn").forEach((b) => b.classList.toggle("active", b.dataset.avatar === avatar));
  $("#avatar-gate").hidden = true;
  $("#build-no-avatar").hidden = !!avatar;
  $("#build-client").hidden = avatar !== "client";
  $("#build-consultant").hidden = avatar !== "consultant";
  $$(".phase-btn").forEach((btn) => {
    if (btn.dataset.phase !== "build") btn.disabled = !avatar;
  });
  if (avatar === "consultant" && state.projectId && !state.projects.some((p) => p.id === state.projectId)) {
    state.projectId = null;
    localStorage.removeItem(STORAGE_PROJECT);
    activeProject = null;
  }
  await loadProjects();
  syncProjectStatus();
}

async function loadProjects() {
  if (!state.avatar) return;
  const role = state.avatar === "consultant" ? "consultant" : "client";
  const { projects } = await api(`/api/projects?role=${role}`);
  state.projects = projects;
  if (state.avatar === "client") renderClientWorkspace();
  else renderConsultantWorkspace();
  renderProjectSelectors();
  if (state.projectId) {
    await refreshActiveProject();
  } else if (state.avatar === "client" && projects.length) {
    await selectProject(projects[0].id);
  } else if (state.avatar === "consultant" && projects.length && !state.projectId) {
    await selectProject(projects[0].id);
  }
  updatePhaseLock();
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
    syncProjectToUI();
    renderBrahlChat();
    renderCycleHistory();
    renderPhaseProgress();
    updateHealHint();
  } catch {
    state.projectId = null;
    localStorage.removeItem(STORAGE_PROJECT);
    activeProject = null;
    updateProjectBanner();
  }
}

async function selectProject(projectId) {
  if (!projectId) return;
  state.projectId = projectId;
  selectedBrahlRun = null;
  localStorage.setItem(STORAGE_PROJECT, projectId);
  await refreshActiveProject();
  if (state.avatar === "client") {
    renderClientWorkspace();
  } else {
    renderConsultantWorkspace();
  }
  renderProjectSelectors();
  applyAiMode();
  updatePhaseLock();
  if ($("#panel-brahl")?.classList.contains("active")) await loadBrahlPanel();
}

function isAiOn() {
  return activeProject?.ai_enabled !== false;
}

function applyAiMode() {
  const on = isAiOn();
  const hasProject = !!activeProject;
  $("#ai-toggle-wrap").hidden = !hasProject;
  renderProjectSelectors();
  if (hasProject) {
    $("#ai-toggle").checked = on;
  }
  $("#ai-toggle-label").textContent = on ? "AI on" : "AI off";
  $("#ai-toggle-wrap")?.classList.toggle("ai-off", !on);
  syncProjectStatus();

  $("#client-ai-build").hidden = !on;
  $("#client-manual-build").hidden = on;
  if (!on && activeProject) {
    $("#manual-purpose").value = activeProject.purpose || activeProject.prompt || "";
  }

  $("#brahl-ai-chat").hidden = !on;
  $("#brahl-ai-off-hint").hidden = on;

  const hitlHint = $("#consultant-hitl-hint");
  if (hitlHint) hitlHint.hidden = on;
  const submitBtn = $("#btn-hitl-submit");
  if (submitBtn) {
    submitBtn.textContent = on
      ? "Submit Human in the Loop report"
      : "Upload Automation + AI report";
  }
}

function syncProjectStatus() {
  const strip = $("#context-strip");
  if (!state.avatar) {
    strip?.classList.remove("has-project");
    setStatus("Choose an avatar to start");
    return;
  }
  if (!activeProject) {
    strip?.classList.remove("has-project");
    setStatus(
      state.avatar === "client"
        ? state.projects.length
          ? "Select or create a project"
          : "Add your first project"
        : state.projects.length
          ? "Select a client project to join"
          : "No client projects available yet"
    );
    return;
  }
  strip?.classList.add("has-project");
  const phaseHints = {
    build: state.avatar === "consultant" ? "Join a project or review client chat" : "Describe purpose · set budget · add context",
    run: "Configure fStart · Run engine",
    analyze: "Refresh runs · review failures",
    heal: "Fix yPAD from Analyze failures",
    loop: "Capture Step 0 · Loop 1 · Verify full",
    brahl: "Review reports · chat with model",
  };
  setStatus(phaseHints[state.phase] || "Project active");
}

function renderPhaseProgress() {
  const bar = $("#phase-progress");
  if (!bar) return;
  if (!state.projectId || !activeProject) {
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
  };
  $$(".phase-progress-step").forEach((el) => {
    const ph = el.dataset.phase;
    el.classList.toggle("done", !!done[ph]);
    el.classList.toggle("current", ph === state.phase);
  });
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
  if (!activeProject) {
    if (meta) meta.hidden = true;
    strip?.classList.remove("has-project");
    const hitlEl = $("#project-banner-hitl");
    if (hitlEl) hitlEl.hidden = true;
    return;
  }
  strip?.classList.add("has-project");
  const budget = Number(activeProject.budget_usd) || 0;
  const split = activeProject.budget_split || { automation_pct: 50, human_pct: 50 };
  const hitl = (activeProject.hitl_consultants || []).length;
  const aiLabel = isAiOn() ? "AI on" : "AI off";
  if (meta) {
    meta.hidden = false;
    meta.textContent =
      `${activeProject.name} · ${aiLabel} · $${budget} · ${split.automation_pct}% auto / ${split.human_pct}% HITL · ${hitl} HITL · ${(activeProject.reports || []).length} report(s)`;
  }
  const hitlEl = $("#project-banner-hitl");
  if (hitl > 0 && payoutPreview?.length) {
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

async function loadBrahlPanel() {
  if (!state.projectId) return;
  const data = await api(`/api/projects/${state.projectId}/brahl/reports`);
  const list = $("#brahl-report-list");
  list.innerHTML = "";
  if (!data.reports.length) {
    list.innerHTML = "<li class=\"empty-hint\">No reports yet.</li>";
    $("#brahl-report-body").innerHTML = "<p class=\"empty-hint\">No BRAHL report for this project yet. Run Loop → Verify or link a run.</p>";
    $("#brahl-report-title").textContent = "";
    $("#brahl-report-source").textContent = "";
    $("#brahl-report-open").hidden = true;
    renderBrahlChat();
    return;
  }
  data.reports.forEach((r, i) => {
    const li = document.createElement("li");
    const isSel = selectedBrahlRun ? r.run_name === selectedBrahlRun : i === 0;
    if (isSel) li.classList.add("selected");
    li.innerHTML = `<span class="source-badge sm">${escapeHtml(r.source_label)}</span><span>${escapeHtml(r.run_name)}</span>`;
    li.onclick = () => selectBrahlReport(r.run_name, r);
    list.appendChild(li);
  });
  const pick = selectedBrahlRun || data.reports.find((r) => r.has_file !== false && r.run_name)?.run_name || data.latest_run_name;
  const meta = data.reports.find((r) => r.run_name === pick) || data.reports.find((r) => r.has_file !== false) || data.reports[0];
  if (pick && meta) await selectBrahlReport(pick, meta);
  renderBrahlChat();
}

async function selectBrahlReport(runName, meta) {
  selectedBrahlRun = runName;
  $$("#brahl-report-list li").forEach((li) => li.classList.remove("selected"));
  $$("#brahl-report-list li").forEach((li) => {
    if (li.textContent.includes(runName)) li.classList.add("selected");
  });
  $("#brahl-report-title").textContent = runName;
  const srcEl = $("#brahl-report-source");
  srcEl.textContent = meta?.source_label || "BRAHL";
  srcEl.className = `source-badge source-${meta?.source || "automation"}`;
  try {
    const data = await api(
      `/api/projects/${state.projectId}/brahl/reports/${encodeURIComponent(runName)}/content`
    );
    $("#brahl-report-body").innerHTML = renderMarkdown(data.markdown);
    const open = $("#brahl-report-open");
    open.href = `/api/files/z/${encodeURIComponent(runName)}/brahl_report.md`;
    open.hidden = false;
  } catch {
    $("#brahl-report-body").innerHTML = "<p class=\"empty-hint\">Report file not found on disk.</p>";
    $("#brahl-report-open").hidden = true;
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

async function linkRunReport() {
  if (!state.projectId) return;
  const runName = prompt("Verify run folder name (e.g. 20260703_120842_qoa_web):");
  if (!runName?.trim()) return;
  const source = prompt(
    "Source: automation | automation_ai | human_in_the_loop | human_ai | human_automation",
    isAiOn() ? "automation" : "automation_ai"
  );
  await api(`/api/projects/${state.projectId}/brahl/reports`, {
    method: "POST",
    body: JSON.stringify({ run_name: runName.trim(), source: (source || "automation").trim() }),
  });
  await refreshActiveProject();
  await loadBrahlPanel();
}

function projectOptionsHtml(includePlaceholder = false) {
  const placeholder = includePlaceholder
    ? `<option value="">${state.avatar === "consultant" ? "Select a project…" : "Select project…"}</option>`
    : "";
  return (
    placeholder +
    state.projects.map((p) => `<option value="${p.id}">${escapeHtml(p.name)}</option>`).join("")
  );
}

function renderProjectSelectors() {
  const topbarWrap = $("#topbar-project");
  const topbarSel = $("#topbar-project-select");
  const topbarAdd = $("#topbar-add-project");
  const clientSel = $("#client-project-select");
  const clientAddBlock = $("#client-add-project-block");
  const clientNewBtn = $("#btn-new-project");
  const consultantSel = $("#consultant-project-select");
  const consultantNoProjects = $("#consultant-no-projects");

  if (!state.avatar) {
    if (topbarWrap) topbarWrap.hidden = true;
    return;
  }
  if (topbarWrap) topbarWrap.hidden = false;

  const isClient = state.avatar === "client";
  const isConsultant = state.avatar === "consultant";
  const hasProjects = state.projects.length > 0;

  if (isClient && !hasProjects) {
    if (topbarSel) topbarSel.hidden = true;
    if (topbarAdd) topbarAdd.hidden = false;
    if (clientSel) clientSel.hidden = true;
    if (clientNewBtn) clientNewBtn.hidden = true;
    if (clientAddBlock) clientAddBlock.hidden = false;
  } else if (isClient) {
    const opts = projectOptionsHtml();
    if (topbarSel) {
      topbarSel.hidden = false;
      topbarSel.innerHTML = opts;
      if (state.projectId) topbarSel.value = state.projectId;
    }
    if (topbarAdd) topbarAdd.hidden = true;
    if (clientSel) {
      clientSel.hidden = false;
      clientSel.innerHTML = opts;
      if (state.projectId) clientSel.value = state.projectId;
    }
    if (clientNewBtn) clientNewBtn.hidden = false;
    if (clientAddBlock) clientAddBlock.hidden = true;
  } else if (isConsultant) {
    if (topbarAdd) topbarAdd.hidden = true;
    if (!hasProjects) {
      if (topbarSel) topbarSel.hidden = true;
      if (consultantSel) consultantSel.hidden = true;
      if (consultantNoProjects) consultantNoProjects.hidden = false;
    } else {
      const opts = projectOptionsHtml(true);
      if (topbarSel) {
        topbarSel.hidden = false;
        topbarSel.innerHTML = opts;
        if (state.projectId) topbarSel.value = state.projectId;
      }
      if (consultantSel) {
        consultantSel.hidden = false;
        consultantSel.innerHTML = opts;
        if (state.projectId) consultantSel.value = state.projectId;
      }
      if (consultantNoProjects) consultantNoProjects.hidden = true;
    }
    renderConsultantProjects();
  }
}

function renderBuildChecklist() {
  const el = $("#build-checklist");
  if (!el || state.avatar !== "client") return;
  const hasProject = !!activeProject;
  el.hidden = !hasProject;
  if (!hasProject) return;

  const userMsgs = (activeProject.chat_messages || []).filter((m) => m.role === "user");
  const hasPurpose =
    !!(activeProject.purpose || activeProject.prompt || "").trim() || userMsgs.length > 0;
  const hasVerify =
    !!(activeProject.reports || []).length || !!(activeProject.latest_run || "").trim();

  const setStep = (step, done) => {
    const item = el.querySelector(`[data-step="${step}"]`);
    if (item) item.classList.toggle("done", done);
  };
  setStep("project", true);
  setStep("purpose", hasPurpose);
  setStep("verify", hasVerify);
}

function openAddProjectModal() {
  if (state.avatar !== "client") return;
  const modal = $("#add-project-modal");
  const nameInput = $("#new-project-name");
  const purposeInput = $("#new-project-purpose");
  if (!modal || !nameInput) return;
  nameInput.value = "";
  if (purposeInput) purposeInput.value = "";
  modal.hidden = false;
  nameInput.focus();
}

function closeAddProjectModal() {
  const modal = $("#add-project-modal");
  if (modal) modal.hidden = true;
}

async function submitAddProjectForm(ev) {
  ev.preventDefault();
  const name = $("#new-project-name")?.value.trim();
  const purpose = $("#new-project-purpose")?.value.trim() || "";
  if (!name) return;
  const body = { name };
  if (purpose) {
    body.purpose = purpose;
    body.prompt = purpose;
  }
  const { project } = await api("/api/projects", {
    method: "POST",
    body: JSON.stringify(body),
  });
  closeAddProjectModal();
  await loadProjects();
  await selectProject(project.id);
  setStatus(`Created: ${project.name}`);
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

function renderClientWorkspace() {
  const has = !!activeProject;
  $("#client-no-project").hidden = has;
  $("#client-workspace").hidden = !has;
  if (!has) {
    renderBuildChecklist();
    return;
  }
  renderBuildChecklist();
  renderChat($("#chat-thread"), activeProject.chat_messages || []);
  renderContextChips($("#context-chips"), activeProject.context_items || []);
  $("#budget-usd").value = activeProject.budget_usd || "";
  const auto = activeProject.budget_split?.automation_pct ?? 50;
  $("#budget-split").value = auto;
  $("#auto-pct").textContent = auto;
  $("#human-pct").textContent = 100 - auto;
  renderHitlRoster(activeProject);
  $("#add-context-panel").hidden = true;
  applyAiMode();
}

function renderChat(el, messages) {
  if (!el) return;
  el.innerHTML = (messages || [])
    .map(
      (m) =>
        `<div class="chat-msg chat-${m.role}"><span class="chat-role">${m.role === "assistant" ? "BRAHL AI" : "You"}</span>${escapeHtml(m.text)}</div>`
    )
    .join("");
  el.scrollTop = el.scrollHeight;
}

function renderContextChips(el, items) {
  if (!el) return;
  el.innerHTML = (items || [])
    .map(
      (c) =>
        `<span class="ctx-chip" title="${escapeHtml(c.value)}">${escapeHtml(c.label || c.kind)}</span>`
    )
    .join("");
}

function renderClientProjectSelect() {
  renderProjectSelectors();
}

function goToBuildPanel() {
  showPhase("build");
}

function renderHitlRoster(project) {
  const el = $("#hitl-roster");
  const team = project.hitl_consultants || [];
  if (!team.length) {
    el.innerHTML = "<p class=\"empty-hint\">No Human in the Loop consultants yet.</p>";
    return;
  }
  el.innerHTML =
    "<h4>Human in the Loop team</h4>" +
    team
      .map((c) => {
        const d = c.deliverables || {};
        return `<div class="hitl-member">${escapeHtml(c.name)} — ${d.critical_issues || 0} critical, ${d.reports_submitted || 0} reports, ${d.time_hours || 0}h</div>`;
      })
      .join("");
}

function getConsultantProjectsSorted() {
  const q = state.consultantFilter.trim().toLowerCase();
  let list = state.projects.filter((p) => {
    if (!q) return true;
    const hay = `${p.name} ${p.purpose || p.prompt || ""} ${p.status || ""}`.toLowerCase();
    return hay.includes(q);
  });
  list = [...list];
  if (state.consultantSort === "budget-desc") {
    list.sort((a, b) => (Number(b.budget_usd) || 0) - (Number(a.budget_usd) || 0));
  } else if (state.consultantSort === "hitl-desc") {
    list.sort(
      (a, b) =>
        (b.hitl_consultants || []).length - (a.hitl_consultants || []).length ||
        a.name.localeCompare(b.name)
    );
  } else {
    list.sort((a, b) => a.name.localeCompare(b.name));
  }
  return list;
}

function renderConsultantProjects() {
  const box = $("#consultant-projects");
  const toolbar = $("#consultant-project-toolbar");
  box.innerHTML = "";
  if (!state.projects.length) {
    if (toolbar) toolbar.hidden = true;
    box.innerHTML = "<p class=\"empty-hint\">No client projects yet.</p>";
    return;
  }
  if (toolbar) toolbar.hidden = false;
  const grid = $("#consultant-projects");
  if (grid) grid.classList.toggle("compact-hidden", state.consultantCompact);
  const list = getConsultantProjectsSorted();
  if (!list.length) {
    box.innerHTML = "<p class=\"empty-hint\">No projects match your filter.</p>";
    return;
  }
  list.forEach((p) => {
    const card = document.createElement("article");
    const selected = state.projectId === p.id;
    const joinedOnCard =
      selected &&
      activeProject &&
      (activeProject.hitl_consultants || []).some((c) => c.id === "local-hitl-consultant");
    card.className = "project-card" + (selected ? " selected" : "");
    const hitl = (p.hitl_consultants || []).length;
    card.innerHTML = `
      <h4>${escapeHtml(p.name)}</h4>
      <p class="project-stats">$${p.budget_usd || 0} · ${hitl} HITL · ${escapeHtml(p.status)}</p>
      <p class="project-url">${escapeHtml((p.purpose || p.prompt || "").slice(0, 80))}</p>`;
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "project-join-btn";
    if (selected && !joinedOnCard) {
      btn.textContent = "Selected — Join as HITL";
      btn.classList.add("primary");
      card.classList.add("join-open");
    } else if (selected) {
      btn.textContent = "Selected";
      btn.classList.add("primary");
    } else {
      btn.textContent = "Open project";
    }
    btn.onclick = () => selectProject(p.id);
    card.appendChild(btn);
    box.appendChild(card);
  });
}

function renderConsultantWorkspace() {
  const ws = $("#consultant-workspace");
  if (!activeProject) {
    ws.hidden = true;
    return;
  }
  ws.hidden = false;
  $("#consultant-project-title").textContent = activeProject.name;
  renderChat($("#consultant-client-chat"), activeProject.chat_messages || []);
  renderContextChips($("#consultant-context"), activeProject.context_items || []);
  const joined = (activeProject.hitl_consultants || []).some((c) => c.id === "local-hitl-consultant");
  $("#btn-join-hitl").hidden = joined;
  $("#consultant-deliver").hidden = !joined;
  applyAiMode();
}

async function createNewProject() {
  openAddProjectModal();
}

async function toggleAiMode() {
  if (!state.projectId) return;
  const ai_enabled = $("#ai-toggle").checked;
  const { project } = await api(`/api/projects/${state.projectId}`, {
    method: "PATCH",
    body: JSON.stringify({ ai_enabled }),
  });
  activeProject = project;
  applyAiMode();
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
  if (!isAiOn()) return;
  const input = $("#chat-input");
  const text = input.value.trim();
  if (!text || !state.projectId) return;
  input.value = "";
  const data = await api(`/api/projects/${state.projectId}/chat`, {
    method: "POST",
    body: JSON.stringify({ text }),
  });
  activeProject = data.project;
  renderClientWorkspace();
  renderBuildChecklist();
  syncProjectToUI();
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
  $("#add-context-panel").hidden = true;
  renderClientWorkspace();
  syncProjectToUI();
  if (kind === "url") {
    await api(`/api/projects/${state.projectId}`, {
      method: "PATCH",
      body: JSON.stringify({ app_url: value }),
    });
    await refreshActiveProject();
  }
}

async function saveBudget() {
  if (!state.projectId) return;
  const budget_usd = parseFloat($("#budget-usd").value) || 0;
  const automation_pct = parseInt($("#budget-split").value, 10);
  const { project } = await api(`/api/projects/${state.projectId}`, {
    method: "PATCH",
    body: JSON.stringify({
      budget_usd,
      budget_split: { automation_pct, human_pct: 100 - automation_pct },
    }),
  });
  activeProject = project;
  await refreshActiveProject();
  renderClientWorkspace();
}

async function joinHitl() {
  if (!state.projectId) return;
  const data = await api(`/api/projects/${state.projectId}/join-hitl`, { method: "POST" });
  activeProject = data.project;
  await refreshActiveProject();
  renderConsultantWorkspace();
  setStatus("Joined as Human in the Loop");
}

async function submitHitlReport() {
  if (!state.projectId) return;
  const runName = selectedRun || prompt("Verify run folder name:");
  if (!runName?.trim()) return;
  await api(`/api/projects/${state.projectId}/submit-hitl-report`, {
    method: "POST",
    body: JSON.stringify({
      run_name: runName.trim(),
      report_path: `z/${runName.trim()}/brahl_report.md`,
      critical_issues: parseInt($("#hitl-critical").value, 10) || 0,
      time_hours: parseFloat($("#hitl-hours").value) || 0,
      features_found: parseInt($("#hitl-features").value, 10) || 0,
    }),
  });
  const file = $("#hitl-ypad").files[0];
  if (file) {
    const fd = new FormData();
    fd.append("file", file);
    await fetch(`/api/projects/${state.projectId}/documents`, { method: "POST", body: fd });
  }
  await refreshActiveProject();
  renderConsultantWorkspace();
  if ($("#panel-brahl")?.classList.contains("active")) await loadBrahlPanel();
  setStatus("Human in the Loop report submitted");
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
      body: JSON.stringify({ run_name: runName }),
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
    const res = await api("/api/ypad/restore", { method: "POST", body: "{}" });
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
      body: JSON.stringify({ run_name: runName, config_path, step_label: "Verify" }),
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
      const res = await api("/api/ypad/restore", { method: "POST", body: "{}" });
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
        body: JSON.stringify({ run_name: runName }),
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
  const { runs } = await api("/api/runs?suite=qoa_web");
  const list = $("#runs-list");
  list.innerHTML = runs.length
    ? ""
    : "<li>No qoa_web runs yet</li>";
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
  $("#dash-link").innerHTML = `<a href="/api/files/z/${encodeURIComponent(name)}/qoa_web_zDash.html" target="_blank">Open zDash</a>`;
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
  const logEl = stepLabel.startsWith("Loop") || stepLabel === "Verify" ? $("#loop-log") : $("#run-log");
  if (stepLabel === "Run") logEl.textContent = "";
  $("#btn-run").disabled = true;
  $("#progress-bar").style.width = "10%";
  const job = await api("/api/jobs", {
    method: "POST",
    body: JSON.stringify({ config_path: $("#config-select").value, step_label: stepLabel }),
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
  const sel = $("#suite-select");
  if (!sel) return;
  sel.innerHTML = suites
    .map((s) => `<option value="${escapeHtml(s.path)}">${escapeHtml(s.name)}${s.url ? ` — ${escapeHtml(s.url)}` : ""}</option>`)
    .join("");
}

async function loadConfigs() {
  const { configs } = await api("/api/configs");
  $("#config-select").innerHTML = configs
    .map((c) => `<option value="${c}"${c.includes("qoa_web") ? " selected" : ""}>${c}</option>`)
    .join("");
}

function initAvatarGate() {
  if (!state.avatar) $("#avatar-gate").hidden = false;
  else setAvatar(state.avatar);
  $$(".avatar-btn, .avatar-choice").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const next = btn.dataset.avatar;
      if (state.avatar && state.avatar !== next && state.projectId) {
        openRoleSwitchModal(next);
        return;
      }
      await setAvatar(next);
    });
  });
}

$$(".phase-btn").forEach((btn) => {
  btn.addEventListener("click", () => showPhase(btn.dataset.phase));
});

$("#client-project-select")?.addEventListener("change", (e) => selectProject(e.target.value));
$("#topbar-project-select")?.addEventListener("change", (e) => selectProject(e.target.value));
$("#consultant-project-select")?.addEventListener("change", (e) => selectProject(e.target.value));
$("#consultant-project-filter")?.addEventListener("input", (e) => {
  state.consultantFilter = e.target.value;
  renderConsultantProjects();
});
$("#consultant-project-sort")?.addEventListener("change", (e) => {
  state.consultantSort = e.target.value;
  renderConsultantProjects();
});
$("#consultant-compact-mode")?.addEventListener("change", (e) => {
  state.consultantCompact = e.target.checked;
  renderConsultantProjects();
});
$("#btn-new-project")?.addEventListener("click", createNewProject);
$("#btn-add-first-project")?.addEventListener("click", createNewProject);
$("#topbar-add-project")?.addEventListener("click", createNewProject);
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
$("#budget-split")?.addEventListener("input", (e) => {
  const v = parseInt(e.target.value, 10);
  $("#auto-pct").textContent = v;
  $("#human-pct").textContent = 100 - v;
});
$("#btn-save-budget")?.addEventListener("click", saveBudget);
$("#ai-toggle")?.addEventListener("change", toggleAiMode);
$("#btn-save-manual-purpose")?.addEventListener("click", saveManualPurpose);
$("#btn-add-context-manual")?.addEventListener("click", () => {
  $("#add-context-panel").hidden = false;
});
$("#btn-join-hitl")?.addEventListener("click", joinHitl);
$("#btn-hitl-submit")?.addEventListener("click", submitHitlReport);
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
$("#brahl-chat-form")?.addEventListener("submit", sendBrahlChat);
$("#btn-link-run-report")?.addEventListener("click", linkRunReport);

initAvatarGate();
checkHealth();
loadSuites();
loadConfigs();
loadRuns();
setInterval(checkHealth, 15000);
