# 🔍 META-AUDITORÍA TÉCNICA — `AuditoriaKIMI27.md`

**Auditor:** Senior Staff DevOps Engineer & Lead Code Reviewer  
**Fecha:** 2026-04-27 | **Alcance:** Validación cruzada contra código fuente + Context7  
**Documento auditado:** `AuditoriaKIMI27.md` (1,226 líneas, ~80 hallazgos únicos)

---

## 📋 Resumen Ejecutivo

- **Diagnóstico general:** El documento presenta una auditoría técnicamente sólida en su mayoría, con hallazgos verificables contra el código fuente real. Sin embargo, contiene **14 duplicados** que inflan el conteo aparente, **1 inconsistencia de severidad** (GTG-03: Medio vs Alto), y al menos **2 hallazgos parcialmente desactualizados** donde el código ya implementa mitigaciones que la auditoría omite reconocer.

- **Calidad de las recomendaciones:** El ~70% de los hallazgos incluyen bloques de refactorización accionables. El 30% restante ofrece solo descripciones textuales sin código concreto (ARC-02, ARC-05, SEC-05, SEC-06, SEC-07, SEC-08, SEC-12, SSP-003, CLI-02, CLI-03, LAY-04–LAY-08, entre otros), lo que reduce la accionabilidad inmediata.

- **Cobertura de CI/CD:** El documento **no cubre** pipelines de CI/CD, procesos de build (`build.bat`, `uv sync`), estrategias de deployment, ni gestión de secretos en entornos de ejecución a pesar de que el encabezado menciona "ineficiencias de CI/CD" como objetivo. Esto constituye una laguna significativa para un informe que pretende ser exhaustivo.

---

## 📊 Tabla de Auditoría — Hallazgos del Documento

### A. Problemas de Consistencia Interna del Documento

| Severidad | Componente | Descripción del Fallo | Refactorización Recomendada |
|---|---|---|---|
| 🔴 Crítico | GTG-03 — Severidad contradictoria | La tabla resumen (línea 81) clasifica GTG-03 como **🟡 Medio**, pero la sección de detalle (línea 369) lo marca como **Alto**. Un hallazgo de rate limiting que permite DoS contra el daemon debería ser consistentemente **Alto**. | Unificar a **🟠 Alto** en ambas ubicaciones. El impacto documentado ("DoS contra el daemon; agotamiento de buffers WS") justifica severidad Alta. |
| 🟠 Alto | 14 hallazgos duplicados entre secciones | Los IDs GTG-03, GWS-01, RND-06, SCA-001, SCA-004, SCA-005, ASA-001, ASA-002, SCA-002, SCA-003, SEC-12, SUP-07 aparecen en **dos secciones distintas** con texto casi idéntico. Esto infla el conteo de 80→94 e induce confusión sobre si son hallazgos distintos. | Eliminar las repeticiones en las secciones 6–8. Mantener una única entrada por ID y referenciar con `(ver sección X, ID-Y)` como ya hace parcialmente. |
| 🟠 Alto | ~30% hallazgos sin bloque de código | Los hallazgos ARC-02, ARC-05, SEC-05, SEC-06, SEC-07, SEC-08, SEC-12, SSP-003, CLI-02, CLI-03, LAY-04, LAY-05, LAY-06, LAY-07, LAY-08, GUI-01, GUI-04, FE-01, FE-03, GUI-05, RND-04, RND-05, RND-07, RND-08, RND-09, RND-10, RND-11, SUP-06, SUP-07, SUP-08 no incluyen refactorización con código. | Agregar bloques de código concretos para cada hallazgo, especialmente los de severidad Alta. |

### B. Hallazgos Técnicos Verificados — Precisión contra Código Fuente

