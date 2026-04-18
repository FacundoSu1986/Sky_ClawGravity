# xEdit Pipeline Service Extraction — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract xEdit patching logic (≈210 líneas) from `SupervisorAgent` a `XEditPipelineService` dedicado, completando el patrón Strangler Fig para Sprint 2 Fase 4.

**Architecture:** Sigue el patrón de `SynthesisPipelineService` — todas las dependencias inyectadas vía constructor, `SnapshotTransactionLock` reemplaza el manejo manual de snapshot/rollback, `CoreEventBus` para observabilidad. `SupervisorAgent` se convierte en un router delegado fino.

**Tech Stack:** Python 3.12, Pydantic v2 (`ConfigDict(frozen=True, strict=True)`), asyncio, SQLite (`DistributedLockManager`, `FileSnapshotManager`), `CoreEventBus`.

---

## File Map

| Acción | Archivo | Responsabilidad |
|--------|---------|-----------------|
| Modify | `sky_claw/core/event_payloads.py` | Agregar `XEditPatchStartedPayload`, `XEditPatchCompletedPayload` |
| Create | `sky_claw/tools/xedit_service.py` | `XEditPipelineService` con `execute_patch()` transaccional |
| Modify | `sky_claw/orchestrator/supervisor.py` | Eliminar 5 métodos xEdit, instanciar servicio, agregar caso en `dispatch_tool`, purgar imports F401 |
| Create | `tests/test_xedit_service.py` | Tests unitarios/integración para el nuevo servicio |

---

### CONTEXTO CRÍTICO para el ejecutor

Antes de empezar, leer estos archivos para entender el patrón a seguir:
- `sky_claw/tools/synthesis_service.py` — patrón exacto a replicar
- `sky_claw/core/event_payloads.py` — dónde agregar los nuevos payloads
- `sky_claw/orchestrator/supervisor.py` líneas 52-62, 159-237, 1119-1336 — código a eliminar
- `tests/test_synthesis_service.py` — patrón de tests a replicar

**Imports a PURGAR de supervisor.py** (causan F401 tras la extracción):
```python
# ELIMINAR completamente:
from sky_claw.xedit.patch_orchestrator import (
    PatchingError,
    PatchOrchestrator,
    PatchPlan,
    PatchResult,
    PatchStrategyType,
)
from sky_claw.xedit.runner import ScriptExecutionResult, XEditRunner
```

**Imports que PERMANECEN en supervisor.py** (usados fuera de xEdit):
```python
# CONSERVAR — ConflictAnalyzer se usa en _run_plugin_limit_guard (línea 611)
from sky_claw.xedit.conflict_analyzer import ConflictAnalyzer, ConflictReport
# CONSERVAR — SnapshotInfo se usa en DynDOLOD pipeline (líneas 864-865, 1087)
from sky_claw.db.snapshot_manager import FileSnapshotManager, SnapshotInfo
```

---

### Task 1: Event Payloads Inmutables

**Files:**
- Modify: `sky_claw/core/event_payloads.py`
- Test: incluido inline en Task 4

- [ ] **Step 1.1: Escribir test fallido para los payloads**

Crear archivo temporal `tests/test_xedit_payloads_temp.py`:

```python
import pytest
from sky_claw.core.event_payloads import XEditPatchStartedPayload, XEditPatchCompletedPayload

def test_started_payload_is_immutable():
    p = XEditPatchStartedPayload(target_plugin="ModA.esp", total_conflicts=3)
    with pytest.raises(Exception):
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
```

- [ ] **Step 1.2: Ejecutar test — debe fallar**

```bash
cd Sky-Claw-fresh && pytest tests/test_xedit_payloads_temp.py -v
```
Esperado: `ImportError: cannot import name 'XEditPatchStartedPayload'`

- [ ] **Step 1.3: Implementar los payloads en event_payloads.py**

Agregar al final del archivo `sky_claw/core/event_payloads.py` (después de `SynthesisPipelineCompletedPayload`):

