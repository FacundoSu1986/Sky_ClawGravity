"""ProcessEmittingMiddleware — propaga eventos ``ops.process.*`` al CoreEventBus.

Middleware transversal registrado OUTERMOST sobre cada :class:`ToolStrategy`
para que el :class:`OrchestrationToolDispatcher` exponga telemetría de ciclo
de vida de cada herramienta sin que las estrategias conozcan el bus.

Emisiones garantizadas (regla de oro Fase 7 #1):

* ``ops.process.started``   — antes de invocar ``next_call``.
* ``ops.process.completed`` — si ``next_call`` retorna sin excepción.
* ``ops.process.error``     — si ``next_call`` levanta ``Exception``.

El middleware **re-lanza** la excepción original tras emitir el evento de
error para que :class:`ErrorWrappingMiddleware` (aguas adentro de la cadena)
la convierta al dict legacy ``{"status": "error", ...}`` como antes.
``asyncio.CancelledError`` **no** genera evento de error y se re-lanza
intacta para respetar el contrato de cancelación asincrónica.

Regla de oro #5 (seguridad — Path Leakage): ``error_message`` se trunca a
``MAX_ERROR_MESSAGE_CHARS`` caracteres para evitar volcar rutas absolutas u
otros contenidos sensibles al frontend.

Regla de oro #5 (backpressure): la bandera ``emit_events: bool = True`` en
el constructor permite silenciar el middleware para herramientas muy
frecuentes si un profiling de producción detectase saturación del bus.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import TYPE_CHECKING, Any, Final

from sky_claw.core.event_bus import Event, ops_process_topic
from sky_claw.orchestrator.tool_strategies.base import NextCall, ToolStrategy

if TYPE_CHECKING:
    from sky_claw.core.event_bus import CoreEventBus

logger = logging.getLogger(__name__)

#: Tope de caracteres para ``error_message``.  Evita Path Leakage y mantiene
#: el payload bajo el límite de 1 MiB del frame WS aiohttp por defecto.
MAX_ERROR_MESSAGE_CHARS: Final[int] = 500

#: Fuente declarada en los eventos emitidos por este middleware.
EMITTER_SOURCE: Final[str] = "process-emitter"


def _truncate(message: str, *, limit: int = MAX_ERROR_MESSAGE_CHARS) -> str:
    """Devuelve ``message`` acotado a ``limit`` caracteres con marcador ``…``."""
    if len(message) <= limit:
        return message
    # Reservar un carácter para el marcador mantiene el tope estricto.
    return message[: limit - 1] + "…"


class ProcessEmittingMiddleware:
    """Cross-cutting middleware que publica ``ops.process.*`` por estrategia.

    Debe registrarse como la capa OUTERMOST de la cadena de middleware para
    ver la excepción cruda antes de que :class:`ErrorWrappingMiddleware` la
    convierta a dict.  La emisión es best-effort: un fallo del bus se loguea
    pero no rompe la ejecución de la herramienta (principio DevOps — la
    observabilidad nunca tumba al negocio).

    Args:
        event_bus:    Instancia de :class:`CoreEventBus` donde publicar.
        emit_events:  Permite apagar la emisión por estrategia si una
            herramienta muy frecuente generase backpressure.  Por defecto
            está activo (``True``) — la emisión es la razón de ser del
            middleware.
    """

    def __init__(
        self,
        event_bus: CoreEventBus,
        *,
        emit_events: bool = True,
    ) -> None:
        self._event_bus = event_bus
        self._emit_events = emit_events

    async def __call__(
        self,
        strategy: ToolStrategy,
        payload_dict: dict[str, Any],
        next_call: NextCall,
    ) -> dict[str, Any]:
        """Envuelve la ejecución publicando los tres eventos del ciclo de vida."""
        if not self._emit_events:
            return await next_call()

        process_id = uuid.uuid4().hex
        tool_name = strategy.name
        started_monotonic = time.monotonic()

        await self._safe_publish(
            topic=ops_process_topic("started"),
            payload={
                "process_id": process_id,
                "tool_name": tool_name,
                "state": "started",
                "ts": time.time(),
            },
        )

        try:
            result = await next_call()
        except Exception as exc:
            duration = round(time.monotonic() - started_monotonic, 3)
            await self._safe_publish(
                topic=ops_process_topic("error"),
                payload={
                    "process_id": process_id,
                    "tool_name": tool_name,
                    "state": "error",
                    "error_message": _truncate(str(exc)),
                    "duration_seconds": duration,
                    "ts": time.time(),
                },
            )
            raise  # Deja que ErrorWrappingMiddleware (o el caller) decida.

        duration = round(time.monotonic() - started_monotonic, 3)
        await self._safe_publish(
            topic=ops_process_topic("completed"),
            payload={
                "process_id": process_id,
                "tool_name": tool_name,
                "state": "completed",
                "exit_code": _infer_exit_code(result),
                "duration_seconds": duration,
                "ts": time.time(),
            },
        )
        return result

    async def _safe_publish(self, *, topic: str, payload: dict[str, Any]) -> None:
        """Publica un evento aislando fallos del bus del caller.

        Un fallo al publicar jamás debe romper la ejecución de la
        herramienta — solo degradamos la observabilidad.
        """
        try:
            await self._event_bus.publish(
                Event(topic=topic, payload=payload, source=EMITTER_SOURCE),
            )
        except Exception:  # noqa: BLE001 — best-effort observability
            logger.exception(
                "ProcessEmittingMiddleware: fallo al publicar '%s' (se ignora)",
                topic,
            )


def _infer_exit_code(result: dict[str, Any] | Any) -> int | None:
    """Deriva un ``exit_code`` a partir del dict devuelto por la estrategia.

    Convenciones observadas en el repo:

    * ``{"status": "ok"}`` / sin status → ``0`` (éxito).
    * ``{"status": "error", ...}``       → ``1``.
    * Cualquier otra estructura          → ``None`` (desconocido).
    """
    if not isinstance(result, dict):
        return None
    status = result.get("status")
    if status == "ok" or status is None:
        return 0
    if status == "error":
        return 1
    return None


__all__ = [
    "MAX_ERROR_MESSAGE_CHARS",
    "ProcessEmittingMiddleware",
]
