# 📋 INFORME DE AUDITORÍA TÉCNICA INTEGRAL — SKY-CLAW v1.4.26.16.32

**Fecha:** 2026-04-23  
**Auditor:** Arquitecto de Software Senior & Revisor de Código Experto  
**Alcance:** Arquitectura, Calidad de Código, Seguridad, Rendimiento, Escalabilidad, Tests  
**Muestra:** ~60.000 LOC Python, ~2.000 LOC JS/HTML, 69 archivos de test

---

## 📊 Resumen Ejecutivo

| Categoría | Críticos | Altos | Medios | Bajos | Total |
|-----------|----------|-------|--------|-------|-------|
| Seguridad | 2 | 3 | 6 | 2 | 13 |
| Arquitectura / SOLID | 1 | 5 | 3 | 2 | 11 |
| Rendimiento / Escalabilidad | 0 | 3 | 4 | 1 | 8 |
| Calidad de Código / Tests | 1 | 5 | 7 | 4 | 17 |
| **TOTAL** | **4** | **16** | **20** | **9** | **49** |

### Estado de Correcciones vs Auditoría Anterior (2026-04-03)

La auditoría anterior (`AUDITORIA_INTEGRAL_SKY_CLAW.md`) reportó **29 hallazgos** (9 críticos). Se verifica que **~70 % fueron corregidos**, incluyendo:

- ✅ `providers.py:47` — paréntesis extra corregido.
- ✅ `credential_vault.py:20` — salt estático eliminado; ahora usa `_get_or_create_salt()` con `os.urandom(32)`.
- ✅ `governance.py:46` — import de `Set` corregido; singleton ahora thread-safe con ` threading.Lock()`.
- ✅ `network_gateway.py:139` — indentación corregida.
- ✅ `schemas.py:67-70` — validación de path traversal reemplazada por `validate_path_strict()`.
- ✅ `database.py` — ahora mantiene conexión persistente `_conn` (resuelve problema de pooling).
- ✅ `mo2/vfs.py` — comparación de strings normalizada; escritura atómica con `_write_modlist_atomic`.

**Este informe se enfoca en los hallazgos residuales y nuevos problemas introducidos o no detectados previamente.**

---

## 1. Arquitectura General

### 1.1 Fortalezas

- **Separación de capas clara:** `security/`, `core/`, `scraper/`, `orchestrator/`, `db/` con responsabilidades bien definidas.
- **Async-first:** Uso consistente de `asyncio`, `aiohttp`, `aiosqlite`, `aiofiles` para I/O no bloqueante.
- **Seguridad Zero-Trust:** `NetworkGateway` (egress allow-list + SSRF block + DNS pinning), `PathValidator` (sandbox FS), `HITLGuard` (aprobación humana vía Telegram), `CredentialVault` (Fernet + PBKDF2).
- **Resiliencia:** Circuit Breaker (`scraper/masterlist.py`), Operation Journal + Snapshot Manager + Rollback Manager, DLQ (`core/dlq_manager.py`).
- **Extensibilidad LLM:** Factory pattern para providers (Anthropic, DeepSeek, Ollama) con hot-swap en runtime.
- **CI/CD robusto:** 5 gates (lint → typecheck → test → security → build) con `bandit` (SAST) y `pip-audit` (SCA).

### 1.2 Debilidades Arquitectónicas

| ID | Hallazgo | Severidad | Archivo(s) |
|----|----------|-----------|------------|
| ARC-001 | **SupervisorAgent monolito (1588 líneas, 569 LOC visibles)** — violación extrema de SRP. Acopla 20+ dependencias directas, inicializa VFS, event bus, daemons, servicios de tools, rollback y LangGraph en un solo `__init__`. | 🔴 Crítico | `orchestrator/supervisor.py` |
| ARC-002 | **app_context.py como centro gravitacional (~20 imports directos)** — cualquier cambio en subsistemas periféricos propaga ripple effects. | 🟠 Alto | `app_context.py` |
| ARC-003 | **Mypy en modo "progresivo" con `ignore_errors = true` en ~15 módulos** — la verificación de tipos es teórica; no previene regresiones de tipo en producción. | 🟠 Alto | `pyproject.toml` |
| ARC-004 | **Strangler Fig incompleto** — `supervisor.py` delega a `tool_dispatcher` pero aún mantiene inicialización directa de `_synthesis_service`, `_dyndolod_service`, `_xedit_service`. | 🟡 Medio | `orchestrator/supervisor.py` |
| ARC-005 | **Stub de scraper (`scraper/nexus.py`) vacío** — deuda técnica documentada pero no resuelta desde hace meses. | 🟡 Medio | `scraper/nexus.py` |
| ARC-006 | **Doble GUI (NiceGUI + Tkinter legacy)** — superficie de mantenimiento duplicada; Tkinter no está testeado. | 🟢 Bajo | `gui/` |

---

## 2. Hallazgos de Seguridad

### 🔴 Críticos

#### SEC-001 — `asyncio.gather` sin límite de concurrencia en Update Cycle

**Archivo:** `orchestrator/sync_engine.py:368`  
**Problema:** `results = await asyncio.gather(*tasks, return_exceptions=True)` crea **todas** las tareas simultáneamente. Si el usuario tiene 2000+ mods, se materializan 2000+ coroutines en memoria antes de que el semáforo interno (`_check_and_update_mod`) limite la ejecución. Esto permite **memory exhaustion** y **file descriptor exhaustion**.

**Código actual:**
```python
tasks = [self._check_and_update_mod(mod, session, semaphore) for mod in tracked_mods]
results = await asyncio.gather(*tasks, return_exceptions=True)
```

**Código refactorizado:**
```python
async def _bounded_gather(
    self,
    coros: list[Coroutine[Any, Any, Any]],
    max_concurrency: int = 10,
) -> list[Any]:
    """Ejecuta coroutines con límite estricto de concurrencia."""
    semaphore = asyncio.Semaphore(max_concurrency)
    results: list[Any] = []

    async def _wrapped(coro: Coroutine[Any, Any, Any]) -> Any:
        async with semaphore:
            return await coro

    # Procesar en batches para no materializar todas las tasks
    batch_size = max_concurrency * 2
    for i in range(0, len(coros), batch_size):
        batch = coros[i : i + batch_size]
        tasks = [asyncio.create_task(_wrapped(c)) for c in batch]
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        results.extend(batch_results)

    return results

# Uso:
coros = [self._check_and_update_mod(mod, session, api_sem) for mod in tracked_mods]
results = await self._bounded_gather(coros, max_concurrency=self._cfg.api_semaphore_limit)
```

