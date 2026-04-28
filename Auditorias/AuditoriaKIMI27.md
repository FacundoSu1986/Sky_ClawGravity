# 🔒 AUDITORÍA TÉCNICA INTEGRAL — SKY-CLAW
**Auditor:** Staff Architect (Nivel L7) | **Fecha:** 2026-04-27  
**Rama:** `claude/confident-dubinsky-be5a49` | **Alcance:** 7 Capas · 17+ Módulos · ~6.500 LoC

---

## 📊 Tabla Resumen de Hallazgos

| Severidad | Dominio | Módulo | Hallazgo (ID) |
|---|---|---|---|
| 🔴 Crítico | Arquitectura | `app_context.py` | `database.close()` no-atómico destruye estado de rollback (ARC-01) |
| 🔴 Crítico | Arquitectura | `orchestrator/supervisor.py` | God Object de ~15 responsabilidades (SUP-01) |
| 🔴 Crítico | Arquitectura | `orchestrator/supervisor.py` | Complejidad ciclomática de clase >60 (SUP-02) |
| 🔴 Crítico | Arquitectura | `agent/tools/nexus_tools.py` | Capa Agent depende de Orchestrator (LAY-01) |
| 🔴 Crítico | Arquitectura | `comms/frontend_bridge.py` · `comms/telegram.py` | Capa Comms depende de Agent y Orchestrator (LAY-02) |
| 🔴 Crítico | Persistencia | `db/async_registry.py` · `db/registry.py` · `core/database.py` | Tres esquemas `mods` mutuamente incompatibles (DB-001) |
| 🔴 Crítico | Persistencia | `db/snapshot_manager.py` | Verificación de checksum en restore nunca funciona (SSP-001) |
| 🔴 Crítico | Dominio Skyrim | `assets/asset_scanner.py` | Scripts Papyrus `.psc` no mapeados; `.pas` confundido con Papyrus (ASA-001) |
| 🔴 Crítico | Testing | `reasoning/tot.py` | Motor Tree-of-Thought sin cobertura de tests (TST-001) |
| 🔴 Crítico | Configuración / UX | `modes/cli_mode.py` | CLI sin `argparse`, `--help`, ni comandos estructurados (CLI-01) |
| 🟠 Alto | Arquitectura | `app_context.py` | `NetworkContext.close()` no libera gateway ni downloader (ARC-02) |
| 🟠 Alto | Arquitectura | `app_context.py` | Rollback parcial deja referencias a objetos zombie (ARC-03) |
| 🟠 Alto | Arquitectura | `orchestrator/supervisor.py` | Acoplamiento fuerte `build_orchestration_dispatcher(self)` (SUP-03) |
| 🟠 Alto | Arquitectura | `orchestrator/supervisor.py` | `_init_rollback_components` viola SRP (SUP-04) |
| 🟠 Alto | Arquitectura | `orchestrator/supervisor.py` | `start()` no maneja fallos parciales de demonios (SUP-05) |
| 🟠 Alto | Arquitectura | `core/path_resolver.py` | Capa Core depende de Security (`PathValidator`) (LAY-03) |
| 🟠 Alto | Rendimiento | `agent/router.py` | Provider chat sin timeout bajo lock transaccional (RND-01) |
| 🟠 Alto | Rendimiento | `agent/tools/external_tools.py` | I/O síncrono bloqueante dentro de función async (`setup_tools`) (RND-02) |
| 🟠 Alto | Rendimiento | `fomod/installer.py` (vía tools) | `zipfile.ZipFile` bloqueante en `resolve_fomod` (RND-03) |
| 🟠 Alto | Seguridad | `core/validators/ssrf.py` | Resolver DNS síncrono + ausencia de DNS pinning (SEC-01) |
| 🟠 Alto | Seguridad | `security/credential_vault.py` | `get_secret` retorna `None` indistintamente para "no existe" vs "tampering" (SEC-02) |
| 🟠 Alto | Seguridad | `security/purple_scanner.py` | Taint tracking roto para `f.read()` (atributo AST nunca matcha) (SEC-03) |
| 🟠 Alto | Seguridad | `tools_installer.py` | Descarga de herramientas sin validación de hash esperado (SEC-04) |
| 🟠 Alto | Seguridad / Integridad | `fomod/installer.py` | Instalación no atómica sin rollback en destino final (INT-01) |
| 🟠 Alto | Dominio Skyrim | `xedit/conflict_analyzer.py` | Record type `SCPT` obsoleto en Skyrim SE/AE (SCA-001) |
| 🟠 Alto | Dominio Skyrim | `xedit/conflict_analyzer.py` | Parser no valida formato de FormID ni campos vacíos (SCA-004) |
| 🟠 Alto | Dominio Skyrim | `xedit/conflict_analyzer.py` | `.esp` con flag ESL no contemplado en límite de plugins (SCA-005) |
| 🟠 Alto | Dominio Skyrim | `assets/asset_scanner.py` | Hash parcial en archivos >2 MB genera colisiones probables (ASA-002) |
| 🟠 Alto | Persistencia | `db/async_registry.py` | `upsert_mod` single vs batch tienen semántica divergente (DB-002) |
| 🟠 Alto | Persistencia | `db/async_registry.py` | `RuntimeError` genérico capturado como corruption de BD (DB-004) |
| 🟠 Alto | Persistencia | `db/journal.py` | `json_set` requiere SQLite JSON1 no garantizado en Windows (JNL-001) |
| 🟠 Alto | Persistencia | `db/snapshot_manager.py` | Operaciones de filesystem bloqueantes en métodos `async` (SSP-002) |
| 🟠 Alto | Testing | `gui/` (NiceGUI) | Sin cobertura de tests automatizados (TST-002) |
| 🟠 Alto | Testing | `gateway/` (Node.js) | Sin cobertura de tests (TST-003) |
| 🟠 Alto | Testing | `modes/cli_mode.py` | Sin cobertura de tests (TST-004) |
| 🟠 Alto | Interfaces / UX | `gui/sky_claw_gui.py` | `_chat_controller` usado sin null-check (GUI-02) |
| 🟠 Alto | Interfaces / UX | `gui/dashboard.py` · `gui/app.py` | `_open_settings_dialog` no definido; crash en navegación (GUI-03) |
| 🟠 Alto | Interfaces / UX | `frontend/js/app.js` | `crypto.randomUUID` con fallback de baja entropía (FE-02) |
| 🟠 Alto | Interfaces / UX | `modes/cli_mode.py` | Sin historial ni autocompletado (CLI-02) |
| 🟡 Medio | Arquitectura | `app_context.py` | `start_minimal()` carece de protección contra re-entrada (ARC-05) |
| 🟡 Medio | Arquitectura | `db/async_registry.py` · `db/journal.py` | Capa DB depende de `core` validators (LAY-04) |
| 🟡 Medio | Arquitectura | `comms/frontend_bridge.py` ↔ `app_context.py` | Import circular potencial (LAY-05) |
| 🟡 Medio | Arquitectura | `tools/*_service.py` | Capa Tools depende de `Core` (`PathResolutionService`) (LAY-06) |
| 🟡 Medio | Arquitectura | `comms/telegram_polling.py` | Import lazy de `security` dentro de loop (LAY-07) |
| 🟡 Medio | Arquitectura | `modes/gui_mode.py` | Ausencia de barrera arquitectónica; composition root disperso (LAY-08) |
| 🟡 Medio | Arquitectura | `orchestrator/supervisor.py` | `execute_rollback` no captura excepciones genéricas (SUP-06) |
| 🟡 Medio | Arquitectura | `orchestrator/supervisor.py` | Lectura directa de `os.environ` en `_ensure_wrye_bash_runner` (SUP-07) |
| 🟡 Medio | Rendimiento | `agent/router.py` | Progress callbacks fire-and-forget sin backpressure (RND-04) |
| 🟡 Medio | Rendimiento | `agent/router.py` | Sin semáforo para limitar sesiones concurrentes de `chat()` (RND-05) |
| 🟡 Medio | Rendimiento | `agent/providers.py` | Sin circuit breaker ante fallos en cascada (RND-06) |
| 🟡 Medio | Rendimiento | `agent/providers.py` | `RetryError` filtrado a callers sin manejo (RND-07) |
| 🟡 Medio | Seguridad | `security/network_gateway.py` | Excepción `is_loopback` deshabilita SSL (SEC-05) |
| 🟡 Medio | Seguridad | `security/path_validator.py` | TOCTOU en symlink check + `resolve()` no estricto (SEC-06) |
| 🟡 Medio | Seguridad | `security/hitl.py` | Ausencia de audit trail inmutable y non-repudiation (SEC-07) |
| 🟡 Medio | Seguridad | `security/sanitize.py` | Bypass potencial por truncamiento previo a detección (SEC-08) |
| 🟡 Medio | Seguridad | `security/text_inspector.py` | Límite de 10KB puede ocultar payloads de prompt injection (SEC-09) |
| 🟡 Medio | Seguridad | `security/agent_guardrail.py` | PII regex demasiado permisivo (DoS de falsos positivos) (SEC-10) |
| 🟡 Medio | Seguridad | `security/governance.py` | DoS auto-inducido por escritura no atómica de HMAC (SEC-11) |
| 🟡 Medio | Seguridad | `security/auth_token_manager.py` | Token de autenticación en texto plano en disco (SEC-12) |
| 🟡 Medio | Seguridad | `fomod/installer.py` | Symlinks en archivos 7z/rar no mitigados post-extracción (INT-02) |
| 🟡 Medio | Seguridad | `gateway/server.js` | `agentServer` siempre en plaintext (`ws://`) (GWS-01) |
| 🟡 Medio | Seguridad | `gateway/server.js` | Race condition en reemplazo de `agentSocket` (GWS-02) |
| 🟡 Medio | Seguridad | `gateway/server.js` | Sin rate limiting en broadcast agente→UI (GWS-03) |
| 🟡 Medio | Seguridad | `gateway/telegram_gateway.js` | Race condition en `daemonSocket` sin sincronización (GTG-01) |
| 🟡 Medio | Seguridad | `gateway/telegram_gateway.js` | Floating promise en `ctx.reply` (GTG-02) |
| 🟡 Medio | Dominio Skyrim | `xedit/conflict_analyzer.py` | No distingue prioridad intrínseca de `.esm` vs `.esp` (SCA-002) |
| 🟡 Medio | Dominio Skyrim | `xedit/conflict_analyzer.py` | `suggest_resolution` ignora semántica de `CELL`/`WRLD` persistentes (SCA-003) |
| 🟡 Medio | Persistencia | `db/registry.py` | API incompleta respecto a `AsyncModRegistry` (DB-003) |
| 🟡 Medio | Persistencia | `db/journal.py` | No usa transacciones SQLite atómicas para operaciones compuestas (JNL-002) |
| 🟡 Medio | Persistencia | `db/snapshot_manager.py` | `cleanup_old_snapshots` usa timezone local vs UTC (SSP-003) |
| 🟡 Medio | Integraciones | `gateway/telegram_gateway.js` | Sin rate limiting en mensajes entrantes de Telegram (GTG-03) |
| 🟡 Medio | Integraciones | `comms/telegram.py` | Mensaje de progreso genérico durante `/update_mods` (TG-01) |
| 🟡 Medio | Integraciones | `agent/providers.py` | Body de request logueado en errores 4xx/5xx (fuga de PII) (RND-08) |
| 🟡 Medio | Testing | `tests/conftest.py` | Vacío; sin fixtures compartidas de proyecto (TST-005) |
| 🟡 Medio | Testing | — | Desbalance hacia unitarios; falta tests E2E (TST-006) |
| 🟡 Medio | Interfaces / UX | `gui/app.py` · `gui/dashboard.py` | Datos de estadísticas hardcodeados/falsos (GUI-01) |
| 🟡 Medio | Interfaces / UX | `gui/setup_wizard.py` · `gui/app.py` | Manejo de errores de `keyring` genérico (GUI-04) |
| 🟡 Medio | Interfaces / UX | `frontend/js/app.js` | Backoff de reconexión WS lineal vs exponencial (FE-01) |
| 🟡 Medio | Interfaces / UX | `frontend/js/app.js` | Race condition en `sendCommand` (FE-03) |
| 🟡 Medio | Interfaces / UX | `modes/cli_mode.py` | Captura de excepciones muy estrecha (`RuntimeError` único) (CLI-03) |
| 🟢 Bajo | Arquitectura | `app_context.py` | Uso de `os.path.join` mezclado con `pathlib` (ARC-06) |
| 🟢 Bajo | Arquitectura | `app_context.py` | `FrontendBridge` task creado antes de registrar callback (ARC-07) |
| 🟢 Bajo | Arquitectura | `orchestrator/supervisor.py` | Uso de f-strings en llamadas a `logger` (SUP-08) |
| 🟢 Bajo | Rendimiento | `agent/router.py` | Crecimiento ilimitado de tabla `chat_history` en SQLite (RND-09) |
| 🟢 Bajo | Rendimiento | `agent/providers.py` | HTTP 408 (Request Timeout) no se reintenta (RND-10) |
| 🟢 Bajo | Rendimiento | `agent/tools/__init__.py` | Uso de lambdas para envolver corutinas (pérdida trazabilidad) (RND-11) |
| 🟢 Bajo | Seguridad | `gateway/server.js` | `timingSafeEqual` compara longitud de caracteres UTF-16 vs bytes (GWS-04) |
| 🟢 Bajo | Seguridad | `gateway/server.js` | Health endpoint HTTP expone metadatos operativos (GWS-05) |
| 🟢 Bajo | Seguridad | `security/loop_guardrail.py` | Determinismo de serialización JSON para hashes (SEC-13) |
| 🟢 Bajo | Seguridad | `security/file_permissions.py` | Verificación post-op omitida tras `restrict_to_owner` (SEC-14) |
| 🟢 Bajo | Calidad de Código | `agent/tools/external_tools.py` | Body logueado con PII (ya listado en Rendimiento) |
| 🟢 Bajo | Testing | — | Escasa parametrización con `@pytest.mark.parametrize` (TST-007) |
| 🟢 Bajo | Interfaces / UX | `gui/sky_claw_gui.py` | Reactividad de `_ReactiveVar` manual/falsa (GUI-05) |

