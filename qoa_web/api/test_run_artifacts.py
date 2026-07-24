"""Run artifact discovery (screenshots, visual playback, filmstrip)."""
from __future__ import annotations

from pathlib import Path

from runner import list_run_artifacts


def test_list_run_artifacts_discovers_playback_and_overlays(tmp_path: Path, monkeypatch) -> None:
    import runner as runner_mod

    run = tmp_path / "20260722_120000_site_shots"
    plan = run / "20260722_120000_PShot_Home"
    plan.mkdir(parents=True)
    (run / "visual_playback.html").write_text("<html></html>", encoding="utf-8")
    (run / "visual_frames.jsonl").write_text("{}\n", encoding="utf-8")
    (run / "site_shots_zDash.html").write_text("<html></html>", encoding="utf-8")
    (plan / "PShot_Home_D1_5_ov_orange_120001.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    (plan / "PShot_Home_D1_4_home_120000.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    (run / "20260722_120000_site_shots_roll.gif").write_bytes(b"GIF89a")
    (run / "20260722_120000_site_shots_filmstrip.png").write_bytes(b"\x89PNG\r\n\x1a\n")

    monkeypatch.setattr(runner_mod, "Z_DIR", tmp_path)
    arts = list_run_artifacts(run.name)
    assert arts["visual_playback"]["url"].endswith("/visual_playback.html")
    assert arts["visual_frames"] is not None
    assert arts["dashboard"] is not None
    assert arts["counts"]["overlays"] == 1
    assert arts["counts"]["screenshots"] == 1
    assert arts["gif"] is not None
    assert arts["filmstrip"] is not None
