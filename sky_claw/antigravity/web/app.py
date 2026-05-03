"""Sky-Claw web UI server — aiohttp application.

Routes
------
GET  /                    → HTML dashboard; redirects to /setup.html on first_run
GET  /api/setup           → loopback-only: read current LocalConfig as JSON
POST /api/setup           → loopback-only: persist LocalConfig fields from JSON body
GET  /api/auto-detect     → loopback-only: run AutoDetector and return discovered paths
POST /api/chat            → optional Bearer-token auth; delegates to router.chat()
POST /api/install-tools   → 503 when no tools_installer configured

Security contract
-----------------
- Setup and auto-detect endpoints are restricted to loopback addresses only.
- Exception details are never forwarded to HTTP clients (prevents information leakage).
- When an ``auth_manager`` is provided, ``/api/chat`` requires a valid Bearer token.
"""

from __future__ import annotations

import json
import logging
import pathlib
import sys
from typing import TYPE_CHECKING, Any

from aiohttp import web

from sky_claw.local import local_config as _local_config_mod
from sky_claw.local.auto_detect import AutoDetector
from sky_claw.local.local_config import load as load_local_config
from sky_claw.local.local_config import save as save_local_config

if TYPE_CHECKING:
    from sky_claw.antigravity.security.auth_token_manager import AuthTokenManager
    from sky_claw.local.local_config import LocalConfig

logger = logging.getLogger(__name__)

# Paths that require the request to originate from loopback.
_SETUP_PATHS: frozenset[str] = frozenset({"/api/setup", "/api/auto-detect"})

# Paths that require Bearer authentication when auth_manager is configured.
_AUTH_PATHS: frozenset[str] = frozenset({"/api/chat"})

# Accepted loopback addresses (IPv4, IPv6, IPv4-mapped IPv6).
_LOOPBACK_ADDRS: frozenset[str] = frozenset({"127.0.0.1", "::1", "::ffff:127.0.0.1"})

_INDEX_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Sky-Claw Operations Hub</title>
</head>
<body>
  <h1>Sky-Claw</h1>
  <p>Operations Hub is running.</p>