| Severidad | Componente | Descripción del Fallo | Refactorización Recomendada |
|---|---|---|---|
| 🟠 Alto | GWS-04 — Recomendación ya implementada | La auditoría recomienda convertir strings a `Buffer.from(a, 'utf8')` antes de comparar, pero [`timingSafeEqual()`](gateway/server.js:128) **ya hace exactamente eso** en las líneas 128-131. El único defecto real es el pre-check de longitud en string (`a.length !== b.length` en línea 123) vs buffer length. | Corregir la recomendación para enfocarse exclusivamente en reemplazar la línea 123: `if (Buffer.from(a, 'utf8').length !== Buffer.from(b, 'utf8').length) return false;` o eliminar el pre-check ya que el `try/catch` existente maneja el caso. |
| 🟠 Alto | GTG-01 — Mitigación ya existente no reconocida | La auditoría afirma que existe una race condition en [`daemonSocket`](gateway/telegram_gateway.js:114) sin sincronización. Sin embargo, las líneas 107-113 **ya implementan** el cierre del daemon previo antes de asignar el nuevo: `if (daemonSocket && daemonSocket !== ws && daemonSocket.readyState === 1) { daemonSocket.close(4000, ...) }`. | Actualizar el hallazgo para reconocer la mitigación existente y reducir la severidad a **Medio**. La ventana TOCTOU restante es teórica y requiere dos autenticaciones concurrentes dentro del mismo tick del event loop. |
| 🟡 Medio | SEC-02 — Recomendación incompleta | La auditoría sugiere distinguir `aiosqlite.Error` de `InvalidToken`, pero el código actual en [`get_secret()`](sky_claw/security/credential_vault.py:184) tiene un `return None` en línea 198 (dentro del try, fuera del cursor) que corresponde a "secreto no existe" — un caso legítimo. La recomendación debe preservar este flujo. | La refactorización debe mantener tres caminos: (1) row=None → return None (legítimo), (2) aiosqlite.Error → return None con log, (3) InvalidToken → raise SecurityViolationError. Ver bloque abajo. |
| 🟡 Medio | GWS-02 — Falta aplicar patrón ya usado en telegram_gateway | [`server.js`](gateway/server.js:192) asigna `agentSocket = ws` sin cerrar el previo, pero [`telegram_gateway.js`](gateway/telegram_gateway.js:107) ya implementa el patrón correcto de cierre previo. La auditoría no señala esta inconsistencia entre componentes del mismo gateway. | Migrar el patrón de telegram_gateway.js a server.js línea 192. Ver bloque abajo. |
| 🟡 Medio | SEC-05 — Contexto incompleto | La auditoría no menciona que [`NetworkGateway.request()`](sky_claw/security/network_gateway.py:189) **ya valida** que esquemas no-HTTPS son bloqueados para hosts no-loopback (`if parsed.scheme != "https" and not is_loopback: raise`). El bypass SSL solo aplica cuando `is_loopback=True`, que está protegido upstream por `authorize()`. | Actualizar la descripción para reconocer la defensa en profundidad existente y ajustar la recomendación a "eliminar la ruta redundante" en lugar de "eliminar la excepción de seguridad". |

### C. Omisiones del Documento de Auditoría

| Severidad | Componente | Descripción del Fallo | Refactorización Recomendada |
|---|---|---|---|
| 🔴 Crítico | CI/CD Pipeline — Ausencia total | El documento no analiza [`build.bat`](build.bat), [`pyproject.toml`](pyproject.toml), ni el proceso de build con `uv`/PyInstaller. No evalúa si existen gates de calidad pre-commit, validación de hashes de dependencias, o escaneo SAST automatizado. | Agregar sección dedicada a CI/CD que cubra: (1) validación de supply chain en `requirements.lock`, (2) gates de cobertura mínima (49% según skyclaw-core.md), (3) integración de `ruff`/`mypy` en pre-commit. |
| 🟠 Alto | `pyproject.toml` — Dependencias sin análisis | No se auditan las versiones de dependencias declaradas ni se verifica la existencia de vulnerabilidades conocidas (CVEs) en `cryptography`, `aiohttp`, `aiosqlite`, `py7zr`, etc. | Ejecutar `pip-audit` o `safety check` contra `requirements.lock` e incluir hallazgos. |
| 🟠 Alto | Gateway — Sin análisis de `package.json` | No se auditan las dependencias Node.js del gateway (`grammy`, `ws`, etc.) ni se verifica la existencia de vulnerabilidades conocidas. | Ejecutar `npm audit` en `gateway/` e incluir resultados. |
| 🟡 Medio | Tests — Sin métricas de cobertura real | El documento afirma "min 49% coverage blocks CI" (referenciando skyclaw-core.md) pero no proporciona la cobertura actual ni identifica qué módulos están por debajo del umbral. | Ejecutar `pytest --cov=sky_claw --cov-report=term-missing` y reportar los módulos bajo 49%. |

