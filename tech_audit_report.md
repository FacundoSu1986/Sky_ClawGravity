# Informe de Auditoría Técnica: SkyClaw Sync

## 1. Introducción

Este informe detalla una auditoría técnica exhaustiva del proyecto "SkyClaw Sync", con un enfoque en la resiliencia, atomicidad y concurrencia asíncrona, actuando como Ingeniero de Software Senior y Tech Lead. El objetivo es identificar fallos, proponer mejoras y señalar componentes faltantes para asegurar que el sistema cumpla con los requisitos de robustez y cumplimiento de los Términos de Servicio (ToS).

## 2. Metodología

La auditoría se centró en los módulos clave del proyecto:

*   **Configuración (`config.py`)**: Gestión de rutas dinámicas y secretos.
*   **Almacenamiento (`sky_claw/db/`)**: Persistencia de datos y mecanismos de bloqueo.
*   **Scraper Core (`sky_claw/scraper/`)**: Cliente de red y patrones de resiliencia.
*   **Sync Engine (`sky_claw/orchestrator/sync_engine.py`)**: Orquestación, concurrencia y transaccionalidad.

Se realizó un análisis estático del código fuente, prestando especial atención a la implementación de patrones de diseño como Circuit Breaker, Producer-Consumer y Unit of Work, así como al uso de primitivas de concurrencia asíncrona (`asyncio.Lock`, `asyncio.Semaphore`).

## 3. Hallazgos y Análisis Detallado

### 3.1. Atomicidad y Rollback (Brecha Crítica)

**Descripción del Problema:**

Existe una brecha significativa entre la intención arquitectónica de "atomicidad (Todo o Nada)" y la implementación actual del sistema de rollback. El `SyncEngine` (`sky_claw/orchestrator/sync_engine.py`) intenta orquestar operaciones de archivo con un patrón "Unit of Work" a través de `execute_file_operation`. Sin embargo, el `RollbackManager` (`sky_claw/db/rollback_manager.py`) es fundamentalmente limitado.

El `RollbackManager` solo permite revertir la *última* operación registrada por un `agent_id` específico, y lo hace de forma individual. No hay un mecanismo implementado para realizar un rollback de una *transacción completa* que abarque múltiples operaciones de archivo, lo cual es crítico para garantizar la atomicidad en escenarios donde una serie de cambios deben ser revertidos si alguno falla. La lógica de `SyncEngine.execute_file_operation` asume un rollback transaccional que el `RollbackManager` actual no proporciona.

**Impacto:**

*   **Pérdida de Integridad:** En caso de fallos intermedios durante una secuencia de operaciones de archivo (ej. instalación o actualización de un mod que implica múltiples copias, eliminaciones y modificaciones), el sistema podría quedar en un estado inconsistente, con archivos parcialmente modificados o eliminados, sin la capacidad de restaurar el estado anterior de forma atómica.
*   **Complejidad de Recuperación:** La recuperación manual o la depuración de estados inconsistentes se vuelve extremadamente compleja y propensa a errores.
*   **Violación del Principio de Atomicidad:** El requisito fundamental de "Todo o Nada" no se cumple para operaciones multi-archivo.

**Evidencia de Código:**

*   `SyncEngine.execute_file_operation` (líneas 217-280 en `sync_engine.py`) orquesta el inicio de transacciones y operaciones individuales en el `OperationJournal`, y maneja la lógica de `try...except` para invocar el rollback. Sin embargo, el `rollback_manager` solo expone `undo_last_operation`.
*   `RollbackManager.undo_last_operation` (líneas 60-98 en `rollback_manager.py`) recupera la *última* entrada del journal y restaura un único snapshot, marcando esa entrada como `ROLLED_BACK`. No hay iteración sobre múltiples entradas de una transacción.
*   El `OperationJournal` (`sky_claw/db/journal.py`) sí define `Transaction` y `TransactionStatus`, y métodos como `begin_transaction`, `commit_transaction`, `fail_transaction`, pero el `RollbackManager` no los utiliza para orquestar un rollback transaccional.