```python
class XEditPatchStartedPayload(BaseModel):
    """Payload inmutable para el evento ``xedit.patch.started``.

    Publicado por :class:`XEditPipelineService` al iniciar la ejecución
    de un parche xEdit transaccional.

    Attributes:
        target_plugin: Nombre del plugin objetivo del parcheo.
        total_conflicts: Total de conflictos a resolver.
        started_at: Timestamp de inicio (epoch float, autogenerado).
    """

    model_config = ConfigDict(frozen=True, strict=True)

    target_plugin: str
    total_conflicts: int
    started_at: float = Field(default_factory=time.time)

    def to_log_dict(self) -> dict[str, object]:
        """Serialización compatible con el sistema de logging estructurado."""
        return self.model_dump()


class XEditPatchCompletedPayload(BaseModel):
    """Payload inmutable para el evento ``xedit.patch.completed``.

    Publicado por :class:`XEditPipelineService` al finalizar la ejecución
    de un parche xEdit (éxito o fallo).

    Attributes:
        target_plugin: Nombre del plugin objetivo del parcheo.
        total_conflicts: Total de conflictos solicitados.
        success: Si la ejecución fue exitosa.
        records_patched: Número de records procesados.
        conflicts_resolved: Número de conflictos resueltos.
        duration_seconds: Duración total de la ejecución.
        rolled_back: Si se ejecutó rollback automático.
        completed_at: Timestamp de finalización (epoch float, autogenerado).
    """

    model_config = ConfigDict(frozen=True, strict=True)

    target_plugin: str
    total_conflicts: int
    success: bool
    records_patched: int
    conflicts_resolved: int
    duration_seconds: float
    rolled_back: bool
    completed_at: float = Field(default_factory=time.time)

    def to_log_dict(self) -> dict[str, object]:
        """Serialización compatible con el sistema de logging estructurado."""
        return self.model_dump()
```

- [ ] **Step 1.4: Ejecutar test — debe pasar**

```bash
pytest tests/test_xedit_payloads_temp.py -v
```
Esperado: 3 PASSED

- [ ] **Step 1.5: Commit**

```bash
git add sky_claw/core/event_payloads.py tests/test_xedit_payloads_temp.py
git commit -m "feat(sprint-2): add XEditPatch{Started,Completed}Payload immutable event payloads"
```

---

### Task 2: XEditPipelineService

**Files:**
- Create: `sky_claw/tools/xedit_service.py`

- [ ] **Step 2.1: Escribir el servicio completo**

Crear `sky_claw/tools/xedit_service.py`:

