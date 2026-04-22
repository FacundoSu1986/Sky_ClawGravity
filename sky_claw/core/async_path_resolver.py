"""AsyncPathResolver — primitiva de infraestructura para resolución de rutas no bloqueante.

Mitiga el bloqueo del Event Loop provocado por llamadas síncronas a
``pathlib.Path.resolve()`` en entornos cruzados WSL2/Windows, donde la
traducción de rutas entre sistemas de ficheros puede incurrir en latencias
significativas (stat syscalls a través de 9P/Plan 9, resolución de symlinks,
hydration de OneDrive, etc.).

Invariantes de diseño:

* **Concurrencia pura**: toda I/O de disco se delega a ``asyncio.to_thread``.
* **Caché thread-safe**: diccionario interno protegido por ``asyncio.Lock``.
* **Fast-Path / Slow-Path**: lookup O(1) antes de incurrir en I/O.
* **Manejo de errores quirúrgico**: sólo ``OSError`` y ``RuntimeError`` son
  traducidos a :class:`AsyncPathResolutionError`; cualquier otra excepción
  es un bug upstream y se propaga sin modificación.

La clase es *stateful* únicamente en lo que respecta al caché; no mantiene
estado de dominio, por lo que puede vivir como singleton del contenedor DI.
"""

from __future__ import annotations

import asyncio
import logging
import pathlib
from typing import Final


class AsyncPathResolutionError(RuntimeError):
    """Error de dominio para fallos de resolución asíncrona de rutas.

    Envuelve la causa raíz (``OSError`` o ``RuntimeError``) mediante la
    cadena de excepciones (``raise ... from exc``) para preservar la
    trazabilidad sin filtrar detalles del sistema de archivos al caller.
    """


class AsyncPathResolver:
    """Servicio asíncrono de resolución de rutas con caché O(1).

    Encapsula ``pathlib.Path(raw).resolve(strict=...)`` dentro de
    ``asyncio.to_thread`` para evitar el bloqueo del Event Loop y memoiza
    los resultados en un diccionario interno protegido por un
    ``asyncio.Lock`` para garantizar seguridad frente a corutinas
    concurrentes.

    La clase no utiliza variables globales ni estado compartido fuera de
    la instancia, respetando el principio SRP: su única responsabilidad
    es trasladar I/O bloqueante a un pool de hilos y memoizar el resultado.
    """

    __slots__ = ("_cache", "_lock", "_logger")

    def __init__(self, *, logger: logging.Logger | None = None) -> None:
        self._cache: dict[str, pathlib.Path] = {}
        self._lock: Final[asyncio.Lock] = asyncio.Lock()
        self._logger: Final[logging.Logger] = logger or logging.getLogger(
            "SkyClaw.AsyncPathResolver",
        )

    async def resolve_safe(
        self,
        raw_path: str,
        *,
        strict: bool = True,
    ) -> pathlib.Path:
        """Resuelve ``raw_path`` sin bloquear el Event Loop.

        Algoritmo:
            1. **Fast-Path**: consulta el caché bajo el lock; si hay hit,
               retorna en O(1).
            2. **Slow-Path**: delega ``Path(raw_path).resolve(strict=strict)``
               a ``asyncio.to_thread``.
            3. **Memoización**: guarda el resultado en el caché bajo el lock.

        Args:
            raw_path: Ruta textual sin resolver. No se normaliza previamente
                para preservar el contrato original del caller.
            strict: Si ``True`` (por defecto), la resolución falla con
                ``FileNotFoundError`` (subclase de ``OSError``) si alguno
                de los componentes del path no existe.

        Returns:
            Instancia de ``pathlib.Path`` ya resuelta.

        Raises:
            AsyncPathResolutionError: Si la resolución falla con
                ``OSError`` (incluye ``FileNotFoundError``, ``PermissionError``,
                etc.) o ``RuntimeError`` (p. ej. loops de symlinks).
        """
        # Fast-Path — lookup protegido por lock.
        async with self._lock:
            cached = self._cache.get(raw_path)
        if cached is not None:
            return cached

        # Slow-Path — I/O delegada a un hilo secundario.
        try:
            resolved = await asyncio.to_thread(
                self._resolve_blocking,
                raw_path,
                strict,
            )
        except (OSError, RuntimeError) as exc:
            self._logger.error(
                "Fallo al resolver ruta %r (strict=%s): %s",
                raw_path,
                strict,
                exc,
                exc_info=True,
            )
            raise AsyncPathResolutionError(
                f"No se pudo resolver la ruta {raw_path!r} (strict={strict})"
            ) from exc

        # Memoización — setdefault previene sobreescritura en carreras.
        async with self._lock:
            return self._cache.setdefault(raw_path, resolved)

    @staticmethod
    def _resolve_blocking(raw_path: str, strict: bool) -> pathlib.Path:
        """Sección crítica síncrona ejecutada en el thread pool.

        Aislada como ``staticmethod`` para evitar capturar ``self`` en el
        hilo secundario y mantener el contrato funcional puro.
        """
        return pathlib.Path(raw_path).resolve(strict=strict)