---

## 1. Seguridad

### SEC-01 — SSRF: Resolver DNS síncrono + ausencia de DNS pinning
**Módulo y Línea(s):** `core/validators/ssrf.py:88-103`, `105-219`
**Descripción y Evidencia:** `_default_resolver` invoca `socket.getaddrinfo` (bloqueante) dentro de un validador que se consume desde código async. No existe DNS pinning: la IP resuelta se valida pero no se "fija" para la conexión subsiguiente, abriendo una ventana TOCTOU de DNS rebinding si otro componente usa la URL validada sin pasar por `NetworkGateway`.
**Severidad:** Alto
**Impacto:** Bloqueo del event loop durante resolución DNS. Riesgo de SSRF por DNS rebinding en componentes que confíen solo en este validador.
**Recomendación:** Migrar a `asyncio.get_running_loop().getaddrinfo()` y unificar la validación SSRF con `SafeResolver` del `network_gateway` para garantizar pinning en todo el stack.

```python
async def _default_resolver(hostname: str) -> list[str]:
    loop = asyncio.get_running_loop()
    try:
        infos = await loop.getaddrinfo(hostname, None)
        return list({r[4][0] for r in infos})
    except socket.gaierror:
        return []
```

---

### SEC-02 — CredentialVault: Indistinguible "no existe" vs "tampering"
**Módulo y Línea(s):** `security/credential_vault.py:184-208`
**Descripción y Evidencia:** `get_secret` captura `Exception` genérico y retorna `None` indistintamente tanto si el secreto no existe como si la clave maestra es inválida o los datos están corruptos. Esto impide detectar ataques de manipulación del vault.
**Severidad:** Alto
**Impacto:** Un atacante que corrompa el ciphertext puede forzar comportamiento silencio idéntico a "secreto no configurado", ocultando el ataque.
**Recomendación:** Distinguir excepciones de base de datos (`aiosqlite.Error`) de errores criptográficos (`cryptography.fernet.InvalidToken`).

```python
except aiosqlite.Error:
    return None
except cryptography.fernet.InvalidToken:
    logger.critical("Vault tampering or invalid master key")
    raise SecurityViolationError("Vault integrity check failed")
```

---

### SEC-03 — PurpleScanner: Taint tracking roto para lecturas de archivo
**Módulo y Línea(s):** `security/purple_scanner.py:124-128`
**Descripción y Evidencia:** `_is_tainted_source` verifica `node.func.id in ("input", "open", "f.read", "__import__")`. Como `f.read` es un `ast.Attribute`, nunca será `ast.Name`; por tanto, lecturas de archivo **nunca** se marcan como tainted.
**Severidad:** Alto
**Impacto:** Falsos negativos en análisis de flujo de datos: código que lee de archivo y pasa a `exec()`/`eval()` no se reportará como tainted.
**Recomendación:** Corregir la lógica para soportar `ast.Attribute`:

```python
def _is_tainted_source(self, node: ast.AST) -> bool:
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name):
            return node.func.id in ("input", "open", "__import__")
        if isinstance(node.func, ast.Attribute):
            return node.func.attr == "read"
    return False
```

---

### SEC-04 — ToolsInstaller: Descargas sin validación de hash esperado
**Módulo y Línea(s):** `tools_installer.py:508-565`
**Descripción y Evidencia:** `_download_asset` calcula SHA256 durante la descarga pero solo lo loguea truncado. No existe una whitelist de hashes esperados para LOOT, SSEEdit ni Pandora; tampoco se valida contra checksums publicados por los proyectos upstream.
**Severidad:** Alto
**Impacto:** Si el release de GitHub es comprometido o ocurre un ataque de supply-chain, el instalador descargará y extraerá el binario malicioso sin detección.
**Recomendación:** Mantener un diccionario de hashes SHA256 pinned por versión/tag conocido.

```python
KNOWN_SHA256 = {
    "loot_v0.22.4.zip": "aabbccdd...",
}
if hasher.hexdigest() != KNOWN_SHA256[asset.name]:
    raise ToolInstallError("Hash mismatch — possible tampered release")
```

---

### SEC-05 — NetworkGateway: Excepción loopback deshabilita SSL
**Módulo y Línea(s):** `security/network_gateway.py:167-220`, `233-243`
**Descripción y Evidencia:** En el método `request`, si `is_loopback` es `True`, se fuerza `ssl=False`. Aunque `authorize` ya debería haber bloqueado loopback cuando `block_private_ips=True`, la existencia de esta ruta "blanda" para loopback local es un anti-patrón.
**Severidad:** Medio
**Impacto:** Si alguna ruta de bypass futura permite `is_loopback=True` sin pasar por `authorize`, el tráfico local iría en claro.
**Recomendación:** Eliminar la excepción `is_loopback` + `ssl=False`. Si el loopback local es necesario, usar un certificado autofirmado y `ssl=ssl_context` explícito.

---

