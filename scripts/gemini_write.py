#!/usr/bin/env python3
"""Gemini Write Pipeline — Anti-hallucination barrier.

Usage:
    python scripts/gemini_write.py --prompt "Implement X" --output sky_claw/module.py
    python scripts/gemini_write.py --prompt "Fix bug in Y" --output sky_claw/fix.py --model gemini-2.5-flash

Pipeline: Gemini API → extract code → ruff fix → mypy check → pytest -x --tb=short
"""

from __future__ import annotations

import argparse
import logging
import os
import re
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger("gemini-write")


# ---------------------------------------------------------------------------
# Gemini API Integration
# ---------------------------------------------------------------------------


def call_gemini(prompt: str, model: str = "gemini-2.5-pro") -> str:
    """Send prompt to Gemini API and return raw response text.

    Requires GEMINI_API_KEY environment variable or keyring entry.
    """
    try:
        from google import genai
    except ImportError:
        logger.error("google-genai not installed. Run: uv add google-genai")
        sys.exit(1)

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        # Fallback: try keyring
        try:
            import keyring

            api_key = keyring.get_password("sky-claw", "gemini-api-key")
        except Exception:
            pass

    if not api_key:
        logger.error("GEMINI_API_KEY not set. Run: setx GEMINI_API_KEY 'your-key'")
        sys.exit(1)

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model,
        contents=prompt,
    )
    if response.text is None:
        logger.error("Gemini returned empty response")
        sys.exit(1)
    return response.text


# ---------------------------------------------------------------------------
# Code Extraction
# ---------------------------------------------------------------------------


def extract_code(response: str) -> str:
    """Extract Python code block from markdown-wrapped response."""
    # Try ```python ... ``` first
    match = re.search(r"```python\s*\n(.*?)```", response, re.DOTALL)
    if match:
        return match.group(1).strip()

    # Try generic ``` ... ```
    match = re.search(r"```\s*\n(.*?)```", response, re.DOTALL)
    if match:
        return match.group(1).strip()

    # Assume raw code
    return response.strip()


# ---------------------------------------------------------------------------
# Validation Pipeline
# ---------------------------------------------------------------------------


def _run_cmd(cmd: list[str], label: str) -> tuple[bool, str]:
    """Run a subprocess command and return (success, output)."""
    logger.info("Running %s: %s", label, " ".join(cmd))
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=120,
    )
    output = result.stdout + result.stderr
    if result.returncode != 0:
        logger.warning("%s failed (exit %d):\n%s", label, result.returncode, output)
    else:
        logger.info("%s passed", label)
    return result.returncode == 0, output


def validate_ruff(filepath: Path) -> bool:
    """Run ruff check --fix + ruff format on the file."""
    ok1, _ = _run_cmd(
        [sys.executable, "-m", "ruff", "check", "--fix", str(filepath)],
        "ruff-check",
    )
    ok2, _ = _run_cmd(
        [sys.executable, "-m", "ruff", "format", str(filepath)],
        "ruff-format",
    )
    return ok1 and ok2


def validate_mypy(filepath: Path) -> bool:
    """Run mypy type checking on the file."""
    ok, output = _run_cmd(
        [sys.executable, "-m", "mypy", str(filepath), "--config-file=pyproject.toml"],
        "mypy",
    )
    if not ok:
        print(f"[FAIL] mypy errors:\n{output}", file=sys.stderr)
    return ok


def run_pytest(test_path: str = "tests/", tb: str = "short") -> bool:
    """Run pytest with fail-fast and short traceback."""
    ok, output = _run_cmd(
        [sys.executable, "-m", "pytest", "-x", f"--tb={tb}", test_path],
        "pytest",
    )
    if not ok:
        print(f"[FAIL] pytest failures:\n{output}", file=sys.stderr)
    return ok


# ---------------------------------------------------------------------------
# Main Pipeline
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Gemini Write Pipeline: Gemini → ruff → mypy → pytest",
    )
    parser.add_argument("--prompt", required=True, help="Prompt for Gemini code generation")
    parser.add_argument("--output", required=True, help="Output file path for generated code")
    parser.add_argument("--model", default="gemini-2.5-pro", help="Gemini model to use")
    parser.add_argument("--skip-tests", action="store_true", help="Skip pytest step")
    parser.add_argument("--test-path", default="tests/", help="Test path for pytest")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose logging")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    output_path = Path(args.output)

    # Step 1: Generate code with Gemini
    print(f"[AI] Generating code with {args.model}...")
    raw_response = call_gemini(args.prompt, args.model)
    code = extract_code(raw_response)

    # Step 2: Write to file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(code + "\n", encoding="utf-8")
    print(f"[OK] Written to {output_path}")

    # Step 3: Validate with ruff
    print("[>>] Running ruff...")
    ruff_ok = validate_ruff(output_path)
    if not ruff_ok:
        print("[WARN] ruff found issues (auto-fixed where possible)")

    # Step 4: Validate with mypy
    print("[>>] Running mypy...")
    mypy_ok = validate_mypy(output_path)
    if not mypy_ok:
        print("[FAIL] mypy type errors -- aborting")
        sys.exit(1)

    # Step 5: Run tests
    if not args.skip_tests:
        print("[>>] Running pytest...")
        tests_ok = run_pytest(args.test_path)
        if not tests_ok:
            print("[FAIL] Tests failed -- code may be hallucinated")
            sys.exit(1)

    print("[PASS] All validations passed! Code is ready for review.")


if __name__ == "__main__":
    main()
