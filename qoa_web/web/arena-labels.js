/** User-facing avatar names — internal keys stay client / consultant / networker. */
const AVATAR_LABELS = {
  client: {
    short: "Creator",
    letter: "C",
    tagline: "Champion — post a challenge · BRAHL it",
    projectLabel: "Projects",
    projectPlaceholder: "Select project…",
  },
  consultant: {
    short: "QA Hunter",
    letter: "H",
    tagline: "Contender — hunt defects · save the ship",
    projectLabel: "Projects",
    projectPlaceholder: "Select project…",
  },
  networker: {
    short: "Nalanda",
    letter: "N",
    tagline: "Learn · teach · discuss — free knowledge community",
    projectLabel: "Projects",
    projectPlaceholder: "Browse projects…",
  },
};

/** Every signed-in user may switch among arena avatars (persona = profile chip only). */
const UNIVERSAL_AVATARS = ["client", "consultant", "networker"];

const ARENA_TAGLINE = "Your QA agent — FoXYiZ runs the tests · BRAHL decides Go/No-Go";

function avatarLabel(key) {
  return AVATAR_LABELS[key] || AVATAR_LABELS.client;
}

function applyAvatarLabelsToDom() {
  document.querySelectorAll(".avatar-btn").forEach((b) => {
    const meta = avatarLabel(b.dataset.avatar);
    const icon = b.querySelector(".avatar-icon");
    const lbl = b.querySelector(".avatar-label");
    if (icon) icon.textContent = meta.letter;
    if (lbl) lbl.textContent = meta.short;
    b.title = `${meta.short} — ${meta.tagline}`;
  });
}
