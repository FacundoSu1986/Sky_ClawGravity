"""Tests para ProcessEmittingMiddleware (Fase 7).

Cubre las reglas de oro de la Fase 7 para la emisión ``ops.process.*``:

* Regla #1 — Emisión Garantizada: ``started`` + terminal (``completed`` |
  ``error``) por cada dispatch que atraviesa el middleware.
* Regla #3 — Tipado: el tópico final matchea el patrón ``ops.process.*`` del
  puente WS y contiene los campos que el frontend espera.
* Regla #5 — Seguridad: ``error_message`` se trunca a 500 caracteres para
  evitar fuga de rutas absolutas (Path Leakage).
* Regla #5 — Backpressure: la bandera ``emit_events=False`` silencia el
  middleware sin tocar al resto de la cadena.
* Contrato asíncrono: ``asyncio.CancelledError`` se re-lanza sin emitir
  evento de error (no ensucia la telemetría con cancelaciones legítimas).
* Observabilidad best-effort: un fallo al publicar en el bus NO tumba la
  ejecución de la herramienta.
* Integración: ``ProcessEmittingMiddleware`` OUTERMOST convive con
  ``ErrorWrappingMiddleware`` INNER — la excepción se observa cruda y luego
  se convierte al dict legacy.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from typing import Any
from unittest.mock import AsyncMock

import pytest

from sky_claw.core.event_bus import CoreEventBus, Event
from sky_claw.orchestrator.tool_dispatcher import OrchestrationToolDispatcher
from sky_claw.orchestrator.tool_strategies.middleware import ErrorWrappingMiddleware
from sky_claw.orchestrator.tool_strategies.process_emitter import (
    MAX_ERROR_MESSAGE_CHARS,
    ProcessEmittingMiddleware,
)


# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------


class _Strategy:
    """Estrategia de prueba configurable (éxito, fallo, o suspensión)."""

    def __init__(
        self,
        name: str,
        *,
        returns: Any = None,
        raises: BaseException | None = None,
        awaitable: Awaitable[Any] | None = None,
    ) -> None:
        self.name = name
        self._returns = returns
        self._raises = raises
        self._awaitable = awaitable

    async def execute(self, payload_dict: dict[str, Any]) -> Any:
        if self._awaitable is not None:
            return await self._awaitable
        if self._raises is not None:
            raise self._raises
        return self._returns


async def _start_bus_with_capture(topic_pattern: str) -> tuple[CoreEventBus, list[Event]]:
    """Construye un bus arrancado que captura eventos del patrón dado."""
    bus = CoreEventBus()
    captured: list[Event] = []

    async def _capture(event: Event) -> None:
        captured.append(event)

    bus.subscribe(topic_pattern, _capture)
    await bus.start()
    return bus, captured


async def _settle(bus: CoreEventBus) -> None:
    """Drena la cola interna del bus antes de hacer asserts.

    ``publish`` + ``create_task`` son fire-and-forget, así que concedemos un
    tick del event loop para que el dispatcher los procese.
    """
    await asyncio.sleep(0.05)
    await bus.stop()


# ---------------------------------------------------------------------------
# Camino feliz — started + completed
# ---------------------------------------------------------------------------


async def test_emits_started_then_completed_on_success() -> None:
    bus, events = await _start_bus_with_capture("ops.process.*")
    dispatcher = OrchestrationToolDispatcher()
    dispatcher.register(
        _Strategy("alpha", returns={"status": "ok"}),
        middleware=[ProcessEmittingMiddleware(bus)],
    )

    result = await dispatcher.dispatch("alpha", {})
    await _settle(bus)

    assert result == {"status": "ok"}
    assert len(events) == 2, f"Esperaba 2 eventos, se emitieron {len(events)}"
    started, completed = events
    assert started.topic == "ops.process.started"
    assert started.payload["state"] == "started"
    assert started.payload["tool_name"] == "alpha"
    assert completed.topic == "ops.process.completed"
    assert completed.payload["state"] == "completed"
    assert completed.payload["exit_code"] == 0
    assert isinstance(completed.payload["duration_seconds"], float)
    assert completed.payload["duration_seconds"] >= 0.0


async def test_started_and_completed_share_process_id() -> None:
    bus, events = await _start_bus_with_capture("ops.process.*")
    dispatcher = OrchestrationToolDispatcher()
    dispatcher.register(
        _Strategy("alpha", returns={"status": "ok"}),
        middleware=[ProcessEmittingMiddleware(bus)],
    )

    await dispatcher.dispatch("alpha", {})
    await _settle(bus)

    assert len(events) == 2
    assert events[0].payload["process_id"] == events[1].payload["process_id"]


# ---------------------------------------------------------------------------
# Camino de error — started + error + excepción re-lanzada
# ---------------------------------------------------------------------------


async def test_emits_started_then_error_and_reraises_exception() -> None:
    bus, events = await _start_bus_with_capture("ops.process.*")
    dispatcher = OrchestrationToolDispatcher()
    dispatcher.register(
        _Strategy("alpha", raises=RuntimeError("boom")),
        middleware=[ProcessEmittingMiddleware(bus)],
    )

    with pytest.raises(RuntimeError, match="boom"):
        await dispatcher.dispatch("alpha", {})
    await _settle(bus)

    assert len(events) == 2
    started, error_ev = events
    assert started.topic == "ops.process.started"
    assert error_ev.topic == "ops.process.error"
    assert error_ev.payload["state"] == "error"
    assert error_ev.payload["error_message"] == "boom"
    assert error_ev.payload["tool_name"] == "alpha"


async def test_error_message_is_truncated_to_guard_path_leakage() -> None:
    """Rutas absolutas u otros volcados largos no deben filtrarse al frontend."""
    bus, events = await _start_bus_with_capture("ops.process.error")
    dispatcher = OrchestrationToolDispatcher()
    long_path = "C:\\" + "x" * 5000  # simula stack con paths absolutos
    dispatcher.register(
        _Strategy("alpha", raises=RuntimeError(long_path)),
        middleware=[ProcessEmittingMiddleware(bus)],
    )

    with pytest.raises(RuntimeError):
        await dispatcher.dispatch("alpha", {})
    await _settle(bus)

    assert len(events) == 1
    message = events[0].payload["error_message"]
    assert len(message) == MAX_ERROR_MESSAGE_CHARS
    assert message.endswith("…")


# ---------------------------------------------------------------------------
# Cancelación — contrato asíncrono
# ---------------------------------------------------------------------------


async def test_cancelled_error_propagates_without_error_event() -> None:
    """CancelledError jamás debe producir un evento de error (es shutdown)."""
    bus, events = await _start_bus_with_capture("ops.process.*")
    dispatcher = OrchestrationToolDispatcher()
    dispatcher.register(
        _Strategy("alpha", raises=asyncio.CancelledError()),
        middleware=[ProcessEmittingMiddleware(bus)],
    )

    with pytest.raises(asyncio.CancelledError):
        await dispatcher.dispatch("alpha", {})
    await _settle(bus)

    topics = [ev.topic for ev in events]
    # `started` sí se emite antes de entrar al try; `error` nunca.
    assert "ops.process.started" in topics
    assert "ops.process.error" not in topics


# ---------------------------------------------------------------------------
# Resiliencia — fallo del bus no tumba la herramienta
# ---------------------------------------------------------------------------


async def test_bus_publish_failure_does_not_break_tool_execution() -> None:
    """La observabilidad es best-effort; nunca debe romper al productor."""
    faulty_bus = AsyncMock(spec=CoreEventBus)
    faulty_bus.publish.side_effect = RuntimeError("bus down")

    dispatcher = OrchestrationToolDispatcher()
    dispatcher.register(
        _Strategy("alpha", returns={"status": "ok"}),
        middleware=[ProcessEmittingMiddleware(faulty_bus)],
    )

    # No debe raise — el middleware debe swallow el fallo del bus.
    result = await dispatcher.dispatch("alpha", {})

    assert result == {"status": "ok"}
    # Intentó publicar ambos eventos (started + completed), los dos fallaron.
    assert faulty_bus.publish.await_count == 2


# ---------------------------------------------------------------------------
# Backpressure — emit_events=False
# ---------------------------------------------------------------------------


async def test_emit_events_false_skips_all_publishes() -> None:
    faulty_bus = AsyncMock(spec=CoreEventBus)
    dispatcher = OrchestrationToolDispatcher()
    dispatcher.register(
        _Strategy("alpha", returns={"status": "ok"}),
        middleware=[ProcessEmittingMiddleware(faulty_bus, emit_events=False)],
    )

    result = await dispatcher.dispatch("alpha", {})

    assert result == {"status": "ok"}
    faulty_bus.publish.assert_not_awaited()


# ---------------------------------------------------------------------------
# Integración — OUTERMOST + ErrorWrappingMiddleware INNER
# ---------------------------------------------------------------------------


async def test_outermost_emitter_plus_inner_error_wrapping() -> None:
    """La cadena OUTERMOST emite ``error`` ANTES de que ErrorWrapping convierta."""
    bus, events = await _start_bus_with_capture("ops.process.*")
    dispatcher = OrchestrationToolDispatcher()
    dispatcher.register(
        _Strategy("alpha", raises=ValueError("bad input")),
        middleware=[
            ProcessEmittingMiddleware(bus),            # OUTERMOST
            ErrorWrappingMiddleware("AlphaFailed"),     # INNER
        ],
    )

    # Regla clave: el caller sigue viendo el dict legacy, NO la excepción.
    result = await dispatcher.dispatch("alpha", {})
    await _settle(bus)

    assert result == {
        "status": "error",
        "reason": "AlphaFailed",
        "details": "bad input",
    }
    # Pero el middleware OUTERMOST vio la excepción cruda y emitió ``error``.
    topics = [ev.topic for ev in events]
    assert topics == ["ops.process.started", "ops.process.error"]
    assert events[1].payload["error_message"] == "bad input"


async def test_topic_matches_ws_bridge_pattern() -> None:
    """Los tópicos emitidos deben pasar el filtro fnmatch del puente WS."""
    import fnmatch

    bus, events = await _start_bus_with_capture("ops.process.*")
    dispatcher = OrchestrationToolDispatcher()
    dispatcher.register(
        _Strategy("alpha", returns={"status": "ok"}),
        middleware=[ProcessEmittingMiddleware(bus)],
    )

    await dispatcher.dispatch("alpha", {})
    await _settle(bus)

    for ev in events:
        assert fnmatch.fnmatch(ev.topic, "ops.process.*"), (
            f"Tópico {ev.topic!r} no matchea ops.process.* del puente WS"
        )