### 3.2. Concurrencia y Persistencia en `AsyncModRegistry`

**Descripción del Problema:**

El `AsyncModRegistry` (`sky_claw/db/async_registry.py`) utiliza `aiosqlite` para operaciones asíncronas con la base de datos SQLite, lo cual es una buena práctica para evitar bloqueos del event loop. También configura `PRAGMA journal_mode=WAL` y `PRAGMA foreign_keys=ON`, lo que mejora el rendimiento y la integridad. La gestión de la corrupción de la base de datos al inicio es robusta, intentando renombrar archivos corruptos y recrear la base de datos.

Sin embargo, la clase `AsyncModRegistry` no implementa un `asyncio.Lock` interno para proteger el acceso a la conexión de la base de datos (`self._conn`) durante operaciones de escritura o lectura que podrían ser llamadas concurrentemente desde diferentes tareas asíncronas. Aunque `aiosqlite` maneja la concurrencia a nivel de la conexión subyacente, la ausencia de un lock explícito en el `AsyncModRegistry` podría llevar a condiciones de carrera o comportamientos inesperados si múltiples tareas intentan modificar el estado de la conexión o ejecutar comandos que no son intrínsecamente serializados por `aiosqlite` de la manera esperada en un entorno de alto rendimiento.

**Impacto:**

*   **Condiciones de Carrera Potenciales:** Aunque `aiosqlite` es thread-safe, la concurrencia a nivel de la aplicación (múltiples `await self._conn.execute(...)` en paralelo) podría, en casos extremos, llevar a que las operaciones se entrelacen de formas no deseadas, especialmente si se realizan cambios de estado en la conexión o se ejecutan secuencias de comandos que deben ser atómicas desde la perspectiva de la aplicación.
*   **Dificultad de Depuración:** Los problemas de concurrencia son notoriamente difíciles de reproducir y depurar.
*   **Coherencia de Datos:** Aunque SQLite es robusto, la falta de un lock explícito en la capa de la aplicación para operaciones críticas podría, teóricamente, comprometer la coherencia de los datos en escenarios de alta concurrencia si las operaciones no son completamente independientes.

**Evidencia de Código:**

*   La clase `AsyncModRegistry` no tiene un `asyncio.Lock` inicializado en su `__init__` ni utilizado en sus métodos `upsert_mod`, `set_vfs_status`, `upsert_mods_batch`, etc.
*   Comparar con `SyncMetrics` (líneas 109-137 en `sync_engine.py`), que sí utiliza `_lock: asyncio.Lock` para proteger sus contadores y diccionarios internos, demostrando que el patrón de protección de recursos compartidos asíncronos es conocido en el proyecto.

### 3.3. Resiliencia del Scraper Core (Componente Faltante)

**Descripción del Problema:**

El `MasterlistClient` (`sky_claw/scraper/masterlist.py`) implementa un `_CircuitBreaker` robusto que previene fallos en cascada al interactuar con la API de Nexus Mods. Esto es excelente para la resiliencia de las llamadas a la API. El `NetworkGateway` (`sky_claw/security/network_gateway.py`) también proporciona una capa de seguridad y control de egreso bien diseñada, asegurando el cumplimiento de ToS y mitigando ataques como SSRF.

Sin embargo, el `NexusScraper` (`sky_claw/scraper/nexus.py`), que se describe en los comentarios como el módulo que utilizará Playwright para el scraping headless (lectura de dependencias, parseo de DOM, activación de descargas), es actualmente un *stub* vacío. Esto significa que la funcionalidad de scraping web real, que es crucial para obtener metadatos de mods que no están disponibles a través de la API o para interactuar con la interfaz web de Nexus Mods, está completamente ausente.

**Impacto:**