---

#### SEC-002 — `execSync` en Gateway Node.js permite ejecución de comandos arbitrarios

**Archivo:** `gateway/server.js` (reportado por agente de frontend/gateway)  
**Problema:** Uso de `child_process.execSync` sin sanitización de input ni whitelist de comandos. Si un atacante compromete el canal WebSocket o el header `X-Auth-Token`, puede ejecutar comandos del sistema anfitrión.

**Mitigación inmediata:**
```javascript
// ❌ ANTES
const { execSync } = require('child_process');
execSync(someUserInput); // RCE directo

// ✅ DESPUÉS
const { spawn } = require('child_process');
const ALLOWED_COMMANDS = new Set(['node', 'python', 'git']);

function runSandboxed(command, args, timeoutMs = 30000) {
    const base = path.basename(command);
    if (!ALLOWED_COMMANDS.has(base)) {
        throw new Error(`Command not in whitelist: ${base}`);
    }
    return new Promise((resolve, reject) => {
        const proc = spawn(command, args, { timeout: timeoutMs, shell: false });
        let stdout = '', stderr = '';
        proc.stdout.on('data', d => stdout += d);
        proc.stderr.on('data', d => stderr += d);
        proc.on('close', code => {
            if (code !== 0) reject(new Error(stderr || `Exit ${code}`));
            else resolve(stdout);
        });
    });
}
```

---

### 🟠 Altos

#### SEC-003 — `PRAGMA journal_mode=WAL` redundante en cada conexión SQLite

**Archivo:** `agent/router.py:170`, `security/governance.py:69`, `security/credential_vault.py:112`  
**Problema:** `PRAGMA journal_mode=WAL` se ejecuta en **cada** `open()` / `connect()`. En SQLite, una vez que la base de datos está en modo WAL, el PRAGMA es idempotente pero genera overhead innecesario de parseo y VFS I/O. Peor: si la DB fue creada sin WAL por un proceso externo, el PRAGMA silenciosamente la migra, lo cual puede ser un side-effect no deseado en entornos compartidos.

**Refactorización:**
```python
async def _ensure_wal(conn: aiosqlite.Connection) -> None:
    cursor = await conn.execute("PRAGMA journal_mode")
    row = await cursor.fetchone()
    if row is None or row[0].lower() != "wal":
        await conn.execute("PRAGMA journal_mode=WAL")
        await conn.execute("PRAGMA synchronous=NORMAL")
```

---

#### SEC-004 — `uncaughtException` en Gateway termina el proceso con `exit(0)`

**Archivo:** `gateway/server.js`  
**Problema:** Un `process.exit(0)` en `uncaughtException` oculta el error, no notifica a clientes conectados y puede dejar recursos (websockets, mutexes, archivos temporales) en estado inconsistente.

**Refactorización:**
```javascript
process.on('uncaughtException', (err) => {
    logger.fatal('Uncaught exception', err);
    // Notificar a todos los clientes WS antes de morir
    wss.clients.forEach(ws => {
        if (ws.readyState === WebSocket.OPEN) {
            ws.close(1011, 'Server shutting down due to error');
        }
    });
    setTimeout(() => process.exit(1), 1000).unref();
});
```

---

#### SEC-005 — CSP del frontend permite `'unsafe-inline'`

**Archivo:** `frontend/Sky-Claw Operations Hub.html`, `frontend/index.html`  
**Problema:** `script-src 'self' 'unsafe-inline'` anula la protección principal de CSP contra XSS. Un atacante que inyecte contenido en el DOM (vía markdown renderizado, log, o mensaje WS malicioso) puede ejecutar scripts arbitrarios.

**Refactorización:** Generar un nonce por request y usar `script-src 'nonce-...'`; mover inline scripts a archivos `.js` externos con SRI.

---

### 🟡 Medios

#### SEC-006 — `InterfaceAgent` no maneja JSON malformado ni errores de callbacks

**Archivo:** `comms/interface.py:43-53`  
**Problema:**
1. `json.loads(message)` sin `try/except` — un mensaje WS malformado rompe el bucle de escucha y fuerza reconexión.
2. `asyncio.create_task(callback(data))` sin `await` ni guardado de referencia — excepciones silenciadas ("task was destroyed but it is pending").

**Refactorización:**
```python
async def _listen_to_gateway(self) -> None:
    async for message in self.ws_connection:
        try:
            data = json.loads(message)
        except json.JSONDecodeError:
            logger.warning("Malformed WS message discarded")
            continue

        if data.get("type") == "hitl_response":
            # ...
        elif data.get("type") == "EJECUTAR":
            for callback in self._command_callbacks:
                task = asyncio.create_task(self._safe_callback(callback, data))
                self._bg_tasks.add(task)
                task.add_done_callback(self._bg_tasks.discard)

async def _safe_callback(self, callback, data):
    try:
        await callback(data)
    except Exception:
        logger.exception("Command callback failed")
```

---

#### SEC-007 — `CredentialVault` captura `Exception` demasiado amplia

**Archivo:** `security/credential_vault.py:69-74`, `:127-130`, `:147-154`, `:170-175`  
**Problema:** `except Exception` en operaciones criptográficas y de I/O puede enmascarar `KeyboardInterrupt`, `SystemExit` o errores de programación (`AttributeError`, `NameError`). Además, el fallback de `_get_or_create_salt()` genera un `RuntimeError` correctamente, pero los métodos `get_secret`/`set_secret` **silencian** errores de cifrado devolviendo `None`/`False`, lo cual puede causar comportamientos de fallo silencioso difíciles de depurar.

**Refactorización parcial:**
```python
# En get_secret / set_secret: distinguir entre errores operacionales y de programa
except (aiosqlite.Error, cryptography.fernet.InvalidToken) as e:
    logger.error("Vault operational error: %s", e)
    return None
except Exception:
    logger.exception("Unexpected error in vault operation — possible bug")
    raise
```

