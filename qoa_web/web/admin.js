/* Scoped Admin Panel — Platform / Project */
(() => {
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const TOKEN_KEY = "qoa_auth_token";
  const TOKEN_ADMIN = "qoa_admin_token";

  const state = {
    me: null,
    tab: "users",
    scope: "platform",
    projectId: "",
    liveMap: null,
  };

  function authHeaders() {
    const h = { "Content-Type": "application/json" };
    const t = localStorage.getItem(TOKEN_KEY);
    if (t) h.Authorization = `Bearer ${t}`;
    const at = sessionStorage.getItem(TOKEN_ADMIN) || localStorage.getItem(TOKEN_ADMIN);
    if (at) h["X-Admin-Token"] = at;
    return h;
  }

  async function api(path, opts = {}) {
    const res = await fetch(path, {
      ...opts,
      headers: { ...authHeaders(), ...(opts.headers || {}) },
    });
    if (!res.ok) throw new Error((await res.text()) || res.statusText);
    const ct = res.headers.get("content-type") || "";
    return ct.includes("application/json") ? res.json() : res.text();
  }

  function escapeHtml(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function roleChips(roles) {
    const priv = new Set(["admin", "super_admin"]);
    return `<span class="role-chips">${(roles || [])
      .map(
        (r) =>
          `<span class="role-chip${priv.has(r) ? " priv" : ""}">${escapeHtml(r)}</span>`
      )
      .join("")}</span>`;
  }

  function isPlatform() {
    return state.scope === "platform" && state.me?.can_platform;
  }

  function syncScopeUi() {
    const mode = $("#admin-scope-mode");
    const proj = $("#admin-project-select");
    if (!mode) return;
    if (!state.me?.can_platform) {
      mode.value = "project";
      mode.disabled = true;
      state.scope = "project";
    } else {
      mode.disabled = false;
    }
    const scopes = state.me?.project_scopes || [];
    if (state.scope === "project") {
      proj.hidden = false;
      proj.innerHTML = scopes.length
        ? scopes
            .map(
              (p) =>
                `<option value="${escapeHtml(p.id)}">${escapeHtml(p.name || p.id)}</option>`
            )
            .join("")
        : `<option value="">No projects</option>`;
      if (!state.projectId && scopes[0]) state.projectId = scopes[0].id;
      if (state.projectId) proj.value = state.projectId;
    } else {
      proj.hidden = true;
    }
    $$(".admin-tab").forEach((tab) => {
      const platformOnly = tab.hasAttribute("data-platform-only");
      tab.hidden = platformOnly && !isPlatform();
    });
  }

  function setStats(items) {
    $("#admin-stats").innerHTML = items
      .map(
        (it) =>
          `<div class="admin-stat"><strong>${escapeHtml(it.value)}</strong><span>${escapeHtml(
            it.label
          )}</span></div>`
      )
      .join("");
  }

  async function renderUsers() {
    const body = $("#admin-panel-body");
    if (isPlatform()) {
      const data = await api("/api/admin/users");
      setStats([
        { value: data.total, label: "Total Users" },
        { value: data.admins, label: "Admins" },
        { value: data.regular, label: "Regular Users" },
      ]);
      const canGrantAdmin = !!state.me?.is_super_admin;
      body.innerHTML =
        `<p class="admin-hint">Multi-profile roles on each account. Only Super Admin can grant Admin / Super Admin.</p>` +
        `<ul class="admin-list">${data.users
          .map((u) => {
            const roles = (u.roles || []).join(",");
            return `<li>
              <div>
                <strong>${escapeHtml(u.name || u.email)}</strong>
                <div class="meta">${escapeHtml(u.email)}</div>
                ${roleChips(u.roles)}
              </div>
              <div class="admin-row-actions">
                <button type="button" data-edit-roles="${escapeHtml(u.id)}" data-roles="${escapeHtml(
              roles
            )}">Edit roles</button>
                ${
                  canGrantAdmin
                    ? `<button type="button" data-make-admin="${escapeHtml(u.id)}" data-roles="${escapeHtml(
                        roles
                      )}">Make Admin</button>`
                    : ""
                }
              </div>
            </li>`;
          })
          .join("")}</ul>`;
      body.querySelectorAll("[data-edit-roles]").forEach((btn) => {
        btn.addEventListener("click", async () => {
          const current = (btn.dataset.roles || "").split(",").filter(Boolean);
          const raw = prompt(
            "Roles (comma-separated): creator, qa_hunter, nalanda, promoter, trainer, student, admin, super_admin",
            current.join(", ")
          );
          if (raw == null) return;
          const next = raw
            .split(",")
            .map((s) => s.trim())
            .filter(Boolean);
          await api(`/api/admin/users/${btn.dataset.editRoles}/roles`, {
            method: "PATCH",
            body: JSON.stringify({ roles: next }),
          });
          renderUsers();
        });
      });
      body.querySelectorAll("[data-make-admin]").forEach((btn) => {
        btn.addEventListener("click", async () => {
          const roles = new Set((btn.dataset.roles || "").split(",").filter(Boolean));
          roles.add("admin");
          await api(`/api/admin/users/${btn.dataset.makeAdmin}/roles`, {
            method: "PATCH",
            body: JSON.stringify({ roles: [...roles] }),
          });
          renderUsers();
        });
      });
      return;
    }
    // Project members
    if (!state.projectId) {
      body.innerHTML = `<p class="admin-hint">Select a project to see members.</p>`;
      setStats([]);
      return;
    }
    const ov = await api(`/api/admin/projects/${encodeURIComponent(state.projectId)}/overview`);
    const members = [];
    const ownerId = ov.project?.owner_user_id;
    if (ownerId) members.push({ name: "Owner", id: ownerId, roles: ["creator"] });
    (ov.hitl || []).forEach((h) =>
      members.push({
        name: h.consultant_name || h.team_name || "Hunter",
        email: h.email,
        roles: ["qa_hunter"],
        status: h.status,
      })
    );
    setStats([
      { value: members.length, label: "Members" },
      { value: (ov.hitl || []).length, label: "Hunters joined" },
      { value: (ov.invites_pending || []).length, label: "Pending invites" },
    ]);
    body.innerHTML = `<ul class="admin-list">${
      members.length
        ? members
            .map(
              (m) => `<li><div><strong>${escapeHtml(m.name)}</strong>
                <div class="meta">${escapeHtml(m.email || m.status || "")}</div>${roleChips(
                m.roles
              )}</div></li>`
            )
            .join("")
        : `<li class="meta">No members yet — invite QA Hunters from Build.</li>`
    }</ul>`;
  }

  async function renderClients() {
    const data = await api("/api/admin/clients");
    setStats([
      { value: data.total_clients, label: "Total Clients" },
      { value: data.projects_posted, label: "Projects Posted" },
      { value: data.active_clients, label: "Active Clients" },
    ]);
    $("#admin-panel-body").innerHTML = `<ul class="admin-list">${(data.clients || [])
      .map(
        (c) => `<li>
          <div><strong>${escapeHtml(c.name || "Client")}</strong>
          <div class="meta">${escapeHtml(c.email || c.owner_user_id || "unowned")}</div>
          ${roleChips(c.roles)}</div>
          <span class="meta">${c.project_count} project(s)</span>
        </li>`
      )
      .join("")}</ul>`;
  }

  async function renderProjects() {
    const data = await api("/api/admin/projects");
    setStats([
      { value: data.total, label: "Total Projects" },
      { value: data.active, label: "Active" },
      { value: data.paused, label: "Paused" },
      { value: data.completed, label: "Completed" },
    ]);
    const body = $("#admin-panel-body");
    body.innerHTML =
      `<input class="admin-search" id="admin-project-filter" placeholder="Search projects…" />` +
      `<div class="admin-card-grid" id="admin-project-cards">${(data.projects || [])
        .map(
          (p) => `<article class="admin-card" data-name="${escapeHtml(
            (p.name || "").toLowerCase()
          )}">
          <h3>${escapeHtml(p.name || p.id)} ${
            p.redacted ? `<span class="badge-redacted">redacted</span>` : ""
          }</h3>
          <p class="meta">${escapeHtml(p.purpose || p.suite_name || "")}</p>
          <p class="meta">Status: ${escapeHtml(p.status || "—")} · Hunters: ${
            p.hunter_count ?? 0
          } · AI ${p.ai_enabled === false ? "off" : "on"}</p>
          <div class="admin-row-actions" style="margin-left:0">
            <button type="button" class="admin-inline-btn" data-open-project="${escapeHtml(
              p.id
            )}">${p.is_member || !p.redacted ? "Open Project Admin" : "View metadata"}</button>
          </div>
        </article>`
        )
        .join("")}</div>`;
    $("#admin-project-filter")?.addEventListener("input", (e) => {
      const q = e.target.value.toLowerCase();
      $$("#admin-project-cards .admin-card").forEach((card) => {
        card.hidden = q && !card.dataset.name.includes(q);
      });
    });
    body.querySelectorAll("[data-open-project]").forEach((btn) => {
      btn.addEventListener("click", () => {
        state.scope = "project";
        state.projectId = btn.dataset.openProject;
        $("#admin-scope-mode").value = "project";
        syncScopeUi();
        state.tab = "xp";
        $$(".admin-tab").forEach((t) => t.classList.toggle("active", t.dataset.tab === "xp"));
        renderTab();
      });
    });
  }

  async function renderConsultants() {
    const q = state.scope === "project" && state.projectId ? `?project_id=${encodeURIComponent(state.projectId)}` : "";
    const data = await api(`/api/admin/consultants${q}`);
    setStats([{ value: data.total, label: "Consultants" }, { value: "—", label: "Assigned issues" }]);
    $("#admin-panel-body").innerHTML = `<ul class="admin-list">${(data.consultants || [])
      .map(
        (c) => `<li>
          <div><strong>${escapeHtml(c.name || "Hunter")}</strong>
          <div class="meta">${escapeHtml(c.email || c.status || "")}${
          c.time_spent_sec != null ? ` · ${Math.round(c.time_spent_sec / 60)}m in arena` : ""
        }</div>
          ${roleChips(c.roles || ["qa_hunter"])}</div>
          ${c.redacted ? `<span class="badge-redacted">redacted</span>` : ""}
        </li>`
      )
      .join("") || `<li class="meta">No consultants in this scope.</li>`}</ul>`;
  }

  async function renderXp() {
    const body = $("#admin-panel-body");
    if (state.scope === "project" && state.projectId) {
      const ov = await api(`/api/admin/projects/${encodeURIComponent(state.projectId)}/overview`);
      const m = ov.cost_meter || {};
      setStats([
        { value: m.budget_usd ?? "—", label: "Budget $" },
        { value: ov.ai_enabled === false ? "Off" : "On", label: "AI" },
        { value: (m.ai_usage && m.ai_usage.usd_est) ?? m.ai_usd_est ?? "0", label: "AI $ est" },
      ]);
      const spent = (ov.time_spent || [])
        .map(
          (t) =>
            `<li><strong>${escapeHtml(t.name || t.user_id)}</strong> <span class="meta">${Math.round(
              (t.seconds || 0) / 60
            )} min</span></li>`
        )
        .join("");
      body.innerHTML = `
        <div class="admin-card">
          <h3>Project cost &amp; AI</h3>
          <p class="admin-hint">Creators control AI for their project. Cost meter mirrors Arena Wallet ($).</p>
          <div class="admin-toggle-row">
            <label><input type="checkbox" id="admin-ai-toggle" ${
              ov.ai_enabled === false ? "" : "checked"
            } ${ov.access === "full" ? "" : "disabled"} /> AI on</label>
          </div>
          <pre class="admin-hint" style="white-space:pre-wrap">${escapeHtml(
            JSON.stringify(
              {
                runtime_mode: m.runtime_mode,
                budget_usd: m.budget_usd,
                ai_usage: m.ai_usage,
                phases: (m.phases || []).slice?.(0, 6) || m.phase_rows || undefined,
              },
              null,
              2
            )
          )}</pre>
        </div>
        <div class="admin-card" style="margin-top:0.75rem">
          <h3>HITL joins</h3>
          <ul class="admin-list">${(ov.hitl || [])
            .map(
              (h) =>
                `<li><strong>${escapeHtml(h.consultant_name || "Hunter")}</strong>
                <span class="meta">${escapeHtml(h.status || "")}</span></li>`
            )
            .join("") || `<li class="meta">No hunters joined yet.</li>`}</ul>
        </div>
        <div class="admin-card" style="margin-top:0.75rem">
          <h3>Time spent (heartbeat)</h3>
          <ul class="admin-list">${spent || `<li class="meta">No time tracked yet — open Arena to send heartbeats.</li>`}</ul>
        </div>`;
      $("#admin-ai-toggle")?.addEventListener("change", async (e) => {
        await api(`/api/admin/projects/${encodeURIComponent(state.projectId)}/ai`, {
          method: "PATCH",
          body: JSON.stringify({ ai_enabled: !!e.target.checked }),
        });
        renderXp();
      });
      return;
    }
    setStats([
      { value: "1000", label: "XP → $1 (ref)" },
      { value: "On", label: "Local XP ledger" },
    ]);
    body.innerHTML = `<div class="admin-card">
      <h3>XP &amp; Payments (platform)</h3>
      <p class="admin-hint">Arena XP lives in the browser ledger today. Wallet / cost meter is per project — open a project scope for live AI cost and Hunter time.</p>
      <p class="admin-hint">V2: Convert All, min payout, and server-side XP rates (aligned with QAonAir XP tab).</p>
    </div>`;
  }

  async function renderLive() {
    const scope = state.scope === "project" && state.projectId ? "project" : "platform";
    const q =
      scope === "project"
        ? `?scope=project&project_id=${encodeURIComponent(state.projectId)}`
        : "?scope=platform";
    const data = await api(`/api/admin/live${q}`);
    setStats([
      { value: data.online_now, label: "Online Now" },
      { value: data.total_sessions, label: "Total Sessions" },
      { value: data.mapped_locations, label: "Mapped Locations" },
      { value: data.countries, label: "Countries" },
    ]);
    const body = $("#admin-panel-body");
    body.innerHTML = `
      <h3 class="section-sub" style="margin-top:0">Live user map</h3>
      <p class="admin-hint">Markers from heartbeat geo (browser consent or IP). Platform view redacts names. Auto-refresh 15s.</p>
      <div id="admin-live-map" class="admin-map"></div>
      <h3 class="section-sub">Recent sessions</h3>
      <ul class="admin-list" id="admin-live-sessions"></ul>`;
    const list = $("#admin-live-sessions");
    list.innerHTML = (data.recent || [])
      .map((s) => {
        const mins = Math.floor((s.duration_sec || 0) / 60);
        const secs = (s.duration_sec || 0) % 60;
        const ago =
          (s.ago_sec || 0) < 60 ? "just now" : `${Math.round((s.ago_sec || 0) / 60)}m ago`;
        return `<li>
          <div>
            <strong>${escapeHtml(s.display_name || "User")}${s.online ? " · online" : ""}</strong>
            <div class="meta">@ ${escapeHtml(s.location_label || "Unknown")} — ${escapeHtml(
          s.path || "/"
        )}</div>
            ${roleChips(s.roles?.length ? s.roles : [s.avatar || "creator"])}
          </div>
          <span class="meta">${mins}m ${secs}s · ${ago}</span>
        </li>`;
      })
      .join("") || `<li class="meta">No sessions yet.</li>`;

    if (state.liveMap) {
      try {
        state.liveMap.remove();
      } catch {
        /* ignore */
      }
      state.liveMap = null;
    }
    if (window.L) {
      const map = L.map("admin-live-map").setView([20, 0], 2);
      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: "&copy; OpenStreetMap",
        maxZoom: 18,
      }).addTo(map);
      (data.markers || []).forEach((m) => {
        if (m.lat == null || m.lng == null) return;
        const color = m.online ? "#3dd68c" : "#3d8bfd";
        L.circleMarker([m.lat, m.lng], {
          radius: m.online ? 10 : 7,
          color,
          fillColor: color,
          fillOpacity: 0.7,
        })
          .bindPopup(escapeHtml(m.label || m.avatar || ""))
          .addTo(map);
      });
      state.liveMap = map;
      setTimeout(() => map.invalidateSize(), 50);
    }
  }

  async function renderGtm() {
    setStats([]);
    const body = $("#admin-panel-body");
    body.innerHTML = `<div class="admin-card">
      <h3>Go-to-market</h3>
      <p class="admin-hint">Invite batches stay on the classic admin APIs. Open About for marketing copy, or generate invites below.</p>
      <div class="admin-row-actions" style="margin-left:0">
        <button type="button" class="primary" id="admin-gtm-batch">Generate 50 Creator + 50 Hunter invites</button>
        <a class="secondary admin-inline-btn" href="/about#about-admin-title">About / GTM notes</a>
      </div>
      <pre id="admin-gtm-log" class="admin-hint" style="margin-top:0.75rem"></pre>
    </div>`;
    $("#admin-gtm-batch")?.addEventListener("click", async () => {
      const log = $("#admin-gtm-log");
      try {
        const a = await api("/api/admin/invites/batch", {
          method: "POST",
          body: JSON.stringify({ batch_type: "creator", count: 50, label: "admin-panel" }),
        });
        const b = await api("/api/admin/invites/batch", {
          method: "POST",
          body: JSON.stringify({ batch_type: "consultant", count: 50, label: "admin-panel" }),
        });
        log.textContent = `Created batch creator + consultant invites. Check /api/admin/invites.`;
        console.log(a, b);
      } catch (e) {
        log.textContent = e.message;
      }
    });
  }

  async function renderTab() {
    try {
      if (state.tab === "users") await renderUsers();
      else if (state.tab === "clients") await renderClients();
      else if (state.tab === "projects") await renderProjects();
      else if (state.tab === "consultants") await renderConsultants();
      else if (state.tab === "xp") await renderXp();
      else if (state.tab === "live") await renderLive();
      else if (state.tab === "gtm") await renderGtm();
    } catch (e) {
      $("#admin-panel-body").innerHTML = `<p class="admin-hint">Error: ${escapeHtml(e.message)}</p>`;
    }
  }

  async function boot() {
    const params = new URLSearchParams(location.search);
    if (params.get("scope") === "project") state.scope = "project";
    if (params.get("project")) {
      state.scope = "project";
      state.projectId = params.get("project");
    }
    try {
      state.me = await api("/api/admin/me");
    } catch (e) {
      $("#admin-gate").hidden = false;
      $("#admin-shell").hidden = true;
      return;
    }
    $("#admin-gate").hidden = true;
    $("#admin-shell").hidden = false;
    if (!state.me.can_platform && state.me.project_scopes?.length) {
      state.scope = "project";
      state.projectId = state.projectId || state.me.project_scopes[0].id;
    }
    $("#admin-scope-mode").value = state.scope;
    syncScopeUi();
    renderTab();
    setInterval(() => {
      if (state.tab === "live" && !$("#admin-shell").hidden) renderLive();
    }, 15000);
  }

  $("#admin-scope-mode")?.addEventListener("change", (e) => {
    state.scope = e.target.value;
    syncScopeUi();
    if (state.tab === "clients" || state.tab === "gtm") {
      if (!isPlatform()) {
        state.tab = "projects";
        $$(".admin-tab").forEach((t) => t.classList.toggle("active", t.dataset.tab === "projects"));
      }
    }
    renderTab();
  });
  $("#admin-project-select")?.addEventListener("change", (e) => {
    state.projectId = e.target.value;
    renderTab();
  });
  $$(".admin-tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      state.tab = tab.dataset.tab;
      $$(".admin-tab").forEach((t) => t.classList.toggle("active", t === tab));
      renderTab();
    });
  });

  boot();
})();
