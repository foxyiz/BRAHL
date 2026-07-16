/** QA on Air theme — Pro only (Arena skin retired). */
const STORAGE_THEME = "qoa_web_theme";
const THEMES = ["pro"];

function getTheme() {
  return "pro";
}

function setTheme(_name) {
  const theme = "pro";
  localStorage.setItem(STORAGE_THEME, theme);
  document.documentElement.dataset.theme = theme;
  document.body.classList.remove("theme-arena");
  document.body.classList.add("theme-pro");
  document.querySelectorAll("[data-theme-btn]").forEach((btn) => {
    const on = btn.dataset.themeBtn === "pro";
    btn.classList.toggle("active", on);
    btn.setAttribute("aria-pressed", on ? "true" : "false");
  });
  const rail = document.getElementById("visual-reward-rail");
  if (rail) rail.hidden = true;
  window.dispatchEvent(new CustomEvent("qoa-theme-change", { detail: { theme } }));
}

function initTheme() {
  setTheme("pro");
}

window.QoaTheme = { getTheme, setTheme, initTheme, THEMES };
