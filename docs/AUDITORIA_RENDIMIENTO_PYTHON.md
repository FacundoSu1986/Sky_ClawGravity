# 🔬 Auditoría de Rendimiento Python — Sky-Claw-fresh

**Fecha:** 2026-04-17  
**Alcance:** Análisis completo del código Python del proyecto Sky-Claw-fresh  
**Metodología:** Análisis estático de código fuente + revisión arquitectónica  

---

## 1. Resumen Ejecutivo

Sky-Claw es un **agente autónomo de gestión de mods para Skyrim SE/AE** que opera sobre Mod Organizer 2. La arquitectura sigue un patrón de **orquestación asíncrona** con múltiples capas: GUI (NiceGUI/Tkinter), Web (aiohttp), Telegram, CLI, y un motor de agentes LLM con routing semántico.

### Hallazgos Críticos de Rendimiento

| # | Severidad | Módulo | Problema | Impacto Estimado |
|---|-----------|--------|----------|------------------|
| 1 | 🔴 CRÍTICO | `config.py` | Inicialización eager de `DB_PATH` a nivel de módulo | ~200ms en import |
| 2 | 🔴 CRÍTICO | `sanitize.py` | Multi-pass regex con hasta 10 iteraciones | O(n×10) por sanitización |
| 3 | 🟠 ALTO | `network_gateway.py` | `fnmatch` lineal por cada request | O(n) con n=16 hosts |
| 4 | 🟠 ALTO | `context_manager.py` | Apertura de conexión SQLite por consulta | ~50ms overhead por query |
| 5 | 🟠 ALTO | `semantic_router.py` | Similitud Jaccard O(n×m) sin cache | O(routes×utterances) por query |
| 6 | 🟡 MEDIO | `sync_engine.py` | `_passive_pruning()` síncrono en hot path | Bloquea event loop |
| 7 | 🟡 MEDIO | `nexus_downloader.py` | Jitter `asyncio.sleep(0)` en chunk loop | Latencia innecesaria |
| 8 | 🟡 MEDIO | `supervisor.py` | God Object con ~800 líneas | Acoplamiento excesivo |
| 9 | 🟢 BAJO | `vfs.py` | Re-lectura completa de modlist en toggle/add | I/O redundante |
| 10 | 🟢 BAJO | `auto_detect.py` | Búsqueda secuencial de paths sin cache | ~100ms en startup |

---

## 2. Análisis Detallado por Módulo

### 2.1 `config.py` — Gestión de Configuración

**Funcionalidad:** Centraliza la configuración del sistema. Carga desde TOML, keyring (OS credential store), y variables de entorno. Define constantes de seguridad (hosts permitidos, paths de búsqueda).

#### Cuello de Botella #1: Inicialización Eager de `DB_PATH`

```python
# PROBLEMA: Esto se ejecuta en IMPORT TIME
def _get_db_path() -> pathlib.Path:
    cfg = _get_config()  # Instancia Config() → lee TOML → consulta keyring
    return pathlib.Path(cfg.mo2_root) / "mod_registry.db"

DB_PATH = _get_db_path()  # ← Se ejecuta al importar config.py
```

**Impacto:** Cada `import sky_claw.config` (o cualquier módulo que lo importe transitivamente) ejecuta:
1. `Config.__init__()` → lee `~/.sky_claw/config.toml` del disco
2. `_load_from_keyring()` → 7 llamadas a `keyring.get_password()` (cada una ~20-50ms en Windows)
3. `_load_from_env()` → itera sobre todas las keys

**Tiempo estimado:** 150-300ms solo en importación.

**Refactorización propuesta:**

```python
# ANTES (eager)
DB_PATH = _get_db_path()

# DESPUÉS (lazy)
_global_cfg: Config | None = None
_db_path: pathlib.Path | None = None

def get_db_path() -> pathlib.Path:
    global _db_path
    if _db_path is None:
        cfg = _get_config()
        _db_path = (
            pathlib.Path(cfg.mo2_root) / "mod_registry.db"
            if cfg.mo2_root
            else pathlib.Path("mod_registry.db")
        )
    return _db_path
```

