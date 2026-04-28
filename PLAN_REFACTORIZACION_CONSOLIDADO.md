# 🏗️ Plan de Refactorización Progresiva — Sky-Claw

**Autor:** Principal Software Architect & Tech Lead  
**Fecha:** 2026-04-28 | **Versión:** 2.0 Consolidada  
**Fuentes:** `AuditoriaKIMI27.md` + `AUDITORIA_META_REVISION_KIMI27.md`  
**Estado OODA:** Fase 0 y Fase 1 (KIMI) verificadas ✅ — Sin conflictos ni regresiones

---

## 📋 Resumen Ejecutivo

Se consolidan los hallazgos de ambas auditorías eliminando los 14 duplicados, corrigiendo las inconsistencias de severidad (GTG-03 → Alto), y reconociendo las mitigaciones ya existentes (GTG-01, GWS-04, SEC-05). El plan resultante contiene **~66 hallazgos únicos** organizados en 6 fases de ejecución progresiva.

### Principios de Diseño

1. **Context Quarantine:** Cada tarea atómica modifica ≤3 archivos y es verificable en un hilo independiente.
2. **No-regresión:** Cada tarea incluye criterios de aceptación explícitos.
3. **Orden topológico:** Las dependencias entre tareas están declaradas explícitamente.
4. **Strangler Fig:** Las refactorizaciones arquitectónicas grandes (SUP-01, DB-001) se dividen en incrementos seguros.

---

## 📊 Estado de Progreso

| Fase | Descripción | Estado | Tareas |
|------|-------------|--------|--------|
| 0 | Cimentación de Seguridad | ✅ Completada (KIMI) | 5/5 |
| 1 | Bugs Críticos Funcionales | ✅ Completada (KIMI) | 4/4 |
| 2 | I/O Síncrono Bloqueante | ⬜ Pendiente | 3 |
| 3 | Seguridad y Dominio Skyrim | ⬜ Pendiente | 5 |
| 4 | Persistencia y Resiliencia | ⬜ Pendiente | 4 |
| 5 | Arquitectura (Strangler Fig) | ⬜ Pendiente | 6 |

---

## ✅ Fase 0: Cimentación de Seguridad (COMPLETADA)

| Tarea | ID | Archivo | Criterio de Verificación |
|-------|-----|---------|--------------------------|
| Corregir taint tracking roto | SEC-03 | `security/purple_scanner.py` | `_is_tainted_source()` detecta `ast.Attribute` con `.read` |
| Distinguir "no existe" vs "tampering" | SEC-02 | `security/credential_vault.py` | `get_secret()` retorna `None` para no-existe, `None`+log para DB error, `raise SecurityViolationError` para tampering |
| Fix timingSafeEqual UTF-16 vs bytes | GWS-04 | `gateway/server.js` | Compara longitudes de `Buffer` UTF-8, no `string.length` |
| Cerrar agentSocket previo | GWS-02 | `gateway/server.js` | `agentSocket.close(4000)` antes de reasignar |
| Await ctx.reply() | GTG-02 | `gateway/telegram_gateway.js` | `await ctx.reply(...).catch(...)` |

---

## ✅ Fase 1: Bugs Críticos Funcionales (COMPLETADA)

| Tarea | ID | Archivo | Criterio de Verificación |
|-------|-----|---------|--------------------------|
| Fix checksum snapshot restore | SSP-001 | `db/snapshot_manager.py` | Sidecar `.meta.json` persiste checksum completo; `_extract_checksum_from_meta()` lo lee |
| Mapear .psc (Papyrus source) | ASA-001 | `assets/asset_scanner.py` | `AssetType.SCRIPT: frozenset({".pex", ".psc"})` |
| Teardown atómico en app_context | ARC-01 | `app_context.py` | `_start_full_inner()` envuelve teardown en `try/except` |
| Nulling de referencias zombie | ARC-03 | `app_context.py` | `except Exception` fuerza `None` en router, polling, hitl, sender, frontend_bridge, tools_installer |

---

## ⬜ Fase 2: I/O Síncrono Bloqueante (PENDIENTE)

### Tarea 2.1 — RND-02: Delegar `save_local_config` a `asyncio.to_thread()`