*   **Funcionalidad Incompleta:** El motor de sincronización no puede realizar tareas que requieran interacción directa con la interfaz web de Nexus Mods, como la extracción de información detallada de páginas HTML o la simulación de interacciones de usuario para descargar mods.
*   **Dependencia Excesiva de la API:** Si la API de Nexus Mods tiene limitaciones en los datos que proporciona o en la frecuencia de acceso, el sistema no tiene una alternativa robusta para obtener la información necesaria.
*   **Riesgo de Obsolescencia:** Si la API cambia o se vuelve menos completa, el sistema no podrá adaptarse sin una implementación de scraping web.

**Evidencia de Código:**

*   `sky_claw/scraper/nexus.py` contiene solo una clase `NexusScraper` con un `pass` en su interior, y un comentario que indica que la implementación está "diferida hasta que la capa de control de egreso de seguridad esté completamente definida y probada".

### 3.4. Configuración y Rutas Dinámicas

**Descripción del Problema:**

La clase `Config` (`sky_claw/config.py`) maneja la carga de configuración desde `config.toml`, variables de entorno y `keyring` para secretos, lo cual es un enfoque robusto y seguro. La clase `SystemPaths` proporciona una abstracción para la resolución dinámica de rutas entre Windows y WSL2, lo cual es fundamental para la portabilidad del proyecto.

La lógica de `SystemPaths.resolve` y `get_base_drive` intenta mapear rutas de Windows a sus equivalentes en WSL2 (ej. `C:/` a `/mnt/c/`). Sin embargo, la complejidad inherente a la detección de entornos y el mapeo de rutas puede ser una fuente de errores sutiles si no se prueba exhaustivamente en todas las combinaciones posibles de sistemas operativos y configuraciones de WSL2. La dependencia de `sys.platform` y `os.path.exists("/mnt/c")` es un buen punto de partida, pero no cubre todos los escenarios posibles (ej. diferentes distribuciones de Linux en WSL, montajes personalizados).

**Impacto:**

*   **Errores de Ruta:** Rutas incorrectamente resueltas pueden llevar a que el sistema no encuentre archivos o directorios críticos, resultando en fallos de operación o en la imposibilidad de iniciar el servicio.
*   **Problemas de Portabilidad:** Aunque el objetivo es la portabilidad, una implementación incompleta o con errores en la resolución de rutas puede limitar la capacidad del software para ejecutarse sin problemas en diferentes entornos.
*   **Dificultad de Configuración:** Los usuarios podrían tener dificultades para configurar el sistema si las rutas no se resuelven correctamente de forma automática.

**Evidencia de Código:**

*   `SystemPaths.get_base_drive` (líneas 18-24 en `config.py`) y `SystemPaths.resolve` (líneas 27-43 en `config.py`) contienen la lógica de detección y mapeo.
*   Las rutas comunes (`LOOT_COMMON_PATHS`, `XEDIT_COMMON_PATHS`, `STEAM_DEFAULT_PATHS`, etc.) están hardcodeadas con formatos de ruta de Windows (`r"C:\..."`), lo que requiere una conversión robusta por `SystemPaths`.

## 4. Recomendaciones de Mejora

### 4.1. Refactorización del Sistema de Rollback para Atomicidad Transaccional

**Prioridad:** Alta

**Descripción:**

Es imperativo refactorizar el `RollbackManager` para que opere a nivel de transacción, en lugar de operaciones individuales. Esto implica:

1.  **Extender `RollbackManager`:** Añadir métodos como `rollback_transaction(transaction_id)` que orquesten la reversión de *todas* las operaciones asociadas a un `transaction_id` específico en el `OperationJournal`.
2.  **Integración con `OperationJournal`:** El `RollbackManager` debe utilizar los métodos de `OperationJournal` para obtener todas las entradas de una transacción fallida, restaurar los snapshots correspondientes y marcar la transacción y sus operaciones como `ROLLED_BACK`.
3.  **Manejo de Errores:** Implementar una lógica robusta para manejar fallos durante el proceso de rollback, posiblemente con reintentos o un mecanismo de "compensación" si un rollback parcial es inevitable.
4.  **Pruning y Gestión de Espacio:** Implementar la lógica de `rollback_max_size_mb` y `max_pruning_age_days` definida en `SyncConfig` para gestionar el espacio en disco ocupado por los snapshots.

