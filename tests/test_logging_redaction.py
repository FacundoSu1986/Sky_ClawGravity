from __future__ import annotations

import logging
from unittest.mock import patch

from sky_claw import logging_config
from sky_claw.logging_config import SecurityRedactionFilter


def test_redacts_modern_llm_and_bearer_tokens() -> None:
    redact_filter = SecurityRedactionFilter()
    text = (
        "openai=sk-proj-ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 "
        "anthropic=sk-ant-ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 "
        "auth=Authorization: Bearer abcdefghijklmnopqrstuvwxyz0123456789"
    )

    redacted = redact_filter._redact(text)

    assert "sk-proj-" not in redacted
    assert "sk-ant-" not in redacted
    assert "Bearer abc" not in redacted
    assert redacted.count("[REDACTED]") == 3


def test_redacts_long_telegram_bot_ids() -> None:
    redact_filter = SecurityRedactionFilter()

    redacted = redact_filter._redact("token=12345678901:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi")

    assert "12345678901:" not in redacted
    assert redacted == "token=[REDACTED]"


def test_filter_redacts_nested_extra_values() -> None:
    redact_filter = SecurityRedactionFilter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="event",
        args=(),
        exc_info=None,
    )
    record.context = {
        "headers": {"Authorization": "Bearer abcdefghijklmnopqrstuvwxyz0123456789"},
        "keys": ["sk-proj-ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"],
    }

    assert redact_filter.filter(record)

    assert "Bearer abc" not in str(record.context)
    assert "sk-proj-" not in str(record.context)


def test_filter_breaks_cycles_in_nested_extra_values() -> None:
    redact_filter = SecurityRedactionFilter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="event",
        args=(),
        exc_info=None,
    )
    context: dict[str, object] = {"token": "sk-proj-ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"}
    context["self"] = context
    record.context = context

    assert redact_filter.filter(record)

    assert record.context["self"] == "[REDACTED:CYCLE]"
    assert "sk-proj-" not in str(record.context)


def test_resolve_current_user_falls_back_for_legacy_getpass_errors() -> None:
    with patch("sky_claw.logging_config.getpass.getuser", side_effect=KeyError("missing passwd entry")):
        assert logging_config._resolve_current_user() == "User"
