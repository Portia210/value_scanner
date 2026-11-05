from pathlib import Path

import pytest

from value_scanner.cli import main
from value_scanner.settings import DEFAULT_DB_PATH, SettingsError, load_settings


def test_defaults_when_env_empty():
    s = load_settings({})
    assert s.db_path == Path(DEFAULT_DB_PATH)
    assert s.my_email is None


def test_reads_values_and_strips_whitespace():
    s = load_settings({"DB_PATH": "/data/x.db", "MY_EMAIL": "  a@b.co  ", "SESSION_SECRET": " "})
    assert s.db_path == Path("/data/x.db")
    assert s.my_email == "a@b.co"
    assert s.session_secret is None  # blank counts as unset


def test_require_names_variable_but_not_value():
    s = load_settings({})
    with pytest.raises(SettingsError, match="MY_EMAIL is not set"):
        s.require("my_email")
    assert load_settings({"MY_EMAIL": "a@b.co"}).require("my_email") == "a@b.co"


def test_repr_hides_secrets():
    fake_password = "not-a-real-password"  # pragma: allowlist secret
    s = load_settings(
        {"MY_EMAIL": "a@b.co", "DASHBOARD_PASSWORD": fake_password, "GOOGLE_API_KEY": "k"}
    )
    text = repr(s)
    assert "a@b.co" not in text and fake_password not in text


def test_cli_help_exits_zero(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0
    assert "run" in capsys.readouterr().out


def test_cli_unknown_command_is_an_error(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["bogus"])
    assert exc.value.code == 2


def test_google_app_password_configures_gmail():
    fake = "app-password-for-test"  # pragma: allowlist secret
    s = load_settings({"MY_EMAIL": "a@b.co", "GOOGLE_APP_PASSWORD": fake})
    assert (s.smtp_host, s.smtp_port, s.smtp_user) == ("smtp.gmail.com", 587, "a@b.co")
    assert s.smtp_password == fake and fake not in repr(s)


def test_explicit_smtp_settings_beat_the_gmail_shortcut():
    s = load_settings(
        {
            "MY_EMAIL": "a@b.co",
            "GOOGLE_APP_PASSWORD": "x",
            "SMTP_HOST": "mail.example.com",
            "SMTP_USER": "u",
            "SMTP_PASSWORD": "p",
        }  # pragma: allowlist secret
    )
    assert (s.smtp_host, s.smtp_user, s.smtp_password) == ("mail.example.com", "u", "p")
