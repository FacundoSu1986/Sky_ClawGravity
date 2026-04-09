# 🔐 AUDITORÍA TÉCNICA EXHAUSTIVA - SKYCLAW v0.1.0
## Informe de Revisión de Código y Seguridad Empresarial

**Fecha:** 2026-04-03  
**Auditor:** Arquitecto de Ciberseguridad & Ingeniero Principal de Software  
**Alcance:** Módulos críticos de Skyclaw (core, agent, comms, security, orchestrator, scraper)  
**Clasificación:** CONFIDENCIAL - USO INTERNO

---

## 📋 RESUMEN EJECUTIVO

### Estado General del Código: **MODERADO - Requiere Refactorización**

| Categoría | Puntuación | Estado |
|-----------|------------|--------|
| **Seguridad** | 7/10 | ⚠️ Mejorable |
| **Arquitectura** | 8/10 | ✅ Sólida |
| **Manejo de Errores** | 6/10 | ⚠️ Deficiente |
| **Test Coverage** | 5/10 | ❌ Insuficiente |
| **Documentación** | 7/10 | ✅ Adecuada |
| **Deuda Técnica** | MEDIA-ALTA | ⚠️ Requiere atención |

---

## 🚨 VULNERABILIDADES CRÍTICAS DE SEGURIDAD

### 1. **CRÍTICO: Salt Estático en CredentialVault**
**Archivo:** [`sky_claw/security/credential_vault.py:20`](sky_claw/security/credential_vault.py:20)

```python
# VULNERABLE
salt = b"sky_claw_static_salt_for_vault"  # Salt hardcodeado
```

**Impacto:** Si un atacante obtiene acceso a la base de datos SQLite, puede derivar la clave de cifrado usando el salt conocido, comprometiendo todos los secretos almacenados.

**Recomendación:**
```python
# SEGURO
import os
class CredentialVault:
    SALT_FILE = "vault_salt.bin"
    
    def __init__(self, db_path: str, master_key: bytes | str):
        salt = self._load_or_generate_salt(db_path)
        # ... resto del código
    
    def _load_or_generate_salt(self, db_path: str) -> bytes:
        salt_path = Path(db_path).parent / self.SALT_FILE
        if salt_path.exists():
            return salt_path.read_bytes()
        salt = os.urandom(16)
        salt_path.write_bytes(salt)
        return salt
```

---

### 2. **ALTO: Token de Autenticación en Archivo de Texto Plano**
**Archivo:** [`sky_claw/security/auth_token_manager.py:60`](sky_claw/security/auth_token_manager.py:60)

```python
# VULNERABLE
self._token_path.write_text(self._token, encoding="utf-8")
```

**Impacto:** El token de autenticación WebSocket se escribe en texto plano. Cualquier proceso con acceso al directorio `~/.sky_claw/tokens/` puede leerlo.

**Recomendación:**
- Usar `keyring` para almacenar el token (ya disponible como dependencia)
- O encriptar el token antes de escribirlo
- Implementar permisos restrictivos en Windows usando `ctypes` para ACL

---

### 3. **ALTO: Falta de Validación de Entrada en governance.py**
**Archivo:** [`sky_claw/security/governance.py:46`](sky_claw/security/governance.py:46)

```python
# FALTA IMPORT
def _load_whitelist(self) -> Set[str]:  # Set no está importado
```

**Impacto:** El código fallará en runtime. Además, no hay validación del contenido del JSON cargado.

**Recomendación:**
```python
from typing import Set
# Agregar validación de schema
from pydantic import BaseModel

class WhitelistSchema(BaseModel):
    approved_hashes: list[str]
```

---

### 4. **MEDIO: Singleton Global en Governance**
**Archivo:** [`sky_claw/security/governance.py:125`](sky_claw/security/governance.py:125)

```python
# PROBLEMÁTICO
governance = GovernanceManager()  # Singleton a nivel de módulo
```

**Impacto:** 
- Dificulta testing (estado compartido entre tests)
- Inicialización antes de configuración
- No permite múltiples instancias con diferentes configuraciones

**Recomendación:** Usar inyección de dependencias o patrón Factory.

---

### 5. **MEDIO: Validación de Path Incompleta**
**Archivo:** [`sky_claw/core/schemas.py:63-71`](sky_claw/core/schemas.py:63)

```python
# INCOMPLETO
@field_validator("target_path")
@classmethod
def validate_path(cls, v: str) -> str:
    if ".." in v:
        raise ValueError("Path traversal detectado")
    if v.startswith("/etc") or v.startswith("/root"):
        raise ValueError("Path traversal detectado")
    return v
```