</body>
</html>
"""

_GENERIC_ERROR = "An internal error occurred. Please try again later."


# ---------------------------------------------------------------------------
# PyInstaller / frozen-mode path helpers
# ---------------------------------------------------------------------------


def _get_static_dir() -> pathlib.Path:
    """Return the static-assets directory, aware of PyInstaller frozen mode."""
    if getattr(sys, "frozen", False):
        return pathlib.Path(sys._MEIPASS) / "static"  # type: ignore[attr-defined]
    return pathlib.Path(__file__).parent / "static"


def _get_exe_dir() -> pathlib.Path:
    """Return the directory that contains the running executable (or CWD in dev)."""
    if getattr(sys, "frozen", False):
        return pathlib.Path(sys.executable).parent
    return pathlib.Path.cwd()


# ---------------------------------------------------------------------------
# Internal config helpers
# ---------------------------------------------------------------------------


def _load_cfg(config_path: pathlib.Path | None) -> LocalConfig:
    """Load LocalConfig, bypassing test monkeypatches when a path is provided.

    When *config_path* is given the underlying ``local_config.load`` function
    is called directly (via the module reference), so monkeypatches applied to
    the module-level alias ``load_local_config`` do not interfere.
    When *config_path* is *None* the (potentially patched) module-level alias
    is used — this is the behaviour expected by tests that inject fixtures via
    ``monkeypatch.setattr("sky_claw.antigravity.web.app.load_local_config", …)``.
    """
    if config_path is not None:
        return _local_config_mod.load(config_path)
    return load_local_config()


def _save_cfg(cfg: LocalConfig, config_path: pathlib.Path | None) -> None:
    """Persist LocalConfig, symmetric with :func:`_load_cfg`."""
    if config_path is not None:
        _local_config_mod.save(cfg, config_path)
    else:
        save_local_config(cfg)


class WebApp:
    """aiohttp-based web UI server for Sky-Claw.

    Parameters
    ----------
    router:
        Object exposing ``async chat(message, session) -> str``.
        May be *None* during the setup-wizard phase (lazy initialisation);
        ``/api/chat`` returns **503** until a router is assigned.
    session:
        Session context forwarded to ``router.chat``.
    config_path:
        Optional :class:`pathlib.Path` to the local config file.
        When *None* the default path from ``local_config`` is used.
    auth_manager:
        Optional :class:`~sky_claw.antigravity.security.auth_token_manager.AuthTokenManager`.
        When provided, ``/api/chat`` requires a valid Bearer token.
    tools_installer:
        Optional tools-installer object.  When *None*,
        ``POST /api/install-tools`` returns **503 Service Unavailable**.
    on_setup_complete:
        Optional ``async (web_app_instance) -> None`` callback invoked after
        ``POST /api/setup`` successfully saves the config.  Intended for lazy
        initialisation of the provider + router.  If the callback raises,
        ``/api/setup`` returns 500 with ``{"error": "initialization failed"}``.
    """

    def __init__(
        self,
        *,
        router: Any = None,
        session: Any = None,
        config_path: pathlib.Path | None = None,
        auth_manager: AuthTokenManager | None = None,
        tools_installer: Any = None,
        on_setup_complete: Any = None,
    ) -> None:
        self._router = router
        self._session = session
        self._config_path = config_path
        self._auth_manager = auth_manager
        self._tools_installer = tools_installer
        self._on_setup_complete = on_setup_complete

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_app(self) -> web.Application:
        """Build and return the configured :class:`aiohttp.web.Application`."""
        # ``_setup_auth_middleware`` is an instance method, so we cannot apply
        # ``@web.middleware`` at class definition time.  Wrap it here with a
        # new-style middleware closure so aiohttp receives a coroutine function
        # that carries the ``_is_middleware = True`` marker.
        _mw_impl = self._setup_auth_middleware

        @web.middleware
        async def _auth_middleware(
            request: web.Request,
            handler: Any,
        ) -> web.Response:
            return await _mw_impl(request, handler)

        app = web.Application(middlewares=[_auth_middleware])
        app.router.add_get("/", self._handle_index)
        app.router.add_get("/api/setup", self._handle_get_setup)
        app.router.add_post("/api/setup", self._handle_post_setup)
        app.router.add_get("/api/auto-detect", self._handle_auto_detect)
        app.router.add_post("/api/chat", self._handle_chat)
        app.router.add_post("/api/install-tools", self._handle_install_tools)
        return app

    # ------------------------------------------------------------------
    # Middleware (also called directly in tests for isolated unit checks)
    # ------------------------------------------------------------------

    async def _setup_auth_middleware(
        self,
        request: web.Request,
        handler: Any,
    ) -> web.Response:
        """Enforce loopback restriction and optional Bearer authentication.

        Setup/auto-detect paths → 403 for non-loopback origins.
        Chat path + auth_manager configured → 401 if token missing or invalid.
        All other paths pass through unchanged.
        """
        path = request.path

        # ── Loopback-only guard for setup endpoints ────────────────────
        if path in _SETUP_PATHS and request.remote not in _LOOPBACK_ADDRS:
            return web.Response(
                status=403,
                content_type="application/json",
                body=json.dumps({"error": "Forbidden: this endpoint is only accessible from localhost"}).encode(),
            )

        # ── Bearer token guard for chat endpoint ──────────────────────
        if path in _AUTH_PATHS and self._auth_manager is not None:
            auth_header = request.headers.get("Authorization", "")
            if not auth_header.startswith("Bearer "):
                return web.Response(
                    status=401,
                    content_type="application/json",
                    body=json.dumps({"error": "Unauthorized: Bearer token required"}).encode(),
                )
            token = auth_header[len("Bearer ") :]
            if not self._auth_manager.validate(token):
                return web.Response(
                    status=401,
                    content_type="application/json",
                    body=json.dumps({"error": "Unauthorized: invalid or expired token"}).encode(),
                )

        return await handler(request)

    # ------------------------------------------------------------------
    # Route handlers
    # ------------------------------------------------------------------

    async def _handle_index(self, _request: web.Request) -> web.Response:
        # When a config file is known, check first_run and redirect to the
        # setup wizard before the router is initialised.
        if self._config_path is not None:
            try:
                cfg = _load_cfg(self._config_path)
                if cfg.first_run:
                    return web.Response(
                        status=302,
                        headers={"Location": "/setup.html"},
                    )
            except Exception:
                logger.exception("Failed to read config for index redirect check")

        return web.Response(
            status=200,
            content_type="text/html",
            text=_INDEX_HTML,
        )

    async def _handle_get_setup(self, _request: web.Request) -> web.Response:
        try:
            cfg = _load_cfg(self._config_path)
            data: dict[str, Any] = {
                "first_run": cfg.first_run,
                "mo2_root": str(cfg.mo2_root or ""),
                "install_dir": str(cfg.install_dir or ""),
                "loot_exe": str(cfg.loot_exe or ""),
                "xedit_exe": str(cfg.xedit_exe or ""),
                "pandora_exe": str(cfg.pandora_exe or ""),
                "bodyslide_exe": str(cfg.bodyslide_exe or ""),
            }
            return web.Response(
                status=200,
                content_type="application/json",
                body=json.dumps(data).encode(),
            )
        except Exception:
            logger.exception("Failed to read local config")
            return web.Response(
                status=500,
                content_type="application/json",
                body=json.dumps({"error": _GENERIC_ERROR}).encode(),
            )

    async def _handle_post_setup(self, request: web.Request) -> web.Response:
        try:
            body = await request.json()
        except Exception:
            return web.Response(
                status=400,
                content_type="application/json",
                body=json.dumps({"error": "Invalid JSON body"}).encode(),
            )
        try:
            cfg = _load_cfg(self._config_path)

            # Plain path / string fields.
            for field in (
                "mo2_root",
                "install_dir",
                "loot_exe",
                "xedit_exe",
                "pandora_exe",
                "bodyslide_exe",
            ):
                if field in body:
                    setattr(cfg, field, body[field])

            # Secure key fields — stored obfuscated via LocalConfig helpers.
            if "api_key" in body:
                cfg.set_api_key(body["api_key"])
            if "nexus_api_key" in body:
                cfg.set_nexus_api_key(body["nexus_api_key"])

            cfg.first_run = False
            _save_cfg(cfg, self._config_path)
        except Exception:
            logger.exception("Failed to save local config")
            return web.Response(
                status=500,
                content_type="application/json",
                body=json.dumps({"error": _GENERIC_ERROR}).encode(),
            )

        # Invoke lazy-initialisation callback (e.g. start_full()).
        if self._on_setup_complete is not None:
            try:
                await self._on_setup_complete(self)
            except Exception:
                logger.exception("on_setup_complete callback failed")
                return web.Response(
                    status=500,
                    content_type="application/json",
                    body=json.dumps({"error": "initialization failed"}).encode(),
                )

        return web.Response(
            status=200,
            content_type="application/json",
            body=json.dumps({"ok": True}).encode(),
        )

    async def _handle_auto_detect(self, _request: web.Request) -> web.Response:
        try:
            result = await AutoDetector.detect_all()
            return web.Response(
                status=200,
                content_type="application/json",
                body=json.dumps(result).encode(),
            )
        except Exception:
            logger.exception("AutoDetector.detect_all failed")
            return web.Response(
                status=500,
                content_type="application/json",
                body=json.dumps({"error": _GENERIC_ERROR}).encode(),
            )

    async def _handle_chat(self, request: web.Request) -> web.Response:
        # Guard: router not yet initialised (setup-wizard / lazy-init phase).
        if self._router is None:
            return web.Response(
                status=503,
                content_type="application/json",
                body=json.dumps({"error": "El router no está configurado"}).encode(),
            )

        # Parse JSON body (400 on invalid JSON or missing/empty message).
        try:
            body = await request.json()
        except Exception:
            return web.Response(
                status=400,
                content_type="application/json",
                body=json.dumps({"error": "Invalid JSON body"}).encode(),
            )

        message: str = body.get("message", "")
        if not message:
            return web.Response(
                status=400,
                content_type="application/json",
                body=json.dumps({"error": "Field 'message' is required and must be non-empty"}).encode(),
            )

        # Delegate to router — mask any exception detail from the client.
        try:
            response_text = await self._router.chat(message, self._session)
            return web.Response(
                status=200,
                content_type="application/json",
                body=json.dumps({"response": response_text}).encode(),
            )
        except Exception:
            logger.exception("router.chat raised an exception")
            return web.Response(
                status=500,
                content_type="application/json",
                body=json.dumps({"error": _GENERIC_ERROR}).encode(),
            )

    async def _handle_install_tools(self, _request: web.Request) -> web.Response:
        """Return 503 when no tools installer has been configured."""
        if self._tools_installer is None:
            return web.Response(
                status=503,
                content_type="application/json",
                body=json.dumps({"error": "Tools installer is not configured"}).encode(),
            )
        # Future: delegate to self._tools_installer.install(…)
        return web.Response(
            status=200,
            content_type="application/json",
            body=json.dumps({"ok": True}).encode(),
        )