### SEC-06 — PathValidator: TOCTOU en symlink check
**Módulo y Línea(s):** `security/path_validator.py:46-86`
**Descripción y Evidencia:** `validate()` llama `target.is_symlink()` y luego `target.resolve(strict=True)`. Entre ambas llamadas un atacante con acceso concurrente al filesystem puede swappear el symlink. Además, `resolved = target.resolve()` en línea 77 usa `strict=False` por defecto.
**Severidad:** Medio
**Impacto:** Bypass teórico de sandbox por race condition en symlinks. En Windows, `resolve(strict=False)` puede no normalizar correctamente componentes inexistentes.
**Recomendación:** Usar `strict=True` en la resolución final y realizar la verificación de symlink en un solo paso post-resolución.

---

### SEC-07 — HITL: Ausencia de audit trail inmutable
**Módulo y Línea(s):** `security/hitl.py:1-154`
**Descripción y Evidencia:** Las decisiones HITL se registran solo en logging. No hay persistencia en append-only log ni firma criptográfica (`hmac` / `ed25519`) de cada decisión. Un atacante con acceso al sistema podría borrar logs o falsificar una aprobación.
**Severidad:** Medio
**Impacto:** Imposibilidad de demostrar compliance ante auditoría. Riesgo de repudio de decisiones críticas.
**Recomendación:** Persistir cada evento HITL en SQLite con `PRAGMA journal_mode=WAL`, incluyendo HMAC-SHA256 de la fila usando una clave separada del vault.

---

### SEC-08 — Sanitize: Bypass potencial por truncamiento previo
**Módulo y Línea(s):** `security/sanitize.py:64-108`
**Descripción y Evidencia:** `sanitize_for_prompt` aplica NFKC y regex anti-injection. El truncamiento ocurre dentro de la función, pero si el caller trunca manualmente antes de llamar a `sanitize_for_prompt`, el payload malicioso podría perderse.
**Severidad:** Medio
**Impacto:** Si un desarrollador trunca manualmente antes de sanitizar, pierde detección.
**Recomendación:** Documentar en la docstring que `sanitize_for_prompt` debe ser la primera operación y el truncamiento la última; nunca truncar previamente.

---

### SEC-09 — TextInspector: Límite de 10KB oculta payloads
**Módulo y Línea(s):** `security/text_inspector.py:59-62`, `67-68`
**Descripción y Evidencia:** `TextInspector` limita el análisis a `max_chars` (10KB por defecto). Un atacante puede colocar un prompt injection al final de un documento de 20KB, quedando fuera del fragmento analizado.
**Severidad:** Medio
**Impacto:** Bypass de detección de indirect prompt injection en contenidos largos.
**Recomendación:** Implementar análisis de ventanas deslizantes (inicio + final) o aumentar `max_chars` para archivos de configuración críticos.

```python
fragments = [content[:max_chars//2], content[-max_chars//2:]]
for frag in fragments:
    findings.extend(self._inspect_fragment(frag))
```

---

### SEC-10 — AgentGuardrail: PII regex demasiado permisivo
**Módulo y Línea(s):** `security/agent_guardrail.py:56-62`
**Descripción y Evidencia:** El patrón `(?P<card>\b(?:\d{4}[ -]?){3}\d{1,4}\b)` matcha cualquier número de 13-16 dígitos con separadores opcionales. Incluye números de versión, IDs de mods, timestamps, etc.
**Severidad:** Medio
**Impacto:** Denegación de servicio funcional: descripciones de mods con IDs numéricos largos serán rechazadas.
**Recomendación:** Usar el algoritmo de Luhn para validar que el número matchado sea realmente una tarjeta.

```python
import luhn
match = _COMBINED_PII_RE.search(text)
if match and match.group("card") and not luhn.verify(match.group("card").replace(" ", "").replace("-", "")):
    match = None
```

---

### SEC-11 — Governance: DoS auto-inducido por escritura no atómica de HMAC
**Módulo y Línea(s):** `security/governance.py:140-153`
**Descripción y Evidencia:** `save_whitelist` escribe `whitelist_path` y luego `_hmac_sig_path`. Si el proceso crasha entre ambas, la siguiente carga fallará cerrado (líneas 117-121). Es un DoS auto-inducido por diseño.
**Severidad:** Medio
**Impacto:** Whitelist legítima se vuelve inusable tras un crash en el momento equivocado; requiere regeneración manual.
**Recomendación:** Escribir ambos archivos como un paquete atómico: directorio temporal, escritura de ambos, renombrado atómico. O usar un único archivo `.signed.json`.

---

### SEC-12 — AuthTokenManager: Token en texto plano en disco
**Módulo y Línea(s):** `security/auth_token_manager.py:60-77`, `145-180`
**Descripción y Evidencia:** `generate()` escribe el token en JSON plano en `~/.sky_claw/tokens/ws_auth_token`. Cualquier proceso del usuario (o malware) puede leerlo.
**Severidad:** Medio
**Impacto:** Elevación de privilegios lateral: un proceso comprometido puede robar el token y suplantar el WS daemon.
**Recomendación:** Cifrar el token en disco usando una clave derivada del mismo mecanismo que `CredentialVault`, o usar Named Pipes/Unix domain sockets en lugar de archivos.

---

### SEC-13 — LoopGuardrail: Determinismo de serialización JSON
**Módulo y Línea(s):** `security/loop_guardrail.py:50`
**Descripción y Evidencia:** `json.dumps(tool_args, sort_keys=True, default=str)` puede generar representaciones inconsistentes para objetos no serializables nativamente (ej. `set`, `datetime`).
**Severidad:** Bajo
**Impacto:** Falsos negativos en detección de bucles cuando los argumentos contienen tipos complejos.
**Recomendación:** Validar previamente que `tool_args` solo contenga tipos JSON-serializables básicos, o usar `pydantic.v1.json()` con modelo estricto.

---

### SEC-14 — FilePermissions: Verificación post-op omitida
**Módulo y Línea(s):** `security/file_permissions.py:24-41`
**Descripción y Evidencia:** `restrict_to_owner` no re-verifica que los permisos se aplicaron correctamente. En Windows, `icacls` puede fallar silenciosamente si el proceso no tiene privilegios.
**Severidad:** Bajo
**Impacto:** Archivos sensibles (salts, HMAC keys) podrían quedar con permisos permisivos.
**Recomendación:** Agregar `assert_restricted(path)` que verifique `os.stat(path).st_mode` en POSIX y ACL efectiva en Windows.

---

### GWS-01 — Gateway server.js: Servidor agente siempre en plaintext
**Módulo y Línea(s):** `gateway/server.js:187`, `243`
**Descripción y Evidencia:** `agentServer` se crea sin TLS (`ws://`) aun cuando `tlsCreds` existen. Solo el servidor UI usa `wss://`. Esto representa un downgrade forzado para el canal agente-gateway.
**Severidad:** Medio
**Impacto:** Tráfico local en texto plano; riesgo de escalada de privilegios si otro proceso local escucha o inyecta conexiones.
**Recomendación:** Reutilizar `tlsCreds` para el agente o al menos validar que el fallback a `ws://` esté explícitamente autorizado por configuración.

---

### GWS-02 — Gateway server.js: Race condition en reemplazo de agentSocket
**Módulo y Línea(s):** `gateway/server.js:189-193`
**Descripción y Evidencia:** Una nueva conexión de agente sobrescribe `agentSocket` sin verificar si ya existe una activa. El socket anterior permanece abierto.
**Severidad:** Medio
**Impacto:** Ambigüedad sobre qué agente es autoritativo; posible enrutamiento incorrecto.
**Recomendación:** Cerrar el agente previo antes de asignar el nuevo.

```javascript
if (agentSocket && agentSocket !== ws && agentSocket.readyState === ws.OPEN) {
    agentSocket.close(4000, 'Replaced by new agent connection');
}
agentSocket = ws;
```

---

### GWS-03 — Gateway server.js: Sin rate limiting en broadcast agente→UI
**Módulo y Línea(s):** `gateway/server.js:201-221`
**Descripción y Evidencia:** El handler de mensajes del agente retransmite a `uiSockets` sin limitación de tasa ni verificación de backpressure (`ws.bufferedAmount`).
**Severidad:** Medio
**Impacto:** Un agente comprometido podría inundar los frontends conectados.
**Recomendación:** Añadir limitador por socket similar al implementado en el lado UI.

---

### GWS-04 — Gateway server.js: timingSafeEqual con longitud de caracteres UTF-16
**Módulo y Línea(s):** `gateway/server.js:117-135`
**Descripción y Evidencia:** `a.length !== b.length` compara unidades de código UTF-16 (JS strings), no bytes UTF-8. Si el token contiene caracteres multibyte, `timingSafeEqual` puede lanzar (capturado como `false`).
**Severidad:** Bajo
**Impacto:** Falsos negativos para tokens UTF-8 válidos con caracteres multibyte.
**Recomendación:** Comparar longitudes de buffer.

```javascript
const bufA = Buffer.from(a, 'utf8');
const bufB = Buffer.from(b, 'utf8');
if (bufA.length !== bufB.length) return false;
return crypto.timingSafeEqual(bufA, bufB);
```

---

### GWS-05 — Gateway server.js: Health endpoint expone metadatos
**Módulo y Línea(s):** `gateway/server.js:338-348`
**Descripción y Evidencia:** El endpoint `/health` en HTTP plano expone `agent_connected`, `ui_connections` y `uptime_seconds`.
**Severidad:** Bajo
**Impacto:** Información útil para reconocimiento local.
**Recomendación:** Limitar exposición o requerir autenticación en el health check.

---