#### Cuello de Botella #2: `_load_from_keyring()` sin cache

```python
def _load_from_keyring(self):
    sensitive_keys = ["llm_api_key", "openai_api_key", ...]  # 7 keys
    for key in sensitive_keys:
        stored = keyring.get_password("sky_claw", key)  # ← ~30ms c/u en Windows
```

**Refactorización:** Cargar keyring en background o usar `lru_cache`:

```python
from functools import lru_cache

@lru_cache(maxsize=32)
def _cached_keyring_get(service: str, key: str) -> str | None:
    try:
        return keyring.get_password(service, key)
    except (keyring.errors.KeyringError, OSError):
        return None
```

---

### 2.2 `sanitize.py` — Sanitización de Prompts

**Funcionalidad:** Limpia texto externo (descripciones de Nexus Mods, metadata LOOT) antes de inyectarlo en prompts LLM. Previene prompt injection y token bombing.

#### Cuello de Botella #3: Multi-pass Regex (hasta 10 iteraciones)

```python
_INJECTION_PATTERNS = re.compile(
    r"<\|" r"|\|>" r"|<<SYS>>" r"|<</SYS>>" r"|\[INST\]" r"|\[/INST\]"
    r"|..."  # ~25 patrones combinados
    , re.IGNORECASE,
)

# PROBLEMA: Hasta 10 pasadas sobre el texto completo
_max_passes = 10
for _ in range(_max_passes):
    cleaned = _INJECTION_PATTERNS.sub("", text)
    if cleaned == text:
        break
    text = cleaned
```

**Análisis:** El regex ya está compilado (✅), pero el loop de hasta 10 pasadas es costoso para textos largos (8KB por defecto). En la práctica, la mayoría de los textos se estabilizan en 1-2 pasadas.

**Refactorización propuesta:**

```python
def sanitize_for_prompt(text: str, *, max_length: int = DEFAULT_MAX_LENGTH) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = _CONTROL_CHAR_RE.sub("", text)
    
    # Single-pass: el regex compilado ya maneja todos los patrones
    # en una sola pasada. Solo repetir si el resultado cambió.
    prev_len = -1
    while len(text) != prev_len:  # Comparar longitud es O(1)
        prev_len = len(text)
        text = _INJECTION_PATTERNS.sub("", text)
    
    if len(text) > max_length:
        text = text[:max_length] + "... [truncated]"
    return text
```

**Mejora:** Reemplazar comparación de strings (`cleaned == text`) con comparación de longitudes (`len(text) != prev_len`), que es O(1) en CPython.

---

### 2.3 `network_gateway.py` — Gateway de Egreso

**Funcionalidad:** Proxy obligatorio para todo tráfico HTTP saliente. Implementa allow-list de dominios, validación de métodos HTTP, bloqueo de IPs privadas (SSRF), y DNS pinning anti-rebinding.

#### Cuello de Botella #4: Búsqueda lineal en `_matching_pattern()`

```python
def _matching_pattern(self, hostname: str) -> str | None:
    for pattern in self._policy.allowed_hosts:  # 16 hosts
        if fnmatch.fnmatch(hostname, pattern):  # ← O(pattern_length)
            return pattern
    return None
```

**Impacto:** Se ejecuta 2-3 veces por cada request HTTP (`_check_host_allowed`, `_check_method_allowed`, `_check_telegram_path`). Con 16 hosts, son ~48 comparaciones fnmatch por request.

**Refactorización propuesta:**

```python
class NetworkGateway:
    def __init__(self, policy: EgressPolicy | None = None) -> None:
        self._policy = policy or EgressPolicy()
        # Pre-computed lookup: hostname exacto → allowed methods
        self._exact_host_map: dict[str, frozenset[str]] = {
            host: self._policy.allowed_methods.get(host, frozenset())
            for host in self._policy.allowed_hosts
        }
    
    def _matching_pattern(self, hostname: str) -> str | None:
        # O(1) exact match first
        if hostname in self._exact_host_map:
            return hostname
        # Fallback to fnmatch for wildcard patterns (if any)
        for pattern in self._policy.allowed_hosts:
            if '*' in pattern and fnmatch.fnmatch(hostname, pattern):
                return pattern
        return None
```