**Problemas:**
- Solo valida rutas Unix (`/etc`, `/root`)
- No valida rutas Windows (`C:\Windows`, `%SYSTEMROOT%`)
- No valida symlinks
- `..` podría estar codificado (URL encoding)

**Recomendación:** Usar [`PathValidator`](sky_claw/security/path_validator.py) existente que ya implementa validación robusta.

---

## 🐛 ERRORES DE LÓGICA DETECTADOS

### 1. **Race Condition en HITLGuard**
**Archivo:** [`sky_claw/security/hitl.py:104-117`](sky_claw/security/hitl.py:104)

```python
self._pending[request_id] = req
# ... window entre asignación y wait
await asyncio.wait_for(req._event.wait(), timeout=self._timeout)
```

**Problema:** Si `respond()` es llamado entre la asignación y el `wait()`, el evento podría perderse en ciertos escenarios de concurrencia.

**Recomendación:** Usar `asyncio.Lock` para proteger el acceso a `_pending`.

---

### 2. **Manejo de Excepciones Silencioso en Config**
**Archivo:** [`sky_claw/config.py:75-76`](sky_claw/config.py:75)

```python
except Exception:
    stored = None  # Excepción silenciada sin logging
```

**Problema:** Errores de keyring se ignoran silenciosamente, dificultando debugging.

**Recomendación:**
```python
except Exception as e:
    logger.debug(f"Keyring unavailable for {key}: {e}")
    stored = None
```

---

### 3. **Timeout Hardcodeado en ManagedToolExecutor**
**Archivo:** [`sky_claw/agent/executor.py:140`](sky_claw/agent/executor.py:140)

```python
await asyncio.wait_for(self.proc.wait(), timeout=3.0)  # Magic number
```

**Problema:** 3 segundos puede ser insuficiente para procesos grandes.

**Recomendación:** Usar constante configurada o parámetro.

---

### 4. **Validación de Proveedor Incompleta**
**Archivo:** [`sky_claw/comms/frontend_bridge.py:54`](sky_claw/comms/frontend_bridge.py:54)

```python
VALID_PROVIDERS = {"deepseek", "anthropic", "ollama"}
```

**Problema:** No incluye "openai" que está referenciado en otros módulos.

---

## ⚡ INEFICIENCIAS DE RENDIMIENTO

### 1. **Conexiones SQLite No Reutilizadas**
**Archivo:** [`sky_claw/core/database.py`](sky_claw/core/database.py)

Cada método crea una nueva conexión:
```python
async with aiosqlite.connect(self.db_path) as db:
```

**Impacto:** Overhead de conexión en cada operación.

**Recomendación:** Implementar connection pool o conexión persistente.

---

### 2. **Polling en SupervisorAgent**
**Archivo:** [`sky_claw/orchestrator/supervisor.py:61`](sky_claw/orchestrator/supervisor.py:61)

```python
await asyncio.sleep(10.0)  # Polling cada 10 segundos
```

**Problema:** Polling activo consume recursos innecesariamente.

**Alternativas:**
- Usar `watchdog` con soporte 9P para WSL2
- Implementar notificación via socket Unix

---

### 3. **Hash Recalculado en Governance**
**Archivo:** [`sky_claw/security/governance.py:79`](sky_claw/security/governance.py:79)

```python
def is_scanned_and_clean(self, file_path: str) -> bool:
    file_hash = self.get_file_hash(file_path)  # Hash en cada llamada
```

**Recomendación:** Implementar caché LRU para hashes.

---

## 📦 DEUDA TÉCNICA IDENTIFICADA

### 1. **Imports No Utilizados**
```python
# sky_claw/__main__.py
import uuid  # Posiblemente no usado en todos los modos
```

### 2. **Código Comentado**
**Archivo:** [`sky_claw/orchestrator/supervisor.py:127`](sky_claw/orchestrator/supervisor.py:127)

```python
# asyncio.run(supervisor.start()) # En producción
```

### 3. **Type Hints Faltantes**
- [`sky_claw/agent/tools.py`](sky_claw/agent/tools.py) - Varios métodos usan `Any`
- [`sky_claw/comms/frontend_bridge.py:128`](sky_claw/comms/frontend_bridge.py:128) - `router: Any`

### 4. **Constantes Magic Numbers**
```python
# sky_claw/security/hitl.py
# HITL_TIMEOUT_SECONDS importado pero valor hardcodeado en otros lugares
```

---

## ✅ FORTALEZAS DEL CÓDIGO

