/** GTM invite gate — 7-day trial after redeeming batch invite code. */
const STORAGE_INVITE_TRIAL = "qoa_web_invite_trial";
const STORAGE_DEMO_BYPASS = "qoa_web_demo_bypass";

function getInviteTrial() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_INVITE_TRIAL) || "null");
  } catch {
    return null;
  }
}

function saveInviteTrial(trial) {
  localStorage.setItem(STORAGE_INVITE_TRIAL, JSON.stringify(trial));
}

function clearInviteTrial() {
  localStorage.removeItem(STORAGE_INVITE_TRIAL);
}

function isDemoBypass() {
  if (window.__QOA_ALLOW_DEMO__ === false) return false;
  if (localStorage.getItem(STORAGE_DEMO_BYPASS) === "1") return true;
  const params = new URLSearchParams(location.search);
  return params.get("demo") === "1";
}

function enableDemoBypass() {
  if (window.__QOA_ALLOW_DEMO__ === false) return;
  localStorage.setItem(STORAGE_DEMO_BYPASS, "1");
}

(async function loadDemoConfig() {
  try {
    const res = await fetch("/api/config");
    if (!res.ok) return;
    const cfg = await res.json();
    window.__QOA_ALLOW_DEMO__ = cfg.allow_demo !== false;
    if (!window.__QOA_ALLOW_DEMO__) {
      localStorage.removeItem(STORAGE_DEMO_BYPASS);
    }
  } catch {
    /* keep default allow */
  }
})();

function isInviteTrialValid() {
  if (isDemoBypass()) return true;
  const trial = getInviteTrial();
  if (!trial?.trial_ends_at) return false;
  const end = new Date(trial.trial_ends_at);
  return !Number.isNaN(end.getTime()) && end.getTime() > Date.now();
}

function inviteTrialDaysLeft() {
  const trial = getInviteTrial();
  if (!trial?.trial_ends_at) return 0;
  const ms = new Date(trial.trial_ends_at).getTime() - Date.now();
  return Math.max(0, Math.ceil(ms / (24 * 60 * 60 * 1000)));
}

function requireInviteTrialOrRedirect(targetWelcome = "/welcome") {
  if (isInviteTrialValid()) return true;
  const path = location.pathname.replace(/\/$/, "") || "/";
  if (path === "/welcome" || path === "/") return false;
  location.replace(targetWelcome);
  return false;
}

if (typeof window !== "undefined") {
  window.QoaInviteGate = {
    getInviteTrial,
    saveInviteTrial,
    clearInviteTrial,
    isDemoBypass,
    enableDemoBypass,
    isInviteTrialValid,
    inviteTrialDaysLeft,
    requireInviteTrialOrRedirect,
    STORAGE_INVITE_TRIAL,
    STORAGE_DEMO_BYPASS,
  };
}