```python
"""XEditPipelineService — servicio dedicado para parcheo transaccional xEdit.

Extraído de ``supervisor.py`` como parte del Sprint 2 Fase 4 (Strangler Fig).
Reemplaza el manejo manual de snapshots/rollback con
:class:`SnapshotTransactionLock` para atomicidad y seguridad concurrente.

Regla T11: toda excepción dentro del context manager activa rollback automático
vía ``__aexit__``. El bloque ``except Exception`` exterior marca el journal y
retorna un dict de error serializable — nunca propaga hacia el Supervisor.
"""

from __future__ import annotations

import dataclasses
import logging
import os
import pathlib
import time
from typing import TYPE_CHECKING, Any

from sky_claw.core.event_bus import CoreEventBus, Event
from sky_claw.core.event_payloads import (
    XEditPatchCompletedPayload,
    XEditPatchStartedPayload,
)
from sky_claw.db.locks import (
    DistributedLockManager,
    LockAcquisitionError,
    SnapshotTransactionLock,
)
from sky_claw.xedit.conflict_analyzer import ConflictReport
from sky_claw.xedit.patch_orchestrator import (
    PatchingError,
    PatchOrchestrator,
    PatchPlan,
    PatchResult,
    PatchStrategyType,
)
from sky_claw.xedit.runner import ScriptExecutionResult, XEditRunner

if TYPE_CHECKING:
    from sky_claw.core.path_resolver import PathResolutionService
    from sky_claw.db.journal import OperationJournal
    from sky_claw.db.snapshot_manager import FileSnapshotManager

logger = logging.getLogger(__name__)

_BACKUP_STAGING_DIR = ".skyclaw_backups/"


class XEditPipelineService:
    """Servicio dedicado para la ejecución de parches xEdit transaccionales.

    Coordina ``PatchOrchestrator``, ``XEditRunner``,
    ``SnapshotTransactionLock`` y ``CoreEventBus`` para ejecutar
    parches con protección transaccional y observabilidad.
    """

    AGENT_ID: str = "xedit-service"

    def __init__(
        self,
        *,
        lock_manager: DistributedLockManager,
        snapshot_manager: FileSnapshotManager,
        journal: OperationJournal,
        path_resolver: PathResolutionService,
        event_bus: CoreEventBus,
    ) -> None:
        self._lock_manager = lock_manager
        self._snapshot_manager = snapshot_manager
        self._journal = journal
        self._path_resolver = path_resolver
        self._event_bus = event_bus

        # Lazy init — paths may not be available at construction time
        self._xedit_runner: XEditRunner | None = None
        self._patch_orchestrator: PatchOrchestrator | None = None

    # ------------------------------------------------------------------
    # Lazy initialization (migrado de SupervisorAgent._ensure_patch_orchestrator)
    # ------------------------------------------------------------------

    def _ensure_patch_orchestrator(self) -> PatchOrchestrator:
        """Inicializa lazily el PatchOrchestrator validando paths del entorno.

        CRIT-003: Valida XEDIT_PATH y SKYRIM_PATH antes de usar.

        Returns:
            PatchOrchestrator inicializado.

        Raises:
            PatchingError: Si las variables de entorno son inválidas.
        """
        if self._patch_orchestrator is not None:
            return self._patch_orchestrator

        xedit_path_str = os.environ.get("XEDIT_PATH", "")
        game_path_str = os.environ.get("SKYRIM_PATH", "")

        xedit_path = self._path_resolver.validate_env_path(xedit_path_str, "XEDIT_PATH")
        game_path = self._path_resolver.validate_env_path(game_path_str, "SKYRIM_PATH")

        if not xedit_path or not game_path:
            raise PatchingError(
                "Cannot initialize PatchOrchestrator: "
                "XEDIT_PATH and SKYRIM_PATH environment variables must be valid paths"
            )

        if not xedit_path.exists():
            raise PatchingError(f"xEdit executable not found: {xedit_path}")

        self._xedit_runner = XEditRunner(
            xedit_path=xedit_path,
            game_path=game_path,
            output_dir=pathlib.Path(_BACKUP_STAGING_DIR) / "patches",
        )

        from sky_claw.db.rollback_manager import RollbackManager

        self._patch_orchestrator = PatchOrchestrator(
            xedit_runner=self._xedit_runner,
            snapshot_manager=self._snapshot_manager,
            rollback_manager=RollbackManager(
                journal=self._journal,
                snapshot_manager=self._snapshot_manager,
            ),
        )

        logger.info(
            "PatchOrchestrator inicializado: xedit=%s, game=%s",
            xedit_path,
            game_path,
        )
        return self._patch_orchestrator

    # ------------------------------------------------------------------
    # Patch execution (migrado de SupervisorAgent.resolve_conflict_with_patch)
    # ------------------------------------------------------------------

    async def execute_patch(
        self,
        report: ConflictReport,
        target_plugin: pathlib.Path,
    ) -> dict[str, Any]:
        """Ejecuta un parche xEdit con protección transaccional completa.

        Usa ``SnapshotTransactionLock`` para garantizar atomicidad:
        si la ejecución falla, el snapshot se restaura automáticamente
        via ``__aexit__``.

        Args:
            report: ConflictReport con los conflictos detectados.
            target_plugin: Path al plugin objetivo del parcheo.

        Returns:
            Diccionario serializable con los campos de ``PatchResult``.
        """
        t0 = time.monotonic()

        # --- Early init ---
        try:
            orchestrator = self._ensure_patch_orchestrator()
        except PatchingError as exc:
            logger.error("Error inicializando PatchOrchestrator: %s", exc)
            return self._error_dict(str(exc))

        # --- Publish started event ---
        started_payload = XEditPatchStartedPayload(
            target_plugin=str(target_plugin),
            total_conflicts=report.total_conflicts,
        )
        await self._event_bus.publish(
            Event(
                topic="xedit.patch.started",
                payload=started_payload.to_log_dict(),
                source=self.AGENT_ID,
            )
        )

        # --- Transactional execution ---
        result: PatchResult | None = None
        rolled_back = False
        tx_id: int | None = None
        in_lock_context = False

        try:
            async with SnapshotTransactionLock(
                lock_manager=self._lock_manager,
                snapshot_manager=self._snapshot_manager,
                resource_id=target_plugin.name,
                agent_id=self.AGENT_ID,
                target_files=[target_plugin],
                metadata={
                    "source": "xedit_patch",
                    "plugin": str(target_plugin),
                    "total_conflicts": report.total_conflicts,
                },
            ):
                in_lock_context = True
                tx_id = await self._journal.begin_transaction(
                    description="xedit_patch",
                    agent_id=self.AGENT_ID,
                )

                # Resolver conflictos (genera plan)
                result = await orchestrator.resolve(report)

                # Ejecutar script si el orquestador lo requiere
                if result.success and result.output_path and self._xedit_runner is not None:
                    strategy_type = PatchStrategyType.CREATE_MERGED_PATCH
                    if orchestrator._strategies:
                        strategy_name = orchestrator._strategies[0].__class__.__name__
                        if strategy_name == "ExecuteXEditScript":
                            strategy_type = PatchStrategyType.EXECUTE_XEDIT_SCRIPT
                        elif strategy_name == "ForwardDeclaration":
                            strategy_type = PatchStrategyType.FORWARD_DECLARATION

                    plan = PatchPlan(
                        strategy_type=strategy_type,
                        target_plugins=(
                            [p.plugin_a for p in report.plugin_pairs[:1]]
                            if report.plugin_pairs
                            else []
                        ),
                        output_plugin=str(result.output_path),
                        form_ids=[],
                        estimated_records=result.records_patched,
                        requires_hitl=False,
                    )

                    script_result: ScriptExecutionResult = (
                        await self._xedit_runner.execute_patch(plan)
                    )
                    result = PatchResult(
                        success=script_result.exit_code == 0,
                        output_path=result.output_path,
                        records_patched=script_result.records_processed,
                        conflicts_resolved=len(report.plugin_pairs),
                        xedit_exit_code=script_result.exit_code,
                        warnings=tuple(script_result.warnings),
                        error=(
                            None if script_result.exit_code == 0 else script_result.stderr
                        ),
                    )

                # Lanzar DENTRO del context manager para activar rollback automático
                if result is not None and not result.success:
                    raise PatchingError(
                        f"xEdit falló con código {result.xedit_exit_code}: {result.error}"
                    )

            # Normal exit — lock context exited without error
            in_lock_context = False
            if tx_id is not None:
                await self._journal.commit_transaction(tx_id)

        except PatchingError as exc:
            # __aexit__ ya restauró el snapshot
            rolled_back = True
            if tx_id is not None:
                await self._journal.mark_transaction_rolled_back(tx_id)
            logger.error("Parcheo xEdit falló: %s", exc)
            result = PatchResult(
                success=False,
                output_path=None,
                records_patched=0,
                conflicts_resolved=0,
                xedit_exit_code=-1,
                warnings=(),
                error=str(exc),
            )

        except LockAcquisitionError as exc:
            logger.warning("Lock contention para %s: %s", target_plugin.name, exc)
            result = PatchResult(
                success=False,
                output_path=None,
                records_patched=0,
                conflicts_resolved=0,
                xedit_exit_code=-1,
                warnings=(),
                error=f"Lock contention: {exc}",
            )

        except Exception as exc:
            rolled_back = in_lock_context
            if tx_id is not None:
                try:
                    await self._journal.mark_transaction_rolled_back(tx_id)
                except Exception as rollback_exc:
                    logger.critical(
                        "Failed to mark journal TX %d rolled back after unexpected error: %s",
                        tx_id,
                        rollback_exc,
                        exc_info=True,
                    )
            logger.error(
                "Unexpected exception in xedit patch pipeline: %s", exc, exc_info=True
            )
            result = PatchResult(
                success=False,
                output_path=None,
                records_patched=0,
                conflicts_resolved=0,
                xedit_exit_code=-1,
                warnings=(),
                error=f"Unexpected error: {exc}",
            )

        duration = time.monotonic() - t0

        # --- Publish completed event ---
        assert result is not None
        completed_payload = XEditPatchCompletedPayload(
            target_plugin=str(target_plugin),
            total_conflicts=report.total_conflicts,
            success=result.success,
            records_patched=result.records_patched,
            conflicts_resolved=result.conflicts_resolved,
            duration_seconds=round(duration, 3),
            rolled_back=rolled_back,
        )
        await self._event_bus.publish(
            Event(
                topic="xedit.patch.completed",
                payload=completed_payload.to_log_dict(),
                source=self.AGENT_ID,
            )
        )

        if result.success:
            logger.info(
                "Parcheo xEdit exitoso: %s (%d records, %d conflictos, %.1fs)",
                target_plugin.name,
                result.records_patched,
                result.conflicts_resolved,
                duration,
            )

        return self._result_to_dict(result)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _result_to_dict(result: PatchResult) -> dict[str, Any]:
        """Convierte PatchResult a dict serializable."""
        raw = dataclasses.asdict(result)
        if raw.get("output_path") is not None:
            raw["output_path"] = str(raw["output_path"])
        return raw

    @staticmethod
    def _error_dict(message: str) -> dict[str, Any]:
        """Construye un dict de error para retornos tempranos."""
        return {
            "success": False,
            "output_path": None,
            "records_patched": 0,
            "conflicts_resolved": 0,
            "xedit_exit_code": -1,
            "warnings": [],
            "error": message,
        }
```

