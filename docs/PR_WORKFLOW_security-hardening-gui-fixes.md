# Flujo de Trabajo: Pull Request — Security Hardening & GUI Critical Fixes

> **Repositorio**: `https://github.com/FacundoSu1986/Sky-Claw.git`
> **Fecha**: 2026-04-23
> **Rama base**: `main`
> **Rama feature**: `feature/security-hardening-gui-fixes`

---

## 1. Estado Actual del Repositorio (Pre-Workflow)

### Remotes
```
origin → https://github.com/FacundoSu1986/Sky-Claw.git (fetch/push)
```

### Branch activa
```
claude/fix-migration-parity-gaps  (HEAD = 1c72eca)
```

### HEAD vs origin/main
- `HEAD` (`1c72eca`) es ancestro de `origin/main` (`1f779fa`)
- La rama actual está **detrás** de `origin/main` — sin commits propios por delante
- Todos los cambios están **sin commitear** en el working tree

### Working Tree — Resumen de cambios

| Categoría | Archivos | Líneas (+/-) |
|-----------|----------|-------------|
| Security hardening | 8 archivos en `sky_claw/security/` | +97/-43 |
| GUI critical fixes | `sky_claw/gui/app.py` | +63/-4 |
| Build config | `sky_claw.spec` | +16 |
| Test reliability | `tests/test_event_bus_dlq_integration.py` | +22/-8 |
| Config/Metadata | `.agents/...`, `.antigravity/...` | +13/-2 |
| **Total** | **13 archivos** | **+165/-73** |

---

## 2. Secuencia Completa de Comandos Git

### Paso 0 — Backup de seguridad (siempre antes de operaciones destructivas)

```bash
# Crear rama de respaldo del estado actual
git branch backup/pre-pr-snapshot-20260423
```

### Paso 1 — Sincronizar con origin/main

```bash
# Fetch latest del remote
git fetch origin

# Crear nueva rama feature desde origin/main (HEAD actualizado)
git checkout -b feature/security-hardening-gui-fixes origin/main
```

### Paso 2 — Commit 1: Security — PII protection & regex fixes

```bash
# Stage archivos de seguridad con cambios de protección de PII y regex
git add sky_claw/security/credential_vault.py
git add sky_claw/security/agent_guardrail.py
git add sky_claw/security/text_inspector.py

git commit -m "fix(security): harden PII logging and fix regex/parameter accuracy

- credential_vault: hash service_name with SHA-256 before logging to
  prevent PII leakage in error messages
- agent_guardrail: tighten credit-card regex from greedy (\\d[ -]?){13,16}
  to grouped (\\d{4}[ -]?){3}\\d{1,4} — reduces false positives
- text_inspector: rename max_bytes → max_chars for semantic correctness
  (Python str length ≠ byte length)

Refs: SKY-SEC-001, SKY-SEC-002"
```

### Paso 3 — Commit 2: Security — governance singleton & HMAC key protection

```bash
# Stage governance y path_validator
git add sky_claw/security/governance.py
git add sky_claw/security/path_validator.py

git commit -m "fix(security): governance singleton conflict detection and path validator hardening

- governance: detect base_path conflicts in singleton factory (raises
  RuntimeError instead of silently returning stale instance)
- governance: restrict HMAC key file to owner-only permissions via
  restrict_to_owner() to prevent local key extraction
- path_validator: validate required path arguments in decorator before
  calling validate() — prevents silent None passthrough

Refs: SKY-SEC-003"
```

### Paso 4 — Commit 3: Security — purple_scanner SoC refactor & metacognitive fixes

```bash
# Stage purple_scanner, metacognitive_logic, sanitize
git add sky_claw/security/purple_scanner.py
git add sky_claw/security/metacognitive_logic.py
git add sky_claw/security/sanitize.py

git commit -m "refactor(security): separate I/O from scanning in purple_scanner; fix edge cases

- purple_scanner: extract _scan_text_payloads(filepath) →
  _scan_text_payloads(content, filename) for testability and SoC;
  scan_file() now reads file once and dispatches
- metacognitive_logic: use datetime.now(UTC) instead of naive
  datetime.now() for timezone-aware timestamps
- metacognitive_logic: replace fragile glob *.[pm][yd]* with explicit
  *.py + *.md + *.txt patterns
- sanitize: fix truncation logic to guarantee output ≤ max_length
  (previously suffix could exceed the limit)

Refs: SKY-SEC-004"
```

