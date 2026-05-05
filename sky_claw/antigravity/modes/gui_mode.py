"""GUI mode entry point — boots the NiceGUI Forge interface."""

from __future__ import annotations

import asyncio
import logging
import uuid

from sky_claw.antigravity.gui.sky_claw_gui import set_runtime_context, setup_app
from sky_claw.antigravity.orchestrator.supervisor import SupervisorAgent
from sky_claw.app_context import AppContext, _resolve_config_path_static, start_full
from sky_claw.logging_config import correlation_id_var

logger = logging.getLogger("sky_claw")


async def _gui_logic_loop(ctx: AppContext) -> None:
    """Process chat messages from the GUI in a background task."""
    consecutive_errors = 0
    while True:
        try:
            item = await asyncio.to_thread(ctx.logic_queue.get)
            if not isinstance(item, (tuple, list)) or len(item) < 2:
                logger.warning("Malformed item in logic_queue: %r", item)
                continue
            if item[0] == "chat":
                text = item[1]
                if not ctx.router:
                    ctx.gui_queue.put(("error", "Router no inicializado. Completá el setup primero."))
                    continue
                correlation_id_var.set(str(uuid.uuid4()))
                try:
                    response = await ctx.router.chat(text, ctx.session, chat_id="gui-session")
                    ctx.gui_queue.put(("response", response))
                    consecutive_errors = 0
                except Exception as e:
                    logger.exception("Logic error in chat: %s", e)
                    ctx.gui_queue.put(("error", f"Error procesando comando: {type(e).__name__}: {e}"))
        except asyncio.CancelledError:
            break
        except Exception as e:
            consecutive_errors += 1
            backoff = min(2**consecutive_errors, 30)
            logger.exception("GUI logic loop error (backoff=%ds): %s", backoff, e)
            await asyncio.sleep(backoff)


async def _gui_mod_update_loop(ctx: AppContext) -> None:
    """Periodically fetch the mod list for the GUI queue consumer."""
    while True:
        try:
            if ctx.registry:
                mods_dicts = await ctx.registry.search_mods("")
                mods = [m["name"] for m in mods_dicts]
                ctx.gui_queue.put(("modlist", mods))
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.error("Error updating modlist in GUI: %s", exc)
            await asyncio.sleep(5)


def run_gui_mode(args) -> None:
    from nicegui import app, ui

    config_path = _resolve_config_path_static(args)

    setup_app()

    _runtime: dict[str, object] = {}

    async def _bootstrap() -> None:
        """Spin up AppContext + supervisor + background loops, then publish."""
        if "ctx" in _runtime:
            return
        ctx = await start_full(args)
        _runtime["ctx"] = ctx

        supervisor = SupervisorAgent()
        _runtime["supervisor"] = supervisor
        ctx._track_task(supervisor.start(), name="supervisor-daemon")
        ctx._track_task(_gui_logic_loop(ctx), name="gui-logic-loop")
        ctx._track_task(_gui_mod_update_loop(ctx), name="gui-mod-update")

        set_runtime_context(app_context=ctx, config_path=config_path, supervisor=supervisor)
        logger.info("Sky-Claw Daemon Core initialised; runtime context published.")

    app.on_startup(_bootstrap)

    async def _shutdown() -> None:
        ctx = _runtime.get("ctx")
        if ctx is not None:
            await ctx.stop()  # type: ignore[attr-defined]

    app.on_shutdown(_shutdown)

    ui.run(
        title="Sky-Claw",
        dark=True,
        show=True,
        reload=False,
        port=8080,
        host="127.0.0.1",
    )