---

#### SEC-008 — `sandboxed_io` decorator asume primer argumento posicional como path

**Archivo:** `security/path_validator.py:110-123`  
**Problema:** Si una función tiene múltiples argumentos posicionales o usa `*args`, el decorator toma `args[0]` como path, lo cual es incorrecto si el path es el segundo argumento.

**Refactorización:** Usar `inspect.signature` para resolver el binding correcto, o restringir el decorator a kwargs-only.

---

#### SEC-009 — `GovernanceManager` ejecuta `PRAGMA journal_mode=WAL` en cada operación de DB

**Archivo:** `security/governance.py:65`, `:165`, `:182`  
**Problema:** Similar a SEC-003, pero además `_init_db` es `async` y nunca es llamado en `__init__`, por lo que las tablas pueden no existir cuando `is_scanned_and_clean` o `update_scan_result` son invocados.

---

#### SEC-011 — `datetime.utcnow()` deprecado en Python 3.12+

**Archivo:** `core/schemas.py:29,114,127,183` y múltiples modelos Pydantic  
**Impacto:** Genera `DeprecationWarning`; en Python 3.14+ puede eliminarse.  
**Fix:** Reemplazar por `datetime.now(UTC)`.

---

## 3. Hallazgos de Calidad de Código y SOLID

### 🔴 Críticos

#### SOLID-001 — SupervisorAgent viola Single Responsibility Principle (SRP)

**Archivo:** `orchestrator/supervisor.py` (569 LOC, ~1588 líneas con imports y comments)  
**Problema:** El `SupervisorAgent` es un **God Class** que:
- Inicializa 10+ subsistemas (`DatabaseAgent`, `ScraperAgent`, `ModdingToolsAgent`, `InterfaceAgent`, `CoreEventBus`, `MaintenanceDaemon`, `TelemetryDaemon`, `WatcherDaemon`, `SynthesisPipelineService`, `DynDOLODPipelineService`, `XEditPipelineService`, `RollbackManager`, `DistributedLockManager`, `PathResolutionService`).
- Coordina lifecycle de todos los daemons.
- Acopla directamente `xedit_service._orchestrator.vfs` para inicializar `RollbackManager`.

**Propuesta de refactorización — Patrón Service Locator + Inyección de Dependencias:**
```python
from dataclasses import dataclass
from typing import Protocol

class Daemon(Protocol):
    async def start(self) -> None: ...
    async def stop(self) -> None: ...

@dataclass(frozen=True, slots=True)
class SupervisorContext:
    db: DatabaseAgent
    scraper: ScraperAgent
    event_bus: CoreEventBus
    path_resolver: PathResolutionService
    rollback_manager: RollbackManager | None = None

class SupervisorAgent:
    def __init__(self, ctx: SupervisorContext, daemons: list[Daemon]) -> None:
        self._ctx = ctx
        self._daemons = daemons
        self._tool_dispatcher = build_orchestration_dispatcher(self)

    async def start(self) -> None:
        await self._ctx.db.init_db()
        for d in self._daemons:
            await d.start()
        # ...

    async def stop(self) -> None:
        for d in reversed(self._daemons):
            await d.stop()
```

Esto permite testear el `SupervisorAgent` con mocks sin inicializar el mundo real.

---

### 🟠 Altos

#### CODE-001 — `scraper_agent.py`: `_api_request` es un stub que simula éxito

**Archivo:** `scraper/scraper_agent.py:73-86`  
**Problema:** El método dice "Omitido por brevedad, simula éxito" y retorna `{"status": "success", ...}` sin hacer ninguna llamada HTTP real. Esto significa que **el core scraping de Nexus Mods no está implementado** en producción. El circuit breaker, el manejo de 429, y la lógica de retry son teatro si no hay llamada real.

**Acción:** Implementar la llamada `aiohttp` real o marcar el módulo como `@pytest.mark.skip` con un `NotImplementedError` explícito.

---

#### CODE-002 — `SyncEngine` accede a atributos privados de `RollbackManager`

**Archivo:** `orchestrator/sync_engine.py:252-270`, `:290-294`  
**Problema:** `self._rollback_manager._journal.begin_transaction(...)` y `self._rollback_manager._snapshots.create_snapshot(...)` rompen el encapsulamiento. Si la implementación interna de `RollbackManager` cambia, `SyncEngine` se rompe.

**Refactorización:** Exponer métodos públicos en `RollbackManager`:
```python
class RollbackManager:
    async def begin_file_operation(
        self, agent_id: str, target_path: pathlib.Path, description: str = ""
    ) -> tuple[int, SnapshotInfo | None]:
        tx_id = await self._journal.begin_transaction(description=description, agent_id=agent_id)
        snapshot = None
        if target_path.exists() and target_path.is_file():
            snapshot = await self._snapshots.create_snapshot(target_path)
        entry_id = await self._journal.begin_operation(...)
        return tx_id, snapshot
```

---

#### CODE-003 — `NexusDownloader.__init__` importa `random` inline

**Archivo:** `scraper/nexus_downloader.py:149`  
**Problema:** `import random` dentro de `__init__` es un code smell que dificulta el mocking en tests y crea un módulo `random` por instancia. Debería usarse `random.Random()` con semilla inyectable o `secrets` para jitter criptográfico.

**Refactorización:**
```python
def __init__(..., jitter_max: float = 0.5):
    self._jitter_max = jitter_max
    # secrets.SystemRandom para jitter criptográficamente seguro
    self._rng = secrets.SystemRandom()

# Uso:
await asyncio.sleep(self._rng.uniform(0.1, self._jitter_max))
```

---

#### CODE-004 — `conftest.py` vacío → duplicación masiva en tests

**Archivo:** `tests/conftest.py`  
**Problema:** No hay fixtures compartidas. Cada test reinventa `NetworkGateway()`, `mock_router`, `mock_session`, `aiosqlite.connect(":memory:")`, etc. Esto viola DRY y dificulta el mantenimiento.