**Beneficios:**

*   Garantía de atomicidad "Todo o Nada" para operaciones de archivo complejas.
*   Mayor integridad del sistema y reducción de estados inconsistentes.
*   Simplificación de la lógica de recuperación ante fallos.

### 4.2. Fortalecimiento de la Concurrencia en `AsyncModRegistry`

**Prioridad:** Media

**Descripción:**

Aunque `aiosqlite` es asíncrono, se recomienda añadir un `asyncio.Lock` interno en `AsyncModRegistry` para proteger explícitamente el acceso a la conexión de la base de datos durante operaciones de escritura y lectura críticas. Esto asegurará que solo una tarea asíncrona pueda interactuar con la conexión en un momento dado, eliminando cualquier posible condición de carrera a nivel de la aplicación y garantizando la coherencia de los datos.

**Beneficios:**

*   Eliminación de posibles condiciones de carrera en el acceso a la base de datos.
*   Mayor robustez y previsibilidad en entornos de alta concurrencia.
*   Mejora de la coherencia de los datos.

### 4.3. Implementación del `NexusScraper` Headless

**Prioridad:** Alta

**Descripción:**

La implementación del `NexusScraper` utilizando Playwright es una funcionalidad crítica que actualmente está ausente. Se debe priorizar el desarrollo de este módulo para:

1.  **Extracción de Metadatos:** Obtener información de mods directamente de las páginas web de Nexus Mods cuando la API no sea suficiente.
2.  **Simulación de Interacciones:** Permitir la simulación de inicio de sesión, navegación y descarga de archivos para mods que requieran interacción manual o que no estén expuestos a través de la API.
3.  **Integración con `NetworkGateway`:** Asegurar que todas las operaciones de scraping pasen por el `NetworkGateway` para mantener el cumplimiento de ToS y las políticas de seguridad.

**Beneficios:**

*   Funcionalidad completa del motor de sincronización.
*   Mayor flexibilidad y resiliencia ante cambios en la API de Nexus Mods.
*   Capacidad para manejar escenarios de mods complejos que requieren interacción web.

### 4.4. Pruebas Exhaustivas de `SystemPaths` en Entornos Híbridos

**Prioridad:** Media

**Descripción:**

Se deben desarrollar un conjunto de pruebas unitarias y de integración exhaustivas para la clase `SystemPaths`, cubriendo una amplia gama de escenarios de resolución de rutas en entornos Windows nativos, WSL2 (con diferentes distribuciones de Linux) y posibles configuraciones personalizadas de montaje. Esto incluye:

1.  **Casos Borde:** Probar rutas con espacios, caracteres especiales, rutas relativas y absolutas, y diferentes letras de unidad.
2.  **Detección de Entorno:** Asegurar que la detección de Windows vs. WSL2 sea precisa y robusta.
3.  **Mapeo de Rutas:** Validar que las rutas de Windows se mapeen correctamente a sus equivalentes de WSL2 y viceversa.

**Beneficios:**

*   Mayor fiabilidad en la resolución de rutas.
*   Reducción de errores relacionados con la configuración del entorno.
*   Mejora de la portabilidad y la experiencia del usuario.

## 5. Conclusión

SkyClaw Sync presenta una arquitectura prometedora con un fuerte énfasis en la seguridad y la resiliencia de la red. Sin embargo, la implementación actual tiene brechas críticas en la atomicidad transaccional de las operaciones de archivo y una funcionalidad clave de scraping web aún pendiente. Abordar estas recomendaciones fortalecerá significativamente la robustez, la integridad y la capacidad del sistema para manejar fallos de manera elegante y predecible, alineándose con la visión de un motor de automatización y sincronización de mods "extremadamente robusto".
