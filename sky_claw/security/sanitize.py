"""Input sanitization for external content injected into LLM prompts.

Scraped web content (Nexus Mods descriptions, LOOT metadata, etc.)
must be sanitized before being embedded in prompts to prevent:

* **Prompt Injection** – adversarial text that overrides the system
  prompt or forces unintended tool calls.
* **Malformed JSON** – broken Unicode or control characters that break
  downstream JSON serialization.
"""

from __future__ import annotations

import json
import re

# Characters that have special meaning in many LLM prompt formats.
_CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

# Cap to avoid token-bomb attacks from massive scraped pages.
DEFAULT_MAX_LENGTH = 8192


def sanitize_for_prompt(
    text: str,
    *,
    max_length: int = DEFAULT_MAX_LENGTH,
    strip_control: bool = True,
) -> str:
    """Clean *text* so it is safe to embed in an LLM prompt.

    1. Removes ASCII control characters (except ``\\n``, ``\\r``, ``\\t``).
    2. Truncates to *max_length* characters to bound token usage.
    3. Escapes sequences that resemble common prompt-injection markers
       (e.g. ``<|system|>``, ``<|im_start|>``).

    Args:
        text: Raw external content.
        max_length: Maximum allowed length after sanitization.
        strip_control: Whether to strip ASCII control characters.

    Returns:
        Sanitized string safe for prompt embedding.
    """
    if strip_control:
        text = _CONTROL_CHAR_RE.sub("", text)

    # Defang common prompt-injection delimiters.
    text = text.replace("<|", "< |").replace("|>", "| >")

    if len(text) > max_length:
        text = text[:max_length] + "… [truncated]"

    return text


def safe_json_loads(raw: str) -> dict | list | None:
    """Attempt to parse *raw* as JSON, returning ``None`` on failure.

    This is a convenience wrapper that never raises, making it safe to
    use on untrusted scraped payloads.
    """
    try:
        result = json.loads(raw)
        if isinstance(result, (dict, list)):
            return result
        return None
    except (json.JSONDecodeError, TypeError, ValueError):
        return None
