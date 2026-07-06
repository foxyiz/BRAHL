const $ = (sel) => document.querySelector(sel);

function prefillCodeFromUrl() {
  const params = new URLSearchParams(location.search);
  const code = params.get("code");
  if (code) {
    const input = $("#invite-code");
    if (input) input.value = code.trim();
  }
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
      status.className = "waitlist-status";
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
        status.className = "waitlist-status waitlist-status-ok";
        status.textContent = data.message || "Trial started — redirecting…";
      }
      setTimeout(() => {
        location.href = "/signin";
      }, 600);
    } catch (err) {
      if (status) {
        status.className = "waitlist-status waitlist-status-err";
        status.textContent = err.message || "Could not redeem invite";
      }
    }
  });
}

function bindDemoBypass() {
  $("#welcome-demo-bypass")?.addEventListener("click", () => {
    window.QoaInviteGate?.enableDemoBypass();
    location.href = "/signin";
  });
}

function showTrialActiveHint() {
  if (!window.QoaInviteGate?.isInviteTrialValid?.()) return;
  const params = new URLSearchParams(location.search);
  if (params.get("code")) return;
  const foot = document.querySelector(".welcome-footnote");
  if (!foot) return;
  const days = window.QoaInviteGate.inviteTrialDaysLeft?.() ?? 0;
  const hint = document.createElement("p");
  hint.className = "welcome-trial-hint";
  hint.innerHTML =
    `Trial active${days ? ` (${days} day${days === 1 ? "" : "s"} left)` : ""} — ` +
    `<a href="/signin">continue to profiles →</a>`;
  foot.parentElement?.insertBefore(hint, foot.nextSibling);
}

prefillCodeFromUrl();
bindInviteForm();
bindDemoBypass();
showTrialActiveHint();