**Mejora:** De O(16) a O(1) para la mayoría de los requests (todos los hosts actuales son exactos, sin wildcards).

#### DNS Pinning: Cache Ilimitado

```python
class SafeResolver:
    def __init__(self, policy):
        self._pinned: dict[tuple[str, int], list[dict]] = {}  # ← Sin límite
```

**Problema:** El cache de DNS pinning crece sin límite durante la vida de la aplicación. Para un agente de larga ejecución, esto puede acumular miles de entradas.

**Refactorización:** Usar `collections.OrderedDict` con LRU eviction o `functools.lru_cache`.

---

### 2.4 `context_manager.py` — Gestor de Contexto LLM

**Funcionalidad:** Construye contexto dinámico para inyección en prompts LLM, consultando la base de datos local de mods y el load order.

#### Cuello de Botella #5: Apertura de conexión SQLite por consulta

```python
async def _get_mod_metadata(self, names: list[str]) -> list[dict]:
    # PROBLEMA: Abre y cierra conexión en CADA consulta
    async with aiosqlite.connect(self.db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
```

**Impacto:** Cada `aiosqlite.connect()` + `close()` implica:
- Crear thread SQLite subyacente (~10ms)
- Ejecutar `PRAGMA journal_mode=WAL` (si no está en cache)
- Crear/cerrar cursor

**Refactorización propuesta:**

```python
class ContextManager:
    def __init__(self, db_path: str, mo2_profile_path: str):
        self.db_path = db_path
        self.profile_path = mo2_profile_path
        self._db: aiosqlite.Connection | None = None
    
    async def _ensure_db(self) -> aiosqlite.Connection:
        if self._db is None:
            self._db = await aiosqlite.connect(self.db_path)
            self._db.row_factory = aiosqlite.Row
        return self._db
    
    async def close(self) -> None:
        if self._db is not None:
            await self._db.close()
            self._db = None
    
    async def _get_mod_metadata(self, names: list[str]) -> list[dict]:
        db = await self._ensure_db()
        async with db.execute(query, params) as cursor:
            return [dict(row) for row in await cursor.fetchall()]
```

#### Cuello de Botella #6: `_get_load_order()` con `os.path.exists` síncrono

```python
async def _get_load_order(self) -> str:
    lo_file: str = os.path.join(self.profile_path, "loadorder.txt")
    if not os.path.exists(lo_file):  # ← BLOQUEANTE en event loop
        return "Load Order file not found."
    data = await asyncio.to_thread(self._read_lo_safe, lo_file)
```

**Refactorización:**

```python
async def _get_load_order(self) -> str:
    lo_file = os.path.join(self.profile_path, "loadorder.txt")
    try:
        data = await asyncio.to_thread(self._read_lo_safe, lo_file)
        return data
    except FileNotFoundError:
        return "Load Order file not found."
    except Exception as e:
        logger.error(f"Fallo de acceso I/O a loadorder.txt: {e}")
        return "Plugin topology unavailable."
```

---

### 2.5 `semantic_router.py` — Router Semántico

**Funcionalidad:** Clasifica intents de usuario para routing hacia herramientas/agentes específicos. Usa similitud de palabras (Jaccard) como fallback.

#### Cuello de Botella #7: Similitud Jaccard O(n×m) sin cache

```python
def _calculate_similarity(self, query: str, utterance: str) -> float:
    query_words = set(query.lower().split())
    utterance_words = set(utterance.lower().split())
    intersection = query_words & utterance_words
    union = query_words | utterance_words
    return len(intersection) / len(union)
```

**Problema:** Para cada query, itera sobre 5 rutas × 5 utterances = 25 comparaciones, cada una creando 2 sets y computando intersección/unión.

**Refactorización propuesta:**

