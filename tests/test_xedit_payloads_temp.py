import pytest
from pydantic import ValidationError

from sky_claw.core.event_payloads import (
    XEditPatchCompletedPayload,
    XEditPatchStartedPayload,
)


def test_started_payload_is_immutable():
    p = XEditPatchStartedPayload(target_plugin="ModA.esp", total_conflicts=3)
    with pytest.raises(ValidationError):
        p.target_plugin = "changed"  # frozen=True debe lanzar


def test_completed_payload_fields():
    p = XEditPatchCompletedPayload(
        target_plugin="ModA.esp",
        total_conflicts=3,
        success=True,
        records_patched=12,
        conflicts_resolved=3,
        duration_seconds=1.5,
        rolled_back=False,
    )
    assert p.success is True
    assert p.rolled_back is False


def test_payloads_to_log_dict():
    p = XEditPatchStartedPayload(target_plugin="ModA.esp", total_conflicts=5)
    d = p.to_log_dict()
    assert d["target_plugin"] == "ModA.esp"
    assert "started_at" in d
