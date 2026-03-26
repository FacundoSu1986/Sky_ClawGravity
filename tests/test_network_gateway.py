"""Tests for sky_claw.security.network_gateway."""

from __future__ import annotations

import pytest

from sky_claw.security.network_gateway import (
    EgressPolicy,
    EgressViolation,
    NetworkGateway,
)


@pytest.fixture()
def gw() -> NetworkGateway:
    """Gateway with private-IP checks disabled (avoids DNS in CI)."""
    policy = EgressPolicy(block_private_ips=False)
    return NetworkGateway(policy)


@pytest.fixture()
def gw_strict() -> NetworkGateway:
    """Gateway with full policy (including private-IP blocking)."""
    return NetworkGateway()


# ------------------------------------------------------------------
# Domain allow-list
# ------------------------------------------------------------------


class TestHostAllowList:
    def test_nexus_www_allowed(self, gw: NetworkGateway) -> None:
        gw.authorize("GET", "https://www.nexusmods.com/skyrimspecialedition/mods/1234")

    def test_nexus_subdomain_allowed(self, gw: NetworkGateway) -> None:
        gw.authorize("GET", "https://staticdelivery.nexusmods.com/file.7z")

    def test_telegram_allowed(self, gw: NetworkGateway) -> None:
        gw.authorize("POST", "https://api.telegram.org/bot123456:ABC/sendMessage")

    def test_random_host_blocked(self, gw: NetworkGateway) -> None:
        with pytest.raises(EgressViolation, match="not in the allow-list"):
            gw.authorize("GET", "https://evil.example.com/payload")

    def test_github_get_allowed(self, gw: NetworkGateway) -> None:
        # github.com is in the allow-list for GET (tool auto-install).
        gw.authorize("GET", "https://github.com/some/repo")

    def test_github_post_blocked(self, gw: NetworkGateway) -> None:
        with pytest.raises(EgressViolation, match="not allowed"):
            gw.authorize("POST", "https://github.com/some/repo")

    def test_empty_url_rejected(self, gw: NetworkGateway) -> None:
        with pytest.raises(EgressViolation, match="no hostname"):
            gw.authorize("GET", "")


# ------------------------------------------------------------------
# Method restrictions
# ------------------------------------------------------------------


class TestMethodRestrictions:
    def test_nexus_get_ok(self, gw: NetworkGateway) -> None:
        gw.authorize("GET", "https://www.nexusmods.com/mods")

    def test_nexus_post_blocked(self, gw: NetworkGateway) -> None:
        with pytest.raises(EgressViolation, match="not allowed"):
            gw.authorize("POST", "https://www.nexusmods.com/api/upload")

    def test_telegram_get_ok(self, gw: NetworkGateway) -> None:
        gw.authorize("GET", "https://api.telegram.org/bot123/getUpdates")

    def test_telegram_post_ok(self, gw: NetworkGateway) -> None:
        gw.authorize("POST", "https://api.telegram.org/bot123/sendMessage")


# ------------------------------------------------------------------
# Telegram path prefix
# ------------------------------------------------------------------


class TestTelegramPathPrefix:
    def test_valid_bot_path(self, gw: NetworkGateway) -> None:
        gw.authorize("GET", "https://api.telegram.org/bot123/getMe")

    def test_missing_bot_prefix(self, gw: NetworkGateway) -> None:
        with pytest.raises(EgressViolation, match="does not start with"):
            gw.authorize("GET", "https://api.telegram.org/file/something")


# ------------------------------------------------------------------
# Private-IP blocking
# ------------------------------------------------------------------


class TestPrivateIPBlocking:
    def test_loopback_literal_blocked(self, gw_strict: NetworkGateway) -> None:
        with pytest.raises(EgressViolation, match="private/loopback"):
            gw_strict.authorize("GET", "http://127.0.0.1:8080/data")

    def test_private_10_blocked(self, gw_strict: NetworkGateway) -> None:
        with pytest.raises(EgressViolation, match="private/loopback"):
            gw_strict.authorize("GET", "http://10.0.0.1/data")

    def test_private_192_blocked(self, gw_strict: NetworkGateway) -> None:
        with pytest.raises(EgressViolation, match="private/loopback"):
            gw_strict.authorize("GET", "http://192.168.1.1/data")

    def test_link_local_blocked(self, gw_strict: NetworkGateway) -> None:
        with pytest.raises(EgressViolation, match="private/loopback"):
            gw_strict.authorize("GET", "http://169.254.0.1/x")