### GTG-01 — Gateway telegram_gateway.js: Race condition en daemonSocket
**Módulo y Línea(s):** `gateway/telegram_gateway.js:107-114`
**Descripción y Evidencia:** Dos conexiones WS concurrentes pueden autenticarse y competir por asignar `daemonSocket`. El `close` handler mitiga parcialmente, pero existe una ventana TOCTOU.
**Severidad:** Medio
**Impacto:** Referencia de socket incorrecta; pérdida de mensajes.
**Recomendación:** Usar un flag o mutex simple para secuenciar autenticaciones.

---

### GTG-02 — Gateway telegram_gateway.js: Floating promise en ctx.reply
**Módulo y Línea(s):** `gateway/telegram_gateway.js:203-205`
**Descripción y Evidencia:** `ctx.reply("SISTEMA: ...")` no se awaita, generando una promesa desconectada. Si rechaza, se convierte en `unhandledRejection`.
**Severidad:** Medio
**Impacto:** Promise rechazada no manejada; riesgo de crash en modo estricto de Node.js.
**Recomendación:** Await con catch.

```javascript
await ctx.reply("SISTEMA: Conexión con el núcleo Python no establecida.")
    .catch(err => console.error("Reply failed:", err.message));
```

---

### GTG-03 — Gateway telegram_gateway.js: Sin rate limiting en mensajes entrantes
**Módulo y Línea(s):** `gateway/telegram_gateway.js:173-206`
**Descripción y Evidencia:** `bot.on("message:text")` reenvía cada mensaje válido al daemon vía WebSocket sin throttling. Un usuario autorizado (o bot comprometido) puede generar tráfico ilimitado.
**Severidad:** Alto
**Impacto:** DoS contra el daemon; agotamiento de buffers WS.
**Recomendación:** Implementar token bucket por `user_id`.

```javascript
const userBuckets = new Map();
function checkRateLimit(userId) {
    const now = Date.now();
    const bucket = userBuckets.get(userId) || { tokens: 5, last: now };
    bucket.tokens = Math.min(10, bucket.tokens + (now - bucket.last) / 1000);
    bucket.last = now;
    if (bucket.tokens < 1) return false;
    bucket.tokens--;
    userBuckets.set(userId, bucket);
    return true;
}
```

---

## 2. Arquitectura

### ARC-01 — database.close() no-atómico destruye estado de rollback
**Módulo y Línea(s):** `app_context.py:187-193`
**Descripción y Evidencia:** En `_start_full_inner()`, `await self.database.close()` se invoca fuera de cualquier bloque `try/except`. Si esta llamada lanza una excepción, el método termina abruptamente sin reconstruir el `AsyncExitStack`. La próxima invocación encontrará un `_exit_stack` en estado indefinido.
**Severidad:** Crítico
**Impacto:** Estado del `AsyncExitStack` corrupto entre reintentos. Fuga de callbacks acumulados.
**Recomendación:** Envolver la fase de teardown previo en un `try/finally` propio, o usar patrón de *two-phase commit*.

```python
async def _start_full_inner(self) -> None:
    prev_polling, prev_router = self.polling, self.router
    self.polling = self.router = None
    try:
        if prev_polling: await prev_polling.stop()
        if prev_router:  await prev_router.close()
        await self.database.close()
    except Exception:
        logger.exception("Teardown previo falló; continuando con fresh init")
    old_stack, self._exit_stack = self._exit_stack, AsyncExitStack()
    await old_stack.aclose()
    self._exit_stack.push_async_callback(self.network.close)
```

---

### ARC-02 — NetworkContext.close() no libera gateway ni downloader
**Módulo y Línea(s):** `app_context.py:76-79`
**Descripción y Evidencia:** `NetworkContext.close()` únicamente cierra la `ClientSession`. Ni el `NetworkGateway` ni el `NexusDownloader` tienen callback de cierre.
**Severidad:** Alto
**Impacto:** Fuga de descriptores de archivo si `NexusDownloader` crea archivos temporales en `staging_dir`.
**Recomendación:** Añadir cierre explícito o inyectar el gateway/downloader en el exit stack.

---

### ARC-03 — Rollback parcial deja referencias a objetos zombie
**Módulo y Línea(s):** `app_context.py:460-466`
**Descripción y Evidencia:** El bloque `except Exception` ejecuta `await self._exit_stack.aclose()` y relanza, pero no anula las referencias de instancia (`self.router`, `self.polling`, etc.).
**Severidad:** Alto
**Impacto:** Llamadas subsiguientes a `is_configured` devuelven `True`, pero el router está cerrado/corrupto.
**Recomendación:** Forzar *nulling* de todas las referencias mutables en un bloque `finally`.

```python
finally:
    self.router = self.polling = self.hitl = self.sender = None
    self.frontend_bridge = None
    self.tools_installer = None
```

---

### ARC-05 — start_minimal() carece de protección contra re-entrada
**Módulo y Línea(s):** `app_context.py:152-161`
**Descripción y Evidencia:** A diferencia de `start_full()`, `start_minimal()` no utiliza el `asyncio.Lock`.
**Severidad:** Medio
**Impacto:** Condición de carrera en `_migrate_legacy_json()` y doble inicialización de la `ClientSession`.
**Recomendación:** Unificar el lock para proteger todo el ciclo de vida.

---

### ARC-06 — Uso de os.path.join mezclado con pathlib
**Módulo y Línea(s):** `app_context.py:412`
**Descripción y Evidencia:** Inconsistencia en el manejo de rutas. El resto del módulo utiliza `pathlib.Path` exclusivamente, pero en línea 412 se usa `os.path.join`.
**Severidad:** Bajo
**Impacto:** Riesgo de incompatibilidad con validadores `PathValidator` que esperan objetos `Path`.
**Recomendación:** `mo2_profile = str(pathlib.Path(mo2_root) / "profiles" / "Default")`

---

### ARC-07 — FrontendBridge task creado antes de registrar callback
**Módulo y Línea(s):** `app_context.py:435-436`
**Descripción y Evidencia:** Entre la creación de la tarea (`self._track_task(...)`) y el registro en el exit stack existe una ventana de interrupción infinitesimal.
**Severidad:** Bajo
**Impacto:** Teórico pero posible en sistemas con alta presión de memoria.
**Recomendación:** Registrar el callback *antes* de crear la tarea.

---

### SUP-01 — SupervisorAgent es un God Object de ~15 responsabilidades
**Módulo y Línea(s):** `orchestrator/supervisor.py:48-576`
**Descripción y Evidencia:** La clase centraliza 15+ responsabilidades no cohesivas: persistencia, interfaz de comunicación, grafo de estados, rollback, concurrencia distribuida, resolución de rutas, event bus, demonios, servicios de pipeline, detección de conflictos, ejecución de Wrye Bash, validación de límites de plugins, dispatch de herramientas, rollback manual, manejo de señales GUI.
**Severidad:** Crítico
**Impacto:** Imposibilidad de testear unidades aisladas. Cambios en Wrye Bash pueden romper el daemon de telemetría.
**Recomendación:** Aplicar **Strangler Fig** extrayendo cada responsabilidad en subsistemas coordinados por un `Facade` ligero. El `SupervisorAgent` debería convertirse en un orquestador declarativo de no más de 80 líneas.

```python
class SkyClawFacade:
    def __init__(self, deps: Container):
        self.rollback = RollbackSubsystem(deps.journal, deps.snapshot_mgr)
        self.pipelines = PipelineSubsystem(deps.lock_mgr, deps.event_bus)
        self.tools = ToolDispatchSubsystem(deps.dispatcher)
        self.daemons = DaemonSubsystem(deps.bus, deps.watcher, deps.telemetry)
```

---

### SUP-02 — Complejidad ciclomática aproximada >60 para la clase
**Módulo y Línea(s):** Clase completa
**Descripción y Evidencia:** Estimación de MCC por método: `__init__` ≈ 18, `start` ≈ 12, `_run_plugin_limit_guard` ≈ 8, `execute_wrye_bash_pipeline` ≈ 10, `_ensure_wrye_bash_runner` ≈ 8. Total clase >60.
**Severidad:** Crítico
**Impacto:** Alta probabilidad de introducir regresiones. Dificultad extrema para code review efectivo.
**Recomendación:** Refactorizar cada método en clases `Strategy` o State Machine.

---

### SUP-03 — Acoplamiento fuerte: build_orchestration_dispatcher(self)
**Módulo y Línea(s):** `orchestrator/supervisor.py:118`
**Descripción y Evidencia:** El dispatcher de herramientas recibe la instancia completa del `SupervisorAgent` (`self`). Las *strategies* acceden a atributos privados del supervisor a través de *lambdas*.
**Severidad:** Alto
**Impacto:** Las strategies están acopladas a la firma completa del supervisor. No se pueden mover a otro proceso/agente.
**Recomendación:** Usar inyección de dependencias explícitas vía un `dataclass` de colaboradores.

---

### SUP-04 — _init_rollback_components viola SRP
**Módulo y Línea(s):** `orchestrator/supervisor.py:125-162`
**Descripción y Evidencia:** Un único método crea `OperationJournal`, `FileSnapshotManager`, `RollbackManager`, `DistributedLockManager` y `PathValidator`.
**Severidad:** Alto
**Impacto:** Dificulta sustituir un componente sin tocar este método.
**Recomendación:** Extraer a un factory o inyectar desde un `Container` DI.

---

### SUP-05 — start() no maneja fallos parciales de demonios
**Módulo y Línea(s):** `orchestrator/supervisor.py:164-211`
**Descripción y Evidencia:** Los demonios se inician secuencialmente. Si `_watcher_daemon.start()` falla, `_maintenance_daemon` y `_telemetry_daemon` ya están corriendo.
**Severidad:** Alto
**Impacto:** Watcher caído pero Maintenance activo → inconsistencia entre snapshots y filesystem real.
**Recomendación:** Usar `asyncio.TaskGroup` para el arranque de demonios.

