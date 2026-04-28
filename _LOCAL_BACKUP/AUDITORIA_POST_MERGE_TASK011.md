# Auditoría de Código Post-Merge: TASK-011 / Origin Main Integration

**Auditor:** Ingeniero de Software Principal  
**Fecha:** 2026-04-26  
**Commit Auditado:** `9f45504` — Merge branch 'main' into refactor/sync-engine-golden-rules  
**Scope:** `sky_claw/core/windows_interop.py`, `sky_claw/loot/cli.py`, `sky_claw/mo2/vfs.py`, `tests/*`  
**Herramientas Auxiliares:** Context7 (Git docs), pytest 8.x, ruff 0.15.x, Python 3.14.3  

---

## Resumen Ejecutivo

El merge integra correctamente la arquitectura asíncrona de TASK-011 (WSL2, timeouts, prevención de zombies) con la localización en español y el "Parche Estándar 2026" del remoto. **Sin embargo, se detectan 2 fallos críticos de funcionalidad, 1 pérdida de cobertura de tests del remoto, y 7 defectos de severidad media/alta** que comprometen la estabilidad, portabilidad y mantenibilidad del código. Los tests pasan (58/58) pero su validez estadística está comprometida porque se descartaron intencionalmente los tests de `origin/main`.

**Estado general: NO APTO PARA PRODUCCIÓN sin las correcciones aquí detalladas.**

---

## Hallazgos Críticos (Severidad: P0 – Bloqueante)

### 🔴 P0-001: `MO2Controller.launch_game()` destruye el proceso MO2 en lugar de lanzarlo

**Archivo:** `sky_claw/mo2/vfs.py`  
**Líneas:** 291–314  
**Tipo:** Regresión funcional total / Error de lógica de negocio

#### Descripción Técnica

`launch_game()` ejecuta:

```python
proc = await asyncio.create_subprocess_exec(...)
try:
    await asyncio.wait_for(proc.wait(), timeout=self._launch_timeout)
except TimeoutError:
    proc.kill()
    ...
    raise GameLaunchTimeoutError(...)
```

`ModOrganizer.exe` **no es un proceso efímero**. Es un launcher que se mantiene residente mientras el juego (SkyrimSE.exe) esté en ejecución, ya que inyecta el VFS (Virtual File System) y gestiona el perfil de mods. Por tanto, `proc.wait()` con un timeout de 30 s **siempre** expirará, provocando que el código mate (`proc.kill()`) al proceso MO2 recién creado, impidiendo que el juego arranque.

#### Impacto Potencial
- **Corrupción funcional absoluta**: El usuario no puede lanzar el juego. El "zombie prevention" se convirtió en un "process terminator".
- **Falsa sensación de seguridad**: Los tests mockean `proc.wait()` para retornar inmediatamente, ocultando el defecto.
- **Riesgo de corrupción de perfil MO2**: Matar MO2 durante su fase de inicialización del VFS puede dejar el perfil en estado inconsistente.

#### Causa Raíz
El diseño de TASK-011 aplicó el patrón "timeout + kill + reap" — válido para herramientas CLI como LOOT (proceso corto) — a un proceso daemon/long-running como MO2, sin distinguir entre **ejecución de utilidad** y **lanzamiento de aplicación**.

#### Refactorización Requerida

El lanzamiento de MO2 no debe esperar a que el proceso termine. El timeout debe aplicarse a la **aparición del proceso hijo en el sistema** (verificación de PID vivo), no a su finalización. Implementar un *heartbeat* o validación de PID post-spawn:

```python
async def launch_game(self, profile: str = "Default") -> dict[str, Any]:
    """Launch Skyrim via SKSE through MO2 for the given profile.

    TASK-011: Async spawn with PID validation.  MO2 is a long-running
    process; we do **not** wait for it to exit.
    """
    mo2_exe = self._root / "ModOrganizer.exe"
    validated_exe = self._validator.validate(mo2_exe)

    if not validated_exe.exists():
        raise FileNotFoundError(f"MO2 executable not found: {validated_exe}")

    # WSL2: cwd must remain a Linux path for asyncio subprocess;
    # the Windows path is only for the executable arguments.
    cwd_local = str(self._root)
    if is_wsl2_cached():
        # Under WSL2, cwd for create_subprocess_exec must be a Linux path.
        # translate_path_if_wsl is meant for CLI arguments, not for cwd.
        cwd_local = str(self._root)  # /mnt/c/... remains valid in WSL2

    cmd = [str(validated_exe), "-p", profile, "moshortcut://SKSE"]
    logger.info("Launching game with command: %s", " ".join(cmd))

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
            cwd=cwd_local,
        )
    except FileNotFoundError:
        raise FileNotFoundError(f"MO2 executable not found: {validated_exe}") from None

    # TASK-011: Validate the process actually appeared (spawn verification).
    # We give the OS a short grace period to register the PID.
    try:
        await asyncio.wait_for(_wait_for_pid_alive(proc.pid), timeout=5.0)
    except TimeoutError:
        proc.kill()
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(proc.wait(), timeout=3.0)
        raise GameLaunchTimeoutError(5) from None

    return {"pid": proc.pid, "status": "launched", "profile": profile}


async def _wait_for_pid_alive(pid: int) -> None:
    """Poll until *pid* is visible in the process table or raises."""
    for _ in range(50):  # 5 s total @ 0.1 s
        if psutil.pid_exists(pid):
            return
        await asyncio.sleep(0.1)
    raise TimeoutError
```