```python
class SemanticRouter:
    def __init__(self, confidence_threshold: float = 0.7):
        self.confidence_threshold = confidence_threshold
        self._encoder = None
        # Pre-compute utterance word sets at init time
        self._utterance_word_sets: dict[str, list[set[str]]] = {}
        self._rebuild_cache()
    
    def _rebuild_cache(self) -> None:
        """Pre-compute word sets for all utterances."""
        for route_name, utterances in self.ROUTES.items():
            self._utterance_word_sets[route_name] = [
                set(u.lower().split()) for u in utterances
            ]
    
    def _calculate_similarity(self, query_words: set[str], utterance_words: set[str]) -> float:
        if not query_words or not utterance_words:
            return 0.0
        intersection = query_words & utterance_words
        union = query_words | utterance_words
        return len(intersection) / len(union) if union else 0.0
    
    async def classify(self, query: str, fallback_route: str = "unknown") -> RouteClassification:
        query_words = set(query.lower().split())  # Compute once
        best_route = None
        best_score = 0.0
        
        for route_name, word_sets in self._utterance_word_sets.items():
            for ws in word_sets:
                sim = self._calculate_similarity(query_words, ws)
                if sim > best_score:
                    best_score = sim
                    best_route = route_name
        # ...
```

**Mejora:** Pre-calcular los sets de palabras de utterances una sola vez en `__init__` en vez de recrearlos en cada llamada.

---

### 2.6 `sync_engine.py` — Motor de Sincronización

**Funcionalidad:** Orquesta la sincronización de mods entre MO2 y la base de datos local. Usa patrón Producer-Consumer con cola asíncrona acotada y workers concurrentes.

#### Cuello de Botella #8: `_passive_pruning()` en hot path

```python
async def execute_file_operation(self, ...):
    try:
        # ... operación principal ...
    finally:
        await self._passive_pruning()  # ← Se ejecuta DESPUÉS de CADA operación

async def _passive_pruning(self) -> None:
    stats = await self._rollback_manager._snapshots.get_stats()
    max_size = self._get_max_backup_size_bytes()
    if stats.total_size_bytes > max_size:
        result = await self._rollback_manager._snapshots.cleanup_old_snapshots(...)
```

**Problema:** `_passive_pruning()` invoca `get_stats()` (que recorre el directorio de snapshots) después de **cada** operación de archivo. Para una sincronización de 200 mods, esto se ejecuta 200 veces.

**Refactorización propuesta:**

```python
class SyncEngine:
    def __init__(self, ...):
        self._pruning_interval = 50  # Ejecutar pruning cada 50 operaciones
        self._operation_count = 0
    
    async def _maybe_prune(self) -> None:
        self._operation_count += 1
        if self._operation_count % self._pruning_interval == 0:
            await self._passive_pruning()
```

#### Cuello de Botella #9: `_extract_nexus_id()` con I/O de disco

```python
def _extract_nexus_id(mod_name: str) -> int | None:
    # ... intenta parsear del nombre ...
    
    # FALLBACK: Lee meta.ini del disco para CADA mod
    meta_path = SystemPaths.modding_root() / "MO2/mods" / mod_name / "meta.ini"
    if meta_path.exists():  # ← I/O síncrono
        config = configparser.ConfigParser()
        config.read(str(meta_path), encoding="utf-8")  # ← I/O síncrono
```

**Problema:** Se ejecuta por cada mod en el batch. Para 200 mods, son hasta 200 lecturas de archivo síncronas en el event loop.

**Refactorización:**

```python
async def _extract_nexus_id_async(mod_name: str) -> int | None:
    """Versión asíncrona que no bloquea el event loop."""
    # Fast path: parse from name
    parts = mod_name.split("-")
    for part in parts:
        stripped = part.strip()
        if stripped.isdigit() and len(stripped) >= 2:
            return int(stripped)
    
    # Slow path: offload to thread
    return await asyncio.to_thread(_read_meta_ini, mod_name)
```

---

### 2.7 `nexus_downloader.py` — Descargador de Nexus Mods

**Funcionalidad:** Descarga mods desde Nexus Mods API con reintentos exponenciales, validación MD5/SHA256, y soporte para cuentas premium y free.

#### Cuello de Botella #10: `asyncio.sleep(0)` en chunk loop

```python
async with aiofiles.open(dest, "wb") as fh:
    async for chunk in resp.content.iter_chunked(self._chunk_size):
        await fh.write(chunk)
        md5_hash.update(chunk)
        sha256_hash.update(chunk)
        progress.downloaded_bytes += len(chunk)
        if progress_cb is not None:
            await progress_cb(progress)
        await asyncio.sleep(0)  # ← Yield explícito por CADA chunk
```