---

### SUP-06 — execute_rollback no captura excepciones genéricas
**Módulo y Línea(s):** `orchestrator/supervisor.py:288`
**Descripción y Evidencia:** El método captura `(OSError, RuntimeError)` pero no `Exception`. Si `RollbackManager` lanza `TypeError` o `AttributeError`, la excepción burbujea.
**Severidad:** Medio
**Impacto:** El caller (posiblemente LangGraph) recibe una excepción cruda en lugar del contrato `dict` esperado.
**Recomendación:** `except Exception as e:`

---

### SUP-07 — Dependencia directa de variables de entorno
**Módulo y Línea(s):** `orchestrator/supervisor.py:318-320`
**Descripción y Evidencia:** Lee `os.environ` directamente en lugar de usar la configuración inyectada.
**Severidad:** Medio
**Impacto:** Comportamiento no determinista entre entornos.
**Recomendación:** Inyectar un `PathsConfig` dataclass.

---

### SUP-08 — Uso de f-strings en llamadas a logger
**Módulo y Línea(s):** `orchestrator/supervisor.py:548`
**Descripción y Evidencia:** `logger.info(f"Detectados {len(conflicts)} conflictos de assets")` fuerza la evaluación inmediata.
**Severidad:** Bajo
**Impacto:** Micro-optimización; acumulable en escaneos frecuentes.
**Recomendación:** `logger.info("Detectados %d conflictos de assets", len(conflicts))`

---

### LAY-01 — Capa Agent depende de Orchestrator (SyncEngine)
**Módulo y Línea(s):** `agent/tools/nexus_tools.py:24`
**Descripción y Evidencia:** La capa `agent` importa `SyncEngine` desde `orchestrator`. Invierte la jerarquía de dependencias.
**Severidad:** Crítico
**Impacto:** Cualquier cambio en `SyncEngine` obliga a recompilar/revisar la capa Agent.
**Recomendación:** Definir un protocolo (`typing.Protocol`) en `core/contracts.py`.

```python
class DownloadQueue(Protocol):
    def enqueue_download(self, coro: Coroutine[Any, Any, Any], context: str = "") -> asyncio.Task[Any]: ...
```

---

### LAY-02 — Capa Comms depende de Agent y Orchestrator
**Módulo y Línea(s):** `comms/frontend_bridge.py:40`, `comms/telegram.py:49,51`
**Descripción y Evidencia:** `frontend_bridge.py` importa `create_provider` desde `agent.providers`. `telegram.py` importa `LLMRouter` y `UpdatePayload`.
**Severidad:** Crítico
**Impacto:** No se puede extraer la capa Comms a un microservicio independiente.
**Recomendación:** Aplicar Dependency Inversion. Comms debe depender de abstracciones en `core/contracts.py`.

---

### LAY-03 — Capa Core depende de Security (PathValidator)
**Módulo y Línea(s):** `core/path_resolver.py:23`
**Descripción y Evidencia:** `core/path_resolver.py` importa `PathValidator` desde `security.path_validator`. Si `core` es la capa más fundamental, no debería depender de `security`.
**Severidad:** Alto
**Impacto:** Riesgo de import circular si `security` necesita utilidades de `core`.
**Recomendación:** Mover la interfaz `PathValidator` a `core/contracts.py` o `core/validators/path.py`.

---

### LAY-04 — Capa DB depende de Core validators
**Módulo y Línea(s):** `db/async_registry.py:122`, `db/journal.py:235`
**Descripción y Evidencia:** La capa de persistencia importa validadores de path desde `core`.
**Severidad:** Medio
**Impacto:** Acoplamiento sutil: cambios en validadores de path en `core` afectan la capa DB.
**Recomendación:** Extraer `validators` a un paquete transversal `sky_claw.validators`.

---

### LAY-05 — Import circular potencial app_context ↔ frontend_bridge
**Módulo y Línea(s):** `app_context.py:427`, `comms/frontend_bridge.py:44`
**Descripción y Evidencia:** Aunque el import está bajo `TYPE_CHECKING`, el constructor de `FrontendBridge` recibe `app_context: AppContext` como parámetro runtime.
**Severidad:** Medio
**Impacto:** Refactorización de `AppContext` requiere necesariamente revisar `FrontendBridge`.
**Recomendación:** Definir un protocolo `AppContextProtocol` en `core/contracts.py`.

---

### LAY-06 — Capa Tools depende de Core (PathResolutionService)
**Módulo y Línea(s):** Múltiples en `tools/*_service.py`
**Descripción y Evidencia:** `dyndolod_service.py`, `synthesis_service.py`, etc., importan `CoreEventBus`, `EventPayloads` y `PathResolutionService` desde `core`.
**Severidad:** Medio
**Impacto:** `PathResolutionService` no es un concepto fundamental; eleva la complejidad de `core`.
**Recomendación:** Mover `PathResolutionService` a `orchestrator/` y recibir solo un `PathResolver` protocolizado.

---

### LAY-07 — telegram_polling realiza import lazy de security
**Módulo y Línea(s):** `comms/telegram_polling.py:78`
**Descripción y Evidencia:** Import dentro del método `_run_loop()` en lugar de tope de módulo.
**Severidad:** Medio
**Impacto:** Dificulta el análisis estático de dependencias.
**Recomendación:** Inyectar `connector_factory` como parámetro de constructor.

---

### LAY-08 — Ausencia de barrera arquitectónica entre modes y subsistemas
**Módulo y Línea(s):** `modes/gui_mode.py:7-9`
**Descripción y Evidencia:** El modo GUI importa directamente `AppContext`, `SupervisorAgent` y `DashboardGUI`. No existe un `Container` de inyección de dependencias.
**Severidad:** Medio
**Impacto:** Cada modo debe conocer la firma exacta de construcción de `AppContext` y `SupervisorAgent`.
**Recomendación:** Crear un `AppFactory` en `sky_claw/bootstrap.py`.

---

## 3. Calidad de Código

### DB-001 — Tres esquemas mods mutuamente incompatibles
**Módulo y Línea(s):** `db/async_registry.py:37-71`, `db/registry.py:23-58`, `core/database.py:51-84`
**Descripción y Evidencia:** Existen tres definiciones de la tabla `mods` con columnas divergentes. `core/database.py` usa `id` (PK) y `name` (UNIQUE) sin `nexus_id`. Las registries usan `mod_id` (PK) y `nexus_id` (UNIQUE).
**Severidad:** Crítico
**Impacto:** Riesgo de escritura cruzada si algún futuro refactor une los agentes. Datos inconsistentes entre scraper y registry.
**Recomendación:** Unificar bajo single source of truth. Usar migraciones versionadas (`alembic` o tabla `schema_version`).

---

### SSP-001 — Verificación de checksum en restore nunca funciona
**Módulo y Línea(s):** `db/snapshot_manager.py:288-302`, `582-598`
**Descripción y Evidencia:** `create_snapshot` genera un hash truncado a 16 caracteres. `_extract_checksum_from_path` espera un prefijo de 64 caracteres, por lo que `expected_checksum` siempre es `None`.
**Severidad:** Crítico
**Impacto:** Restauración de snapshot corrupto se reportará como exitosa. El usuario pierde la garantía de rollback.
**Recomendación:** Persistir el checksum en un archivo `.meta` JSON sidecar o incluir el SHA256 completo en el nombre.

---

### DB-002 — upsert_mod single vs batch tienen semántica divergente
**Módulo y Línea(s):** `db/async_registry.py:74-98`, `204-224`
**Descripción y Evidencia:** `_UPSERT_MOD_SQL` (single) no actualiza `category`, `installed`, `enabled_in_vfs`. `_UPSERT_MOD_SQL_BATCH` sí lo hace.
**Severidad:** Alto
**Impacto:** Llamar a `upsert_mod` después de `set_vfs_status` puede revertir `installed/enabled` a 0.
**Recomendación:** Unificar ambos statements para que el single upsert también actualice todas las columnas.

---

### DB-004 — RuntimeError genérico capturado como corruption
**Módulo y Línea(s):** `db/async_registry.py:148-157`
**Descripción y Evidencia:** El bloque `except RuntimeError` asume que cualquier `RuntimeError` es integrity check fallido. Si algún helper lanza `RuntimeError` por otra razón, se renombrará el archivo y se perderá la BD.
**Severidad:** Alto
**Impacto:** Pérdida de datos silenciosa por falsos positivos de corrupción.
**Recomendación:** Usar una excepción custom `DatabaseCorruptionError(RuntimeError)` y capturar solo esa.

---

### JNL-001 — json_set requiere SQLite JSON1 no portable
**Módulo y Línea(s):** `db/journal.py:585-590`, `648-656`
**Descripción y Evidencia:** `fail_operation` y `mark_rolled_back` usan `json_set(COALESCE(metadata, '{}'), '$.error', ?)`. JSON1 no está habilitada por defecto en muchas builds de SQLite para Windows/Python <3.11.
**Severidad:** Alto
**Impacto:** El journal no puede registrar fallos en entornos Windows con SQLite estándar, perdiendo audit trail.
**Recomendación:** Reemplazar `json_set` por aplicación-side con `json.loads` / `json.dumps`.

---

### SSP-002 — Operaciones filesystem bloqueantes en métodos async
**Módulo y Línea(s):** `db/snapshot_manager.py:275-282`, `326`, `430-471`, `481-488`
**Descripción y Evidencia:** `restore_snapshot` usa `shutil.copy2`, `cleanup_old_snapshots` usa `shutil.rmtree`, `_enforce_size_limit` y `get_stats` usan `stat()` síncronos sin `asyncio.to_thread`.
**Severidad:** Alto
**Impacto:** Bloqueo del event loop durante I/O de archivos grandes.
**Recomendación:** Envolver en `asyncio.to_thread`.