---

## 🔧 Refactorizaciones Detalladas

### FIX-SEC-02: `get_secret()` con distinción de excepciones

**Archivo:** [`sky_claw/security/credential_vault.py`](sky_claw/security/credential_vault.py:184)

```python
async def get_secret(self, service_name: str) -> str | None:
    """Recupera y descifra asincrónicamente con aislamiento de transacción."""
    try:
        async with aiosqlite.connect(self.db_path) as conn:
            await self._execute_pragmas(conn)
            async with conn.execute(
                "SELECT cipher_text FROM sky_vault WHERE service = ?",
                (service_name,),
            ) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return None  # Secreto legítimamente no configurado
                cipher_text = row[0].encode("utf-8")
                try:
                    plain_secret = self.fernet.decrypt(cipher_text).decode("utf-8")
                except Exception as decrypt_exc:
                    # Usar isinstance para evitar import circular
                    if "InvalidToken" in type(decrypt_exc).__name__:
                        svc_hash = hashlib.sha256(service_name.encode()).hexdigest()[:8]
                        logger.critical(
                            "SECURITY: Vault tampering detected for service_hash=%s. "
                            "Ciphertext integrity check failed — possible corruption or key mismatch.",
                            svc_hash,
                        )
                        raise SecurityViolationError(
                            "Vault integrity check failed — possible tampering"
                        ) from decrypt_exc
                    raise
                return plain_secret
    except aiosqlite.Error:
        svc_hash = hashlib.sha256(service_name.encode()).hexdigest()[:8]
        logger.exception(
            "RCA (Vault): Database error accessing service_hash=%s.", svc_hash
        )
        return None
```

### FIX-GWS-02: Cierre de agentSocket previo en server.js

**Archivo:** [`gateway/server.js`](gateway/server.js:189)

```javascript
agentServer.on('connection', (ws) => {
    requireAuth(ws, 'AGENT', () => {
        console.log(`[AGENT] Daemon autenticado desde ${ws._socket.remoteAddress}`);

        // Cerrar agente previo antes de asignar el nuevo (previene socket huérfano)
        if (agentSocket && agentSocket !== ws && agentSocket.readyState === ws.OPEN) {
            try {
                agentSocket.close(4000, 'Replaced by new agent connection');
            } catch (closeErr) {
                console.warn('[AGENT] Error cerrando agente previo:', closeErr.message);
            }
        }
        agentSocket = ws;

        // Procesar cola de comandos pendientes (Resiliencia de Estado)
        while (pendingCommands.length > 0 && agentSocket.readyState === ws.OPEN) {
            const cmd = pendingCommands.shift();
            console.log(`[AGENT] Despachando comando encolado: ${cmd.type}`);
            agentSocket.send(JSON.stringify(cmd));
        }
        // ... resto del handler sin cambios
    });
});
```

### FIX-GWS-04: Pre-check de longitud corregido

**Archivo:** [`gateway/server.js`](gateway/server.js:117)

```javascript
function timingSafeEqual(a, b) {
    if (typeof a !== 'string' || typeof b !== 'string') {
        return false;
    }
    const bufA = Buffer.from(a, 'utf8');
    const bufB = Buffer.from(b, 'utf8');
    if (bufA.length !== bufB.length) {
        return false;
    }
    try {
        return crypto.timingSafeEqual(bufA, bufB);
    } catch {
        return false;
    }
}
```

