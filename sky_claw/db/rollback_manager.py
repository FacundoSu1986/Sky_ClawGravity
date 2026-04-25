# sky_claw/db/rollback_manager.py

from __future__ import annotations

import logging
import pathlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from .journal import OperationJournal, OperationStatus, OperationType

if TYPE_CHECKING:
    from .snapshot_manager import FileSnapshotManager

logger = logging.getLogger(__name__)


class RollbackError(Exception):
    """Error durante operación de rollback."""

    pass


@dataclass(frozen=True)
class RollbackResult:
    """Resultado inmutable de una operación de rollback.

    ``frozen=True`` garantiza que el resultado no pueda ser mutado después
    de la construcción, previniendo bugs por asignación accidental de campos
    (ej. ``result.success = False`` que enmascararía el resultado real del rollback).
    """

    success: bool
    transaction_id: int | None = None
    entries_restored: int = 0
    files_deleted: int = 0
    errors: tuple[str, ...] = ()
    dry_run: bool = False
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class RollbackManager:
    """Gestiona operaciones de rollback para archivos."""

    def __init__(
        self,
        journal: OperationJournal,
        snapshot_manager: FileSnapshotManager,
    ) -> None:
        self._journal = journal
        self._snapshots = snapshot_manager

    async def __aenter__(self) -> RollbackManager:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        pass

    async def undo_last_operation(self, agent_id: str) -> RollbackResult:
        """
        Revierte la última operación de un agente.

        Flujo:
        1. Consultar Journal para obtener última operación 'COMPLETED' o 'FAILED'
        2. Delegar al FileSnapshotManager para restaurar archivo original
        3. Actualizar estado de la entrada en el Journal a 'ROLLED_BACK'
        """
        # Obtener última operación
        entry = await self._journal.get_last_operation(agent_id, [OperationStatus.COMPLETED, OperationStatus.FAILED])

        if entry is None:
            return RollbackResult(
                success=False,
                transaction_id=None,
                errors=("No completed or failed operation found for agent",),
            )

        # Restaurar archivo desde snapshot
        if entry.snapshot_path:
            try:
                await self._snapshots.restore_snapshot(
                    pathlib.Path(entry.snapshot_path), pathlib.Path(entry.target_path)
                )
            except OSError as e:
                logger.critical("Rollback failed for %s: %s", agent_id, str(e), exc_info=True)
                raise RollbackError(str(e)) from e

        # Actualizar estado en journal
        await self._journal.mark_rolled_back(entry.id)

        return RollbackResult(
            success=True,
            transaction_id=entry.id,
            entries_restored=1 if entry.snapshot_path else 0,
            files_deleted=1 if entry.operation_type in [OperationType.FILE_CREATE, OperationType.MOD_INSTALL] else 0,
            errors=(),
        )
