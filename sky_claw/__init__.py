"""Sky-Claw – Autonomous Skyrim mod management agent."""

__version__ = "0.1.0"

# FASE 5: Asset Conflict Detection Module
from sky_claw.assets import (
    AssetType,
    AssetInfo,
    AssetConflictReport,
    AssetConflictDetector,
)

__all__ = [
    "AssetType",
    "AssetInfo",
    "AssetConflictReport",
    "AssetConflictDetector",
]