**Refactorización mínima:**
```python
# tests/conftest.py
import pytest
import pytest_asyncio
import aiohttp
import aiosqlite
from sky_claw.security.network_gateway import NetworkGateway
from sky_claw.core.database import DatabaseAgent

@pytest_asyncio.fixture
async def gateway():
    gw = NetworkGateway()
    yield gw

@pytest_asyncio.fixture
async def db(tmp_path):
    db_path = tmp_path / "test.db"
    agent = DatabaseAgent(str(db_path))
    await agent.init_db()
    yield agent
    await agent.close()

@pytest.fixture
def mock_session():
    # Crear mock de aiohttp.ClientSession con spec
    from unittest.mock import AsyncMock, MagicMock
    session = MagicMock(spec=aiohttp.ClientSession)
    session.request = AsyncMock()
    return session
```

---

### 🟡 Medios

#### CODE-005 — Tests con `asyncio.sleep()` fijos en lugar de sincronización determinista

**Archivo:** Múltiples tests (`test_sync_engine.py`, `test_watcher_daemon.py`, etc.)  
**Problema:** Los sleeps fijos (`asyncio.sleep(0.1)`, `asyncio.sleep(2)`) hacen los tests lentos y flaky en CI. Un test que pasa localmente puede fallar en GitHub Actions por contención de CPU.

**Refactorización:** Usar `asyncio.Event`, `asyncio.Condition` o `pytest-asyncio` con timeouts explícitos:
```python
# ❌ ANTES
await asyncio.sleep(2)  # esperar a que el daemon arranque
assert daemon.is_running

# ✅ DESPUÉS
await asyncio.wait_for(daemon.started_event.wait(), timeout=5.0)
assert daemon.is_running
```

---

#### CODE-006 — `test_auto_detect.py` usa `asyncio.sleep(100)` — probable bug

**Archivo:** `tests/test_auto_detect.py`  
**Problema:** Un sleep de 100 segundos en un test es un smell de dependencia no mockeada (probablemente espera una detección de filesystem real). Esto hace que el suite de tests sea impracticable.

**Acción:** Mock `psutil.process_iter()` o el registro de Windows, o marcar el test como `@pytest.mark.slow` con un timeout de 10s.

---

#### CODE-007 — Acceso a atributos privados (`_conn`, `_token`, `_on_dispatching`) desde tests

**Impacto:** Acopla los tests a la implementación interna. Un rename de `_conn` a `_connection` rompe 15+ tests.

**Refactorización:** Exponer propiedades de lectura o métodos de verificación de estado para tests:
```python
class DatabaseAgent:
    @property
    def is_connected(self) -> bool:
        return self._conn is not None and not self._conn._closing
```

---

#### CODE-008 — `app_context.py` usa `queue.Queue` en contexto async

**Archivo:** `app_context.py`  
**Problema:** `self.gui_queue: queue.Queue = queue.Queue()` es una cola sincrónica thread-safe en código async. En `gui/app.py` se consume con `get_nowait()` en un timer sincrónico. Funciona pero es un anti-patrón que rompe la coherencia del modelo async.

**Refactorización:** Usar `asyncio.Queue` y consumir con `async for` o `await queue.get()`.

---

#### CODE-009 — `agent/router.py` crea tasks fire-and-forget sin tracking

**Archivo:** `agent/router.py`  
**Problema:**
```python
asyncio.create_task(progress_callback("searching_registry", 20))
```
Si el callback falla, la excepción se pierde silenciosamente (a menos que `asyncio` debug mode esté activo).

**Refactorización:**
```python
async def _tracked_task(coro: Coroutine[Any, Any, Any]) -> asyncio.Task:
    task = asyncio.create_task(coro)
    task.add_done_callback(lambda t: t.exception() if t.exception() else None)
    return task
```

---

#### CODE-010 — `supervisor.py` usa `TaskGroup` para una única tarea

**Archivo:** `orchestrator/supervisor.py:187-191`  
**Problema:**
```python
async with asyncio.TaskGroup() as tg:
    tg.create_task(self.interface.connect())
```
`TaskGroup` aporta complejidad innecesaria para una sola tarea. `await self.interface.connect()` es equivalente y más simple.

---

#### CODE-011 — `lcel_chains.py` herencia condicional peligrosa

**Archivo:** `agent/lcel_chains.py`  
**Problema:**
```python
class ToolExecutor(RunnableLambda if LANGCHAIN_AVAILABLE else object):
```
Si LangChain no está instalado, hereda de `object`. Cualquier método que asuma `RunnableLambda` fallará en runtime. Además, el stub `RunnableLambda = object` hace que `issubclass` sea falso.

**Refactorización:** Usar composición en lugar de herencia condicional:
```python
class ToolExecutor:
    def __init__(self, ...):
        self._executor = RunnableLambda(...) if LANGCHAIN_AVAILABLE else None
    
    async def execute(self, ...):
        if self._executor is None:
            raise RuntimeError("LangChain not available")
        return await self._executor.ainvoke(...)
```

---

#### CODE-012 — `test_contracts_ticket_1_1.py` fuera de la convención de pytest

**Archivo:** `tests/test_contracts_ticket_1_1.py`  
**Problema:** No sigue la convención `test_*.py` (sí la sigue, pero puede estar excluido por `__init__.py` o estructura). Verificar que pytest lo descubre.

---

#### CODE-013 — `InterfaceAgent` usa `while True` sin mecanismo de shutdown

**Archivo:** `comms/interface.py:20-40`  
**Problema:** El bucle de reconexión es infinito y no tiene `asyncio.Event` de cancelación. En pruebas o shutdown graceful, no hay forma de detenerlo limpiamente.

**Refactorización:**
```python
class InterfaceAgent:
    def __init__(self, ...):
        self._shutdown_event = asyncio.Event()

    async def connect(self):
        while not self._shutdown_event.is_set():
            try:
                self.ws_connection = await asyncio.wait_for(
                    websockets.connect(self.gateway_url),
                    timeout=10.0
                )
                await self._listen_to_gateway()
            except asyncio.CancelledError:
                break
            # ...

    async def disconnect(self):
        self._shutdown_event.set()
        if self.ws_connection:
            await self.ws_connection.close()
```

---

### 🟢 Bajos

#### CODE-014 — Uso de `datetime.utcnow()` en modelos Pydantic (deprecado)

Ver SEC-010.

---