- [ ] **Step 2.2: Verificar que el archivo importa sin errores**

```bash
cd Sky-Claw-fresh && python -c "from sky_claw.tools.xedit_service import XEditPipelineService; print('OK')"
```
Esperado: `OK`

- [ ] **Step 2.3: Commit**

```bash
git add sky_claw/tools/xedit_service.py
git commit -m "feat(sprint-2): create XEditPipelineService with SnapshotTransactionLock (T11 safety)"
```

---

### Task 3: Limpieza de SupervisorAgent

**Files:**
- Modify: `sky_claw/orchestrator/supervisor.py`

**NOTA CRÍTICA:** Hacer los cambios en este orden para que ruff pueda verificar cada paso.

- [ ] **Step 3.1: Eliminar los 5 métodos xEdit de supervisor.py**

Eliminar completamente las siguientes secciones (con sus docstrings y comentarios de sección):
- Líneas ≈159-180: `_init_patch_orchestrator()` — PERO conservar las 3 líneas de lazy-init para otros runners
- Líneas ≈182-237: `_ensure_patch_orchestrator()`
- Líneas ≈1115-1261: Sección completa `# FASE 2: Parcheo Transaccional` + `resolve_conflict_with_patch()`
- Líneas ≈1263-1293: `_rollback_on_failure()`
- Líneas ≈1295-1336: `_log_patch_success()`