**Problema:** Con chunks de 1MB, un archivo de 500MB genera 500 calls a `asyncio.sleep(0)`. Cada `sleep(0)` fuerza un context switch del event loop, añadiendo ~0.1ms por chunk = ~50ms total de overhead innecesario.

**Refactorización:**

```python
chunk_count = 0
async for chunk in resp.content.iter_chunked(self._chunk_size):
    await fh.write(chunk)
    md5_hash.update(chunk)
    sha256_hash.update(chunk)
    progress.downloaded_bytes += len(chunk)
    chunk_count += 1
    # Yield cada 16 chunks (~16MB) en vez de cada chunk
    if chunk_count % 16 == 0:
        await asyncio.sleep(0)
    if progress_cb is not None:
        await progress_cb(progress)
```

#### Cuello de Botella #11: Doble hash (MD5 + SHA256) por chunk

```python
md5_hash = hashlib.md5(usedforsecurity=False)
sha256_hash = hashlib.sha256()
# ...
md5_hash.update(chunk)
sha256_hash.update(chunk)
```

**Impacto:** Dos actualizaciones de hash por chunk. Para archivos grandes, el overhead de SHA256 es ~2x más lento que MD5 solo.

**Optimización:** Si el MD5 ya validó correctamente, el SHA256 podría calcularse en un post-proceso offloaded a thread:

```python
# Solo calcular SHA256 después de descargar, en background
if file_info.md5:
    actual_md5 = md5_hash.hexdigest()
    if actual_md5.lower() != file_info.md5.lower():
        await _cleanup(dest)
        raise HashValidationError(...)

# Calcular SHA256 en background thread (no bloquea descargas)
async def _compute_sha256_async(path: pathlib.Path) -> str:
    return await asyncio.to_thread(_compute_sha256_sync, path)
```

---

### 2.8 `supervisor.py` — Agente Supervisor (God Object)

**Funcionalidad:** Orquesta todos los subsistemas: base de datos, scraper, herramientas, interfaz, rollback, parcheo, DynDOLOD, Wrye Bash, detección de conflictos.

#### Cuello de Botella #12: God Object con inicialización pesada

```python
class SupervisorAgent:
    def __init__(self, profile_name: str = "Default"):
        self.db = DatabaseAgent()
        self.scraper = ScraperAgent(self.db)
        self.tools = ModdingToolsAgent()
        self.interface = InterfaceAgent()
        self.state_graph = create_supervisor_state_graph(...)
        self.event_streamer = LangGraphEventStreamer(...)
        self._init_rollback_components()  # Crea 3 SQLite DBs + directorios
        self._path_resolver = PathResolutionService(...)
        self._event_bus = CoreEventBus()
        self._maintenance_daemon = MaintenanceDaemon(...)
        self._telemetry_daemon = TelemetryDaemon(...)
        self._watcher_daemon = WatcherDaemon(...)
        self._synthesis_service = SynthesisPipelineService(...)
        self._init_patch_orchestrator()
```

**Problema:** El constructor instancia **14+ componentes** eagerly, incluyendo 3 bases de datos SQLite (`journal.db`, `locks.db`, `snapshots/`), un graph de LangGraph, y múltiples daemons.

**Refactorización propuesta — Lazy Loading con `__getattr__`:**

```python
class SupervisorAgent:
    def __init__(self, profile_name: str = "Default"):
        self.profile_name = profile_name
        self._db: DatabaseAgent | None = None
        self._scraper: ScraperAgent | None = None
        # ... solo inicializar lo esencial
    
    @property
    def db(self) -> DatabaseAgent:
        if self._db is None:
            self._db = DatabaseAgent()
        return self._db
    
    @property
    def scraper(self) -> ScraperAgent:
        if self._scraper is None:
            self._scraper = ScraperAgent(self.db)
        return self._scraper
```

---

### 2.9 `vfs.py` — Controlador MO2 VFS

