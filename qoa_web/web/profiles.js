/** Test personas — generated from Docs/test-user-data/. Do not edit by hand. */
const STORAGE_PROFILE = "qoa_web_profile";

const TEST_PROFILES = [
  {
    "id": "p1",
    "code": "P1",
    "name": "Alex Chen",
    "title": "MVP Creator",
    "role": "client-only",
    "defaultAvatar": "client",
    "aiDefault": true,
    "aiLocked": false,
    "dualRole": false,
    "admin": false,
    "techLevel": "business",
    "consultantTier": null,
    "allowedAvatars": [
      "client"
    ],
    "landing": "app",
    "accent": "client",
    "blurb": "Ships software and owns budget. Uses AI chat for requirements, invites QA Hunter, runs BRAHL — no yPAD editing.",
    "journey": [
      "Build · AI chat",
      "Budget & QA Hunter invite",
      "Run → Analyze → BRAHL"
    ],
    "ypadDesignColumn": "D1",
    "firstVisit": false,
    "fictional": true
  },
  {
    "id": "p2",
    "code": "P2",
    "name": "Jordan Lee",
    "title": "Creator · sometimes QA Hunter",
    "role": "dual",
    "defaultAvatar": "client",
    "aiDefault": true,
    "aiLocked": false,
    "dualRole": true,
    "admin": false,
    "techLevel": "mixed",
    "consultantTier": null,
    "allowedAvatars": [
      "client",
      "consultant"
    ],
    "landing": "app",
    "accent": "dual",
    "blurb": "Product owner who also joins as QA Hunter on other teams' projects.",
    "journey": [
      "Creator workspace",
      "Switch to QA Hunter",
      "Join project · deliver report",
      "$ wallet"
    ],
    "ypadDesignColumn": "D2",
    "firstVisit": false,
    "fictional": true
  },
  {
    "id": "p3",
    "code": "P3",
    "name": "Sam Rivera",
    "title": "Consultant only",
    "role": "consultant-only",
    "defaultAvatar": "consultant",
    "aiDefault": true,
    "aiLocked": false,
    "dualRole": false,
    "admin": false,
    "techLevel": "qa",
    "consultantTier": "standard",
    "allowedAvatars": [
      "consultant"
    ],
    "landing": "app",
    "accent": "QA Hunter",
    "blurb": "QA consultant — joins Creator challenges, uploads yPADs offline, enriches BRAHL reports.",
    "journey": [
      "QA Hunter workspace",
      "Join · deliverables",
      "Cost · QA Hunter wallet"
    ],
    "ypadDesignColumn": "D3",
    "firstVisit": false,
    "fictional": true
  },
  {
    "id": "p4",
    "code": "P4",
    "name": "Dr. Priya Nair",
    "title": "Senior consultant",
    "role": "consultant-senior",
    "defaultAvatar": "consultant",
    "aiDefault": true,
    "aiLocked": false,
    "dualRole": false,
    "admin": false,
    "techLevel": "expert",
    "consultantTier": "senior",
    "allowedAvatars": [
      "consultant"
    ],
    "landing": "app",
    "accent": "senior",
    "blurb": "15+ years QA architecture. Deep yPAD, shrink/restore, hybrid reports.",
    "journey": [
      "Senior QA Hunter badge",
      "yPAD · Loop · BRAHL enrich"
    ],
    "ypadDesignColumn": "D4",
    "firstVisit": false,
    "fictional": true
  },
  {
    "id": "p5",
    "code": "P5",
    "name": "Chris Martinez",
    "title": "Non-technical user",
    "role": "client-manual",
    "defaultAvatar": "client",
    "aiDefault": false,
    "aiLocked": true,
    "dualRole": false,
    "admin": false,
    "techLevel": "none",
    "consultantTier": null,
    "allowedAvatars": [
      "client"
    ],
    "landing": "app",
    "accent": "manual",
    "blurb": "No automation or AI comfort. Manual Build only — invite humans to run FoXYiZ.",
    "journey": [
      "AI locked off",
      "Manual purpose",
      "Invite QA Hunter"
    ],
    "ypadDesignColumn": "D5",
    "firstVisit": false,
    "fictional": true
  },
  {
    "id": "p6",
    "code": "P6",
    "name": "Morgan Admin",
    "title": "Platform admin",
    "role": "admin",
    "defaultAvatar": "client",
    "aiDefault": true,
    "aiLocked": false,
    "dualRole": true,
    "admin": true,
    "superAdmin": true,
    "techLevel": "ops",
    "consultantTier": null,
    "allowedAvatars": [
      "client",
      "consultant"
    ],
    "landing": "admin",
    "accent": "admin",
    "blurb": "Super Admin — platform ops, Users/roles, Live Activity; project secrets only when a member.",
    "journey": [
      "Admin Panel (platform)",
      "Grant Admin roles",
      "Creator + QA Hunter switch"
    ],
    "ypadDesignColumn": "D6",
    "firstVisit": false,
    "fictional": true
  },
  {
    "id": "p7",
    "code": "P7",
    "name": "Taylor Kim",
    "title": "Power Creator",
    "role": "client-power",
    "defaultAvatar": "client",
    "aiDefault": true,
    "aiLocked": false,
    "dualRole": false,
    "admin": false,
    "techLevel": "engineer",
    "consultantTier": null,
    "allowedAvatars": [
      "client"
    ],
    "landing": "app",
    "accent": "power",
    "blurb": "Engineer who edits yPAD CSVs, fStart configs, AI docs, shrink/restore.",
    "journey": [
      "yPAD explorer",
      "fStart editor",
      ".md AI context · cost meter"
    ],
    "ypadDesignColumn": "D7",
    "firstVisit": false,
    "fictional": true
  },
  {
    "id": "p8",
    "code": "P8",
    "name": "Riley Okonkwo",
    "title": "Bug-bounty QA Hunter",
    "role": "consultant-bounty",
    "defaultAvatar": "consultant",
    "aiDefault": true,
    "aiLocked": false,
    "dualRole": false,
    "admin": false,
    "techLevel": "security",
    "consultantTier": "bounty",
    "allowedAvatars": [
      "consultant"
    ],
    "landing": "app",
    "accent": "bounty",
    "blurb": "External tester via bug-bounty tag — critical issues focus.",
    "journey": [
      "Join via invite tag",
      "Critical issues",
      "Submit enriched report"
    ],
    "ypadDesignColumn": "D8",
    "firstVisit": false,
    "fictional": true
  },
  {
    "id": "p9",
    "code": "P9",
    "name": "Casey Nguyen",
    "title": "First-time user",
    "role": "new-user",
    "defaultAvatar": "client",
    "aiDefault": true,
    "aiLocked": false,
    "dualRole": false,
    "admin": false,
    "techLevel": "new",
    "consultantTier": null,
    "allowedAvatars": [
      "client"
    ],
    "landing": "signin",
    "accent": "newcomer",
    "blurb": "Never used BRAHL before. Starts at sign-in, explores personas, adds a first challenge, learns Creator vs QA Hunter from the UI — no preloaded suite.",
    "journey": [
      "Sign-in page",
      "Pick profile · learn roles",
      "Add first challenge",
      "Build checklist"
    ],
    "ypadDesignColumn": "D9",
    "firstVisit": true,
    "fictional": true
  }
];

function getProfileById(id) {
  return TEST_PROFILES.find((p) => p.id === id) || null;
}

function getActiveProfile() {
  return getProfileById(localStorage.getItem(STORAGE_PROFILE));
}

function saveProfile(id) {
  localStorage.setItem(STORAGE_PROFILE, id);
}

function clearStoredProfile() {
  localStorage.removeItem(STORAGE_PROFILE);
}

function profileAllowsAvatar(profile, avatar) {
  if (!profile) return true;
  return (profile.allowedAvatars || []).includes(avatar);
}

function profileLabel(profile) {
  if (!profile) return "";
  return `${profile.code} · ${profile.name}`;
}