Para `_init_patch_orchestrator`, el contenido útil que queda (los lazy-init de otros runners) se mueve directamente al `__init__` de `SupervisorAgent`. Reemplazar la llamada `self._init_patch_orchestrator()` en `__init__` (línea 122) con estas 3 líneas inline:

```python
        # Lazy init para runners de otras fases
        self._dyndolod_runner: DynDOLODRunner | None = None
        self._asset_detector: AssetConflictDetector | None = None
        self._wrye_bash_runner: WryeBashRunner | None = None
```

- [ ] **Step 3.2: Instanciar XEditPipelineService en __init__ de SupervisorAgent**

Después de `self._synthesis_service = SynthesisPipelineService(...)` (línea ≈111-119), agregar:

```python
        # Sprint-2 Fase 4: XEditPipelineService — extraído del Supervisor
        self._xedit_service = XEditPipelineService(
            lock_manager=self._lock_manager,
            snapshot_manager=self.snapshot_manager,
            journal=self.journal,
            path_resolver=self._path_resolver,
            event_bus=self._event_bus,
        )
```

Y agregar el import al bloque de imports de herramientas:

```python
from sky_claw.tools.xedit_service import XEditPipelineService
```

- [ ] **Step 3.3: Agregar caso en dispatch_tool**

Después del case `"execute_synthesis_pipeline"` y antes de `"generate_lods"`, agregar:

```python
            # Sprint-2 Fase 4: xEdit Patch (delegado a XEditPipelineService)
            case "resolve_conflict_with_patch":
                target_plugin = pathlib.Path(payload_dict["target_plugin"])
                from sky_claw.xedit.conflict_analyzer import ConflictReport
                report = ConflictReport(**payload_dict["report"])
                return await self._xedit_service.execute_patch(report, target_plugin)
```

**NOTA:** El import de `ConflictReport` aquí es local (dentro del case) porque el import global
de `ConflictAnalyzer` ya trae `ConflictReport`. Puede usarse el import global existente directamente.
Verificar con ruff.

- [ ] **Step 3.4: Purgar imports F401 de supervisor.py**

Eliminar estas líneas del bloque de imports:

```python
# ELIMINAR — estas 7 líneas:
from sky_claw.xedit.patch_orchestrator import (
    PatchingError,
    PatchOrchestrator,
    PatchPlan,
    PatchResult,
    PatchStrategyType,
)
from sky_claw.xedit.runner import ScriptExecutionResult, XEditRunner
```

Verificar que estas permanecen (son usadas en otros lugares del supervisor):
- `from sky_claw.xedit.conflict_analyzer import ConflictAnalyzer, ConflictReport` ✅ (línea 611)
- `from sky_claw.db.snapshot_manager import FileSnapshotManager, SnapshotInfo` ✅ (DynDOLOD, líneas 864-865)

- [ ] **Step 3.5: Verificar con ruff**

```bash
cd Sky-Claw-fresh && ruff check sky_claw/orchestrator/supervisor.py
```
Esperado: sin output (sin errores F401)

- [ ] **Step 3.6: Verificar que el módulo importa**

```bash
python -c "from sky_claw.orchestrator.supervisor import SupervisorAgent; print('OK')"
```
Esperado: `OK`

- [ ] **Step 3.7: Commit**

```bash
git add sky_claw/orchestrator/supervisor.py sky_claw/tools/xedit_service.py
git commit -m "refactor(sprint-2): extract xedit pipeline from SupervisorAgent, purge F401 imports"
```

---

### Task 4: Test Suite

**Files:**
- Create: `tests/test_xedit_service.py`
- Delete: `tests/test_xedit_payloads_temp.py` (se absorbe aquí)

