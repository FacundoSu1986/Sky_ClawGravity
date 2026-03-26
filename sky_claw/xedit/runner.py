"""xEdit headless runner — async subprocess wrapper.

Executes SSEEdit (xEdit) scripts in headless mode via
``asyncio.create_subprocess_exec`` with configurable timeout
and input validation to prevent path traversal and command injection.
"""

from __future__ import annotations

import asyncio
import logging
import pathlib
import re
import sys

from sky_claw.security.path_validator import PathValidator
from sky_claw.xedit.output_parser import XEditOutputParser, XEditResult

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 120

# Only allow safe script names: alphanumeric, underscores, hyphens, dots.
_SAFE_SCRIPT_NAME = re.compile(r"^[a-zA-Z0-9_\-]+\.pas$")

# Only allow safe plugin names.
_SAFE_PLUGIN_NAME = re.compile(r"^[a-zA-Z0-9_\- .]+\.es[pmlt]$")


class XEditNotFoundError(FileNotFoundError):
    """Raised when the xEdit executable is not found."""


class XEditValidationError(ValueError):
    """Raised when input fails validation."""


class XEditRunner:
    """Async wrapper for xEdit headless execution.

    Args:
        xedit_path: Path to SSEEdit.exe.
        game_path: Path to the Skyrim SE installation.
        timeout: Maximum execution time in seconds.
        path_validator: Optional validator for path sandboxing.
    """

    def __init__(
        self,
        xedit_path: pathlib.Path,
        game_path: pathlib.Path,
        timeout: int = DEFAULT_TIMEOUT,
        path_validator: PathValidator | None = None,
    ) -> None:
        self._xedit_path = xedit_path
        self._game_path = game_path
        self._timeout = timeout
        self._validator = path_validator

    async def run_script(
        self,
        script_name: str,
        plugins: list[str],
    ) -> XEditResult:
        """Execute an xEdit Pascal script in headless mode.

        Args:
            script_name: Name of the .pas script (e.g. ``list_conflicts.pas``).
                Must match ``^[a-zA-Z0-9_\\-]+\\.pas$``.
            plugins: List of plugin filenames to load.
                Each must match ``^[a-zA-Z0-9_\\- .]+\\.es[pmlt]$``.

        Returns:
            Parsed xEdit result with conflicts and processed plugins.

        Raises:
            XEditNotFoundError: If the xEdit executable doesn't exist.
            XEditValidationError: If inputs fail validation.
            RuntimeError: If xEdit times out.
        """
        self._validate_inputs(script_name, plugins)

        if self._validator is not None:
            self._validator.validate(self._xedit_path)

        if not self._xedit_path.exists():
            raise XEditNotFoundError(
                f"xEdit executable not found at {self._xedit_path}"
            )

        args = [
            str(self._xedit_path),
            "-SSE",
            "-autoload",
            f'-script:"{script_name}"',
            "-D:" + str(self._game_path),
        ]

        # Append plugins to load.
        for plugin in plugins:
            args.append(plugin)

        logger.info("Running xEdit: %s", " ".join(args))

        # Windows: CREATE_NO_WINDOW to avoid console popups.
        kwargs: dict = {}
        if sys.platform == "win32":
            kwargs["creationflags"] = 0x08000000  # CREATE_NO_WINDOW

        try:
            proc = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                **kwargs,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=self._timeout,
            )
        except FileNotFoundError:
            raise XEditNotFoundError(
                f"xEdit executable not found at {self._xedit_path}"
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.communicate()
            raise RuntimeError(
                f"xEdit timed out after {self._timeout}s"
            )

        stdout_text = stdout.decode(errors="replace")
        stderr_text = stderr.decode(errors="replace")

        if proc.returncode != 0:
            logger.warning(
                "xEdit exited with code %d: %s", proc.returncode, stderr_text
            )

        return XEditOutputParser.parse(
            stdout=stdout_text,
            stderr=stderr_text,
            return_code=proc.returncode or 0,
        )

    def _validate_inputs(
        self, script_name: str, plugins: list[str]
    ) -> None:
        """Validate script name and plugin names against injection."""
        if not _SAFE_SCRIPT_NAME.match(script_name):
            raise XEditValidationError(
                f"Invalid script name: {script_name!r}. "
                f"Must match {_SAFE_SCRIPT_NAME.pattern}"
            )

        for plugin in plugins:
            if not _SAFE_PLUGIN_NAME.match(plugin):
                raise XEditValidationError(
                    f"Invalid plugin name: {plugin!r}. "
                    f"Must match {_SAFE_PLUGIN_NAME.pattern}"
                )
