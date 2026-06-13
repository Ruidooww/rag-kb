"""Env sanity check for batch scripts (#26 follow-up).

Raise ConfigError before any LLM call if LLM_API_KEY is missing,
contains non-ASCII chars, lacks the standard 'sk-' prefix, or is
shorter than a real Bailian key. Pure boundary check — never logs
or exposes the key value.
"""

from __future__ import annotations

from app.core.config import settings
from app.core.exceptions import ConfigError

_MIN_KEY_LENGTH = 20
_KEY_PREFIX = "sk-"


def assert_llm_api_key_is_real() -> None:
    """Validate LLM_API_KEY format without leaking its value."""
    key = settings.llm_api_key.get_secret_value()
    if not key.isascii():
        raise ConfigError("LLM_API_KEY contains non-ASCII characters")
    if not key.startswith(_KEY_PREFIX):
        raise ConfigError(f"LLM_API_KEY must start with {_KEY_PREFIX!r}")
    if len(key) < _MIN_KEY_LENGTH:
        raise ConfigError(f"LLM_API_KEY is shorter than {_MIN_KEY_LENGTH} chars")