| Campo | Valor |
|-------|-------|
| **Archivos** | `sky_claw/agent/tools/external_tools.py` (1 archivo) |
| **Dependencias** | Ninguna |
| **Cambio** | Envolver `save_local_config(local_cfg, config_path)` en `await asyncio.to_thread(save_local_config, local_cfg, config_path)` |
| **Línea** | 145 |
| **Criterio de Aceptación** | (1) `save_local_config` no se llama directamente en contexto async. (2) `python -c "import ast; tree=ast.parse(open('sky_claw/agent/tools/external_tools.py').read()); print('asyncio.to_thread' in open('sky_claw/agent/tools/external_tools.py').read())"` retorna `True`. (3) Tests existentes pasan. |

### Tarea 2.2 — RND-03: Envolver extracción ZIP FOMOD en `asyncio.to_thread()`

| Campo | Valor |
|-------|-------|
| **Archivos** | `sky_claw/fomod/installer.py` (1 archivo) |
| **Dependencias** | Ninguna |
| **Cambio** | En `preview()` (async), envolver `self._extract_fomod_xml(archive_path)` en `await asyncio.to_thread(self._extract_fomod_xml, archive_path)`. En `install()` (async), envolver `extractor(archive_path, tmp_dir)` en `await asyncio.to_thread(extractor, archive_path, tmp_dir)`. |
| **Líneas** | 169, 231 |
| **Criterio de Aceptación** | (1) `_extract_fomod_xml` se invoca vía `asyncio.to_thread` desde `preview()`. (2) `extractor()` se invoca vía `asyncio.to_thread` desde `install()`. (3) `test_fomod.py` y `test_fomod_installer.py` pasan. |

### Tarea 2.3 — SSP-002: Envolver operaciones filesystem bloqueantes en snapshot_manager

| Campo | Valor |
|-------|-------|
| **Archivos** | `sky_claw/db/snapshot_manager.py` (1 archivo) |
| **Dependencias** | Ninguna |
| **Cambio** | Envolver las siguientes llamadas bloqueantes en `asyncio.to_thread()`: (1) Línea 298: `shutil.copy2(target, backup_path)`, (2) Línea 312: `shutil.copy2(backup_path, target)`, (3) Línea 486: `shutil.rmtree(date_dir)`, (4) Líneas 484/503/529: `file_path.stat().st_size` y `sum(f.stat()...)` envolver en helper async `_stat_size()`. |
| **Criterio de Aceptación** | (1) Ningún `shutil.copy2`/`shutil.rmtree`/`.stat()` se llama directamente en métodos `async`. (2) `test_snapshot_manager_ssp001.py` pasa. (3) `python -m pytest tests/test_snapshot_manager_ssp001.py -v` sin errores. |

---

## ⬜ Fase 3: Seguridad y Dominio Skyrim

### Tarea 3.1 — GTG-03: Rate limiting en telegram_gateway.js

| Campo | Valor |
|-------|-------|
| **Archivos** | `gateway/telegram_gateway.js` (1 archivo) |
| **Dependencias** | Ninguna |
| **Cambio** | Implementar token bucket por `user_id` antes de `daemonSocket.send()`. |
| **Criterio de Aceptación** | (1) Mensajes que excedan 5/minuto son dropeados con log. (2) `node -e "require('./gateway/telegram_gateway.js')"` no crashea (syntax check). |

### Tarea 3.2 — SCA-004: Validación de FormID en conflict_analyzer.py

| Campo | Valor |
|-------|-------|
| **Archivos** | `sky_claw/xedit/conflict_analyzer.py` (1 archivo) |
| **Dependencias** | Ninguna |
| **Cambio** | Agregar regex `^[0-9A-Fa-f]{8}$` para validar `form_id` en `parse_conflict_lines`. Skip líneas con FormID inválido + log warning. |
| **Criterio de Aceptación** | (1) FormIDs no-hex de 8 dígitos generan `logger.warning` y se skipan. (2) `test_conflict_analyzer.py` pasa. |

### Tarea 3.3 — SCA-001: Reemplazar SCPT por SCEN/INFO