- [ ] **Step 4.1: Crear el archivo de tests**

Crear `tests/test_xedit_service.py` siguiendo el patrón de `tests/test_synthesis_service.py`:

```python
"""Tests for XEditPipelineService.

Sprint 2 (Fase 4): Validates the extracted xEdit service using
SnapshotTransactionLock for transactional protection, event bus
integration, and proper journal lifecycle (Regla T11).
"""

from __future__ import annotations

import pathlib
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sky_claw.core.event_bus import CoreEventBus
from sky_claw.core.event_payloads import (
    XEditPatchCompletedPayload,
    XEditPatchStartedPayload,
)
from sky_claw.db.locks import DistributedLockManager
from sky_claw.db.snapshot_manager import FileSnapshotManager
from sky_claw.tools.xedit_service import XEditPipelineService
from sky_claw.xedit.conflict_analyzer import ConflictReport
from sky_claw.xedit.patch_orchestrator import PatchResult

if TYPE_CHECKING:
    pass


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def tmp_lock_db(tmp_path: pathlib.Path) -> pathlib.Path:
    return tmp_path / "test_locks.db"


@pytest.fixture
async def lock_manager(tmp_lock_db: pathlib.Path) -> DistributedLockManager:
    mgr = DistributedLockManager(
        tmp_lock_db,
        default_ttl=5.0,
        max_retries=2,
        backoff_base=0.05,
        backoff_max=0.2,
    )
    await mgr.initialize()
    yield mgr  # type: ignore[misc]
    await mgr.close()


@pytest.fixture
def snapshot_dir(tmp_path: pathlib.Path) -> pathlib.Path:
    d = tmp_path / "snapshots"
    d.mkdir()
    return d


@pytest.fixture
async def snapshot_manager(snapshot_dir: pathlib.Path) -> FileSnapshotManager:
    mgr = FileSnapshotManager(snapshot_dir=snapshot_dir)
    await mgr.initialize()
    return mgr


@pytest.fixture
def mock_journal() -> AsyncMock:
    journal = AsyncMock()
    journal.begin_transaction = AsyncMock(return_value=1)
    journal.commit_transaction = AsyncMock()
    journal.mark_transaction_rolled_back = AsyncMock()
    return journal


@pytest.fixture
def mock_path_resolver(tmp_path: pathlib.Path) -> MagicMock:
    resolver = MagicMock()
    xedit_exe = tmp_path / "xEdit.exe"
    xedit_exe.touch()
    game_path = tmp_path / "Skyrim"
    game_path.mkdir()
    resolver.validate_env_path = MagicMock(side_effect=lambda val, key: (
        xedit_exe if key == "XEDIT_PATH" else game_path
    ))
    return resolver


@pytest.fixture
def mock_event_bus() -> AsyncMock:
    bus = AsyncMock(spec=CoreEventBus)
    bus.publish = AsyncMock()
    return bus


@pytest.fixture
def mock_conflict_report() -> ConflictReport:
    report = MagicMock(spec=ConflictReport)
    report.total_conflicts = 2
    report.critical_conflicts = 0
    report.plugin_pairs = []
    return report


@pytest.fixture
def target_plugin(tmp_path: pathlib.Path) -> pathlib.Path:
    plugin = tmp_path / "TestMod.esp"
    plugin.write_bytes(b"TES4")  # minimal plugin content
    return plugin


def make_service(lock_manager, snapshot_manager, mock_journal, mock_path_resolver, mock_event_bus):
    return XEditPipelineService(
        lock_manager=lock_manager,
        snapshot_manager=snapshot_manager,
        journal=mock_journal,
        path_resolver=mock_path_resolver,
        event_bus=mock_event_bus,
    )


# =============================================================================
# Tests: Event Payloads
# =============================================================================


def test_started_payload_is_immutable():
    p = XEditPatchStartedPayload(target_plugin="ModA.esp", total_conflicts=3)
    with pytest.raises(Exception):
        object.__setattr__(p, "target_plugin", "changed")


def test_completed_payload_rolled_back_field():
    p = XEditPatchCompletedPayload(
        target_plugin="ModA.esp",
        total_conflicts=3,
        success=False,
        records_patched=0,
        conflicts_resolved=0,
        duration_seconds=0.5,
        rolled_back=True,
    )
    assert p.rolled_back is True
    assert p.success is False


def test_payloads_to_log_dict_contains_expected_keys():
    p = XEditPatchStartedPayload(target_plugin="ModA.esp", total_conflicts=5)
    d = p.to_log_dict()
    assert "target_plugin" in d
    assert "total_conflicts" in d
    assert "started_at" in d


# =============================================================================
# Tests: XEditPipelineService — init failures
# =============================================================================


@pytest.mark.asyncio
async def test_execute_patch_returns_error_when_xedit_path_missing(
    lock_manager,
    snapshot_manager,
    mock_journal,
    mock_event_bus,
    mock_conflict_report,
    target_plugin,
):
    """Si XEDIT_PATH no está configurado, retorna error dict sin crash."""
    resolver = MagicMock()
    resolver.validate_env_path = MagicMock(return_value=None)

    service = XEditPipelineService(
        lock_manager=lock_manager,
        snapshot_manager=snapshot_manager,
        journal=mock_journal,
        path_resolver=resolver,
        event_bus=mock_event_bus,
    )

    result = await service.execute_patch(mock_conflict_report, target_plugin)

    assert result["success"] is False
    assert "XEDIT_PATH" in result["error"]
    mock_journal.begin_transaction.assert_not_called()


# =============================================================================
# Tests: XEditPipelineService — happy path
# =============================================================================


@pytest.mark.asyncio
async def test_execute_patch_success_publishes_events(
    lock_manager,
    snapshot_manager,
    mock_journal,
    mock_path_resolver,
    mock_event_bus,
    mock_conflict_report,
    target_plugin,
):
    """Un patch exitoso publica started + completed events y hace commit al journal."""
    mock_patch_result = PatchResult(
        success=True,
        output_path=target_plugin,
        records_patched=5,
        conflicts_resolved=2,
        xedit_exit_code=0,
        warnings=(),
        error=None,
    )
    mock_orchestrator = AsyncMock()
    mock_orchestrator.resolve = AsyncMock(return_value=mock_patch_result)
    mock_orchestrator._strategies = []

    service = make_service(
        lock_manager, snapshot_manager, mock_journal, mock_path_resolver, mock_event_bus
    )

    with patch.object(service, "_ensure_patch_orchestrator", return_value=mock_orchestrator):
        result = await service.execute_patch(mock_conflict_report, target_plugin)

    assert result["success"] is True
    assert result["records_patched"] == 5
    assert mock_event_bus.publish.call_count == 2

    # Verify event topics
    calls = mock_event_bus.publish.call_args_list
    topics = [call.args[0].topic for call in calls]
    assert "xedit.patch.started" in topics
    assert "xedit.patch.completed" in topics

    mock_journal.commit_transaction.assert_called_once_with(1)
    mock_journal.mark_transaction_rolled_back.assert_not_called()


@pytest.mark.asyncio
async def test_execute_patch_failure_marks_rollback_and_publishes_completed(
    lock_manager,
    snapshot_manager,
    mock_journal,
    mock_path_resolver,
    mock_event_bus,
    mock_conflict_report,
    target_plugin,
):
    """Si el parche falla, marca rollback en journal y publica completed con rolled_back=True."""
    from sky_claw.xedit.patch_orchestrator import PatchingError

    mock_orchestrator = AsyncMock()
    mock_orchestrator.resolve = AsyncMock(side_effect=PatchingError("xEdit crashed"))
    mock_orchestrator._strategies = []

    service = make_service(
        lock_manager, snapshot_manager, mock_journal, mock_path_resolver, mock_event_bus
    )

    with patch.object(service, "_ensure_patch_orchestrator", return_value=mock_orchestrator):
        result = await service.execute_patch(mock_conflict_report, target_plugin)

    assert result["success"] is False
    assert "xEdit crashed" in result["error"]

    mock_journal.mark_transaction_rolled_back.assert_called_once_with(1)
    mock_journal.commit_transaction.assert_not_called()

    # Completed event debe indicar rolled_back=True
    calls = mock_event_bus.publish.call_args_list
    completed_call = next(c for c in calls if c.args[0].topic == "xedit.patch.completed")
    assert completed_call.args[0].payload["rolled_back"] is True


@pytest.mark.asyncio
async def test_execute_patch_unexpected_exception_marks_rollback(
    lock_manager,
    snapshot_manager,
    mock_journal,
    mock_path_resolver,
    mock_event_bus,
    mock_conflict_report,
    target_plugin,
):
    """Una excepción inesperada dentro del lock activa rollback y retorna error dict (T11)."""
    mock_orchestrator = AsyncMock()
    mock_orchestrator.resolve = AsyncMock(side_effect=OSError("Disk full"))
    mock_orchestrator._strategies = []

    service = make_service(
        lock_manager, snapshot_manager, mock_journal, mock_path_resolver, mock_event_bus
    )

    with patch.object(service, "_ensure_patch_orchestrator", return_value=mock_orchestrator):
        result = await service.execute_patch(mock_conflict_report, target_plugin)

    assert result["success"] is False
    assert "Disk full" in result["error"]
    mock_journal.mark_transaction_rolled_back.assert_called_once()


# =============================================================================
# Tests: SupervisorAgent delegation
# =============================================================================


def test_supervisor_has_xedit_service_attribute():
    """SupervisorAgent debe tener _xedit_service tras el refactor."""
    with patch("sky_claw.orchestrator.supervisor.DatabaseAgent"), \
         patch("sky_claw.orchestrator.supervisor.ScraperAgent"), \
         patch("sky_claw.orchestrator.supervisor.ModdingToolsAgent"), \
         patch("sky_claw.orchestrator.supervisor.InterfaceAgent"), \
         patch("sky_claw.orchestrator.supervisor.create_supervisor_state_graph"), \
         patch("sky_claw.orchestrator.supervisor.LangGraphEventStreamer"), \
         patch.object(
             __import__("sky_claw.orchestrator.supervisor", fromlist=["SupervisorAgent"]).SupervisorAgent,
             "_init_rollback_components",
             lambda self: _fake_init_rollback(self),
         ):
        pass  # Este test se verifica manualmente tras el refactor


def _fake_init_rollback(self):
    """Stub para _init_rollback_components en tests de supervisor."""
    from unittest.mock import MagicMock
    self._path_validator = MagicMock()
    self.journal = MagicMock()
    self.snapshot_manager = MagicMock()
    self.rollback_manager = MagicMock()
    self._lock_manager = MagicMock()
```

