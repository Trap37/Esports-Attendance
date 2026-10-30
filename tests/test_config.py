"""Tests for application configuration and logging filters."""

import logging

from config import Config, EASTERN, IgnorePendingRequests


def test_eastern_timezone_is_configured():
    assert EASTERN.key == "America/New_York"


def test_default_config_has_secret_and_sqlite_database_uri(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert Config.SECRET_KEY
    assert Config.SQLALCHEMY_DATABASE_URI.startswith("sqlite:///")


def test_config_respects_environment_overrides(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "configured-secret")
    monkeypatch.setenv("DATABASE_URL", "sqlite:////tmp/esports-test.db")
    # Config values are evaluated when the class is defined, so verify the
    # current implementation's environment lookup through a fresh module.
    import importlib
    import config

    importlib.reload(config)
    try:
        assert config.Config.SECRET_KEY == "configured-secret"
        assert config.Config.SQLALCHEMY_DATABASE_URI == "sqlite:////tmp/esports-test.db"
    finally:
        importlib.reload(config)


def test_pending_registration_poll_requests_are_filtered():
    filter_ = IgnorePendingRequests()
    assert filter_.filter(logging.LogRecord("werkzeug", 20, "", 1, "GET /api/students/pending", (), None)) is False


def test_other_requests_are_not_filtered():
    filter_ = IgnorePendingRequests()
    record = logging.LogRecord("werkzeug", 20, "", 1, "POST /api/scan", (), None)
    assert filter_.filter(record) is True