| Campo | Valor |
|-------|-------|
| **Archivos** | `sky_claw/xedit/conflict_analyzer.py` (1 archivo) |
| **Dependencias** | Ninguna |
| **Cambio** | En `DEFAULT_CRITICAL_TYPES`, reemplazar `"SCPT"` por `"SCEN"` e `"INFO"`. |
| **Criterio de Aceptación** | (1) `"SCPT"` no aparece en `DEFAULT_CRITICAL_TYPES`. (2) `"SCEN"` e `"INFO"` sí aparecen. (3) Tests pasan. |

### Tarea 3.4 — SEC-09: TextInspector con ventanas deslizantes

| Campo | Valor |
|-------|-------|
| **Archivos** | `sky_claw/security/text_inspector.py` (1 archivo) |
| **Dependencias** | Ninguna |
| **Cambio** | Implementar análisis de inicio + final del contenido: `fragments = [content[:max_chars//2], content[-max_chars//2:]]`. |
| **Criterio de Aceptación** | (1) Payload malicioso en los últimos 500 chars de un texto de 20KB es detectado. (2) Tests existentes pasan. |

### Tarea 3.5 — SSP-003: Timezone UTC en cleanup_old_snapshots

| Campo | Valor |
|-------|-------|
| **Archivos** | `sky_claw/db/snapshot_manager.py` (1 archivo) |
| **Dependencias** | Tarea 2.3 (para evitar conflicto en mismas líneas) |
| **Cambio** | Reemplazar `time.mktime(dir_time)` por `datetime.strptime(date_dir.name, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp()`. |
| **Criterio de Aceptación** | (1) No se usa `time.mktime` en el módulo. (2) `datetime` con `tzinfo=UTC` se usa consistentemente. |

---

## ⬜ Fase 4: Persistencia y Resiliencia

### Tarea 4.1 — DB-002: Unificar semántica upsert_mod single vs batch

| Campo | Valor |
|-------|-------|
| **Archivos** | `sky_claw/db/async_registry.py` (1 archivo) |
| **Dependencias** | Ninguna |
| **Cambio** | Unificar `_UPSERT_MOD_SQL` para que incluya las mismas columnas que `_UPSERT_MOD_SQL_BATCH`. |
| **Criterio de Aceptación** | (1) Ambos SQL statements actualizan `category`, `installed`, `enabled_in_vfs`. (2) `test_async_registry.py` pasa. |

### Tarea 4.2 — DB-004: Excepción custom para corruption detection

| Campo | Valor |
|-------|-------|
| **Archivos** | `sky_claw/db/async_registry.py` (1 archivo) |
| **Dependencias** | Tarea 4.1 (mismo archivo, evitar conflicto) |
| **Cambio** | Crear `class DatabaseCorruptionError(RuntimeError)` y capturar solo esa en el handler de integrity check. |
| **Criterio de Aceptación** | (1) `RuntimeError` genérico ya no dispara renombrado de BD. (2) Solo `DatabaseCorruptionError` lo hace. |

### Tarea 4.3 — RND-01: Timeout en provider chat bajo lock

| Campo | Valor |
|-------|-------|
| **Archivos** | `sky_claw/agent/router.py` (1 archivo) |
| **Dependencias** | Ninguna |
| **Cambio** | Envolver `await self._provider.chat(...)` con `asyncio.wait_for(..., timeout=120.0)`. |
| **Criterio de Aceptación** | (1) Si el provider no responde en 120s, se lanza `asyncio.TimeoutError` en lugar de colgar indefinidamente. (2) `test_router.py` pasa. |

### Tarea 4.4 — SUP-06: Capturar Exception genérica en execute_rollback

| Campo | Valor |
|-------|-------|
| **Archivos** | `sky_claw/orchestrator/supervisor.py` (1 archivo) |
| **Dependencias** | Ninguna |
| **Cambio** | Ampliar `except (OSError, RuntimeError)` a `except Exception as e` con `logger.exception`. |
| **Criterio de Aceptación** | (1) `TypeError` o `AttributeError` ya no burbujean al caller. (2) Se retorna `dict` de error en lugar de excepción cruda. |

---

## ⬜ Fase 5: Arquitectura (Strangler Fig — Incrementos)

### Tarea 5.1 — LAY-01: Protocol para SyncEngine (inversión de dependencia)