**Funcionalidad:** Gestiona el sistema de archivos virtual de MO2: lectura/escritura de modlist.txt, lanzamiento de juegos, toggle de mods.

#### Cuello de Botella #13: Re-lectura completa de modlist en operaciones de escritura

```python
async def add_mod_to_modlist(self, mod_name: str, profile: str = "Default"):
    async with self._modlist_lock:
        existing_names: set[str] = set()
        async with aiofiles.open(validated, encoding="utf-8-sig") as fh:
            async for raw_line in fh:  # ← Lee TODO el archivo
                # ... para verificar si el mod ya existe
        if mod_name in existing_names:
            return
        async with aiofiles.open(validated, mode="a", ...) as fh:
            await fh.write(f"+{mod_name}\n")
```

**Problema:** Para agregar un mod, lee todo el archivo (potencialmente miles de líneas) solo para verificar existencia.

**Refactorización:** Mantener un cache en memoria del modlist:

```python
class MO2Controller:
    def __init__(self, ...):
        self._modlist_cache: dict[str, set[str]] = {}  # profile → set de nombres
        self._modlist_lock = asyncio.Lock()
    
    async def _get_modlist_names(self, profile: str) -> set[str]:
        if profile not in self._modlist_cache:
            names = set()
            async for name, _ in self.read_modlist(profile):
                names.add(name)
            self._modlist_cache[profile] = names
        return self._modlist_cache[profile]
    
    async def add_mod_to_modlist(self, mod_name: str, profile: str = "Default"):
        async with self._modlist_lock:
            existing = await self._get_modlist_names(profile)
            if mod_name in existing:
                return
            # Append sin re-leer
            async with aiofiles.open(validated, mode="a", ...) as fh:
                await fh.write(f"+{mod_name}\n")
            self._modlist_cache[profile].add(mod_name)
```

---

### 2.10 `auto_detect.py` — Auto-detección de Herramientas

**Funcionalidad:** Busca automáticamente MO2, Skyrim SE, LOOT y SSEEdit en paths comunes, registro de Windows, y librerías de Steam.

#### Cuello de Botella #14: Búsqueda secuencial sin cache

```python
@staticmethod
async def _find_mo2_inner() -> pathlib.Path | None:
    for raw in _MO2_COMMON:  # 7 paths
        p = pathlib.Path(raw)
        if (p / "ModOrganizer.exe").exists():  # ← I/O síncrono
            return p
    
    local_appdata = os.environ.get("LOCALAPPDATA")
    if local_appdata:
        mo_dir = pathlib.Path(local_appdata) / "ModOrganizer"
        if mo_dir.is_dir():
            for child in mo_dir.iterdir():  # ← I/O síncrono
                if child.is_dir() and (child / "ModOrganizer.exe").exists():
                    return child
```

**Problema:** Todos los `.exists()` e `.iterdir()` son llamadas síncronas al filesystem que bloquean el event loop.

**Refactorización:**

```python
@staticmethod
async def _find_mo2_inner() -> pathlib.Path | None:
    def _sync_search() -> pathlib.Path | None:
        for raw in _MO2_COMMON:
            p = pathlib.Path(raw)
            if (p / "ModOrganizer.exe").exists():
                return p
        # ... resto de la búsqueda
        return None
    
    return await asyncio.to_thread(_sync_search)
```

---

## 3. Ineficiencias de Memoria

### 3.1 Carga de modlist completa en `toggle_mod_in_modlist()`

```python
async def toggle_mod_in_modlist(self, ...):
    async with aiofiles.open(validated, encoding="utf-8-sig") as fh:
        async for raw_line in fh:
            lines.append(raw_line)  # ← Acumula TODAS las líneas en memoria
```

**Problema:** Para modlists con miles de entradas, acumula todas las líneas en una lista antes de reescribir.

**Alternativa:** Usar escritura streaming con archivo temporal:

