/** Nalanda community panel — learn, teach, discuss, invite */
(function () {
  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => document.querySelectorAll(sel);

  let selectedThreadId = null;

  function profileId() {
    return (localStorage.getItem(STORAGE_PROFILE) || "").toLowerCase();
  }

  function profileName() {
    const p = typeof getProfileById === "function" ? getProfileById(profileId()) : null;
    return p?.name || profileId().toUpperCase();
  }

  async function api(path, opts = {}) {
    const res = await fetch(path, {
      headers: { "Content-Type": "application/json", ...(opts.headers || {}) },
      ...opts,
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || res.statusText || "Request failed");
    return data;
  }

  function escapeHtml(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function renderXpStrip() {
    const el = $("#nalanda-xp-strip");
    if (!el) return;
    let total = 0;
    let shares = 0;
    try {
      const led = JSON.parse(localStorage.getItem("qoa_web_xp") || "{}");
      total = Object.values(led).reduce((a, b) => a + (Number(b) || 0), 0);
      shares = led.promote_shares || 0;
    } catch {
      /* ignore */
    }
    el.innerHTML =
      `<span><strong>${total}</strong> community XP</span>` +
      `<span><strong>${shares}</strong> shares</span>` +
      `<span class="hint">Knowledge is free — contribute to earn XP</span>`;
  }

  function renderLessons(lessons) {
    const list = $("#nalanda-lesson-list");
    if (!list) return;
    if (!lessons?.length) {
      list.innerHTML = `<li class="meta">No community lessons yet — be the first to teach.</li>`;
      return;
    }
    list.innerHTML = lessons
      .map(
        (l) =>
          `<li class="nalanda-lesson-item">` +
          `<strong>${escapeHtml(l.title)}</strong>` +
          (l.blurb ? `<div>${escapeHtml(l.blurb)}</div>` : "") +
          (l.url ? `<div><a href="${escapeHtml(l.url)}" target="_blank" rel="noopener">${escapeHtml(l.url)}</a></div>` : "") +
          `<div class="nalanda-item-meta">${escapeHtml(l.author_name || "")} · ${escapeHtml(l.created_at || "")}</div>` +
          `</li>`
      )
      .join("");
  }

  function renderThreads(threads) {
    const list = $("#nalanda-thread-list");
    if (!list) return;
    if (!threads?.length) {
      list.innerHTML = `<li class="meta">No discussions yet.</li>`;
      return;
    }
    list.innerHTML = threads
      .map(
        (t) =>
          `<li class="nalanda-thread-item" data-thread-id="${escapeHtml(t.id)}">` +
          `<strong>${escapeHtml(t.title)}</strong>` +
          `<div class="nalanda-item-meta">${escapeHtml(t.author_name || "")} · ${t.reply_count || 0} replies</div>` +
          `</li>`
      )
      .join("");
    list.querySelectorAll(".nalanda-thread-item").forEach((item) => {
      item.addEventListener("click", () => openThread(item.dataset.threadId));
    });
  }

  async function openThread(threadId) {
    selectedThreadId = threadId;
    const detail = $("#nalanda-thread-detail");
    if (!detail) return;
    try {
      const { thread } = await api(`/api/nalanda/threads/${encodeURIComponent(threadId)}`);
      const replies = (thread.replies || [])
        .map(
          (r) =>
            `<li><strong>${escapeHtml(r.author_name)}</strong>: ${escapeHtml(r.body)}` +
            `<div class="nalanda-item-meta">${escapeHtml(r.created_at || "")}</div></li>`
        )
        .join("");
      detail.hidden = false;
      detail.innerHTML =
        `<h4>${escapeHtml(thread.title)}</h4>` +
        `<p>${escapeHtml(thread.body)}</p>` +
        `<p class="nalanda-item-meta">by ${escapeHtml(thread.author_name)}</p>` +
        `<ul class="nalanda-replies">${replies || "<li class='meta'>No replies yet.</li>"}</ul>` +
        `<form id="nalanda-reply-form" class="nalanda-teach-form">` +
        `<textarea id="nalanda-reply-body" rows="3" placeholder="Add your reply…" required></textarea>` +
        `<button type="submit" class="primary">Reply</button>` +
        `</form>`;
      $("#nalanda-reply-form")?.addEventListener("submit", submitReply);
    } catch (e) {
      detail.hidden = false;
      detail.textContent = e.message || "Could not load thread";
    }
  }

  async function submitReply(ev) {
    ev.preventDefault();
    const body = $("#nalanda-reply-body")?.value?.trim();
    if (!body || !selectedThreadId) return;
    try {
      await api(`/api/nalanda/threads/${encodeURIComponent(selectedThreadId)}/replies`, {
        method: "POST",
        body: JSON.stringify({
          profile_id: profileId(),
          body,
          author_name: profileName(),
        }),
      });
      window.QoaXp?.add?.("networker_activity", 10);
      await openThread(selectedThreadId);
      await refreshThreads();
      setStatus("Reply posted");
    } catch (e) {
      setStatus(e.message || "Reply failed");
    }
  }

  function setStatus(msg) {
    const el = $("#nalanda-status");
    if (el) {
      el.hidden = false;
      el.textContent = msg;
    }
  }

  async function refreshLessons() {
    const data = await api("/api/nalanda/lessons");
    renderLessons(data.lessons);
  }

  async function refreshThreads() {
    const data = await api("/api/nalanda/threads");
    renderThreads(data.threads);
  }

  async function loadInvite() {
    const pid = profileId();
    if (!pid) return;
    try {
      const data = await api(
        `/api/nalanda/invite?profile_id=${encodeURIComponent(pid)}&author_name=${encodeURIComponent(profileName())}`
      );
      const codeEl = $("#nalanda-invite-code");
      const linkEl = $("#nalanda-invite-link");
      const shareTa = $("#nalanda-invite-share-text");
      if (codeEl) codeEl.textContent = data.code || "—";
      if (linkEl) {
        linkEl.href = data.invite_path || "#";
        linkEl.textContent = location.origin + (data.invite_path || "");
      }
      if (shareTa) shareTa.value = data.share_text || "";
    } catch (e) {
      setStatus(e.message || "Could not load invite");
    }
  }

  async function submitLesson(ev) {
    ev.preventDefault();
    const title = $("#nalanda-lesson-title")?.value?.trim();
    const url = $("#nalanda-lesson-url")?.value?.trim();
    const blurb = $("#nalanda-lesson-blurb")?.value?.trim();
    if (!title) return;
    try {
      await api("/api/nalanda/lessons", {
        method: "POST",
        body: JSON.stringify({
          profile_id: profileId(),
          title,
          url,
          blurb,
          tags: ["community"],
          author_name: profileName(),
        }),
      });
      window.QoaXp?.add?.("promote_drafts", 5);
      $("#nalanda-teach-form")?.reset();
      await refreshLessons();
      setStatus("Lesson shared with the community");
    } catch (e) {
      setStatus(e.message || "Could not post lesson");
    }
  }

  async function submitThread(ev) {
    ev.preventDefault();
    const title = $("#nalanda-thread-title")?.value?.trim();
    const body = $("#nalanda-thread-body")?.value?.trim();
    if (!title || !body) return;
    try {
      await api("/api/nalanda/threads", {
        method: "POST",
        body: JSON.stringify({
          profile_id: profileId(),
          title,
          body,
          author_name: profileName(),
        }),
      });
      window.QoaXp?.add?.("networker_activity", 15);
      $("#nalanda-new-thread-form")?.reset();
      await refreshThreads();
      setStatus("Discussion started");
    } catch (e) {
      setStatus(e.message || "Could not start thread");
    }
  }

  function draftCommunityShare() {
    const ta = $("#nalanda-community-share-draft");
    if (!ta) return;
    ta.value =
      `Join Nalanda — free knowledge community on QA on Air\n\n` +
      `Learn from SkillFlow AI and ITelearn paths. Teach what you know. Discuss with peers.\n\n` +
      `#Nalanda #FreeKnowledge #QAonAir`;
    window.QoaXp?.add?.("promote_drafts", 5);
    setStatus("Share draft ready");
  }

  async function copyInviteShare() {
    const ta = $("#nalanda-invite-share-text");
    if (!ta?.value.trim()) await loadInvite();
    try {
      await navigator.clipboard.writeText($("#nalanda-invite-share-text")?.value || "");
      window.QoaXp?.add?.("promote_shares", 1);
      setStatus("Invite copied — share with friends");
    } catch {
      setStatus("Copy failed — select text manually");
    }
  }

  async function copyCommunityDraft() {
    const ta = $("#nalanda-community-share-draft");
    if (!ta?.value.trim()) draftCommunityShare();
    try {
      await navigator.clipboard.writeText(ta?.value || "");
      window.QoaXp?.add?.("promote_shares", 1);
      setStatus("Post copied");
    } catch {
      setStatus("Copy failed");
    }
  }

  let bound = false;

  function bindForms() {
    if (bound) return;
    bound = true;
    $("#nalanda-teach-form")?.addEventListener("submit", submitLesson);
    $("#nalanda-new-thread-form")?.addEventListener("submit", submitThread);
    $("#btn-nalanda-draft-share")?.addEventListener("click", draftCommunityShare);
    $("#btn-nalanda-copy-share")?.addEventListener("click", copyCommunityDraft);
    $("#btn-nalanda-copy-invite")?.addEventListener("click", copyInviteShare);
    $$(".nalanda-faq-chip").forEach((chip) => {
      chip.addEventListener("click", () => {
        if (typeof window.sendAtomic77Faq === "function") {
          window.sendAtomic77Faq(chip.dataset.faq);
        }
      });
    });
  }

  async function loadPanel() {
    renderXpStrip();
    bindForms();
    try {
      await Promise.all([refreshLessons(), refreshThreads(), loadInvite()]);
    } catch (e) {
      setStatus(e.message || "Could not load Nalanda");
    }
  }

  window.QoaNalanda = { loadPanel, refreshLessons, refreshThreads, loadInvite };
})();
