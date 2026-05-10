"""Packaging invariants for security-critical data files."""

from __future__ import annotations

import tomllib
from pathlib import Path


def test_security_policy_yaml_is_forced_into_wheel() -> None:
    """Fail-closed sanitizer must ship its YAML policy in built wheels."""
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    wheel_config = pyproject["tool"]["hatch"]["build"]["targets"]["wheel"]
    force_include = wheel_config.get("force-include", {})

    assert "sky_claw/antigravity/security/security_policy.yaml" in force_include
    assert (
        force_include["sky_claw/antigravity/security/security_policy.yaml"]
        == "sky_claw/antigravity/security/security_policy.yaml"
    )


def test_security_policy_yaml_is_in_pyinstaller_datas() -> None:
    """Frozen builds must bundle policy YAML before sanitizer import."""
    spec = Path("sky_claw.spec").read_text(encoding="utf-8")

    assert '("sky_claw/antigravity/security/security_policy.yaml", "sky_claw/antigravity/security")' in spec