| Campo | Valor |
|-------|-------|
| **Archivos** | `sky_claw/core/contracts.py`, `sky_claw/agent/tools/nexus_tools.py` (2 archivos) |
| **Dependencias** | Ninguna |
| **Cambio** | Definir `DownloadQueue` protocol en `core/contracts.py`. Modificar `nexus_tools.py` para depender del protocol en lugar de la importación concreta. |
| **Criterio de Aceptación** | (1) `nexus_tools.py` ya no importa `SyncEngine` directamente. (2) Importa `DownloadQueue` desde `core/contracts.py`. |

### Tarea 5.2 — LAY-03: Mover PathValidator interface a core/contracts.py

| Campo | Valor |
|-------|-------|
| **Archivos** | `sky_claw/core/contracts.py`, `sky_claw/core/path_resolver.py` (2 archivos) |
| **Dependencias** | Tarea 5.1 (mismo archivo contracts.py) |
| **Cambio** | Definir `PathValidatorProtocol` en `core/contracts.py`. Modificar `path_resolver.py` para depender del protocol. |
| **Criterio de Aceptación** | (1) `core/path_resolver.py` ya no importa `PathValidator` desde `security`. (2) Depende de `PathValidatorProtocol` desde `core/contracts.py`. |

### Tarea 5.3 — SUP-04: Extraer _init_rollback_components a factory

| Campo | Valor |
|-------|-------|
| **Archivos** | `sky_claw/orchestrator/supervisor.py`, `sky_claw/orchestrator/rollback_factory.py` (nuevo) (2 archivos) |
| **Dependencias** | Tarea 4.4 (modificaciones previas en supervisor.py) |
| **Cambio** | Extraer la creación de `OperationJournal`, `FileSnapshotManager`, `RollbackManager`, `DistributedLockManager` a un factory method. |
| **Criterio de Aceptación** | (1) `_init_rollback_components` delega al factory. (2) Tests existentes pasan. |

### Tarea 5.4 — SUP-05: Usar TaskGroup para arranque de demonios

| Campo | Valor |
|-------|-------|
| **Archivos** | `sky_claw/orchestrator/supervisor.py` (1 archivo) |
| **Dependencias** | Tarea 5.3 |
| **Cambio** | Reemplazar inicio secuencial de demonios con `asyncio.TaskGroup` para fail-fast colectivo. |
| **Criterio de Aceptación** | (1) Si un daemon falla al iniciar, los demás se cancelan automáticamente. (2) No hay demonios huérfanos tras fallo parcial. |

### Tarea 5.5 — DB-001: Unificar esquemas mods (Fase 1 — diagnóstico)

| Campo | Valor |
|-------|-------|
| **Archivos** | Ninguno (solo análisis) |
| **Dependencias** | Ninguna |
| **Cambio** | Generar documento de mapeo de columnas entre los 3 esquemas `mods`. Definir esquema canonical. |
| **Criterio de Aceptación** | (1) Documento con tabla de mapeo columna-a-columna. (2) Esquema canonical definido con todas las columnas necesarias. |

### Tarea 5.6 — DB-001: Unificar esquemas mods (Fase 2 — migración)

| Campo | Valor |
|-------|-------|
| **Archivos** | `sky_claw/db/async_registry.py`, `sky_claw/db/registry.py`, `sky_claw/core/database.py` (3 archivos) |
| **Dependencias** | Tarea 5.5 |
| **Cambio** | Migrar los 3 esquemas al esquema canonical con tabla `schema_version`. |
| **Criterio de Aceptación** | (1) Solo existe una definición de tabla `mods`. (2) Migración automática vía `schema_version`. (3) Todos los tests de DB pasan. |

---

## 🔒 Tareas Excluidas (Requieren Diseño Previo)

| ID | Razón |
|-----|-------|
| SUP-01/SUP-02 | God Object → Requiere diseño de Facade completo antes de tocar código |
| CLI-01 | Requiere diseño de API de subcomandos |
| TST-001..007 | Se ejecutan en paralelo al plan de refactorización |
| SEC-07 | Audit trail HITL requiere schema DB nuevo |
| SEC-12 | Token encryption requiere diseño de integración con CredentialVault |

---

*Fin del Plan Consolidado — Generado con validación cruzada de ambas auditorías*