### Paso 5 — Commit 4: GUI — Critical attribute initialization & memory leak fix

```bash
# Stage GUI changes
git add sky_claw/gui/app.py

git commit -m "fix(gui): initialize all instance attributes and fix memory leak in DashboardGUI

- CRIT-01: declare all instance attributes in __init__ (_running,
  _is_thinking, _message_elements, _chat_container, etc.) to prevent
  AttributeError during _poll_queue race conditions
- CRIT-02: expose handlers as self.handlers (not only _state.handlers)
  so _poll_queue can resolve them without AppState indirection
- Memory leak: call oldest.delete() after removing chat elements to
  release NiceGUI DOM listeners and prevent unbounded node retention
- Defensive: validate logic_queue before put() with user-facing error
- Defensive: use getattr() for _running and gui_queue in _poll_queue
- UX: disable 'Guardar' button during async save to prevent double-submit

Refs: SKY-GUI-001, SKY-GUI-002"
```

### Paso 6 — Commit 5: Build — hidden imports for new modules

```bash
# Stage build config
git add sky_claw.spec

git commit -m "build(spec): add hidden imports for DLQ, orchestrator, hermes and loop_guardrail

Add 16 missing hiddenimports discovered during migration audit:
- sky_claw.core.dlq_manager
- sky_claw.orchestrator.tool_dispatcher + tool_strategies (10 modules)
- sky_claw.security.loop_guardrail
- sky_claw.agent.hermes_parser

Without these, PyInstaller builds fail with ImportError at runtime."
```

### Paso 7 — Commit 6: Test — replace flaky asyncio.sleep with condition-based polling

```bash
# Stage test changes
git add tests/test_event_bus_dlq_integration.py

git commit -m "test(dlq): replace asyncio.sleep with condition-based polling helper

- Introduce _poll_pending() helper that polls dlq.list_pending() until
  min_count rows appear or timeout (3s) — eliminates race conditions
- Pre-create DLQ schema with _ensure_schema() to avoid SQLite locking
  races between concurrent async tasks
- Remove all bare asyncio.sleep() calls that caused flaky CI failures"
```

### Paso 8 — Commit 7: Chore — config metadata updates

```bash
# Stage config files
git add .agents/skills/sky-claw-automation/SKILL.md
git add .antigravity/settings.json

git commit -m "chore: update skill YAML quoting and antigravity settings

- SKILL.md: quote YAML description string to prevent parser ambiguity
- settings.json: use \${workspaceFolder} for portable Python path,
  add superpowers v5.0.7 configuration block"
```

### Paso 9 — Verificar historia limpia

```bash
# Ver los commits creados
git log --oneline origin/main..HEAD

# Verificar que no hay archivos sin commitear
git status

# Ejecutar tests para confirmar que nada se rompió
python -m pytest tests/test_event_bus_dlq_integration.py -v
python -m pytest tests/test_sanitize.py tests/test_agent_guardrail.py tests/test_credential_vault.py tests/test_path_validator.py -v
```

### Paso 10 — Push y creación del PR

```bash
# Push de la rama feature al remote
git push -u origin feature/security-hardening-gui-fixes
```

---

## 3. Descripción del Pull Request

### Título

```
fix: security hardening, GUI critical fixes & DLQ test reliability
```

### Descripción completa

