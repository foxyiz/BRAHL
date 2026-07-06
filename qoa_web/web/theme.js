/** QA on Air theme: pro (default) vs arena (visual / fight-ring). Same ops, different skin. */
const STORAGE_THEME = "qoa_web_theme";
const THEMES = ["pro", "arena"];

function getTheme() {
  const t = localStorage.getItem(STORAGE_THEME);
  return THEMES.includes(t) ? t : "pro";
}

function setTheme(name) {
  const theme = THEMES.includes(name) ? name : "pro";
  localStorage.setItem(STORAGE_THEME, theme);
  document.documentElement.dataset.theme = theme;
  document.body.classList.toggle("theme-arena", theme === "arena");
  document.body.classList.toggle("theme-pro", theme === "pro");
  document.querySelectorAll("[data-theme-btn]").forEach((btn) => {
    const on = btn.dataset.themeBtn === theme;
    btn.classList.toggle("active", on);
    btn.setAttribute("aria-pressed", on ? "true" : "false");
  });
  const rail = document.getElementById("visual-reward-rail");
  if (rail) rail.hidden = theme !== "arena";
  window.dispatchEvent(new CustomEvent("qoa-theme-change", { detail: { theme } }));
}

function initTheme() {
  setTheme(getTheme());
  document.querySelectorAll("[data-theme-btn]").forEach((btn) => {
    btn.addEventListener("click", () => setTheme(btn.dataset.themeBtn));
  });
}

window.QoaTheme = { getTheme, setTheme, initTheme, THEMES };