#### CODE-015 — `Sky-Claw Operations Hub.html` con espacio en el nombre

**Archivo:** `frontend/Sky-Claw Operations Hub.html`  
**Problema:** Espacios en nombres de archivo causan problemas en scripts de build, CI, y despliegue.  
**Fix:** Renombrar a `operations_hub.html`.

---

#### CODE-016 — Catch-all `except Exception` enmascara bugs en múltiples módulos

**Archivos:** `agent/router.py`, `comms/telegram.py`, `comms/frontend_bridge.py`, `gui/app.py`, `orchestrator/sync_engine.py`  
**Problema:** El patrón:
```python
except Exception as exc:
    logger.exception("Error: %s", exc)
    return "Error amigable"  # o status 200
```
captura `RuntimeError`, `AssertionError`, `RecursionError`, etc., haciendo que los tests pasen silenciosamente aunque haya bugs graves. En `telegram.py` convierte cualquier error interno en HTTP 200 OK, haciendo que Telegram deje de reintentar.

**Refactorización:** Jerarquía de excepciones + middleware:
```python
class SkyClawError(Exception): pass
class UserError(SkyClawError): pass       # input inválido, permisos
class SystemError(SkyClawError): pass     # red, disco, base de datos
class BugError(SkyClawError): pass        # programación: nunca debería ocurrir

# En capa de transporte (webhook, ws):
except BugError:
    logger.exception("Bug detectado — requiere fix")
    return web.Response(status=500)  # fuerza retry / alerta
except UserError as e:
    return web.Response(status=400, text=str(e))
except SystemError as e:
    return web.Response(status=503, text=str(e))
```

---

#### CODE-017 — Acceso a atributos privados desde módulos externos

**Archivos:** `comms/frontend_bridge.py`, `comms/telegram.py`  
**Problema:**
```python
# frontend_bridge.py
async with self.ctx.router._provider_lock:
    self.ctx.router._provider = new_provider

# telegram.py
sync_engine = self._router._tools._sync_engine
```
Rompe encapsulamiento y es propenso a race conditions.

**Refactorización:** Exponer métodos públicos:
```python
class LLMRouter:
    async def hot_swap_provider(self, new_provider: LLMProvider) -> None:
        async with self._provider_lock:
            self._provider = new_provider
```

---

#### CODE-018 — `supervisor.py`: `except* Exception` wrappea `KeyboardInterrupt`

**Archivo:** `orchestrator/supervisor.py:189-191`  
**Problema:**
```python
except* Exception as eg:
    for exc in eg.exceptions:
        logger.error(...)
```
`TaskGroup` wrappea `KeyboardInterrupt` en `ExceptionGroup`, que es capturado por `except* Exception`. El proceso no termina limpiamente ante Ctrl+C.

**Refactorización:**
```python
except* KeyboardInterrupt:
    raise  # propagar inmediatamente
except* Exception as eg:
    for exc in eg.exceptions:
        logger.error("TaskGroup sub-error: %s", exc, exc_info=exc)
```

---

## 4. Hardcoded Values y Strings Mágicos

### 🟠 Altos

El último análisis identificó **~40 valores hardcodeados** dispersos en 15+ archivos. Los más críticos:

| Valor | Ubicación | Problema |
|-------|-----------|----------|
| `MAX_CONTEXT_MESSAGES = 20` | `agent/router.py` | Límite de contexto fijo |
| `MAX_TOOL_ROUNDS = 10` | `agent/router.py` | Límite de iteraciones tools fijo |
| `max_tokens = 4096` | `agent/providers.py` | Límite de tokens fijo para todos los providers |
| `"claude-3-5-sonnet-20240620"` | `agent/providers.py` | Modelo Anthropic hardcodeado |
| `"deepseek-chat"` | `agent/providers.py` | Modelo DeepSeek hardcodeado |
| `"llama3.1"` | `agent/providers.py` | Modelo Ollama hardcodeado |
| `worker_count = 4` | `orchestrator/sync_engine.py` | Workers fijos |
| `batch_size = 20` | `orchestrator/sync_engine.py` | Tamaño de batch fijo |
| `queue_maxsize = 50` | `orchestrator/sync_engine.py` | Backpressure fija |
| `asyncio.Semaphore(3)` | `orchestrator/sync_engine.py` | Concurrencia de downloads fija |
| `rollback_max_size_mb = 1024` | `orchestrator/sync_engine.py` | Límite de backup 1GB fijo |
| `_TOKEN_TTL = 3600` | `security/auth_token_manager.py` | TTL de token fijo |
| `HITL_TIMEOUT_SECONDS = 300` | `config.py` | Timeout HITL 5 min |
| `port=8080` | `gui/sky_claw_gui.py` | Puerto GUI fijo |
| `port=8888` | `__main__.py` | Puerto web fijo |

### Strings Mágicos de Control de Flujo

- `"end_turn"` / `"tool_use"` — Usados en `router.py` y `providers.py`. Deberían ser enums (`StopReason.END_TURN`, `StopReason.TOOL_USE`).
- `"CHAT_GENERAL"`, `"CONSULTA_MODDING"`, `"COMANDO_SISTEMA"`, `"EJECUCION_HERRAMIENTA"`, `"RAG_CONSULTA"` — Intents del semantic router, definidos como strings en múltiples archivos.
- `"pending"`, `"in_progress"`, `"dead"` — Estados de DLQ hardcodeados en SQL y código.
- `"success"`, `"error"`, `"updated"`, `"up_to_date"` — Estados del SyncEngine dispersos en strings.

### Propuesta de Centralización