```markdown
## 📋 Resumen

Este PR consolida **13 archivos modificados** (+165/-73 líneas) agrupados en
tres ejes: **endurecimiento del módulo de seguridad**, **correcciones críticas
del GUI** y **mejora de fiabilidad de tests**. Todos los cambios son
compatibles con la base de código existente y no introducen nuevas
dependencias.

---

## 🔒 Endurecimiento de Seguridad (8 archivos)

### Protección de PII en logs
- **`credential_vault.py`**: Los nombres de servicio se hashean con SHA-256
  antes de incluirlos en mensajes de log, evitando exposición accidental de
  identificadores sensibles.

### Precisión de regex y parámetros
- **`agent_guardrail.py`**: La regex de tarjetas de crédito se ajustó de
  `(?:\d[ -]?){13,16}` (excesivamente greedy, falsos positivos en texto
  genérico) a `(?:\d{4}[ -]?){3}\d{1,4}` (agrupación por dígitos).
- **`text_inspector.py`**: Parámetro `max_bytes` renombrado a `max_chars` —
  en Python, `len(str)` devuelve caracteres, no bytes.

### Gobernanza y validación
- **`governance.py`**: El singleton factory ahora detecta conflictos de
  `base_path` y lanza `RuntimeError` en vez de retornar silenciosamente una
  instancia con path incorrecto. La clave HMAC se protege con permisos
  `owner-only` vía `restrict_to_owner()`.
- **`path_validator.py`**: El decorador `validate_path_arg` ahora valida que
  el argumento requerido exista antes de llamar al validador.

### Separación de responsabilidades
- **`purple_scanner.py`**: `_scan_text_payloads(filepath)` →
  `_scan_text_payloads(content, filename)`. La lectura del archivo se mueve
  a `scan_file()`, mejorando la testeabilidad y eliminando I/O del escáner
  puro.

### Correcciones de edge cases
- **`metacognitive_logic.py`**: `datetime.now()` → `datetime.now(UTC)` para
  timestamps timezone-aware. Glob `*.[pm][yd]*` reemplazado por patrones
  explícitos `*.py`, `*.md`, `*.txt`.
- **`sanitize.py`**: La lógica de truncamiento ahora garantiza que la salida
  nunca exceda `max_length` (antes el sufijo "... [truncated]" podía
  desbordar).

---

## 🖥️ Correcciones Críticas del GUI (1 archivo, 63 adiciones)

### CRIT-01 — Inicialización de atributos de instancia
`DashboardGUI.__init__` ahora declara explícitamente **17 atributos**
(`_running`, `_is_thinking`, `_message_elements`, `_chat_container`, etc.)
eliminando `AttributeError` durante condiciones de carrera en `_poll_queue`.

### CRIT-02 — Referencia de handlers
Los handlers se exponen como `self.handlers` (además de `_state.handlers`)
para que `_poll_queue` pueda resolverlos sin indirección a través de
`AppState`.

### Memory Leak — Nodos DOM huérfanos
Se añade `oldest.delete()` al expulsar mensajes del chat, liberando
explícitamente los listeners y nodos DOM de NiceGUI que de otro modo
permanecerían en memoria indefinidamente.

### Defensivos
- Validación de `logic_queue` antes de `put()` con mensaje de error
  user-friendly.
- `getattr()` defensivo para `_running` y `gui_queue` en `_poll_queue`.
- Botón "Guardar" se deshabilita durante el guardado async para prevenir
  doble-submit.

---

## 🧪 Fiabilidad de Tests (1 archivo)

- **`test_event_bus_dlq_integration.py`**: Se reemplazan los frágiles
  `asyncio.sleep(0.2)` con un helper `_poll_pending()` que sondea
  `dlq.list_pending()` hasta encontrar el mínimo de filas esperadas o
  agotar el timeout (3s). Se pre-crea el schema DLQ para evitar races de
  locking en SQLite.

---

## 📦 Build Config (1 archivo)

- **`sky_claw.spec`**: 16 `hiddenimports` añadidos para módulos nuevos
  (DLQ, orchestrator strategies, hermes_parser, loop_guardrail) que
  provocaban `ImportError` en builds PyInstaller.

---

## 🏗️ Contexto Técnico

Estos cambios surgen de una **auditoría de migración** (Skyclaw 1.4.26.16.32
→ rama principal actual) que identificó gaps de paridad, fugas de PII en
logs y condiciones de carrera en el GUI. Los fixes se priorizaron por
severidad:

| Prioridad | Issue | Archivos |
|-----------|-------|----------|
| 🔴 Crítica | AttributeError en GUI (CRIT-01/02) | `app.py` |
| 🔴 Crítica | Memory leak DOM nodes | `app.py` |
| 🟡 Alta | PII en logs de Vault | `credential_vault.py` |
| 🟡 Alta | Singleton silencioso | `governance.py` |
| 🟢 Media | Regex falsos positivos | `agent_guardrail.py` |
| 🟢 Media | Tests flaky (asyncio.sleep) | `test_event_bus_dlq_integration.py` |
| 🔵 Baja | Hidden imports PyInstaller | `sky_claw.spec` |

---

## ✅ Checklist de Revisión

- [ ] **Seguridad**: Verificar que los hashes SHA-256 en logs no filtraron PII
- [ ] **Seguridad**: Confirmar permisos `0600` en archivo de clave HMAC
- [ ] **GUI**: Probar flujo completo de chat en NiceGUI sin `AttributeError`
- [ ] **GUI**: Verificar que el memory leak está resuelto (monitorizar DOM nodes)
- [ ] **GUI**: Confirmar que el botón "Guardar" se deshabilita correctamente
- [ ] **Tests**: `pytest tests/test_event_bus_dlq_integration.py -v` pasa sin flakiness
- [ ] **Tests**: `pytest tests/test_sanitize.py tests/test_agent_guardrail.py -v` pasa
- [ ] **Tests**: `pytest tests/test_credential_vault.py tests/test_path_validator.py -v` pasa
- [ ] **Build**: Verificar que `sky_claw.spec` incluye los 16 hiddenimports nuevos
- [ ] **Build**: Confirmar que el build PyInstaller no genera `ImportError`
- [ ] **Código**: No hay `print()` de debug ni comentarios temporales
- [ ] **Código**: No se introducen nuevas dependencias
- [ ] **Breaking changes**: Ninguno — todos los cambios son retrocompatibles

---

## 🧭 Plan de Testing Sugerido

```bash
# 1. Tests unitarios de seguridad
python -m pytest tests/test_sanitize.py tests/test_agent_guardrail.py \
  tests/test_credential_vault.py tests/test_path_validator.py -v

