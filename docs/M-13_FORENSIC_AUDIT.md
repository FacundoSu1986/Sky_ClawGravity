# Auditoría Forense - Refactorización M-13
## Módulo Tools - Análisis de Seguridad y Arquitectura

**Fecha:** 2026-04-04  
**Auditor:** Sistema de Análisis Forense  
**Alcance:** `sky_claw/agent/tools/` y `sky_claw/agent/tools.py`

---

## 1. RESUMEN EJECUTIVO

| Categoría | Estado | Criticidad |
|-----------|--------|------------|
| Sintaxis Python | ✅ APROBADO | - |
| Dependencias Circulares | ⚠️ PRECAUCIÓN | MEDIA |
| Seguridad | ⚠️ REQUIERE ATENCIÓN | ALTA |
| Tipado | ⚠️ DEBILITADO | MEDIA |
| Arquitectura | ✅ APROBADO | - |

---

## 2. HALLAZGOS CRÍTICOS

### 2.1 🔴 CRÍTICO: Vulnerabilidad de Path Traversal Potencial

**Ubicación:** [`schemas.py:60`](../sky_claw/agent/tools/schemas.py:60), [`schemas.py:68`](../sky_claw/agent/tools/schemas.py:68), [`schemas.py:76`](../sky_claw/agent/tools/schemas.py:76)

```python
# Patrón actual permite barras y backslashes
archive_path: str = pydantic.Field(
    min_length=1, max_length=512, 
    pattern=r"^[a-zA-Z0-9_\\/\-.:]+$"  # ⚠️ PERMITE \ y /
)
```

**Riesgo:** Un atacante podría construir rutas como `../../../etc/passwd` o `..\..\..\windows\system32`

**Recomendación:**
```python
# Validar que la ruta está dentro de un directorio permitido
import os
ALLOWED_BASE_DIRS = [os.path.expanduser("~/Modding"), "C:/Modding"]

def validate_path(path: str) -> str:
    resolved = os.path.realpath(path)
    if not any(resolved.startswith(base) for base in ALLOWED_BASE_DIRS):
        raise ValueError(f"Path traversal detected: {path}")
    return resolved
```

---

### 2.2 🔴 CRÍTICO: Inyección de Comandos Potencial

**Ubicación:** [`system_tools.py:82`](../sky_claw/agent/tools/system_tools.py:82)

```python
params = XEditAnalysisParams(script_name=script_name, plugins=plugins)
# ...
result = await xedit_runner.run_script(params.script_name, params.plugins)
```

**Riesgo:** El regex `r"^[a-zA-Z0-9_\-]+\.pas$"` es insuficiente si `xedit_runner` construye comandos shell.

**Recomendación:** Verificar que `xedit_runner.run_script()` usa `subprocess.run()` con `shell=False` y lista de argumentos, no string concatenado.

---

### 2.3 🟠 ALTO: Importación Dinámica en Runtime

**Ubicación:** [`system_tools.py:136`](../sky_claw/agent/tools/system_tools.py:136)

```python
async def install_mod_from_archive(...):
    # ...
    from sky_claw.security.hitl import Decision  # ⚠️ Import en función
```

**Problema:** 
- Importaciones en funciones ocultan dependencias
- Puede causar errores en runtime si el módulo no está disponible
- Dificulta el análisis estático de dependencias

**Recomendación:** Mover al nivel de módulo:
```python
from sky_claw.security.hitl import Decision  # Top del archivo
```

---

### 2.4 🟠 ALTO: Falta de Validación de Null para sync_engine

**Ubicación:** [`nexus_tools.py:28`](../sky_claw/agent/tools/nexus_tools.py:28)

```python
async def download_mod(
    downloader: NexusDownloader | None,  # ✅ Valida null
    hitl: HITLGuard | None,              # ✅ Valida null
    sync_engine: SyncEngine,             # ⚠️ NO valida null
    ...
):
    # ...
    sync_engine.enqueue_download(...)  # ❌ Crash si es None
```