- [ ] **Step 4.2: Ejecutar todos los tests del servicio**

```bash
cd Sky-Claw-fresh && pytest tests/test_xedit_service.py -v
```
Esperado: todos los tests marcados como async deben pasar.

- [ ] **Step 4.3: Ejecutar la suite completa para detectar regresiones**

```bash
cd Sky-Claw-fresh && pytest --tb=short -q
```
Esperado: todos los tests que pasaban antes siguen pasando. Si hay fallos, son test files que referenciaban métodos xEdit en supervisor — actualizarlos para apuntar a `XEditPipelineService`.

- [ ] **Step 4.4: Eliminar archivo temporal de payloads**

```bash
git rm tests/test_xedit_payloads_temp.py
```

- [ ] **Step 4.5: Commit final**

```bash
git add tests/test_xedit_service.py
git commit -m "test(sprint-2): add XEditPipelineService test suite (T11, events, journal lifecycle)"
```

---

### Task 5: Rama y Git Workflow

- [ ] **Step 5.1: Verificar estado antes de mergear**

```bash
cd Sky-Claw-fresh
git log --oneline -5
ruff check sky_claw/orchestrator/supervisor.py sky_claw/tools/xedit_service.py
pytest --tb=short -q
```
Todos deben pasar.

- [ ] **Step 5.2: Merge a main (workflow local, sin gh)**

