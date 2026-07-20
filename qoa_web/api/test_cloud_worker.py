"""Unit tests for cloud worker status helpers (no network required for unset URL)."""

from __future__ import annotations

import cloud_worker as cw


def test_cloud_not_configured_by_default(monkeypatch) -> None:
    monkeypatch.delenv("FOXYIZ_CLOUD_WORKER_URL", raising=False)
    monkeypatch.delenv("FOXYIZ_CLOUD_TOKEN", raising=False)
    assert cw.cloud_configured() is False
    st = cw.cloud_status()
    assert st["configured"] is False
    assert st["reachable"] is False


def test_cloud_configured_flag(monkeypatch) -> None:
    monkeypatch.setenv("FOXYIZ_CLOUD_WORKER_URL", "http://127.0.0.1:9")
    monkeypatch.setenv("FOXYIZ_CLOUD_TOKEN", "secret")
    assert cw.cloud_configured() is True
    st = cw.cloud_status()
    assert st["worker_url_set"] is True
    assert st["token_set"] is True
    # port 9 should not be reachable
    assert st["reachable"] is False
