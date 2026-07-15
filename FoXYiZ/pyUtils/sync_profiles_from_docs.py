#!/usr/bin/env python3
"""Sync web/profiles.js from Docs/test-user-data/. Run from KK/: python u/sync_profiles_from_docs.py"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from _paths import KK_ROOT

sys.path.insert(0, str(KK_ROOT / "qoa_web" / "api"))

import test_users  # noqa: E402

OUT = KK_ROOT / "qoa_web" / "web" / "profiles.js"

HEADER = """/** Test personas — generated from Docs/test-user-data/. Do not edit by hand. */
const STORAGE_PROFILE = "qoa_web_profile";

const TEST_PROFILES = """

FOOTER = """
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
"""


def main() -> None:
    profiles = test_users.all_frontend_profiles()
    body = json.dumps(profiles, indent=2, ensure_ascii=False)
    OUT.write_text(HEADER + body + ";\n" + FOOTER, encoding="utf-8")
    print(f"Wrote {OUT} ({len(profiles)} personas from Docs/test-user-data/)")


if __name__ == "__main__":
    main()
