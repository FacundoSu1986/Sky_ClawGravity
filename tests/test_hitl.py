"""Tests for sky_claw.security.hitl."""

from __future__ import annotations

import asyncio

import pytest

from sky_claw.security.hitl import Decision, HITLGuard, HITLRequest


# ------------------------------------------------------------------
# Detection
# ------------------------------------------------------------------


class TestRequiresApproval:
    def test_github_requires_approval(self) -> None:
        guard = HITLGuard()
        assert guard.requires_approval("https://github.com/user/repo") is True

    def test_patreon_requires_approval(self) -> None:
        guard = HITLGuard()
        assert guard.requires_approval("https://patreon.com/modauthor") is True

    def test_nexus_does_not_require_approval(self) -> None:
        guard = HITLGuard()
        assert guard.requires_approval("https://www.nexusmods.com/mod/1") is False

    def test_mega_requires_approval(self) -> None:
        guard = HITLGuard()
        assert guard.requires_approval("https://mega.nz/file/abc") is True


# ------------------------------------------------------------------
# Approval flow
# ------------------------------------------------------------------


class TestApprovalFlow:
    @pytest.mark.asyncio
    async def test_approved_flow(self) -> None:
        notifications: list[HITLRequest] = []

        async def fake_notify(req: HITLRequest) -> None:
            notifications.append(req)

        guard = HITLGuard(notify_fn=fake_notify, timeout=5)

        async def approve_later() -> None:
            await asyncio.sleep(0.1)
            guard.respond("req-1", approved=True)

        task = asyncio.create_task(approve_later())
        decision = await guard.request_approval("req-1", "test reason")
        await task
        assert decision is Decision.APPROVED
        assert len(notifications) == 1

    @pytest.mark.asyncio
    async def test_denied_flow(self) -> None:
        guard = HITLGuard(timeout=5)

        async def deny_later() -> None:
            await asyncio.sleep(0.1)
            guard.respond("req-2", approved=False)

        task = asyncio.create_task(deny_later())
        decision = await guard.request_approval("req-2", "test deny")
        await task
        assert decision is Decision.DENIED

    @pytest.mark.asyncio
    async def test_timeout_flow(self) -> None:
        guard = HITLGuard(timeout=0.2)
        decision = await guard.request_approval("req-t", "timeout test")
        assert decision is Decision.TIMEOUT

    def test_respond_unknown_id(self) -> None:
        guard = HITLGuard()
        assert guard.respond("nonexistent", approved=True) is False