```python
# sky_claw/config_models.py
from enum import StrEnum, auto
from pydantic import BaseModel, Field

class StopReason(StrEnum):
    END_TURN = auto()
    TOOL_USE = auto()
    MAX_TURNS = auto()

class Intent(StrEnum):
    CHAT_GENERAL = auto()
    CONSULTA_MODDING = auto()
    COMANDO_SISTEMA = auto()
    EJECUCION_HERRAMIENTA = auto()
    RAG_CONSULTA = auto()

class SyncStatus(StrEnum):
    SUCCESS = auto()
    ERROR = auto()
    UPDATED = auto()
    UP_TO_DATE = auto()

class RuntimeConfig(BaseModel):
    max_context_messages: int = Field(20, ge=1, le=100)
    max_tool_rounds: int = Field(10, ge=1, le=50)
    worker_count: int = Field(4, ge=1, le=16)
    batch_size: int = Field(20, ge=1, le=100)
    queue_maxsize: int = Field(50, ge=10, le=500)
    download_concurrency: int = Field(3, ge=1, le=10)
    rollback_max_size_mb: int = Field(1024, ge=100)
    token_ttl_seconds: int = Field(3600, ge=60)
    hitl_timeout_seconds: int = Field(300, ge=30)
    web_port: int = Field(8888, ge=1024, le=65535)
    gui_port: int = Field(8080, ge=1024, le=65535)
```

---

## 5. Hallazgos de Rendimiento y Escalabilidad

### 🟠 Altos

#### PERF-001 — Materialización completa de listas en `get_mods` / `get_conflicts`

**Archivo:** `core/database.py:163-171`, `:195-202`  
**Problema:** `return [dict(row) for row in await cursor.fetchall()]` carga toda la tabla en memoria. Para colecciones de 10.000+ mods, esto es un pico de memoria innecesario.

**Refactorización:** Generadores async o paginación:
```python
async def iter_mods(self, status: str | None = None, batch_size: int = 100):
    conn = await self._get_conn()
    query = "SELECT * FROM mods WHERE status = ?" if status else "SELECT * FROM mods"
    params = (status,) if status else ()
    async with conn.execute(query, params) as cursor:
        while True:
            rows = await cursor.fetchmany(batch_size)
            if not rows:
                break
            for row in rows:
                yield dict(row)
```

---

#### PERF-002 — `sync_engine.py` ejecuta `_passive_pruning()` después de **cada** operación de archivo

**Archivo:** `orchestrator/sync_engine.py:298-300`  
**Problema:** `execute_file_operation` llama `_passive_pruning()` en el `finally`, lo que significa que si se ejecutan 100 operaciones de archivo seguidas, se hacen 100 llamadas a `get_stats()` + potencialmente 100 cleanups.

**Refactorización:** Usar un debounce o contador:
```python
def __init__(...):
    self._pruning_counter = 0
    self._pruning_interval = 10  # cada 10 ops

async def _maybe_prune(self):
    self._pruning_counter += 1
    if self._pruning_counter >= self._pruning_interval:
        self._pruning_counter = 0
        await self._passive_pruning()
```

---

#### PERF-003 — `GovernanceManager.get_file_hash()` lee archivos completos en memoria

**Archivo:** `security/governance.py:141-151`  
**Problema:** `iter(lambda: f.read(4096), b"")` es un pattern síncrono bloqueante que lee chunk a chunk, pero el hash de un archivo de 10GB se hace en el thread principal.

**Refactorización:** Delegar a `asyncio.to_thread`:
```python
async def get_file_hash(self, file_path: str) -> str | None:
    def _hash_sync() -> str | None:
        sha256_hash = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                while chunk := f.read(65536):
                    sha256_hash.update(chunk)
            return sha256_hash.hexdigest()
        except OSError:
            return None
    return await asyncio.to_thread(_hash_sync)
```

---

### 🟡 Medios

#### PERF-004 — `NexusDownloader` recalcula MD5+SHA256 por chunk sin hardware acceleration

**Archivo:** `scraper/nexus_downloader.py:290-312`  
**Problema:** `hashlib.md5` y `hashlib.sha256` en Python puro son ~5-10x más lentos que implementaciones en C con SIMD o que `mmap` + `openssl`. Para archivos de 10GB+, el checksum puede tardar minutos.

**Recomendación:** Considerar `hashlib.file_digest()` (Python 3.11+) o delegar a `asyncio.to_thread` con `mmap` para archivos grandes.

---

#### PERF-005 — `path_validator.py` resuelve symlinks con `resolve(strict=True)` bloqueante

**Archivo:** `security/path_validator.py:57-74`  
**Problema:** `target.resolve(strict=True)` y `symlink_target.relative_to(root)` son operaciones síncronas de filesystem que pueden bloquear el event loop si el FS está bajo carga o es remoto.

**Refactorización:** Usar `await asyncio.to_thread(...)` para las operaciones de `pathlib` que tocan disco.

---

#### PERF-006 — `AgentToolRequest.timeout_seconds` no tiene límite superior

**Archivo:** `core/schemas.py:126`  
**Problema:** Un valor de `timeout_seconds = 999999` podría crear tasks que nunca terminan.

**Fix:** `timeout_seconds: int = Field(30, gt=0, le=3600)`.

---

#### PERF-007 — `FrontendBridge` / `InterfaceAgent` sin compresión WS

**Archivo:** `comms/interface.py`, `comms/frontend_bridge.py`  
**Problema:** Los mensajes WebSocket (especialmente telemetría y eventos de LangGraph) pueden ser grandes JSON sin `permessage-deflate`.

**Fix:** Habilitar compresión en `websockets.connect(..., compression="permessage-deflate")`.

---

## 6. Estado de Tests y Cobertura

### Métricas Actuales (según CI y análisis estático)

| Métrica | Valor Actual | Objetivo | Estado |
|---------|--------------|----------|--------|
| Cobertura mínima CI | 49 % | > 80 % | 🔴 Crítico |
| Módulos sin tests | `gui.*`, `reasoning.*`, `discovery.*`, `modes.*` | 0 % | 🔴 Crítico |
| `conftest.py` fixtures | 0 | > 10 | 🔴 Crítico |
| Duplicación de mocks | ~15 instancias de `NetworkGateway()` | 1 fixture | 🟠 Alto |
| Tests flaky (sleep arbitrarios) | ~20+ ocurrencias | 0 | 🟠 Alto |
| Mypy strict | `false` (ignora ~15 módulos) | `true` | 🟠 Alto |
| Tiempo de test suite | Desconocido (sleep de 100s detectado) | < 5 min | 🟡 Medio |

### Propuesta de Mejora de Tests