> **Nota:** Si el requisito de negocio es detectar cuando MO2 *cierra* (por ejemplo, para saber cuándo el usuario dejó de jugar), eso debe implementarse como un **watcher async independiente** (`asyncio.create_task`), no bloqueando `launch_game()`.

---

### 🔴 P0-002: `cwd` en WSL2 recibe un path Windows inválido

**Archivo:** `sky_claw/mo2/vfs.py`  
**Líneas:** 285, 296  
**Tipo:** Error de integración / Fallo multiplataforma

#### Descripción Técnica

```python
cwd_win = await translate_path_if_wsl(self._root)
...
proc = await asyncio.create_subprocess_exec(..., cwd=cwd_win)
```

`translate_path_if_wsl()` retorna un path **Windows** (`C:\MO2`) cuando detecta WSL2. Sin embargo, `asyncio.create_subprocess_exec` bajo WSL2 invoca el runtime de Linux; el parámetro `cwd` debe ser un path absoluto **del filesystem Linux** (`/mnt/c/MO2`). Pasar `C:\MO2` provocará `FileNotFoundError: [Errno 2] No such file or directory: 'C:\\MO2'` en el momento del spawn.

#### Impacto Potencial
- **Fallo 100% replicable en WSL2**: El juego no se lanza en el entorno target principal de TASK-011.
- **Confusión de debugging**: El error aparece como "MO2 executable not found" (línea 299), cuando en realidad el ejecutable sí existe; es el `cwd` el inválido.

#### Refactorización Requerida

`translate_path_if_wsl` está diseñado para **argumentos de línea de comandos** que serán interpretados por el ejecutable Windows, no para el parámetro `cwd` del runtime Linux. En WSL2, `cwd` debe seguir siendo el path Linux original:

```python
# Para argumentos CLI que MO2.exe interpretará en Windows:
# (No aplica en launch_game; el único path Windows que MO2 necesita
# internamente se resuelve dentro de su propio directorio.)
cwd_local = str(self._root)  # /mnt/c/... válido en WSL2
```

Eliminar completamente la llamada a `translate_path_if_wsl` en `launch_game` para el parámetro `cwd`.

---

### 🔴 P0-003: Descarte intencional de tests del remoto (`git checkout HEAD -- tests/...`)

**Archivo:** Documentado en `Resolving Sky-Claw Git Conflicts1.md`  
**Líneas de referencia:** 102, 118–119  
**Tipo:** Pérdida de cobertura / Falso positivo en validación

#### Descripción Técnica

Durante la resolución se ejecutó:

```bash
git checkout HEAD -- tests/test_task011_wsl2_interop.py tests/test_loot.py tests/test_vfs.py
```

Esto **sobrescribió** los tests de `origin/main` con los tests locales de la rama `refactor/sync-engine-golden-rules`. Como resultado:
- Si `origin/main` contenía tests para el "Parche Estándar 2026" (decodificación I/O), esos tests desaparecieron.
- Si `origin/main` contenía tests de regresión para la localización española, desaparecieron.
- El reporte "58 passed, 0 failed" es una **auto-validación circular**: solo verifica que los tests locales pasen en código local, no que la integración sea sana.

#### Impacto Potencial
- **Regresiones ocultas**: Funcionalidades del remoto podrían estar rotas sin tests que lo detecten.
- **Deuda técnica invisible**: La próxima vez que alguien haga merge de `main`, los conflictos de tests se repetirán.

#### Refactorización Requerida

1. Recuperar los tests del remoto para comparar:
   ```bash
   git show origin/main:tests/test_loot.py > /tmp/test_loot_remote.py
   git show origin/main:tests/test_vfs.py > /tmp/test_vfs_remote.py
   ```