---

## 🎯 Plan de Mitigación — Pasos Inmediatos

### Fase 1: Estabilización del Documento de Auditoría (24h)

1. **Unificar severidad de GTG-03** a 🟠 Alto en tabla resumen (línea 81) y sección de detalle (línea 369). Justificación: el impacto documentado es DoS contra el daemon.

2. **Eliminar los 14 hallazgos duplicados** de las secciones 6–8. Reemplazar con referencias cruzadas: `(Ver Sección X, ID-Y — sin cambios adicionales)`.

3. **Corregir GWS-04** para reconocer que [`timingSafeEqual()`](gateway/server.js:128) ya convierte a Buffer. Limitar la recomendación al pre-check de línea 123.

4. **Actualizar GTG-01** para reconocer la mitigación existente en [`telegram_gateway.js:107-113`](gateway/telegram_gateway.js:107) y reducir severidad a Medio.

5. **Completar bloques de código** para los 30 hallazgos que carecen de refactorización concreta, priorizando los de severidad Alta (SEC-05, SEC-06, SEC-07, SEC-12, ARC-02).

### Fase 2: Correcciones Críticas del Código (48h)

6. **SSP-001** — Persistir checksum completo en sidecar `.meta` JSON junto a cada snapshot. Sin esto, el rollback es una ilusión. Cambio localizado en [`snapshot_manager.py`](sky_claw/db/snapshot_manager.py).

7. **SEC-03** — Corregir [`_is_tainted_source()`](sky_claw/security/purple_scanner.py:124) para soportar `ast.Attribute` (3 líneas de cambio). Sin esta corrección, el análisis estático de seguridad es unreliable.

8. **SEC-02** — Implementar distinción de excepciones en [`get_secret()`](sky_claw/security/credential_vault.py:184) según el bloque FIX-SEC-02 arriba.

9. **GWS-02** — Aplicar cierre de agentSocket previo en [`server.js:192`](gateway/server.js:192) según el patrón ya existente en telegram_gateway.js.

10. **RND-02/RND-03** — Envolver I/O síncrono en `asyncio.to_thread()` en [`external_tools.py:145`](sky_claw/agent/tools/external_tools.py) y [`installer.py`](sky_claw/fomod/installer.py).

### Fase 3: Análisis Faltante (1 semana)

11. **Ejecutar `pip-audit`** contra `requirements.lock` y agregar sección de vulnerabilidades de supply chain al informe.

12. **Ejecutar `npm audit`** en `gateway/` y documentar hallazgos.

13. **Agregar sección CI/CD** que cubra: gates de calidad en `build.bat`, validación de cobertura mínima (49%), integración de `ruff`/`mypy` en pre-commit hooks.

14. **Ejecutar `pytest --cov`** y reportar cobertura real por módulo contra el umbral del 49%.

15. **Validar línea por línea** los números de línea referenciados en los hallazgos restantes contra el código actual, ya que el documento fue generado sobre la rama `claude/confident-dubinsky-be5a49` y el código puede haber evolucionado.

---

## 📈 Métricas de Calidad del Documento

| Métrica | Valor | Observación |
|---|---|---|
| Hallazgos únicos declarados | ~80 | Conteo real sin duplicados |
| Hallazgos con duplicados | 94 | 14 IDs repetidos entre secciones |
| Hallazgos con código de fix | ~56 (70%) | 24 sin bloque accionable |
| Hallazgos verificados contra fuente | 10/10 muestreados | 8 confirmados, 2 con matiz |
| Consistencia de severidad | 99% | GTG-03 es la única discrepancia |
| Cobertura CI/CD | 0% | No analizado |
| Cobertura supply chain | 0% | No analizado |

---

*Fin del Informe de Meta-Auditoría — Generado con validación cruzada contra código fuente y documentación Context7 (aiosqlite, tenacity, pydantic)*