```python
await asyncio.to_thread(shutil.copy2, target, backup_path)
await asyncio.to_thread(shutil.rmtree, date_dir)
```

---

### SSP-003 — cleanup_old_snapshots usa timezone local vs UTC
**Módulo y Línea(s):** `db/snapshot_manager.py:354-357`
**Descripción y Evidencia:** `create_snapshot` usa `datetime.now(UTC)`, pero `cleanup_old_snapshots` compara con `time.mktime(dir_time)` que asume timezone local.
**Severidad:** Medio
**Impacto:** Eliminación temprana o tardía de snapshots según la zona horaria del host.
**Recomendación:** `dir_dt = datetime.strptime(date_dir.name, "%Y-%m-%d").replace(tzinfo=timezone.utc)`

---

### DB-003 — Registry API incompleta respecto a AsyncModRegistry
**Módulo y Línea(s):** `db/registry.py` (completo)
**Descripción y Evidencia:** `ModRegistry` (síncrono-async thin wrapper) no expone `executemany`, `find_missing_masters_for_mods`, ni `DatabaseError` custom.
**Severidad:** Medio
**Impacto:** Fragmentación de lógica de negocio; duplicación inevitable de queries en callers.
**Recomendación:** Consolidar en `AsyncModRegistry` como canonical y deprecar `ModRegistry`.

---

### JNL-002 — No transacciones SQLite atómicas compuestas
**Módulo y Línea(s):** `db/journal.py:301-333`, `347-377`, `482-557`
**Descripción y Evidencia:** `begin_transaction` inserta una fila y hace `commit`. `begin_operation` inserta otra fila y hace `commit`. No se usa `BEGIN ... COMMIT` de SQLite para agrupar.
**Severidad:** Medio
**Impacto:** Estados huérfanos en la tabla `transactions`.
**Recomendación:** Exponer un context manager que envuelva múltiples operaciones en una transacción SQLite real.

---

### INT-01 — Instalación no atómica sin rollback en destino final
**Módulo y Línea(s):** `fomod/installer.py:197-258`, `340-409`
**Descripción y Evidencia:** La fase de copia a destino final (`_install_simple`, `_copy_resolved_files`) es no-atómica. Si falla a mitad de la copia, los archivos ya copiados permanecen sin mecanismo de rollback.
**Severidad:** Alto
**Impacto:** Instalaciones parciales que pueden corromper el perfil MO2.
**Recomendación:** Implementar patrón "escritura atómica con staging": copiar todo a un subdirectorio temporal, y solo al finalizar renombrar atómicamente.

---

### INT-02 — Symlinks en 7z/rar no mitigados
**Módulo y Línea(s):** `fomod/installer.py:92-130`
**Descripción y Evidencia:** `_extract_7z` usa `py7zr` sin desactivar extracción de symlinks. La librería puede restaurar symlinks absolutos que escapen el sandbox.
**Severidad:** Medio
**Impacto:** Posible bypass de path-sandbox vía symlink absolute.
**Recomendación:** Realizar un segundo pase recursivo post-extracción que invalide symlinks cuyo `resolve()` escape del destino.

---

### ASA-001 — Scripts Papyrus .psc no mapeados; .pas confundido
**Módulo y Línea(s):** `assets/asset_scanner.py:31-40`, `93-100`
**Descripción y Evidencia:** El comentario dice "scripts .pas/.pex", pero `.pas` es Pascal (xEdit). Los sources de Papyrus son `.psc` y no están en `ASSET_EXTENSIONS`.
**Severidad:** Crítico
**Impacto:** Un mod que distribuye sources `.psc` no será detectado como asset de script. El usuario no sabrá que un override de `.psc` puede invalidar la lógica del `.pex`.
**Recomendación:** `AssetType.SCRIPT: frozenset({".pex", ".psc"})`

---

### ASA-002 — Hash parcial en archivos >2 MB genera colisiones
**Módulo y Línea(s):** `assets/asset_scanner.py:240-261`
**Descripción y Evidencia:** Para archivos >2 MB solo hashea primer y último MB. Dos texturas DDS grandes con mismos headers/footers generarán el mismo checksum.
**Severidad:** Alto
**Impacto:** Falsos negativos en detección de overrides de assets grandes.
**Recomendación:** Usar SHA-256 completo siempre, o hash segmentado con salt de tamaño.

---

### SCA-001 — Record type SCPT obsoleto en Skyrim SE/AE
**Módulo y Línea(s):** `xedit/conflict_analyzer.py:31`, `scripts/list_all_conflicts.pas:24`
**Descripción y Evidencia:** `SCPT` pertenece al motor de Oblivion. En Skyrim SE/AE los scripts son assets externos `.pex`/`.psc`; los records relevantes son `SCEN` e `INFO`.
**Severidad:** Alto
**Impacto:** El LLM puede sugerir parches inútiles o ignorar conflictos en `SCEN`/`INFO` que rompen quests.
**Recomendación:** Reemplazar `SCPT` por `SCEN` e `INFO` en `DEFAULT_CRITICAL_TYPES`.

---

### SCA-004 — Parser no valida formato de FormID
**Módulo y Línea(s):** `xedit/conflict_analyzer.py:421-453`
**Descripción y Evidencia:** `parse_conflict_lines` asume 6 partes separadas por `|`. No valida que `form_id` sea hex de 8 dígitos. Si `editor_id` está vacío, el parser produce un `form_id` vacío.
**Severidad:** Alto
**Impacto:** Corrupción del reporte JSON enviado al LLM.
**Recomendación:**

```python
import re
_FORMID_RE = re.compile(r"^[0-9A-Fa-f]{8}$")
if not _FORMID_RE.match(form_id):
    logger.warning("Invalid FormID in line: %s", line)
    continue
```

---

### SCA-005 — .esp con flag ESL no contemplado
**Módulo y Línea(s):** `xedit/conflict_analyzer.py:201-202`
**Descripción y Evidencia:** Un `.esp` puede tener flag ESL y cargar en slot `0xFE` sin contar para el límite de 254 plugins. El validador solo mira la extensión del filename.
**Severidad:** Alto
**Impacto:** Falsos positivos de error que bloquean análisis de load orders válidas.
**Recomendación:** Delegar la verificación del flag ESL al script Pascal o a lectura del header del plugin.

---

### SCA-002 — No distingue prioridad intrínseca de .esm vs .esp
**Módulo y Línea(s):** `xedit/conflict_analyzer.py:188-221`
**Descripción y Evidencia:** `validate_load_order_limit` cuenta `.esm` y `.esp` en el mismo bucket "full". Los `.esm` siempre se cargan antes que cualquier `.esp`.
**Severidad:** Medio
**Impacto:** Recomendaciones de resolución inválidas para conflictos master→plugin.
**Recomendación:** Añadir flag `is_master` al `RecordConflict` y ajustar `suggest_resolution`.

---

### SCA-003 — suggest_resolution ignora semántica de CELL/WRLD persistentes
**Módulo y Línea(s):** `xedit/conflict_analyzer.py:325-331`
**Descripción y Evidencia:** Para conflictos `CELL`/`WRLD` sugiere "try reordering". Las celdas persistentes no resuelven conflictos por load order simple.
**Severidad:** Medio
**Impacto:** Usuario novato puede romper su savegame reordenando celdas persistentes.
**Recomendación:** Diferenciar entre celdas persistentes y temporales usando el flag de record.

---

## 4. Rendimiento

### RND-01 — Provider chat sin timeout bajo lock transaccional
**Módulo y Línea(s):** `agent/router.py:365-370`
**Descripción y Evidencia:** `async with self._provider_lock:` envuelve `await self._provider.chat(...)`. Si el proveedor se cuelga, el lock se mantiene indefinidamente, bloqueando todos los hot-swaps.
**Severidad:** Alto
**Impacto:** Denegación de servicio para chats concurrentes.
**Recomendación:** Envolver con `asyncio.wait_for`.

```python
async with self._provider_lock:
    response_data = await asyncio.wait_for(
        self._provider.chat(**chat_kwargs),
        timeout=120.0,
    )
```

---

### RND-02 — I/O síncrono bloqueante dentro de función async
**Módulo y Línea(s):** `agent/tools/external_tools.py:145`
**Descripción y Evidencia:** `save_local_config(local_cfg, config_path)` invoca `path.write_text(...)` de forma síncrona dentro de `async def setup_tools(...)`.
**Severidad:** Alto
**Impacto:** Congelamiento del event loop.
**Recomendación:** `await asyncio.to_thread(save_local_config, local_cfg, config_path)`

---

### RND-03 — zipfile.ZipFile bloqueante en resolve_fomod
**Módulo y Línea(s):** `fomod/installer.py:264-286` (invocado desde `system_tools.py`)
**Descripción y Evidencia:** `_extract_fomod_xml` → `_read_from_zip` abre `zipfile.ZipFile` y lee contenido de forma síncrona, llamado desde el async `resolve_fomod`.
**Severidad:** Alto
**Impacto:** Degradación de throughput; latencia impredecible.
**Recomendación:** `await asyncio.to_thread(fomod_installer._extract_fomod_xml, archive)`

---

### RND-04 — Progress callbacks fire-and-forget sin backpressure
**Módulo y Línea(s):** `agent/router.py:303`, `498`
**Descripción y Evidencia:** `asyncio.create_task(progress_callback(...))` no guarda referencias ni limita concurrencia.
**Severidad:** Medio
**Impacto:** Presión de memoria; excepciones no manejadas en tareas desconectadas.
**Recomendación:** Usar `asyncio.Semaphore` o `asyncio.TaskGroup` acotado.