2. Realizar un merge tri-direccional de los archivos de test, preservando:
   - Tests locales de TASK-011 (zombies, WSL2, timeouts).
   - Tests remotos del Parche Estándar 2026 y localización.
3. Ejecutar **todos** los tests unificados antes de declarar el merge válido.

---

## Hallazgos de Severidad Media/Alta (P1)

### 🟠 P1-001: Uso de `os.popen()` deprecado y dependencia de shell

**Archivo:** `sky_claw/core/windows_interop.py`  
**Línea:** 44  
**Tipo:** Vulnerabilidad de seguridad potencial / Deuda técnica

```python
version = os.popen("cat /proc/version 2>/dev/null").read().lower()
```

- `os.popen` está [deprecated desde Python 3.12](https://docs.python.org/3/library/os.html#os.popen) en favor de `subprocess`.
- El string `"cat /proc/version 2>/dev/null"` se ejecuta vía shell (`/bin/sh -c ...`). Aunque hoy es hardcodeado, cualquier refactorización futura que parametriz el path introduciría un vector de shell injection.
- No captura `stderr` de forma portable; en algunos shells Windows/WSL híbridos, `2>/dev/null` podría no funcionar.

#### Refactorización

```python
def is_wsl2() -> bool:
    if sys.platform == "win32":
        return False

    try:
        version = pathlib.Path("/proc/version").read_text(encoding="utf-8", errors="replace")
        if "microsoft" in version.lower() and "wsl" in version.lower():
            return True
    except OSError:
        pass

    return os.path.isdir("/mnt/c")
```

---

### 🟠 P1-002: Cache global `_WSL2_ACTIVE` no thread-safe / no async-safe

**Archivo:** `sky_claw/core/windows_interop.py`  
**Líneas:** 55–67  
**Tipo:** Race condition

```python
_WSL2_ACTIVE: bool | None = None

def is_wsl2_cached() -> bool:
    global _WSL2_ACTIVE
    if _WSL2_ACTIVE is None:
        _WSL2_ACTIVE = is_wsl2()
    return _WSL2_ACTIVE
```

En un entorno `asyncio` con múltiples tareas, dos coroutines pueden entrar simultáneamente al bloque `if _WSL2_ACTIVE is None`, ejecutando `is_wsl2()` dos veces (I/O duplicada). En threads múltiples, podría ocurrir un data race en la asignación.

#### Refactorización

```python
import asyncio

_WSL2_ACTIVE: bool | None = None
_WSL2_LOCK = asyncio.Lock()

async def is_wsl2_cached_async() -> bool:
    global _WSL2_ACTIVE
    if _WSL2_ACTIVE is not None:
        return _WSL2_ACTIVE
    async with _WSL2_LOCK:
        if _WSL2_ACTIVE is None:
            _WSL2_ACTIVE = is_wsl2()
        return _WSL2_ACTIVE
```

> **Nota de diseño:** Dado que `translate_path_if_wsl` ya es `async`, es coherente que la versión cacheada lo sea también. Para código síncrono que necesite el valor, se puede leer `_WSL2_ACTIVE` directamente (asumiendo que el primer caller ya inicializó el cache).

---

### 🟠 P1-003: Inconsistencia en decodificación de subprocess (`errors="replace"` sin encoding explícito)

**Archivo:** `sky_claw/loot/cli.py`  
**Líneas:** 129–130  
**Tipo:** Regresión de comportamiento / Portabilidad

```python
stdout_text = stdout.decode(errors="replace")
stderr_text = stderr.decode(errors="replace")
```

En `windows_interop.py` (líneas 132, 135) el encoding es explícito: `decode("utf-8", errors="replace")`. En `cli.py` se omite `"utf-8"`, delegando al encoding por defecto del sistema (`locale.getpreferredencoding()`). En Windows con codepage distinto (ej. cp1252 en Windows en español), esto puede reintroducir el crash de decodificación que el "Parche Estándar 2026" intentaba solucionar.

#### Refactorización

```python
stdout_text = stdout.decode("utf-8", errors="replace")
stderr_text = stderr.decode("utf-8", errors="replace")
```

Aplicar la misma firma en **todos** los puntos donde se decodifique stdout/stderr de subprocess.

---

### 🟠 P1-004: `test_sort_timeout` no usa la excepción específica

**Archivo:** `tests/test_loot.py`  
**Líneas:** 120–138  
**Tipo:** Test frágil / Falso negativo potencial

```python
with pytest.raises(RuntimeError, match="timed out"):
    await runner.sort()
```

El código lanza `LOOTTimeoutError` (subclase de `RuntimeError`). Si en el futuro alguien introduce otra `RuntimeError` con el mismo mensaje (por ejemplo, un fallo de red), el test seguiría pasando incorrectamente. Además, si la jerarquía de herencia cambia (ej. `LOOTTimeoutError` pasa a heredar de `Exception`), el test rompería sin detectar la regresión real.

#### Refactorización

```python
from sky_claw.loot.cli import LOOTTimeoutError

with pytest.raises(LOOTTimeoutError, match="timed out"):
    await runner.sort()
```

Aplicar igualmente en `test_task011_wsl2_interop.py` donde se usa `pytest.raises(GameLaunchTimeoutError, match="timed out")` — ese sí es correcto, pero verificar que `LOOTTimeoutError` siga el mismo patrón.

---

### 🟠 P1-005: Race condition en archivo temporal de `_write_modlist_atomic`

**Archivo:** `sky_claw/mo2/vfs.py`  
**Línea:** 47  
**Tipo:** Corrupción de datos potencial

```python
tmp: pathlib.Path = path.with_suffix(path.suffix + ".tmp")
```

Si dos operaciones simultáneas (ej. `toggle_mod_in_modlist` y `remove_mod_from_modlist`) se ejecutan en el mismo perfil, ambas usarán el mismo path temporal (`modlist.txt.tmp`), causando que una sobrescriba la otra o que el `os.replace` falle de forma impredecible. Aunque hay un `asyncio.Lock` en el caller (`self._modlist_lock`), la función `_write_modlist_atomic` es pública y estática; podría llamarse desde otro contexto sin lock.

#### Refactorización

```python
import tempfile

async def _write_modlist_atomic(path: pathlib.Path, lines: list[str]) -> None:
    tmp: pathlib.Path = path.parent / f".{path.name}.{uuid.uuid4().hex}.tmp"
    # ... resto idéntico ...
```

---

### 🟠 P1-006: `AsyncMock` nunca awaited en tests de integración

**Archivo:** `tests/test_loot.py`  
**Líneas:** 280, 324  
**Tipo:** Test con warnings / Lógica async defectuosa

La ejecución de pytest emite:

```
RuntimeWarning: coroutine 'AsyncMockMixin._execute_mock_call' was never awaited
```

Esto indica que `AsyncToolRegistry.execute(...)` o algún mock interno no está siendo `await`ed en el path de ejecución. Aunque el test pasa, esto oculta un bug real: si el código productivo deja de awaited alguna coroutine interna, los tests no lo detectarán porque ya aceptan coroutines no awaited.

#### Refactorización Requerida

Ejecutar tests con `-W error::RuntimeWarning` para convertir warnings en errores:

```bash
python -m pytest tests/test_loot.py -W error::RuntimeWarning
```

Luego corregir el mock o el código productivo para que todos los `AsyncMock` sean efectivamente awaited.

---

### 🟠 P1-007: Eliminación de evidencia de auditoría (`.kilocode/`)

**Archivo:** Documentado en conversación  
**Comando:** `Remove-Item -Recurse -Force .kilocode`  
**Tipo:** Incumplimiento de trazabilidad

El protocolo OODA exigía trazabilidad completa. El diff de conflictos (`conflicts.diff`, `conflicts_utf8.diff`) fue eliminado **antes** del commit final. Si en el futuro se descubre una corrupción de datos atribuible a este merge, no hay forma de reconstruir qué conflictos existían originalmente.

#### Acción Correctiva

- Recrear el diff post-merge para archivo:
  ```bash
  git diff 00f21a4...ff4d6fd > docs/merge-evidence/TASK-011-merge-conflicts.diff
  ```
- Establecer política: nunca eliminar artefactos de resolución antes de que un revisar humano los archive.

---

## Hallazgos Menores (P2)

### 🟡 P2-001: Mezcla de idiomas en logs (español/inglés)

**Archivo:** `sky_claw/core/windows_interop.py`  
**Tipo:** Deuda de mantenibilidad

Los logs de `run_loot` fueron traducidos al español (`"Ejecutando LOOT para el perfil"`), mientras que los logs de `cli.py` y `vfs.py` permanecen en inglés. En un codebase orientado a logging estructurado o parseo automatizado por herramientas de observabilidad, la mezcla de idiomas dificulta la creación de alertas y dashboards.

**Recomendación:** Estandarizar al inglés para todo código, logs y docstrings, reservando el español para la UI/frontend o documentación de usuario.

---

### 🟡 P2-002: No se verifica `proc.returncode is None` tras reintento de `proc.wait()`

**Archivo:** Múltiples (`windows_interop.py`, `cli.py`, `vfs.py`)  
**Tipo:** Proceso huérfano potencial

Después del bloque:

```python
proc.kill()
with contextlib.suppress(TimeoutError):
    await asyncio.wait_for(proc.wait(), timeout=3.0)
```

Ningún código verifica si `proc.returncode` sigue siendo `None`. Si el proceso está en estado defunct/zombie y no responde a `SIGKILL` (raro pero posible en contenedores o WSL2 con problemas de init), el sistema operativo retendrá una entrada en la tabla de procesos.

**Recomendación:** Loggear una advertencia crítica si `proc.returncode is None` después del reap:

```python
if proc.returncode is None:
    logger.critical("Process %s (PID %d) could not be reaped after SIGKILL", cmd, proc.pid)
```

---

## Evaluación de Principios SOLID y Buenas Prácticas

| Principio | Estado | Observación |
|-----------|--------|-------------|
| **S**ingle Responsibility | ⚠️ Degradado | `launch_game` ahora mezcla spawn + wait + kill, violando SRP. Debería delegar el "watchdog" a una clase aparte. |
| **O**pen/Closed | ✅ Cumplido | Extensión vía `LOOTConfig` y `PathValidator` sin modificar código existente. |
| **L**iskov Substitution | ✅ Cumplido | `LOOTTimeoutError` hereda de `RuntimeError` sin alterar comportamiento. |
| **I**nterface Segregation | ✅ Cumplido | `PathValidator` inyectado, no hardcodeado. |
| **D**ependency Inversion | ✅ Cumplido | Depende de abstracciones (`PathValidator`, `LOOTConfig`). |
| DRY | ⚠️ Violación | La lógica "kill + reap" está duplicada en 4 lugares. Extraer a `async def _kill_and_reap(proc, timeout=3.0)`. |
| KISS | ❌ Violado | `launch_game` ahora tiene lógica de timeout innecesariamente compleja para un proceso long-running. |

---

## Métricas de Calidad Post-Merge

| Métrica | Valor | Umbral Recomendado | Estado |
|---------|-------|---------------------|--------|
| Cobertura de tests ejecutados | 58 tests | N/A | ⚠️ Solo tests locales; tests remotos descartados |
| Warnings en pytest | 9 | 0 | ❌ Excede |
| RuntimeWarning (coroutine no awaited) | 1+ | 0 | ❌ Excede |
| Violaciones Ruff | 0 | 0 | ✅ OK |
| Duplicación de lógica kill/reap | 4 instancias | 1 (función helper) | ❌ Excede |

---

## Plan de Remediación Recomendado

### Fase 1 – Correcciones Inmediatas (Bloqueantes)
1. **Refactorizar `launch_game`** para eliminar `proc.wait()` con timeout; reemplazar por validación de PID vivo.
2. **Eliminar `translate_path_if_wsl` del parámetro `cwd`** en `launch_game`.
3. **Recuperar y fusionar** los tests de `origin/main` en un conjunto unificado.

### Fase 2 – Robustecimiento (24–48 h)
4. Extraer helper `_kill_and_reap(proc)` para eliminar duplicación.
5. Reemplazar `os.popen` por `pathlib.Path.read_text()`.
6. Agregar lock async al cache WSL2.
7. Estandarizar encoding UTF-8 explícito en todos los `decode()`.

### Fase 3 – Validación Final
8. Ejecutar suite completa con:
   ```bash
   python -m pytest tests/ -q --tb=short -W error::RuntimeWarning
   python -m ruff check sky_claw/
   python -m mypy sky_claw/core/windows_interop.py sky_claw/loot/cli.py sky_claw/mo2/vfs.py
   ```
9. Realizar prueba manual en WSL2 verificando que MO2 lanza SkyrimSE.exe y que el PID persiste > 30 s sin ser asesinado.

---

## Conclusión

El merge **no cumple con el estándar "Zero-Regression"** autoimpuesto en el protocolo OODA. Aunque los tests unitarios pasan, contienen mocks que ocultan un fallo funcional crítico en `launch_game`. La descartada intencionalmente de los tests del remoto invalida la métrica de "58 passed" como evidencia de integridad. **Se recomienda bloquear cualquier despliegue o promoción a `main` hasta que se apliquen las correcciones P0 y P1 documentadas.**

**Firma de Auditoría:**  
Ingeniero de Software Principal  
2026-04-26
