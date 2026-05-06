"""Compatibility shims for upstream third-party dependencies.

Centralizes polyfills required to keep transitively-pulled libraries
(currently `vbuild` via NiceGUI) running on newer Python interpreters.
Removable as a single unit once upstream catches up.
"""

from __future__ import annotations

import importlib.util
import pkgutil
import sys


def setup_python_compat() -> None:
    """Apply global polyfills for deprecated Python features used by 3rd-party libs.

    - Python 3.14 removed `pkgutil.find_loader` (deprecated since 3.4).
      `vbuild` (pulled by NiceGUI) still calls it; redirect to the
      modern `importlib.util.find_spec` equivalent.
    """
    if sys.version_info >= (3, 14):
        if not hasattr(pkgutil, "find_loader"):
            pkgutil.find_loader = importlib.util.find_spec  # type: ignore[attr-defined]