---

### RND-05 — Sin semáforo para limitar sesiones concurrentes de chat()
**Módulo y Línea(s):** `agent/router.py:251-569`
**Descripción y Evidencia:** No existe límite de concurrencia en `chat()`. N llamadas simultáneas compiten por recursos.
**Severidad:** Medio
**Impacto:** Agotamiento de recursos bajo ráfaga.
**Recomendación:** Añadir `asyncio.Semaphore(N)` en `__init__`.

---

### RND-06 — Sin circuit breaker ante fallos en cascada
**Módulo y Línea(s):** `agent/providers.py:87-91`, `254-258`, `292-296`
**Descripción y Evidencia:** Tenacity reintenta hasta 5 veces con backoff exponencial, pero no hay circuit breaker.
**Severidad:** Medio
**Impacto:** Saturación innecesaria de conexiones salientes (thundering herd).
**Recomendación:** Integrar `pybreaker`.

```python
from pybreaker import CircuitBreaker
_llm_breaker = CircuitBreaker(fail_max=5, reset_timeout=60)
@_llm_breaker
@retry(...)
async def chat(self, ...): ...
```

---

### RND-07 — RetryError filtrado a callers sin manejo
**Módulo y Línea(s):** `agent/providers.py:87-91`
**Descripción y Evidencia:** Tras agotar reintentos, tenacity lanza `RetryError`. `router.py` no la captura.
**Severidad:** Medio
**Impacto:** Callers reciben `tenacity.RetryError` en lugar de la excepción original.
**Recomendación:** Añadir `reraise=True` al decorador.

---

### RND-08 — Body de request logueado en errores 4xx/5xx
**Módulo y Línea(s):** `agent/providers.py:272-280`
**Descripción y Evidencia:** En error HTTP se loguea `json.dumps(body)[:500]`, donde `body` contiene prompts del usuario.
**Severidad:** Medio
**Impacto:** Fuga de datos sensibles a archivos de log.
**Recomendación:** Loguear hash truncado del body en lugar del contenido.

---

### RND-09 — Crecimiento ilimitado de tabla chat_history
**Módulo y Línea(s):** `agent/router.py:575-583`
**Descripción y Evidencia:** `_save_message` inserta y hace `COMMIT` en cada turno, pero nunca poda registros antiguos.
**Severidad:** Bajo
**Impacto:** Degradación progresiva de I/O.
**Recomendación:** Añadir política de retención (ej. últimos 1000 mensajes por `chat_id`).

---

### RND-10 — HTTP 408 no se reintenta
**Módulo y Línea(s):** `agent/providers.py:45-49`
**Descripción y Evidencia:** `_should_retry` retorna `False` para status 408.
**Severidad:** Bajo
**Impacto:** Fallos espurios en redes inestables.
**Recomendación:** Incluir `exc.status == 408`.

---

### RND-11 — Uso de lambdas para envolver corutinas
**Módulo y Línea(s):** `agent/tools/__init__.py:249-404`
**Descripción y Evidencia:** Los handlers async se envuelven en `lambda`, oscureciendo el nombre en stack traces.
**Severidad:** Bajo
**Impacto:** Mantenibilidad reducida; trazas de error opacas.
**Recomendación:** Usar `functools.partial` con funciones nombradas.

---

## 5. Testing

### TST-001 — Motor Tree-of-Thought sin cobertura de tests
**Módulo y Línea(s):** `reasoning/tot.py`, `reasoning/engine.py`, `reasoning/strategies.py`
**Descripción y Evidencia:** Búsqueda recursiva en `tests/` con patrones `tot`, `tree_of_thought`, `reasoning` no encontró tests específicos.
**Severidad:** Crítico
**Impacto:** Bugs en `CycleDetector`, `PruningPolicy` o estrategias de búsqueda pueden propagar decisiones erróneas sin ser detectados.
**Recomendación:** Crear `tests/test_tot_engine.py` cubriendo generación de thoughts, detección de ciclos, pruning por score, y cada estrategia (BFS/DFS/MCTS).

---

### TST-002 — GUI NiceGUI sin cobertura de tests
**Módulo y Línea(s):** `gui/sky_claw_gui.py`, `gui/app.py`, `gui/dashboard.py`, `gui/setup_wizard.py`
**Descripción y Evidencia:** Ningún test encontrado. Los únicos tests de frontend son para el Operations Hub WebSocket.
**Severidad:** Alto
**Impacto:** Regresiones visuales o de flujo de configuración no se detectarán en CI.
**Recomendación:** Implementar tests unitarios para `SetupWizardModal._validate_and_save` y al menos un test de integración con NiceGUI Test Client.

---

### TST-003 — Gateway Node.js sin cobertura de tests
**Módulo y Línea(s):** `gateway/server.js`, `gateway/telegram_gateway.js`
**Descripción y Evidencia:** El directorio `gateway/` no contiene subdirectorio `test/`.
**Severidad:** Alto
**Impacto:** Rotura del canal Telegram/WebSocket sin alerta.
**Recomendación:** Agregar tests con Jest/Mocha para `server.js` y `telegram_gateway.js`.

---

### TST-004 — CLI sin cobertura de tests
**Módulo y Línea(s):** `modes/cli_mode.py`
**Descripción y Evidencia:** No existen tests para el modo interactivo ni oneshot.
**Severidad:** Alto
**Impacto:** CLI roto en releases sin detección.
**Recomendación:** Crear `tests/test_cli_mode.py` mockeando `input()` y `ctx.router.chat`.

---

### TST-005 — conftest.py vacío
**Módulo y Línea(s):** `tests/conftest.py`
**Descripción y Evidencia:** Contiene solo 3 líneas de comentario. No hay fixtures compartidas.
**Severidad:** Medio
**Impacto:** Duplicación de código de setup en múltiples archivos de test.
**Recomendación:** Migrar fixtures reutilizables (motor SQLite, mock de router) a `conftest.py`.

---

### TST-006 — Desbalance hacia unitarios; falta tests E2E
**Módulo y Línea(s):** `tests/` (general)
**Descripción y Evidencia:** Mayoría unitarios con mocks totales. No hay tests E2E con navegador real.
**Severidad:** Medio
**Impacto:** Fallos de integración real (WebSocket, DOM, eventos) no se detectan.
**Recomendación:** Agregar al menos un test E2E de Playwright para `frontend/index.html`.

---

### TST-007 — Escasa parametrización
**Módulo y Línea(s):** `tests/` (general)
**Descripción y Evidencia:** No se observa uso sistemático de `@pytest.mark.parametrize`.
**Severidad:** Bajo
**Impacto:** Test suites más extensas de lo necesario.
**Recomendación:** Aplicar `@pytest.mark.parametrize` en validación de campos, matching de patrones de red, etc.

---

## 6. Integraciones Externas

### GTG-03 (repetido como integración) — Sin rate limiting en mensajes entrantes de Telegram
**Módulo y Línea(s):** `gateway/telegram_gateway.js:173-206`
**Descripción y Evidencia:** (Ver sección 1, GTG-03).
**Severidad:** Alto
**Impacto:** DoS contra el daemon.
**Recomendación:** Token bucket por `user_id`.

---

### TG-01 — Mensaje de progreso genérico durante /update_mods
**Módulo y Línea(s):** `comms/telegram.py:271-272`
**Descripción y Evidencia:** No hay actualizaciones de progreso periódicas ni indicador de "X de Y mods verificados".
**Severidad:** Medio
**Impacto:** En ciclos largos el usuario no tiene feedback de avance.
**Recomendación:** Enviar mensajes de progreso cada N mods procesados.

---

### GWS-01 (repetido) — Servidor agente siempre en plaintext
**Módulo y Línea(s):** `gateway/server.js:187`, `243`
**Descripción y Evidencia:** (Ver sección 1, GWS-01).
**Severidad:** Medio
**Impacto:** Downgrade forzado a ws://.
**Recomendación:** Reutilizar `tlsCreds` para el agente.

---

### RND-06 (repetido) — Sin circuit breaker ante fallos en cascada
**Módulo y Línea(s):** `agent/providers.py:87-91`
**Descripción y Evidencia:** (Ver sección 4, RND-06).
**Severidad:** Medio
**Impacto:** Thundering herd contra APIs externas.
**Recomendación:** Integrar `pybreaker`.

---

## 7. Configuración

### CLI-01 — CLI extremadamente básico sin argument parsing
**Módulo y Línea(s):** `modes/cli_mode.py` (completo)
**Descripción y Evidencia:** No usa `argparse`. No hay `--help`, `--version`, `--config`, `--verbose`. Solo un loop `input()`.
**Severidad:** Crítico
**Impacto:** Imposibilidad de automatizar tareas vía CLI (scripts, CI, cron).
**Recomendación:** Implementar `argparse` con subcomandos: `sky-claw chat`, `sky-claw sync`, `sky-claw update`.

---

### CLI-02 — Sin historial ni autocompletado
**Módulo y Línea(s):** `modes/cli_mode.py:23`
**Descripción y Evidencia:** `input("you> ")` plano. Sin `readline`, sin historial.
**Severidad:** Alto
**Impacto:** UX pobre para usuarios avanzados.
**Recomendación:** Integrar `readline` o `prompt_toolkit`.

---

### CLI-03 — Captura de excepciones muy estrecha
**Módulo y Línea(s):** `modes/cli_mode.py:34-35`
**Descripción y Evidencia:** Solo captura `RuntimeError`. No captura `Exception`, `aiohttp.ClientError`, `KeyboardInterrupt`.
**Severidad:** Medio
**Impacto:** Errores inesperados crashean el CLI sin información diagnóstica.
**Recomendación:** Ampliar a `except Exception as exc:` con `logger.exception`.