```python
async def toggle_mod_in_modlist(self, ...):
    tmp_path = validated.with_suffix('.tmp')
    changed = False
    async with aiofiles.open(validated) as src, \
               aiofiles.open(tmp_path, 'w') as dst:
        async for raw_line in src:
            line = raw_line.strip()
            if line and line[1:].strip() == mod_name and line[0] in ("+", "-"):
                if line[0] != target_prefix:
                    await dst.write(f"{target_prefix}{mod_name}\n")
                    changed = True
                else:
                    await dst.write(raw_line)
            else:
                await dst.write(raw_line)
    if changed:
        tmp_path.replace(validated)  # Atomic rename
    else:
        tmp_path.unlink()
```

### 3.2 `SyncResult.errors` como lista sin límite

```python
@dataclass
class SyncResult:
    errors: list[str] = field(default_factory=list)
    # Se agrega un string por cada mod fallido
```

**Problema:** Para sincronizaciones masivas con muchos errores, la lista crece sin límite.

**Refactorización:** Usar `collections.deque(maxlen=100)` para acotar memoria.

### 3.3 Chat history sin compresión ni limpieza

```python
# router.py
messages = messages[-self._max_context :]  # Sliding window de 20 mensajes
```

**Problema:** Los mensajes se almacenan como JSON strings completos en SQLite, incluyendo tool_results que pueden ser de hasta 4KB cada uno. Sin limpieza periódica, la tabla `chat_history` crece indefinidamente.

**Refactorización:** Agregar limpieza periódica:

```python
async def _cleanup_old_history(self, chat_id: str, keep: int = 100) -> None:
    await self._conn.execute(
        "DELETE FROM chat_history WHERE chat_id = ? AND id NOT IN "
        "(SELECT id FROM chat_history WHERE chat_id = ? ORDER BY id DESC LIMIT ?)",
        (chat_id, chat_id, keep)
    )
    await self._conn.commit()
```

---

## 4. Optimizaciones Arquitectónicas

### 4.1 Connection Pooling para SQLite

Actualmente, múltiples módulos abren conexiones SQLite independientes:
- `AsyncModRegistry` → `mod_registry.db`
- `LLMRouter` → `*_history.db`
- `OperationJournal` → `journal.db`
- `DistributedLockManager` → `locks.db`
- `ContextManager` → `mod_registry.db` (duplica conexión)

**Propuesta:** Centralizar la gestión de conexiones en un `DatabasePool`:

```python
class DatabasePool:
    """Centralized SQLite connection manager."""
    _connections: dict[str, aiosqlite.Connection] = {}
    
    async def get(self, db_path: str) -> aiosqlite.Connection:
        if db_path not in self._connections:
            conn = await aiosqlite.connect(db_path)
            conn.row_factory = aiosqlite.Row
            await conn.execute("PRAGMA journal_mode=WAL")
            await conn.execute("PRAGMA foreign_keys=ON")
            self._connections[db_path] = conn
        return self._connections[db_path]
    
    async def close_all(self) -> None:
        for conn in self._connections.values():
            await conn.close()
        self._connections.clear()
```

### 4.2 Batch Operations en `_process_batch()`

```python
async def _process_batch(self, batch, session, semaphore, result):
    mod_rows = []
    log_rows = []
    
    for mod_name, enabled in batch:
        # PROBLEMA: Cada mod hace una consulta HTTP individual
        info = await self._safe_fetch_info(nexus_id, session, semaphore)
    
    # Solo persiste en batch al final
    await self._registry.upsert_mods_batch(mod_rows)
```

**Optimización:** Las consultas HTTP ya son paralelizadas por el semáforo, pero se podría usar `asyncio.gather()` dentro del batch:

```python
async def _process_batch(self, batch, session, semaphore, result):
    async def _fetch_one(mod_name, enabled):
        nexus_id = _extract_nexus_id(mod_name)
        if nexus_id is None:
            return None
        info = await self._safe_fetch_info(nexus_id, session, semaphore)
        return (mod_name, enabled, nexus_id, info)
    
    fetch_results = await asyncio.gather(
        *[_fetch_one(m, e) for m, e in batch],
        return_exceptions=True
    )
    # ... procesar resultados y persistir en batch
```

### 4.3 Caching de PathValidator

```python
class PathValidator:
    def validate(self, path, *, strict_symlink=True):
        target = pathlib.Path(path)
        resolved = target.resolve()  # ← syscall por cada validación
        for root in self._roots:
            try:
                resolved.relative_to(root)
                return resolved
            except ValueError:
                continue
```