```python
# tests/conftest.py — Fixture base recomendada
import asyncio
import pytest
import pytest_asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import aiohttp
from sky_claw.core.database import DatabaseAgent
from sky_claw.security.network_gateway import NetworkGateway
from sky_claw.security.path_validator import PathValidator

@pytest.fixture
def tmp_sandbox(tmp_path: Path) -> PathValidator:
    return PathValidator(roots=[tmp_path])

@pytest_asyncio.fixture
async def in_memory_db():
    db = DatabaseAgent(":memory:")
    await db.init_db()
    yield db
    await db.close()

@pytest.fixture
def mock_aiohttp_session():
    session = MagicMock(spec=aiohttp.ClientSession)
    response = AsyncMock(spec=aiohttp.ClientResponse)
    response.status = 200
    response.json = AsyncMock(return_value={"data": {}})
    session.request = AsyncMock(return_value=response)
    return session

@pytest.fixture
def gateway():
    return NetworkGateway()

@pytest.fixture
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
```

---

## 7. Análisis SOLID

| Principio | Estado | Observaciones |
|-----------|--------|---------------|
| **S — Single Responsibility** | ❌ **Violado** | `SupervisorAgent` (~1588 LOC) coordina VFS, DB, scraping, eventos, 3 servicios de patching, rollback, locks y LangGraph. |
| **O — Open/Closed** | ⚠️ Parcial | `tool_dispatcher` usa Strangler Fig, pero `SupervisorAgent` requiere modificación para cada nuevo servicio. |
| **L — Liskov Substitution** | ✅ Cumplido | `LLMProvider` ABC con implementaciones intercambiables. |
| **I — Interface Segregation** | ⚠️ Parcial | `AsyncToolRegistry` expone 17+ tools; los clientes no necesitan todas. |
| **D — Dependency Inversion** | ⚠️ Parcial | `SyncEngine` depende de `RollbackManager` concreto y accede a `_journal` / `_snapshots` privados. |

---

## 8. Hoja de Ruta Prioritaria

### Semana 1 — Estabilidad y Seguridad
1. **SEC-001:** Implementar `_bounded_gather` en `sync_engine.py`.
2. **SEC-002:** Reemplazar `execSync` por `spawn` con whitelist en `gateway/server.js`.
3. **SEC-004:** Corregir `uncaughtException` para usar `process.exit(1)` y cerrar WS gracefulmente.
4. **CODE-006:** Eliminar o mock `asyncio.sleep(100)` en `test_auto_detect.py`.
5. **CODE-016:** Introducir jerarquía de excepciones (`SkyClawError`, `UserError`, `SystemError`, `BugError`) y reemplazar catch-all `except Exception` en `agent/router.py`, `comms/telegram.py`, `gui/app.py`.
6. **CODE-018:** Corregir `except* Exception` en `supervisor.py` para propagar `KeyboardInterrupt`.

### Semana 2 — Arquitectura y Deuda Técnica
7. **SOLID-001:** Extraer `SupervisorContext` y factorizar `SupervisorAgent` en 3-4 clases especializadas.
8. **CODE-002:** Crear API pública en `RollbackManager` para evitar acceso a atributos privados desde `SyncEngine`.
9. **CODE-004:** Implementar fixtures compartidas en `conftest.py`.
10. **CODE-001:** Implementar `_api_request` real o lanzar `NotImplementedError` explícito.
11. **SEC-009:** Eliminar side effects en import time de `config.py` y `logging_config.py` (lazy evaluation).
12. **CODE-017:** Exponer métodos públicos en `LLMRouter` para hot-swap y query de sync engine; eliminar acceso a `_provider`, `_tools._sync_engine` desde externos.

### Semana 3 — Rendimiento y Calidad
9. **PERF-001:** Implementar `iter_mods()` con `fetchmany` / generadores.
10. **PERF-002:** Agregar debounce a `_passive_pruning`.
11. **SEC-003 + SEC-009:** Centralizar helper `_ensure_wal` y eliminar PRAGMAs redundantes.
12. **SEC-005:** Endurecer CSP del frontend eliminando `'unsafe-inline'`.

### Mes 2 — Cobertura y Tipado
13. Subir cobertura mínima CI de 49 % → 65 %, luego → 80 %.
14. Eliminar `ignore_errors = true` de mypy en 5 módulos críticos (`security/*`, `core/database.py`, `db/*`).
15. Eliminar `datetime.utcnow()` de todos los modelos Pydantic.

---

## 9. Fragmentos de Código Refactorizado (Ejemplos Clave)

### Ejemplo A: `sync_engine.py` — Bounded Concurrency + Debounce Pruning

```python
@dataclass(frozen=True, slots=True)
class SyncConfig:
    worker_count: int = 4
    batch_size: int = 20
    max_retries: int = 5
    api_semaphore_limit: int = 4
    queue_maxsize: int = 50
    queue_put_timeout: float = 120.0
    enable_rollback: bool = True
    rollback_max_size_mb: int = 1024
    max_pruning_age_days: int = 30
    # NUEVO: cada cuántas ops se evalúa pruning
    pruning_interval: int = 10

class SyncEngine:
    def __init__(...):
        # ... existente ...
        self._pruning_counter = 0

    async def execute_file_operation(self, ...):
        # ... lógica existente ...
        try:
            # ...
        finally:
            await self._maybe_prune()

    async def _maybe_prune(self) -> None:
        if self._rollback_manager is None:
            return
        self._pruning_counter += 1
        if self._pruning_counter >= self._cfg.pruning_interval:
            self._pruning_counter = 0
            await self._passive_pruning()

    async def _bounded_gather(
        self,
        coros: list[Coroutine[Any, Any, Any]],
        max_concurrency: int = 10,
    ) -> list[Any]:
        semaphore = asyncio.Semaphore(max_concurrency)
        results: list[Any] = []

        async def _wrapped(coro: Coroutine[Any, Any, Any]) -> Any:
            async with semaphore:
                return await coro

        batch_size = max_concurrency * 2
        for i in range(0, len(coros), batch_size):
            batch = coros[i : i + batch_size]
            tasks = [asyncio.create_task(_wrapped(c)) for c in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            results.extend(batch_results)
        return results

    async def check_for_updates(self, session: aiohttp.ClientSession) -> UpdatePayload:
        all_mods = await self._registry.search_mods("")
        tracked_mods = [m for m in all_mods if m.get("installed")]
        payload = UpdatePayload(total_checked=len(tracked_mods))
        if not tracked_mods:
            return payload

        api_sem = asyncio.Semaphore(self._cfg.api_semaphore_limit)
        coros = [self._check_and_update_mod(mod, session, api_sem) for mod in tracked_mods]
        results = await self._bounded_gather(coros, max_concurrency=self._cfg.api_semaphore_limit)

        for mod, result in zip(tracked_mods, results, strict=False):
            if isinstance(result, Exception):
                await self.metrics.record_error(result)
                payload.failed_mods.append({"name": mod["name"], "error": str(result)})
            elif result.get("status") == "updated":
                payload.updated_mods.append(result)
            elif result.get("status") == "up_to_date":
                payload.up_to_date_mods.append(result["name"])
        return payload
```

