from __future__ import annotations

import pytest
from pydantic import SecretStr

from app.core.exceptions import ConfigError
from scripts import _env_check


def test_valid_ascii_key_passes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(_env_check.settings, "llm_api_key", SecretStr("sk-" + "a" * 32))
    _env_check.assert_llm_api_key_is_real()


def test_non_ascii_key_raises_config_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(_env_check.settings, "llm_api_key", SecretStr("sk-请在此填入Key"))
    with pytest.raises(ConfigError) as exc_info:
        _env_check.assert_llm_api_key_is_real()
    assert "non-ASCII" in str(exc_info.value)


def test_key_without_sk_prefix_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(_env_check.settings, "llm_api_key", SecretStr("xx-" + "a" * 32))
    with pytest.raises(ConfigError) as exc_info:
        _env_check.assert_llm_api_key_is_real()
    assert "sk-" in str(exc_info.value)


def test_too_short_key_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(_env_check.settings, "llm_api_key", SecretStr("sk-short"))
    with pytest.raises(ConfigError) as exc_info:
        _env_check.assert_llm_api_key_is_real()
    assert "shorter" in str(exc_info.value)


def test_error_message_does_not_leak_key_value(monkeypatch: pytest.MonkeyPatch) -> None:
    secret = "sk-中文占位符test"
    monkeypatch.setattr(_env_check.settings, "llm_api_key", SecretStr(secret))
    with pytest.raises(ConfigError) as exc_info:
        _env_check.assert_llm_api_key_is_real()
    assert secret not in str(exc_info.value)
    assert "中文占位符" not in str(exc_info.value)