### 1. **Validación Robusta con Pydantic v2**
- Uso extensivo de `strict=True` en modelos
- Validadores personalizados para sanitización
- Pattern matching en campos de entrada

### 2. **Arquitectura de Seguridad en Capas**
- [`PathValidator`](sky_claw/security/path_validator.py) - Sandbox de filesystem
- [`NetworkGateway`](sky_claw/security/network_gateway.py) - Control de egress
- [`HITLGuard`](sky_claw/security/hitl.py) - Autorización humana para operaciones críticas

### 3. **Manejo de Reintentos con Tenacity**
```python
@retry(
    wait=wait_exponential(multiplier=2, min=2, max=60),
    stop=stop_after_attempt(5),
    retry=retry_if_exception(_should_retry_nexus),
)
```

### 4. **Async/Await Consistente**
- Uso apropiado de `asyncio` throughout
- TaskGroups para gestión de tareas concurrentes

---

## 📊 COBERTURA DE TESTS

### Tests Existentes (Identificados)
| Módulo | Archivo de Test | Cobertura Estimada |
|--------|-----------------|-------------------|
| path_validator | test_path_validator.py | ~80% |
| sanitize | test_sanitize.py | ~90% |
| schemas | test_schemas.py | ~70% |
| network_gateway | test_web.py (parcial) | ~40% |

### Tests Faltantes Críticos
- ❌ `credential_vault.py` - Sin tests
- ❌ `auth_token_manager.py` - Sin tests
- ❌ `governance.py` - Sin tests
- ❌ `executor.py` - Sin tests de integración
- ❌ `supervisor.py` - Sin tests

---

## 🔧 REFACTORIZACIONES RECOMENDADAS

### Prioridad ALTA

1. **Corregir Salt Estático en CredentialVault**
   - Implementar generación dinámica de salt
   - Agregar migración para vaults existentes

2. **Agregar Validación de Entrada en Governance**
   - Importar `Set` faltante
   - Agregar schema Pydantic para whitelist

3. **Implementar Tests para Módulos de Seguridad**
   - credential_vault: Tests de encriptación/desencriptación
   - auth_token_manager: Tests de TTL y revocación

### Prioridad MEDIA

4. **Refactorizar Singleton de Governance**
   ```python
   class GovernanceFactory:
       _instance: Optional[GovernanceManager] = None
       
       @classmethod
       def get(cls, base_path: str = ".") -> GovernanceManager:
           if cls._instance is None:
               cls._instance = GovernanceManager(base_path)
           return cls._instance
   ```

5. **Unificar Validación de Paths**
   - Usar `PathValidator` en todos los schemas
   - Eliminar validación duplicada

6. **Implementar Connection Pool para SQLite**
   ```python
   class DatabasePool:
       _pool: Optional[aiosqlite.Connection] = None
       
       @classmethod
       async def get_connection(cls, db_path: str) -> aiosqlite.Connection:
           if cls._pool is None:
               cls._pool = await aiosqlite.connect(db_path)
           return cls._pool
   ```

### Prioridad BAJA

7. **Agregar Type Hints Completos**
8. **Eliminar Código Comentado**
9. **Documentar Magic Numbers**

---

## 📋 CHECKLIST DE ACCIONES INMEDIATAS

### Seguridad (Completar en 48h)
- [ ] Rotar salt de CredentialVault y re-encriptar secrets
- [ ] Mover token WS a keyring
- [ ] Agregar validación de Windows paths en schemas

### Estabilidad (Completar en 1 semana)
- [ ] Agregar lock en HITLGuard para race conditions
- [ ] Implementar tests para credential_vault
- [ ] Corregir import faltante en governance.py

### Deuda Técnica (Completar en 2 semanas)
- [ ] Refactorizar singleton de Governance
- [ ] Implementar connection pool SQLite
- [ ] Agregar type hints completos

---

## 🏆 CONCLUSIÓN

Skyclaw presenta una **arquitectura sólida** con buenas prácticas de seguridad en varios aspectos (validación Pydantic, sandbox de paths, control de egress). Sin embargo, existen **vulnerabilidades críticas** que deben abordarse antes de un despliegue en producción:

1. **Salt estático** en CredentialVault compromete todos los secretos
2. **Tokens en texto plano** exponen el canal WebSocket
3. **Cobertura de tests insuficiente** en módulos de seguridad críticos

La deuda técnica es manejable pero requiere atención continua. Se recomienda establecer un proceso de code review obligatorio con checklist de seguridad antes de merge.

---

**Auditoría completada por:** Claude (Arquitecto de Ciberseguridad)  
**Próxima revisión recomendada:** 2026-05-03
