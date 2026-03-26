"""Telegram Long Polling — active update retrieval.

Retrieves updates from Telegram via the getUpdates method. This is
suitable for local development or instances behind NAT that cannot
receive webhooks.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

from sky_claw.comms.telegram import TelegramWebhook

logger = logging.getLogger(__name__)

TELEGRAM_API_GET_UPDATES = "https://api.telegram.org/bot{token}/getUpdates"


class TelegramPolling:
    """Long polling client for Telegram Bot API.

    Args:
        token: Telegram Bot API token.
        webhook_handler: Instance of :class:`TelegramWebhook` to process updates.
        session: Shared aiohttp session.
        interval: Polling interval in seconds (default: 1.0).
    """

    def __init__(
        self,
        token: str,
        webhook_handler: TelegramWebhook,
        session: aiohttp.ClientSession,
        interval: float = 1.0,
    ) -> None:
        self._token = token
        self._handler = webhook_handler
        self._session = session
        self._interval = interval
        self._last_update_id = 0
        self._running = False
        self._url = TELEGRAM_API_GET_UPDATES.format(token=token)

    async def start(self) -> None:
        """Start the polling loop."""
        if self._running:
            return
        self._running = True
        logger.info("Telegram long polling started")
        asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        """Stop the polling loop."""
        self._running = False
        logger.info("Telegram long polling stopped")

    async def _run_loop(self) -> None:
        """Internal polling loop."""
        while self._running:
            try:
                await self._poll_once()
            except Exception as exc:
                logger.exception("Error in Telegram polling loop: %s", exc)
            await asyncio.sleep(self._interval)

    async def _poll_once(self) -> None:
        """Perform a single getUpdates request."""
        params = {
            "offset": self._last_update_id + 1,
            "timeout": 30,  # Long polling timeout in seconds
        }
        async with self._session.get(self._url, params=params) as resp:
            if resp.status != 200:
                logger.warning("Telegram getUpdates returned %d", resp.status)
                return
            
            data = await resp.json()
            if not data.get("ok"):
                logger.warning("Telegram getUpdates failed: %s", data.get("description"))
                return

            results = data.get("result", [])
            for update in results:
                update_id = update.get("update_id")
                if update_id:
                    self._last_update_id = update_id
                
                # We mock a web.Request-like object or just call a method
                # tailored for this. Since handle_update expects a web.Request,
                # we'll add a more direct processing method to TelegramWebhook
                # or just simulate the request if needed.
                # BETTER: Add a process_update method to TelegramWebhook.
                await self._process_raw_update(update)

    async def _process_raw_update(self, update: dict[str, Any]) -> None:
        """Process a single raw update dict."""
        # For now, we reuse the deduplication and logic by calling a helper
        # on the handler if we add one, or we just extract and call.
        
        # NOTE: TelegramWebhook uses _seen_updates for deduplication.
        # We can just manually call the same logic.
        
        # Let's assume we add process_update(data) to TelegramWebhook.
        if hasattr(self._handler, "process_update"):
            await self._handler.process_update(update)
        else:
            # Fallback if I haven't modified TelegramWebhook yet
            logger.warning("TelegramWebhook missing process_update method")
