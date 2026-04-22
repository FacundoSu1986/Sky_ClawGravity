# Revisión de Código Exhaustiva — `supervisor.py`

**Archivo:** [`sky_claw/orchestrator/supervisor.py`](../sky_claw/orchestrator/supervisor.py)
**Fecha:** 2026-04-21 (v2 — revisión actualizada)
**Revisor:** Ingeniero de Software Senior
**Líneas analizadas:** 670
**Modo:** Code Review Excellence — retroalimentación constructiva y accionable

---

## Tabla de Contenidos

1. [Resumen Ejecutivo](#resumen-ejecutivo)
2. [Fortalezas Identificadas 🎉](#fortalezas-identificadas-)
3. [Problemas Críticos 🔴](#1-problemas-críticos-)
4. [Problemas Altos 🟠](#2-problemas-altos-)
5. [Problemas Medios 🟡](#3-problemas-medios-)
6. [Problemas Bajos 🟢](#4-problemas-bajos-)
7. [Oportunidades de Refactorización 💡](#5-oportunidades-de-refactorización-)
8. [Plan de Acción Priorizado](#6-plan-de-acción-priorizado)
9. [Veredicto Final](#7-veredicto-final)

---

## Resumen Ejecutivo

[`SupervisorAgent`](../sky_claw/orchestrator/supervisor.py:46) actúa como orquestador central del sistema Sky-Claw, coordinando 15+ componentes incluyendo agentes de scraping, herramientas de modding, demonios de telemetría/watcher/mantenimiento, y servicios de pipeline (Synthesis, DynDOLOD, xEdit, Wrye Bash).

El archivo muestra una **evolución progresiva** (FASE 1.5 → FASE 6) con patrones **Strangler Fig** aplicados parcialmente — varios servicios han sido extraídos correctamente a clases dedicadas. Sin embargo, acumula **deuda técnica significativa** por violaciones a los principios SOLID, un bug de inicialización que probablemente crashea en runtime, manejo inconsistente de errores, y fuga de abstracciones.

| Métrica | Valor |
|---|---|
| Problemas Críticos (blocking) | 3 |
| Problemas Altos (should fix) | 5 |
| Problemas Medios (important) | 7 |
| Problemas Bajos (nit) | 5 |
| Deuda Técnica Estimada | ~30 horas |

---

## Fortalezas Identificadas 🎉

Antes de detallar los problemas, es importante reconocer lo que está bien hecho:

- **🎉 Patrón Strangler Fig aplicado progresivamente:** Los servicios [`DynDOLODPipelineService`](../sky_claw/orchestrator/supervisor.py:94), [`SynthesisPipelineService`](../sky_claw/orchestrator/supervisor.py:85), y [`XEditPipelineService`](../sky_claw/orchestrator/supervisor.py:102) han sido extraídos correctamente del supervisor, reduciendo acoplamiento.
- **🎉 Event Bus desacoplado:** [`CoreEventBus`](../sky_claw/core/event_bus.py:42) es instanciable (no singleton), con dispatch fire-and-forget y pattern-matching. Excelente diseño para testing.
- **🎉 Validación con Pydantic:** Uso consistente de modelos Pydantic ([`ScrapingQuery`](../sky_claw/orchestrator/supervisor.py:246), [`LootExecutionParams`](../sky_claw/orchestrator/supervisor.py:252), [`ConflictReport`](../sky_claw/orchestrator/supervisor.py:297)) en el dispatcher.
- **🎉 HITL (Human-in-the-Loop) para operaciones destructivas:** [`execute_loot_sorting`](../sky_claw/orchestrator/supervisor.py:251) solicita aprobación del usuario antes de reordenar el load order.
- **🎉 Lazy initialization para componentes pesados:** [`_ensure_wrye_bash_runner()`](../sky_claw/orchestrator/supervisor.py:394) y [`asset_detector`](../sky_claw/orchestrator/supervisor.py:607) property evitan inicialización innecesaria.
- **🎉 Shutdown ordenado LIFO:** En [`start()`](../sky_claw/orchestrator/supervisor.py:188) los demonios se detienen en orden inverso al de inicio.
- **🎉 PathValidator centralizado:** Validación de rutas a través de [`PathResolutionService`](../sky_claw/orchestrator/supervisor.py:60) + [`PathValidator`](../sky_claw/orchestrator/supervisor.py:145).
- **🎉 Structured logging con `extra={}`:** [`execute_wrye_bash_pipeline()`](../sky_claw/orchestrator/supervisor.py:569) usa campos estructurados para observabilidad.

---

## 1. Problemas Críticos 🔴

> [blocking] — Deben corregirse antes de merge/producción.

### CRIT-01: Orden de Inicialización Frágil — `AttributeError` en Runtime

**Ubicación:** [`__init__()`](../sky_claw/orchestrator/supervisor.py:47) ↔ [`_init_rollback_components()`](../sky_claw/orchestrator/supervisor.py:113)

```python
# Línea 57 — Se invoca _init_rollback_components()
self._init_rollback_components()

# Pero dentro de _init_rollback_components (líneas 135-136):
self.rollback_manager = RollbackManager(
    db=self.db,
    snapshot_manager=self.snapshot_manager,
    orchestrator=self._xedit_service._orchestrator,  # ← AttributeError!
    vfs=self._xedit_service._orchestrator.vfs,        # ← No existe aún
)

# _xedit_service se crea DESPUÉS, en la línea 102:
self._xedit_service = XEditPipelineService(...)
```

**Problema:** `_init_rollback_components()` se ejecuta en la línea 57 pero accede a `self._xedit_service._orchestrator` que no se inicializa hasta la línea 102. Esto produce un `AttributeError: 'SupervisorAgent' object has no attribute '_xedit_service'` al instanciar la clase.

**Impacto:** El programa crashea al instanciar `SupervisorAgent`. Probablemente enmascarado por un try/except en un nivel superior o porque el código no se ejecuta en el path actual.

**Solución:** Reordenar la inicialización respetando el grafo de dependencias:

```python
class SupervisorAgent:
    def __init__(self, profile_name: str = "Default"):
        self.db = DatabaseAgent()
        self.scraper = ScraperAgent(self.db)
        self.tools = ModdingToolsAgent()
        self.interface = InterfaceAgent()
        self.profile_name = profile_name
        self.state_graph = create_supervisor_state_graph(profile_name=self.profile_name)
        self.event_streamer = LangGraphEventStreamer(self.state_graph, self.interface)

        # PASO 1: PathValidator (sin dependencias)
        backup_dir = pathlib.Path(BACKUP_STAGING_DIR)
        backup_dir.mkdir(parents=True, exist_ok=True)
        self._path_validator = PathValidator(roots=[backup_dir])

        # PASO 2: PathResolutionService
        self._path_resolver = PathResolutionService(
            path_validator=self._path_validator,
            profile_name=self.profile_name,
        )
        self.modlist_path = str(self._path_resolver.resolve_modlist_path(self.profile_name))

        # PASO 3: Componentes básicos de rollback (sin dependencias cruzadas)
        self.journal = OperationJournal(db_path=backup_dir / "journal.db")
        self.snapshot_manager = FileSnapshotManager(
            snapshot_dir=backup_dir / "snapshots",
            max_size_mb=get_max_backup_size_mb(),
        )
        self._lock_manager = DistributedLockManager(db_path=backup_dir / "locks.db")

        # PASO 4: Event bus
        self._event_bus = CoreEventBus()

        # PASO 5: Servicios de pipeline (dependen de lock, snapshot, path_resolver)
        self._synthesis_service = SynthesisPipelineService(
            lock_manager=self._lock_manager,
            snapshot_manager=self.snapshot_manager,
            journal=self.journal,
            path_resolver=self._path_resolver,
            event_bus=self._event_bus,
            pipeline_config_path=pathlib.Path(BACKUP_STAGING_DIR) / "synthesis_pipeline.json",
        )
        self._dyndolod_service = DynDOLODPipelineService(
            lock_manager=self._lock_manager,
            snapshot_manager=self.snapshot_manager,
            journal=self.journal,
            path_resolver=self._path_resolver,
            event_bus=self._event_bus,
        )
        self._xedit_service = XEditPipelineService(
            lock_manager=self._lock_manager,
            snapshot_manager=self.snapshot_manager,
            path_resolver=self._path_resolver,
            event_bus=self._event_bus,
        )

        # PASO 6: RollbackManager (depende de _xedit_service)
        self.rollback_manager = RollbackManager(
            db=self.db,
            snapshot_manager=self.snapshot_manager,
            orchestrator=self._xedit_service.orchestrator,  # Público
            vfs=self._xedit_service.vfs,                      # Público
        )

        # PASO 7: Demonios
        self._maintenance_daemon = MaintenanceDaemon(
            snapshot_manager=self.snapshot_manager,
        )
        self._telemetry_daemon = TelemetryDaemon(event_bus=self._event_bus)
        self._watcher_daemon = WatcherDaemon(
            modlist_path=self.modlist_path,
            profile_name=self.profile_name,
            db=self.db,
            event_bus=self._event_bus,
        )

        # PASO 8: Lazy init
        self._asset_detector: AssetConflictDetector | None = None
        self._wrye_bash_runner: WryeBashRunner | None = None
```

---

### CRIT-02: Violación de Encapsulamiento — Acceso a Atributos Privados

**Ubicación:** [`_init_rollback_components()` líneas 135-136](../sky_claw/orchestrator/supervisor.py:135)

```python
orchestrator=self._xedit_service._orchestrator,   # ← Acceso a _orchestrator
vfs=self._xedit_service._orchestrator.vfs,         # ← Acceso doblemente anidado
```

**Problema:** Se accede a `_orchestrator` (atributo privado por convención Python) de `XEditPipelineService`, violando el Principio de Demeter y creando un acoplamiento frágil. Si `XEditPipelineService` cambia su implementación interna, `SupervisorAgent` se rompe silenciosamente.

**Impacto:** Acoplamiento rígido entre componentes; imposible de testear en aislamiento.

**Solución:** Exponer propiedades públicas de solo lectura en `XEditPipelineService`:

```python
# En XEditPipelineService:
class XEditPipelineService:
    @property
    def orchestrator(self) -> "XEditOrchestrator":
        """Acceso público de solo lectura al orquestador interno."""
        return self._orchestrator

    @property
    def vfs(self) -> "VirtualFileSystem":
        """Acceso público de solo lectura al VFS."""
        return self._orchestrator.vfs

# En SupervisorAgent._init_rollback_components():
self.rollback_manager = RollbackManager(
    db=self.db,
    snapshot_manager=self.snapshot_manager,
    orchestrator=self._xedit_service.orchestrator,   # ← Público
    vfs=self._xedit_service.vfs,                      # ← Público
)
```

---

### CRIT-03: F-strings en Logging — Fuga de Información y Degradación de Rendimiento

**Ubicación:** Líneas [346](../sky_claw/orchestrator/supervisor.py:346), [641](../sky_claw/orchestrator/supervisor.py:641), [644](../sky_claw/orchestrator/supervisor.py:644), [661](../sky_claw/orchestrator/supervisor.py:661)

```python
# PROBLEMÁTICO — f-strings en logging
logger.error(f"RCA: LLM alucinó la herramienta '{tool_name}'.")  # Línea 346
logger.info(f"Detectados {len(conflicts)} conflictos de assets")  # Línea 641
logger.error(f"Error durante escaneo de conflictos: {e}", exc_info=True)  # Línea 644
logger.error(f"Error generando reporte JSON de conflictos: {e}", exc_info=True)  # Línea 661
```

**Problema:**
1. **Rendimiento:** El string se interpola **siempre**, incluso si el nivel de log está desactivado (ej. `logger.debug()` en producción).
2. **Seguridad:** Si `tool_name` proviene de entrada del LLM, podría contener inyecciones de log (Log Forging) o datos sensibles. Un `tool_name` como `"\nERROR: Root access granted"` corrompería los logs.

**Solución:**

```python
# Usar % formatting lazy (PEP 8 / best practice de logging)
logger.error("RCA: LLM alucinó la herramienta '%s'.", tool_name)
logger.info("Detectados %d conflictos de assets", len(conflicts))
logger.error("Error durante escaneo de conflictos: %s", e, exc_info=True)
logger.error("Error generando reporte JSON de conflictos: %s", e, exc_info=True)
```

---

## 2. Problemas Altos 🟠

> [important] — Deberían corregirse; discutir si hay desacuerdo.

### HIGH-01: `__init__` Dios — Violación de SRP + DIP

**Ubicación:** [`__init__()`](../sky_claw/orchestrator/supervisor.py:47) — 65 líneas, 15+ dependencias

El constructor crea directamente todas las dependencias, violando:
- **SRP:** La clase tiene demasiadas razones para cambiar
- **DIP:** Depende de concreciones, no de abstracciones

**Impacto:** Imposible testear en aislamiento; cualquier cambio en una dependencia requiere modificar el constructor.

**Solución:** Inyección de Dependencias con contenedor:

```python
from dataclasses import dataclass, field

@dataclass
class SupervisorDependencies:
    """Contenedor de dependencias inyectables para SupervisorAgent."""
    db: DatabaseAgent
    scraper: ScraperAgent
    tools: ModdingToolsAgent
    interface: InterfaceAgent
    event_bus: CoreEventBus
    path_resolver: PathResolutionService
    path_validator: PathValidator
    journal: OperationJournal
    snapshot_manager: FileSnapshotManager
    lock_manager: DistributedLockManager
    rollback_manager: RollbackManager
    synthesis_service: SynthesisPipelineService
    dyndolod_service: DynDOLODPipelineService
    xedit_service: XEditPipelineService
    maintenance_daemon: MaintenanceDaemon
    telemetry_daemon: TelemetryDaemon
    watcher_daemon: WatcherDaemon


class SupervisorAgent:
    def __init__(
        self,
        deps: SupervisorDependencies,
        profile_name: str = "Default",
    ) -> None:
        self._deps = deps
        self.profile_name = profile_name
        self.state_graph = create_supervisor_state_graph(profile_name=profile_name)
        self.event_streamer = LangGraphEventStreamer(self.state_graph, deps.interface)
        self.modlist_path = str(deps.path_resolver.resolve_modlist_path(profile_name))
        self._asset_detector: AssetConflictDetector | None = None
        self._wrye_bash_runner: WryeBashRunner | None = None

    @classmethod
    def create(cls, profile_name: str = "Default") -> "SupervisorAgent":
        """Factory method que construye todas las dependencias."""
        deps = _build_dependencies(profile_name)
        return cls(deps, profile_name)
```

---

### HIGH-02: `dispatch_tool` — Violación de OCP (Open/Closed Principle)

**Ubicación:** [`dispatch_tool()`](../sky_claw/orchestrator/supervisor.py:233)

El `match/case` tiene **9 ramas** y crecerá con cada nueva herramienta. Agregar una herramienta requiere modificar este método, violando OCP.

**Solución:** Patrón Registry con despacho dinámico:

```python
from collections.abc import Awaitable, Callable

ToolHandler = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]


class SupervisorAgent:
    def __init__(self, ...):
        ...
        self._tool_handlers: dict[str, ToolHandler] = {
            "query_mod_metadata": self._handle_query_mod_metadata,
            "execute_loot_sorting": self._handle_execute_loot_sorting,
            "execute_synthesis_pipeline": self._handle_synthesis_pipeline,
            "resolve_conflict_with_patch": self._handle_xedit_patch,
            "generate_lods": self._dyndolod_service.execute,
            "scan_asset_conflicts": self._handle_scan_asset_conflicts,
            "scan_asset_conflicts_json": self._handle_scan_asset_conflicts_json,
            "generate_bashed_patch": self.execute_wrye_bash_pipeline,
            "validate_plugin_limit": self._handle_validate_plugin_limit,
        }

    def register_tool(self, name: str, handler: ToolHandler) -> None:
        """Permite registrar herramientas dinámicamente (extensibilidad)."""
        self._tool_handlers[name] = handler

    async def dispatch_tool(self, tool_name: str, payload_dict: dict[str, Any]) -> dict[str, Any]:
        handler = self._tool_handlers.get(tool_name)
        if handler is None:
            logger.error("RCA: LLM alucinó la herramienta '%s'.", tool_name)
            return {"status": "error", "reason": "ToolNotFound"}
        try:
            return await handler(payload_dict)
        except Exception as exc:
            logger.exception("RCA: Falló la herramienta '%s'.", tool_name)
            return {
                "status": "error",
                "reason": f"{tool_name}Failed",
                "details": str(exc),
            }
```

---

### HIGH-03: I/O Síncrono en Contexto Asíncrono

**Ubicación:** [`_run_plugin_limit_guard()` líneas 464-469](../sky_claw/orchestrator/supervisor.py:464)

```python
# PROBLEMÁTICO — I/O bloqueante en método async
if modlist_path.exists():
    with open(modlist_path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line.startswith("+") and line.lower().endswith((".esp", ".esm")):
                active_plugins.append(line[1:])
```

**Problema:** `open()` y la lectura del archivo son operaciones bloqueantes que detienen el event loop de asyncio. En producción con múltiples operaciones concurrentes, esto causa latencia en cascada.

**Solución preferida (sin dependencia adicional):**

```python
async def _run_plugin_limit_guard(self, profile: str) -> dict[str, Any]:
    """M-04/M-05: Gate preventivo — valida el límite de plugins."""
    logger.info("[M-04] Ejecutando validación de límite de plugins para perfil '%s'...", profile)
    try:
        modlist_path = self._path_resolver.resolve_modlist_path(profile)
        active_plugins = await asyncio.to_thread(
            self._read_active_plugins, modlist_path
        )

        analyzer = ConflictAnalyzer()
        analyzer.validate_load_order_limit(active_plugins)
    except RuntimeError as exc:
        ...
    return {"valid": True, "profile": profile, "plugin_count": len(active_plugins), "limit": PLUGIN_LIMIT}

    @staticmethod
    def _read_active_plugins(modlist_path: pathlib.Path) -> list[str]:
        """Lee plugins activos del modlist.txt (ejecutado en thread pool)."""
        plugins: list[str] = []
        if modlist_path.exists():
            with open(modlist_path, encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if line.startswith("+") and line.lower().endswith((".esp", ".esm")):
                        plugins.append(line[1:])
        return plugins
```

---

### HIGH-04: Manejo de Errores Inconsistente en `dispatch_tool`

**Ubicación:** [`dispatch_tool()`](../sky_claw/orchestrator/supervisor.py:233)

Cada rama del `match` maneja errores de forma diferente:

| Herramienta | Manejo de errores |
|---|---|
| `query_mod_metadata` | Sin try/except — propaga excepción sin catch |
| `execute_loot_sorting` | Sin try/except — delega a HITL |
| `execute_synthesis_pipeline` | try/except Exception → error dict |
| `resolve_conflict_with_patch` | try/except Exception → error dict |
| `generate_lods` | Sin try/except |
| `scan_asset_conflicts` | Sin try/except — propaga |
| `generate_bashed_patch` | Sin try/except — delega |
| `validate_plugin_limit` | try/except interno |

**Problema:** No existe una estrategia uniforme. Algunas herramientas devuelven `{"status": "error"}`, otras lanzan excepciones no manejadas que pueden crashear el event loop.

**Solución:** El wrapper genérico propuesto en HIGH-02 resuelve esto centralizando el manejo de errores en un solo punto.

---

### HIGH-05: `import` Dentro de Método — Violación PEP 8 + Innecesario

**Ubicación:** [`dispatch_tool()` línea 328](../sky_claw/orchestrator/supervisor.py:328)

```python
case "scan_asset_conflicts":
    import dataclasses  # ← Import dentro de método
```

**Problema:** PEP 8 establece que los imports deben ir al inicio del módulo. Además, `dataclasses` es un módulo de la stdlib ligero — el import diferido no aporta beneficio.

**Solución:**

```python
# Mover al inicio del archivo, sección de imports estándar
import dataclasses
```

---

## 3. Problemas Medios 🟡

> [important] — Deberían corregirse en la iteración actual.

### MED-01: Número Mágico `254` Duplicado 4 Veces

**Ubicación:** Líneas [483](../sky_claw/orchestrator/supervisor.py:483), [484](../sky_claw/orchestrator/supervisor.py:484), [498](../sky_claw/orchestrator/supervisor.py:498), [503](../sky_claw/orchestrator/supervisor.py:503)

```python
"limit": 254,  # Aparece 4 veces en _run_plugin_limit_guard
```

**Solución:**

```python
# Constante a nivel de módulo
PLUGIN_LIMIT = 254  # Skyrim SE/AE plugin limit (esp + esm, excluyendo el master)
```

---

### MED-02: `_trigger_proactive_analysis` — Método Stub Sin Implementación Real

**Ubicación:** [`_trigger_proactive_analysis()`](../sky_claw/orchestrator/supervisor.py:205)

```python
# Aquí se inyectaría la llamada real a la herramienta de parsing local.
```

**Problema:** El método está suscrito al event bus pero no ejecuta lógica alguna. Es dead code que consume recursos del bus.

**Solución:** Agregar `TODO` explícito y considerar si la suscripción al bus debería estar condicionada:

```python
async def _trigger_proactive_analysis(self, event: Event | None = None) -> None:
    """Maneja eventos de cambio en modlist publicados por WatcherDaemon.

    TODO: Implementar llamada al parser de load order cuando esté disponible.
    Por ahora solo registra el evento para observabilidad.
    """
    if event is not None:
        logger.info(
            "Cambio en modlist detectado — profile=%s, mtime=%.1f->%.1f",
            event.payload.get("profile_name", "unknown"),
            event.payload.get("previous_mtime", 0.0),
            event.payload.get("current_mtime", 0.0),
        )
    else:
        logger.info("Análisis proactivo disparado manualmente desde la GUI.")
```

---

### MED-03: `scan_asset_conflicts` y `scan_asset_conflicts_json` — Código Duplicado

**Ubicación:** Líneas [627-645](../sky_claw/orchestrator/supervisor.py:627) y [647-662](../sky_claw/orchestrator/supervisor.py:647)

Ambos métodos tienen la misma estructura try/except/log/raise. La única diferencia es el método invocado en `asset_detector`.

**Solución:** Extraer helper genérico:

```python
def _safe_asset_scan(self, operation_name: str, operation: Callable[[], T]) -> T:
    """Ejecuta una operación de escaneo de assets con manejo de errores uniforme."""
    logger.info("Iniciando %s de conflictos de assets...", operation_name)
    try:
        result = operation()
        logger.info("%s de conflictos completado exitosamente", operation_name.capitalize())
        return result
    except (OSError, RuntimeError) as e:
        logger.error("Error durante %s de conflictos: %s", operation_name, e, exc_info=True)
        raise

def scan_asset_conflicts(self) -> list[AssetConflictReport]:
    """FASE 5: Escanea conflictos de assets (READ-ONLY)."""
    return self._safe_asset_scan("escaneo", self.asset_detector.detect_conflicts)

def scan_asset_conflicts_json(self) -> str:
    """FASE 5: Reporte JSON de conflictos (READ-ONLY)."""
    return self._safe_asset_scan("reporte JSON", self.asset_detector.scan_to_json)
```

---

### MED-04: `except* Exception` Demasiado Amplio

**Ubicación:** [`start()` línea 185](../sky_claw/orchestrator/supervisor.py:185)

```python
except* Exception as eg:
    for exc in eg.exceptions:
        logger.error("TaskGroup del Supervisor — sub-error: %s", exc, exc_info=exc)
```

**Problema:** `except* Exception` captura todo, incluyendo `KeyboardInterrupt` y `SystemExit` indirectamente. No distingue entre errores recuperables y fatales.

**Solución:**

```python
try:
    async with asyncio.TaskGroup() as tg:
        tg.create_task(self.interface.connect())
except* asyncio.CancelledError:
    logger.info("TaskGroup cancelado — shutdown limpio.")
except* ConnectionError as eg:
    for exc in eg.exceptions:
        logger.error("Error de conexión en TaskGroup: %s", exc, exc_info=exc)
except* Exception as eg:
    for exc in eg.exceptions:
        logger.critical("Error inesperado en TaskGroup: %s", exc, exc_info=exc)
```

---

### MED-05: `execute_rollback` — Retorno Inconsistente

**Ubicación:** [`execute_rollback()`](../sky_claw/orchestrator/supervisor.py:350)

```python
# Camino feliz retorna:
return {
    "success": result.success,
    "transaction_id": result.transaction_id,
    "entries_restored": result.entries_restored,
    ...
}

# Camino de error retorna:
return {"success": False, "error": str(e)}  # ← Claves diferentes
```

**Problema:** Las claves del diccionario de retorno son diferentes entre caminos, obligando a los consumidores a verificar múltiples esquemas.

**Solución:** Usar dataclass tipada:

```python
from dataclasses import dataclass, field

@dataclass
class RollbackResult:
    """Resultado tipado de una operación de rollback."""
    success: bool
    transaction_id: str = ""
    entries_restored: int = 0
    files_deleted: int = 0
    errors: list[str] = field(default_factory=list)

async def execute_rollback(self, agent_id: str) -> RollbackResult:
    """Ejecuta rollback de la última operación de un agente."""
    logger.info("Iniciando rollback para agente: %s", agent_id)
    try:
        result = await self.rollback_manager.undo_last_operation(agent_id)
        if result.success:
            logger.info(
                "Rollback exitoso: %d archivos restaurados, %d eliminados",
                result.entries_restored,
                result.files_deleted,
            )
        else:
            logger.error("Rollback falló para agente %s", agent_id)
        return RollbackResult(
            success=result.success,
            transaction_id=result.transaction_id,
            entries_restored=result.entries_restored,
            files_deleted=result.files_deleted,
            errors=result.errors,
        )
    except (OSError, RuntimeError) as e:
        logger.exception("Error crítico durante rollback: %s", e)
        return RollbackResult(success=False, errors=[str(e)])
```

---

### MED-06: `_ensure_wrye_bash_runner` — Validación Redundante de Paths

**Ubicación:** [`_ensure_wrye_bash_runner()`](../sky_claw/orchestrator/supervisor.py:394)

```python
game_path = self._path_resolver.validate_env_path(game_path_str, "SKYRIM_PATH")
mo2_path = self._path_resolver.validate_env_path(mo2_path_str, "MO2_PATH")
wrye_bash_path = self._path_resolver.validate_env_path(wrye_bash_path_str, "WRYE_BASH_PATH")

if not game_path or not mo2_path or not wrye_bash_path:  # ← Ya validados?
    raise WryeBashExecutionError(...)
```

**Problema:** Si `validate_env_path` ya valida, la comprobación posterior es redundante. Si puede retornar `None/False` sin lanzar excepción, la validación es inconsistente.

**Solución:** Hacer que `validate_env_path` lance excepción para paths requeridos:

```python
def _ensure_wrye_bash_runner(self) -> WryeBashRunner:
    if self._wrye_bash_runner is not None:
        return self._wrye_bash_runner

    game_path = self._path_resolver.resolve_required_env_path("SKYRIM_PATH")
    mo2_path = self._path_resolver.resolve_required_env_path("MO2_PATH")
    wrye_bash_path = self._path_resolver.resolve_required_env_path("WRYE_BASH_PATH")

    config = WryeBashConfig(
        wrye_bash_path=wrye_bash_path,
        game_path=game_path,
        mo2_path=mo2_path,
    )
    self._wrye_bash_runner = WryeBashRunner(config)
    return self._wrye_bash_runner
```

---

### MED-07: `start()` Mezcla Setup y Runtime — Difícil de Testear

**Ubicación:** [`start()`](../sky_claw/orchestrator/supervisor.py:153)

El método `start()` realiza inicialización de BD, suscripciones a eventos, inicio de demonios, y luego entra en el loop principal. No hay forma de iniciar los componentes sin entrar al loop.

**Solución:** Separar en fases:

```python
async def initialize(self) -> None:
    """Fase de inicialización: BD, journal, locks, suscripciones."""
    await self.db.init_db()
    await self.journal.open()
    await self.snapshot_manager.initialize()
    await self._lock_manager.initialize()
    self.interface.register_command_callback(self.handle_execution_signal)
    await self._event_bus.start()
    self._event_bus.subscribe("system.telemetry.*", self._bridge_telemetry_to_ws)
    self._event_bus.subscribe("system.modlist.changed", self._trigger_proactive_analysis)
    await self._maintenance_daemon.start()
    await self._telemetry_daemon.start()
    await self._watcher_daemon.start()
    logger.info("SupervisorAgent inicializado correctamente.")

async def run(self) -> None:
    """Fase de runtime: loop principal con TaskGroup."""
    try:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(self.interface.connect())
    except* asyncio.CancelledError:
        logger.info("TaskGroup cancelado — shutdown limpio.")
    except* ConnectionError as eg:
        for exc in eg.exceptions:
            logger.error("Error de conexión en TaskGroup: %s", exc, exc_info=exc)
    except* Exception as eg:
        for exc in eg.exceptions:
            logger.critical("Error inesperado en TaskGroup: %s", exc, exc_info=exc)
    finally:
        await self.shutdown()

async def shutdown(self) -> None:
    """Shutdown ordenado en orden LIFO."""
    await self._watcher_daemon.stop()
    await self._telemetry_daemon.stop()
    await self._maintenance_daemon.stop()
    await self._event_bus.stop()
    await self._lock_manager.close()
    await self.journal.close()
    await self.db.close()

async def start(self) -> None:
    """Entry point completo: initialize + run."""
    await self.initialize()
    await self.run()
```

---

## 4. Problemas Bajos 🟢

> [nit] — Nice to have, no bloqueantes.

### LOW-01: Comentarios Mezclados Español/Inglés

**Ubicación:** Todo el archivo

```python
# FASE 1.5: Constante para directorio de staging de backups  ← Español
# ARC-01: Extracted daemons                                  ← Inglés
# Sprint-2: Inicializar Servicios Extraídos                  ← Español
```

**Solución:** Estandarizar a un solo idioma (recomendado: inglés para código, español solo en docstrings de API si el equipo lo prefiere).

---

### LOW-02: Bloque `__main__` Incompleto

**Ubicación:** [Líneas 665-669](../sky_claw/orchestrator/supervisor.py:665)

```python
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    supervisor = SupervisorAgent()
    # asyncio.run(supervisor.start()) # En producción
```

**Problema:** El entry point está comentado y no ejecuta nada útil.

**Solución:**

```python
if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    profile = sys.argv[1] if len(sys.argv) > 1 else "Default"
    supervisor = SupervisorAgent(profile_name=profile)

    try:
        asyncio.run(supervisor.start())
    except KeyboardInterrupt:
        logger.info("Shutdown solicitado por usuario.")
```

---

### LOW-03: Docstrings con Referencias a Fases/Sprints Internos

**Ubicación:** Múltiples métodos

```python
"""FASE 1.5: Inicializa los componentes de resiliencia para rollback."""
"""FASE 6: Genera el Bashed Patch con Wrye Bash."""
```

**Problema:** Las docstrings públicas no deberían referenciar fases de desarrollo interno.

**Solución:** Mover las referencias a comentarios internos:

```python
# FASE 1.5
def _init_rollback_components(self) -> None:
    """Inicializa journal, snapshots y rollback manager para resiliencia."""
```

---

### LOW-04: Falta de `__slots__` en la Clase

**Ubicación:** [`SupervisorAgent`](../sky_claw/orchestrator/supervisor.py:46)

**Problema:** Sin `__slots__`, cada instancia tiene un `__dict__` dinámico que consume más memoria y permite atributos no declarados.

> **Nota:** Si se aplica DI (HIGH-01), `__slots__` pierde prioridad ya que la clase se simplifica drásticamente.

---

### LOW-05: `scan_asset_conflicts` Métodos Síncronos en Clase Asíncrona

**Ubicación:** [`scan_asset_conflicts()`](../sky_claw/orchestrator/supervisor.py:627), [`scan_asset_conflicts_json()`](../sky_claw/orchestrator/supervisor.py:647)

**Problema:** Estos métodos son síncronos pero realizan I/O (escaneo de sistema de archivos vía `asset_detector`). En un contexto async, deberían ser `async def` para no bloquear el event loop.

**Solución:**

```python
async def scan_asset_conflicts(self) -> list[AssetConflictReport]:
    """Escanea conflictos de assets de forma no bloqueante."""
    return await asyncio.to_thread(self.asset_detector.detect_conflicts)
```

---

## 5. Oportunidades de Refactorización 💡

### REF-01: Extraer `ToolDispatcher` como Clase Independiente

```
SupervisorAgent (actual — 670 líneas)
├── dispatch_tool()        → 9 ramas de lógica
├── scan_asset_conflicts()
├── scan_asset_conflicts_json()
├── execute_wrye_bash_pipeline()
├── _run_plugin_limit_guard()
├── execute_rollback()
└── start() / stop()
```

**Propuesta:**

```
SupervisorAgent (refactorizado — ~150 líneas)
├── ToolDispatcher          ← Nueva clase (OCP)
│   ├── handlers: dict
│   └── dispatch()
├── AssetScanner            ← Extraído
├── WryeBashOrchestrator    ← Extraído
├── PluginLimitGuard        ← Extraído
└── RollbackExecutor        ← Extraído
```

### REF-02: Patrón Context Manager para Ciclo de Vida

```python
class SupervisorAgent:
    async def __aenter__(self) -> "SupervisorAgent":
        await self.initialize()
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.shutdown()

# Uso:
async with SupervisorAgent.create(profile="Default") as supervisor:
    await supervisor.dispatch_tool("query_mod_metadata", {...})
```

### REF-03: Reemplazar Diccionarios por Contratos Tipados

Todos los retornos `dict[str, Any]` deberían migrarse a `TypedDict` o `dataclass`:

```python
from typing import TypedDict

class ToolResult(TypedDict, total=False):
    status: str
    reason: str
    details: str
    success: bool

class PluginLimitResult(TypedDict):
    valid: bool
    profile: str
    plugin_count: int
    limit: int
    error: str
```

---

## 6. Plan de Acción Priorizado

| Prioridad | Issue | Esfuerzo | Impacto |
|---|---|---|---|
| 🔴 P0 | CRIT-01: Reordenar `__init__` (bug de inicialización) | 2h | Crasheo en runtime |
| 🔴 P0 | CRIT-02: Exponer propiedades públicas en XEditService | 1h | Acoplamiento frágil |
| 🔴 P1 | CRIT-03: Reemplazar f-strings en logging | 30min | Seguridad + rendimiento |
| 🟠 P1 | HIGH-04 + HIGH-02: Registry + manejo uniforme de errores | 4h | Mantenibilidad |
| 🟠 P2 | HIGH-03: I/O async en `_run_plugin_limit_guard` | 1h | Rendimiento |
| 🟠 P2 | HIGH-05: Mover `import dataclasses` al tope | 5min | PEP 8 |
| 🟡 P3 | MED-07: Separar `start()` en `initialize()` + `run()` + `shutdown()` | 2h | Testabilidad |
| 🟡 P3 | MED-05: `RollbackResult` dataclass | 30min | Consistencia |
| 🟡 P3 | MED-01: Constante `PLUGIN_LIMIT` | 5min | Legibilidad |
| 🟡 P3 | MED-02 a MED-06: Limpieza general | 3h | Deuda técnica |
| 🟢 P4 | LOW-01 a LOW-05: Estilo y convenciones | 2h | Calidad de código |
| 💡 P5 | REF-01: Extraer ToolDispatcher | 4h | Arquitectura |
| 💡 P5 | REF-02: Context Manager | 1h | Ergonomía |
| 💹 P5 | HIGH-01: Inyección de dependencias completa | 8h | Testabilidad total |

**Esfuerzo total estimado (P0-P4):** ~16 horas
**Esfuerzo total con refactorizaciones (P0-P5):** ~29 horas

---

## 7. Veredicto Final

### Puntuación General: **C+ (6.5/10)**

| Categoría | Puntuación | Observación |
|---|---|---|
| Arquitectura | 6/10 | Strangler Fig parcial; aún monolítico |
| Seguridad | 7/10 | PathValidator presente; f-strings en logs |
| Rendimiento | 6/10 | I/O síncrono en contexto async |
| Manejo de Errores | 5/10 | Inconsistente entre herramientas |
| PEP 8 / Estilo | 7/10 | Mayormente limpio; f-strings e import interno |
| SOLID | 4/10 | SRP, OCP y DIP violados significativamente |
| Testabilidad | 5/10 | Constructor rígido dificulta mocking |

### Decisión: 🔄 Request Changes

Se requiere abordar los 3 issues críticos (CRIT-01 a CRIT-03) antes de aprobar. Los issues altos y medios pueden tratarse en PRs subsiguientes, pero el plan de acción debería acordarse con el equipo.

### Lo Que Me Gustó 🎉

- La progresiva aplicación del patrón Strangler Fig muestra madurez en la evolución del código
- La validación con Pydantic en el dispatcher es una excelente práctica defensiva
- El HITL para operaciones destructivas demuestra conciencia de seguridad
- El shutdown LIFO en `start()` es correcto y muestra atención al detalle
- Los demonios extraídos (ARC-01) son un paso en la dirección correcta

### Riesgo Principal ⚠️

El bug de inicialización (CRIT-01) sugiere que el código puede no estar siendo ejecutado en un path de prueba completo. Recomiendo agregar un test de integración que instancie `SupervisorAgent` y verifique que todos los componentes se inicializan correctamente.