**Optimización:** Cache de paths validados:

```python
from functools import lru_cache

class PathValidator:
    def __init__(self, roots):
        self._roots = tuple(r.resolve() for r in roots)
        self._cache: dict[str, pathlib.Path | None] = {}
    
    def validate(self, path, *, strict_symlink=True):
        key = str(path)
        if key in self._cache:
            cached = self._cache[key]
            if cached is None:
                raise PathViolationError(f"Path '{path}' previously rejected")
            return cached
        
        # ... validación normal ...
        self._cache[key] = resolved
        return resolved
```

---

## 5. Resumen de Refactorizaciones Prioritarias

| Prioridad | Módulo | Cambio | Impacto Esperado | Esfuerzo |
|-----------|--------|--------|------------------|----------|
| P0 | `config.py` | Lazy `DB_PATH` + cache keyring | -200ms startup | Bajo |
| P0 | `context_manager.py` | Conexión SQLite persistente | -50ms/query | Bajo |
| P1 | `sync_engine.py` | Throttle `_passive_pruning()` | -100ms/operación | Bajo |
| P1 | `sync_engine.py` | Async `_extract_nexus_id()` | No bloquea event loop | Medio |
| P1 | `network_gateway.py` | Dict lookup vs fnmatch lineal | -0.1ms/request | Bajo |
| P2 | `semantic_router.py` | Pre-compute word sets | -30% clasificación | Bajo |
| P2 | `sanitize.py` | Optimizar loop de multi-pass | -20% sanitización | Bajo |
| P2 | `nexus_downloader.py` | Reducir `sleep(0)` frequency | -50ms/descarga grande | Bajo |
| P2 | `vfs.py` | Cache de modlist en memoria | -I/O redundante | Medio |
| P3 | `supervisor.py` | Lazy loading de componentes | -500ms instanciación | Alto |
| P3 | `auto_detect.py` | Offload a thread | No bloquea event loop | Bajo |
| P3 | Arquitectura | Connection pooling SQLite | -overhead general | Alto |

---

## 6. Recomendaciones de Profiling en Producción

Para validar estas hipótesis de rendimiento, se recomienda:

### 6.1 Profiling de Startup

```bash
python -m cProfile -o startup.prof -m sky_claw --mode cli
```

Analizar con `gprof2dot` o `snakeviz` para visualizar el call graph de inicialización.

### 6.2 Profiling de Memoria

```bash
pip install memory-profiler
python -m memory_profiler -m sky_claw --mode cli
```

### 6.3 Profiling en Producción (sin reinicio)

```bash
pip install py-spy
py-spy record -o profile.svg -- python -m sky_claw --mode web
```

### 6.4 Line Profiling de Hot Paths

```python
# Agregar a sync_engine.py
from line_profiler import LineProfiler

lp = LineProfiler()
lp.add_function(SyncEngine._process_batch)
lp.add_function(SyncEngine._produce)
lp.add_function(SyncEngine._consume)
```

---

## 7. Conclusión

Sky-Claw presenta una **arquitectura asíncrona bien estructurada** con patrones correctos (Producer-Consumer, Circuit Breaker, Retry con backoff, DNS pinning). Sin embargo, existen **cuellos de botella significativos** en:

1. **Inicialización eager** de recursos pesados (config, supervisor)
2. **I/O síncrono** en el event loop (auto_detect, _extract_nexus_id)
3. **Conexiones SQLite efímeras** que se abren/cierran por consulta
4. **Overhead de pruning** en el hot path de operaciones de archivo

Las refactorizaciones propuestas son **mayormente de bajo esfuerzo y alto impacto**, con la mayoría resolubles en 1-2 horas cada una. La prioridad debe ser:

1. **P0:** Lazy loading de `config.py` y conexión persistente en `ContextManager`
2. **P1:** Throttle de pruning y async `_extract_nexus_id`
3. **P2:** Optimizaciones de cache y reducción de overhead en loops

Estas optimizaciones podrían reducir el tiempo de startup en ~300-500ms y mejorar el throughput de sincronización en ~20-30%.
