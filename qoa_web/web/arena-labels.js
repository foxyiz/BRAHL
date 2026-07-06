/** User-facing avatar names — internal keys stay client / consultant / networker. */
const AVATAR_LABELS = {
  client: {
    short: "Creator",
    letter: "C",
    tagline: "Champion — post a challenge · BRAHL it",
    projectLabel: "My challenge",
    projectPlaceholder: "Select challenge…",
  },
  consultant: {
    short: "QA Hunter",
    letter: "H",
    tagline: "Contender — hunt defects · save the ship",
    projectLabel: "Open challenges",
    projectPlaceholder: "Select challenge…",
  },
  networker: {
    short: "Nalanda",
    letter: "N",
    tagline: "Learn · teach · discuss — free knowledge community",
    projectLabel: "Community",
    projectPlaceholder: "Browse community…",
  },
};

/** Every signed-in user may switch among arena avatars (persona = profile chip only). */
const UNIVERSAL_AVATARS = ["client", "consultant", "networker"];

const ARENA_TAGLINE = "You Build, We QA — let's BRAHL! Champion vs Contender in the arena.";

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