# 2. Tests de integración DLQ
python -m pytest tests/test_event_bus_dlq_integration.py -v

# 3. Linting
ruff check sky_claw/security/ sky_claw/gui/app.py

# 4. Build PyInstaller (verificar hidden imports)
pyinstaller sky_claw.spec --noconfirm
```

---

## 📎 Referencias

- Auditoría de migración: `definitive_fix_log_20260422_200100.txt`
- Spec técnica DLQ: `TECHNICAL_SPEC_DLQ.md`
- Spec técnica Dispatcher: `TECHNICAL_SPEC_DISPATCHER.md`
```

---

## 4. Notas sobre Estrategia Git

### ¿Por qué commits atómicos en vez de un solo commit grande?

1. **Revisión más fácil**: Cada commit encapsula un cambio lógico único
2. **Revert granular**: Si un cambio causa problemas, se puede revertir
   un solo commit sin afectar los demás
3. **Bisect eficiente**: `git bisect` puede identificar el commit exacto
   que introdujo un bug
4. **Historia profesional**: Facilita auditorías y onboarding de nuevos
   desarrolladores

### ¿Por qué `git push -u` en vez de `--force-with-lease`?

La rama `feature/security-hardening-gui-fixes` es **nueva** — no existe en
el remote. Se usa `-u` para establecer el upstream tracking. Si más tarde
se necesita rebase interactivo para limpiar la historia antes del merge,
se usaría:

```bash
git rebase -i origin/main
git push --force-with-lease origin feature/security-hardening-gui-fixes
```

### Limpieza post-merge

```bash
# Después de que el PR sea mergeado
git checkout main
git pull origin main
git branch -d feature/security-hardening-gui-fixes
git push origin --delete feature/security-hardening-gui-fixes

# Opcional: eliminar ramas de respaldo
git branch -D backup/pre-pr-snapshot-20260423
```