---

### SUP-07 (repetido) — Dependencia directa de variables de entorno
**Módulo y Línea(s):** `orchestrator/supervisor.py:318-320`
**Descripción y Evidencia:** (Ver sección 2).
**Severidad:** Medio
**Impacto:** Comportamiento no determinista entre entornos.
**Recomendación:** Inyectar `PathsConfig`.

---

### SEC-12 (repetido) — Token en texto plano en disco
**Módulo y Línea(s):** `security/auth_token_manager.py:60-77`
**Descripción y Evidencia:** (Ver sección 1).
**Severidad:** Medio
**Impacto:** Robo de token por procesos locales.
**Recomendación:** Cifrar token o usar Named Pipes.

---

## 8. Dominio de Skyrim

### SCA-001 — Record type SCPT obsoleto en Skyrim SE/AE
**Módulo y Línea(s):** `xedit/conflict_analyzer.py:31`
**Descripción y Evidencia:** (Ver sección 3).
**Severidad:** Alto
**Impacto:** Sugerencias de parches inútiles.
**Recomendación:** Reemplazar `SCPT` por `SCEN` e `INFO`.

---

### SCA-004 — Parser no valida formato de FormID
**Módulo y Línea(s):** `xedit/conflict_analyzer.py:421-453`
**Descripción y Evidencia:** (Ver sección 3).
**Severidad:** Alto
**Impacto:** Corrupción del reporte JSON.
**Recomendación:** Validar con regex `^[0-9A-Fa-f]{8}$`.

---

### SCA-005 — .esp con flag ESL no contemplado
**Módulo y Línea(s):** `xedit/conflict_analyzer.py:201-202`
**Descripción y Evidencia:** (Ver sección 3).
**Severidad:** Alto
**Impacto:** Falsos positivos en load orders válidas.
**Recomendación:** Verificar flag ESL en header del plugin.

---

### ASA-001 — Scripts Papyrus .psc no mapeados
**Módulo y Línea(s):** `assets/asset_scanner.py:31-40`
**Descripción y Evidencia:** (Ver sección 3).
**Severidad:** Crítico
**Impacto:** Overrides de sources no detectados.
**Recomendación:** `AssetType.SCRIPT: frozenset({".pex", ".psc"})`

---

### ASA-002 — Hash parcial en archivos >2 MB
**Módulo y Línea(s):** `assets/asset_scanner.py:240-261`
**Descripción y Evidencia:** (Ver sección 3).
**Severidad:** Alto
**Impacto:** Colisiones probables en texturas 4K.
**Recomendación:** Usar SHA-256 completo.

---

### SCA-002 — No distingue prioridad intrínseca de .esm vs .esp
**Módulo y Línea(s):** `xedit/conflict_analyzer.py:188-221`
**Descripción y Evidencia:** (Ver sección 3).
**Severidad:** Medio
**Impacto:** Recomendaciones de resolución inválidas.
**Recomendación:** Añadir flag `is_master` al `RecordConflict`.

---

### SCA-003 — suggest_resolution ignora semántica de CELL/WRLD persistentes
**Módulo y Línea(s):** `xedit/conflict_analyzer.py:325-331`
**Descripción y Evidencia:** (Ver sección 3).
**Severidad:** Medio
**Impacto:** Riesgo de romper savegames.
**Recomendación:** Diferenciar celdas persistentes de temporales.

---

## 9. Interfaces y UX

### GUI-02 — _chat_controller usado sin null-check
**Módulo y Línea(s):** `gui/sky_claw_gui.py:335`
**Descripción y Evidencia:** `_chat_controller` se declara como `None` globalmente y solo se inicializa en `setup_app()`.
**Severidad:** Alto
**Impacto:** `AttributeError` si `main_page()` se ejecuta antes de `setup_app()`.
**Recomendación:** `if _chat_controller is None: return []`

---

### GUI-03 — _open_settings_dialog no definido
**Módulo y Línea(s):** `gui/dashboard.py:205`, `gui/app.py:648`
**Descripción y Evidencia:** `_navigate()` llama a `self._open_settings_dialog()` pero el método no existe.
**Severidad:** Alto
**Impacto:** Click en "AJUSTES" lanza `AttributeError`.
**Recomendación:** Implementar el método o deshabilitar el botón.

---

### FE-02 — crypto.randomUUID con fallback de baja entropía
**Módulo y Línea(s):** `frontend/js/app.js:293`, `399`
**Descripción y Evidencia:** Fallback `Math.random().toString(36).substring(7)` genera IDs de ~5-7 caracteres.
**Severidad:** Alto
**Impacto:** Colisión de IDs de mensaje; deduplicación incorrecta.
**Recomendación:** `Date.now().toString(36) + Math.random().toString(36).slice(2)` o `crypto.getRandomValues`.

---

### GUI-01 — Datos de estadísticas hardcodeados
**Módulo y Línea(s):** `gui/app.py:535-536`, `gui/dashboard.py:87-88`
**Descripción y Evidencia:** Valores como `"116"` y `"3,130 ops/s"` son estáticos.
**Severidad:** Medio
**Impacto:** Desconfianza del usuario al ver métricas ficticias.
**Recomendación:** Reemplazar por lectura de `AppState` o mostrar `--`.

---

### GUI-04 — Manejo de errores de keyring genérico
**Módulo y Línea(s):** `gui/setup_wizard.py:318-319`, `gui/app.py:388-399`
**Descripción y Evidencia:** `keyring.set_password()` dentro de `try/except Exception` genérico.
**Severidad:** Medio
**Impacto:** Usuario no entiende por qué no puede guardar credenciales.
**Recomendación:** Capturar `keyring.errors.KeyringError` y mostrar mensaje orientativo.

---

### FE-01 — Backoff de reconexión WS lineal
**Módulo y Línea(s):** `frontend/js/app.js:22-23`, `139-140`
**Descripción y Evidencia:** Factor 1.5 sin jitter, vs. exponencial con jitter en `websocket-client.js`.
**Severidad:** Medio
**Impacto:** Mayor carga en el servidor tras reinicio.
**Recomendación:** Unificar ambos clientes o copiar la lógica exponencial+jitter.

---

### FE-03 — Race condition en sendCommand
**Módulo y Línea(s):** `frontend/js/app.js:284-306`
**Descripción y Evidencia:** Verifica `socket.readyState` pero no hay atomicidad entre la verificación y `socket.send()`.
**Severidad:** Medio
**Impacto:** Excepción no capturada si el socket se cierra entre ambas líneas.
**Recomendación:** Envolver `socket.send()` en `try/catch`.

---

### GUI-05 — Reactividad de _ReactiveVar manual/falsa
**Módulo y Línea(s):** `gui/sky_claw_gui.py:68-88`
**Descripción y Evidencia:** `_ReactiveVar` es un box mutable simple. No dispara re-renders automáticos de NiceGUI.
**Severidad:** Bajo
**Impacto:** Cambios de estado no se reflejan sin llamadas manuales a `ui.update()`.
**Recomendación:** Migrar a `ui.reactive()` o `ui.bind()` nativos de NiceGUI.

---

## 🎯 Top 10 Correcciones Priorizadas

| # | Hallazgo | Riesgo | Esfuerzo | Justificación |
|---|---|---|---|---|
| 1 | **SSP-001**: Verificación checksum restore rota (nunca verifica) | 🔴 Crítico | 🟢 Bajo | Cambio localizado: persistir checksum en sidecar JSON o nombre de archivo. Sin esto, el rollback es una ilusión. |
| 2 | **ARC-01**: `database.close()` no-atómico en `app_context.py` | 🔴 Crítico | 🟢 Bajo | `try/finally` o two-phase commit. Previene corrupción de estado de vida en reintentos. |
| 3 | **ASA-001**: `.psc` no mapeado; dominio Skyrim roto | 🔴 Crítico | 🟢 Bajo | Una línea de cambio en `ASSET_EXTENSIONS`. Impacta directamente en la precisión del sistema para usuarios reales. |
| 4 | **SUP-01 / SUP-02**: Refactor God Object `SupervisorAgent` | 🔴 Crítico | 🔴 Alto | Requiere Strangler Fig, pero bloquea toda evolución arquitectónica futura. Máximo retorno a mediano plazo. |
| 5 | **DB-001**: Unificar esquemas `mods` incompatibles | 🔴 Crítico | 🟡 Medio | Migración de esquemas con `alembic` o `schema_version`. Previene corrupción de datos silenciosa. |
| 6 | **SEC-03**: Taint tracking roto en `purple_scanner.py` | 🟠 Alto | 🟢 Bajo | Fix de 3 líneas en lógica AST. Sin él, el análisis estático de seguridad es unreliable. |
| 7 | **RND-02 / RND-03**: I/O síncrono bloqueante en async (tools + fomod) | 🟠 Alto | 🟢 Bajo | Envolver en `asyncio.to_thread`. Restaura la promesa de throughput del event loop. |
| 8 | **GTG-03**: Rate limiting Telegram→Daemon ausente | 🟠 Alto | 🟢 Bajo | Token bucket de ~20 líneas en JS. Previene DoS trivial contra el daemon. |
| 9 | **SCA-004 / SCA-005**: Validación FormID + ESL flags | 🟠 Alto | 🟡 Medio | Mejora drásticamente la calidad del análisis de conflictos y reduce falsos positivos. |
| 10 | **CLI-01 / CLI-02**: CLI sin argparse ni autocompletado | 🔴 Crítico | 🟡 Medio | Puerta de entrada para usuarios avanzados y automatización. Esfuerzo moderado, alto impacto UX. |

---

*Fin del Informe de Auditoría Integral — Sky-Claw*