```bash
git checkout main
git merge feature/xedit-extraction-final --no-ff -m "refactor(sprint-2): extract xedit pipeline to dedicated service [Fase 4]"
```

- [ ] **Step 5.3: Push**

```bash
git push origin main
```

---

## Resumen de cambios por archivo

| Archivo | Tipo | Detalle |
|---------|------|---------|
| `sky_claw/core/event_payloads.py` | +2 clases | `XEditPatchStartedPayload`, `XEditPatchCompletedPayload` |
| `sky_claw/tools/xedit_service.py` | NUEVO | `XEditPipelineService` con `execute_patch()`, `_ensure_patch_orchestrator()`, helpers |
| `sky_claw/orchestrator/supervisor.py` | -5 métodos, +1 instancia, +1 dispatch case | Eliminados: `resolve_conflict_with_patch`, `_rollback_on_failure`, `_log_patch_success`, `_init_patch_orchestrator`, `_ensure_patch_orchestrator`. Purga F401: `PatchResult`, `ScriptExecutionResult`, `PatchOrchestrator`, `XEditRunner`, `PatchPlan`, `PatchStrategyType`, `PatchingError` |
| `tests/test_xedit_service.py` | NUEVO | Tests de payloads, happy path, failure path, T11 compliance |

## Invariantes críticos

- `ConflictAnalyzer` y `ConflictReport` permanecen importados en supervisor.py (usados en `_run_plugin_limit_guard`)
- `SnapshotInfo` y `FileSnapshotManager` permanecen (usados en DynDOLOD pipeline)
- `asyncio.CancelledError` es `BaseException`, no pasa por `except Exception` — se propaga correctamente
- El `RollbackManager` se construye lazy-inline dentro de `_ensure_patch_orchestrator` del servicio para evitar dependencia circular
