from __future__ import annotations

import asyncio
import inspect
from typing import Any, Callable, Awaitable

async def poll_until(
    condition: Callable[[], Any | Awaitable[Any]],
    *,
    timeout: float = 5.0,
    interval: float = 0.05,
    msg: str = "Condición no cumplida en el tiempo esperado",
) -> None:
    """Poll *condition* (sync or async callable) until truthy or *timeout* elapses.
    Raises AssertionError with *msg* on timeout so failures are descriptive.
    Centralises timeout/interval so callers don't repeat the pattern inline.
    """
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while loop.time() < deadline:
        result = condition()
        if inspect.isawaitable(result):
            result = await result
        if result:
            return
        await asyncio.sleep(interval)
    raise AssertionError(f"{msg} (timeout={timeout}s)")