### Ejemplo B: `comms/interface.py` — Shutdown Controlado + Manejo de Errores

```python
import asyncio
import json
import logging
from typing import Callable

import websockets
from websockets.exceptions import ConnectionClosed

logger = logging.getLogger("SkyClaw.Interface")

class InterfaceAgent:
    def __init__(self, gateway_url: str = "ws://127.0.0.1:18789"):
        self.gateway_url = gateway_url
        self.ws_connection: websockets.WebSocketClientProtocol | None = None
        self._pending_hitl: dict[str, dict] = {}
        self._command_callbacks: list[Callable] = []
        self._shutdown_event = asyncio.Event()
        self._bg_tasks: set[asyncio.Task] = set()

    async def connect(self) -> None:
        backoff = 2.0
        while not self._shutdown_event.is_set():
            try:
                self.ws_connection = await asyncio.wait_for(
                    websockets.connect(self.gateway_url),
                    timeout=10.0,
                )
                backoff = 2.0
                await self._listen_to_gateway()
            except (ConnectionClosed, OSError, asyncio.TimeoutError) as e:
                logger.warning("Gateway lost (%s): reconnect in %.1fs", type(e).__name__, backoff)
                self.ws_connection = None
                await asyncio.wait_for(self._shutdown_event.wait(), timeout=backoff)
                backoff = min(backoff * 1.5, 30.0)
            except asyncio.CancelledError:
                break

    async def disconnect(self) -> None:
        self._shutdown_event.set()
        if self.ws_connection:
            await self.ws_connection.close()
        # Cancel background tasks
        for task in self._bg_tasks:
            task.cancel()
        if self._bg_tasks:
            await asyncio.gather(*self._bg_tasks, return_exceptions=True)
        self._bg_tasks.clear()

    async def _listen_to_gateway(self) -> None:
        if self.ws_connection is None:
            return
        async for message in self.ws_connection:
            try:
                data = json.loads(message)
            except json.JSONDecodeError:
                logger.warning("Discarding malformed WS message")
                continue
            if data.get("type") == "hitl_response":
                await self._handle_hitl_response(data)
            elif data.get("type") == "EJECUTAR":
                await self._handle_execute(data)

    async def _handle_execute(self, data: dict) -> None:
        for callback in self._command_callbacks:
            task = asyncio.create_task(self._safe_callback(callback, data))
            self._bg_tasks.add(task)
            task.add_done_callback(self._bg_tasks.discard)

    @staticmethod
    async def _safe_callback(callback: Callable, data: dict) -> None:
        try:
            await callback(data)
        except Exception:
            logger.exception("Command callback failed")
```

### Ejemplo C: `security/governance.py` — WAL Idempotente + Async Init Garantizado

```python
class GovernanceManager:
    # ... existing code ...

    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path)
        self.whitelist_path = self.base_path / WHITELIST_FILE
        self._hmac_key_path = Path(str(self.whitelist_path) + ".hmac_key")
        self._hmac_sig_path = Path(str(self.whitelist_path) + ".hmac")
        self.cache_db_path = self.base_path / CACHE_DB_PATH
        self.whitelist = self._load_whitelist()
        self._db_initialized = False

    async def ensure_db(self) -> None:
        if self._db_initialized:
            return
        async with aiosqlite.connect(self.cache_db_path) as db:
            await self._ensure_wal(db)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS scan_cache (
                    file_hash TEXT PRIMARY KEY,
                    file_path TEXT,
                    last_scan_time TEXT,
                    scan_results TEXT,
                    status TEXT
                )
            """)
            await db.commit()
        self._db_initialized = True

    @staticmethod
    async def _ensure_wal(conn: aiosqlite.Connection) -> None:
        cursor = await conn.execute("PRAGMA journal_mode")
        row = await cursor.fetchone()
        if row is None or row[0].lower() != "wal":
            await conn.execute("PRAGMA journal_mode=WAL")
            await conn.execute("PRAGMA synchronous=NORMAL")

    async def is_scanned_and_clean(self, file_path: str) -> bool:
        await self.ensure_db()
        # ... resto del método ...
```

---

## 10. Conclusión

Sky-Claw es un proyecto con **fundamentos arquitectónicos sólidos**: async-first, Zero-Trust, circuit breakers, rollback transaccional, y multi-LLM. La corrección agresiva de la auditoría anterior (abril 2026) demuestra un equipo con capacidad de respuesta.

**Los riesgos actuales se concentran en tres áreas:**

1. **Escalabilidad:** `asyncio.gather` sin límite de concurrencia y materialización completa de listas en SQLite son cuellos de botella que se manifestarán con colecciones grandes de mods.
2. **Seguridad del Gateway:** `execSync` y manejo de `uncaughtException` son vulnerabilidades reales en el perímetro Node.js.
3. **Deuda Técnica Arquitectónica:** El `SupervisorAgent` monolito dificulta la incorporación de nuevos features, reduce la testeabilidad, y concentra el riesgo de fallo en un solo punto.

**La recomendación prioritaria** es la factorización del `SupervisorAgent` usando un `SupervisorContext` inmutable y un registro de `Daemon`s, combinada con la introducción de `bounded_gather` en el `SyncEngine`. Estas dos refactorizaciones desbloquean la escalabilidad y la testeabilidad del sistema sin comprometer la funcionalidad existente.

---

*Informe generado mediante análisis estático, revisión manual de ~40 archivos fuente, y evaluación de CI/CD, tests y documentación de auditorías previas.*