**Recomendación:** Agregar validación:
```python
if sync_engine is None:
    return json.dumps({"error": "SyncEngine is not configured"})
```

---

## 3. HALLAZGOS DE ARQUITECTURA

### 3.1 ⚠️ Riesgo de Dependencia Circular

**Estructura actual:**
```
tools.py → sky_claw.agent.tools (paquete) → __init__.py → handlers
```

**Análisis:** Python resuelve `sky_claw/agent/tools.py` antes que `sky_claw/agent/tools/__init__.py`, pero esto es frágil.

**Recomendación:** Renombrar `tools.py` a `tools_facade.py` para eliminar ambigüedad.

---

### 3.2 🟡 Tipado Débil con `Any`

**Ubicación:** Múltiples archivos

```python
# system_tools.py
async def check_load_order(mo2: Any, profile: str) -> str:
async def detect_conflicts(registry: Any, mo2: Any, profile: str) -> str:
async def run_xedit_script(xedit_runner: Any, ...) -> str:
```

**Problema:** El uso excesivo de `Any` elimina los beneficios del type checking.

**Recomendación:** Definir protocolos o interfaces:
```python
from typing import Protocol

class MO2Interface(Protocol):
    async def read_modlist(self, profile: str) -> AsyncIterator[tuple[str, bool]]: ...
    async def launch_game(self, profile: str) -> dict[str, Any]: ...
    async def close_game(self) -> dict[str, Any]: ...
```

---

### 3.3 ✅ Patrón Facade Correcto

**Implementación:** [`tools.py`](../sky_claw/agent/tools.py) correctamente re-exporta desde el paquete modular.

```python
from sky_claw.agent.tools import (
    AsyncToolRegistry,
    ToolDescriptor,
    # ... todos los componentes
)
```

---

## 4. ANÁLISIS DE SEGURIDAD POR ARCHIVO

| Archivo | Path Traversal | Command Injection | Input Validation |
|---------|---------------|-------------------|------------------|
| schemas.py | ⚠️ MEDIO | N/A | ✅ Pydantic strict |
| db_tools.py | ✅ BAJO | N/A | ✅ Pydantic |
| nexus_tools.py | ✅ BAJO | N/A | ✅ Pydantic + HITL |
| system_tools.py | ⚠️ MEDIO | ⚠️ MEDIO | ✅ Pydantic |
| external_tools.py | ⚠️ MEDIO | ⚠️ MEDIO | ✅ Pydantic |

---

## 5. RECOMENDACIONES PRIORITARIAS

### Inmediato (P0)
1. **Agregar validación de path canonical** en todos los handlers que usan `archive_path`
2. **Validar `sync_engine` no sea None** en `nexus_tools.py`
3. **Mover importaciones** al nivel de módulo

### Corto Plazo (P1)
4. **Definir Protocolos/Interfaces** para eliminar `Any`
5. **Agregar tests de seguridad** para path traversal
6. **Renombrar tools.py** a tools_facade.py

### Medio Plazo (P2)
7. **Implementar rate limiting** en descargas Nexus
8. **Agregar logging de auditoría** en operaciones críticas
9. **Documentar superficie de ataque** en README

---

## 6. VALIDACIONES EXITOSAS

✅ **Sintaxis:** Todos los archivos pasan `py_compile`  
✅ **Importaciones:** No hay dependencias circulares en runtime  
✅ **Patrón Facade:** Implementado correctamente  
✅ **Pydantic v2:** Uso de `strict=True` en todos los schemas  
✅ **HITL:** Aprobación obligatoria en operaciones destructivas  

---

## 7. CONCLUSIÓN

La refactorización M-13 es **arquitectónicamente sólida** pero requiere **endurecimiento de seguridad** antes de producción. Los riesgos identificados son mitigables sin cambios estructurales.

**Veredicto:** ⚠️ **APROBADO CON CONDICIONES**

**Condiciones:**
1. Resolver P0 antes de deploy
2. Agregar tests de seguridad
3. Code review de `xedit_runner` y `fomod_installer`
