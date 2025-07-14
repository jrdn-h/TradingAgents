"""
Graph package init
==================

During early development we want a *very light* import path so that
`python -m tradingagents run-demo` works even when big optional
dependencies (yfinance, langchain‑openai, etc.) are missing.

Hence:
* Always expose `Orchestrator` (zero heavy deps).
* Lazily expose other graph variants **only when their own imports succeed**.
"""

from importlib import import_module
import logging

logger = logging.getLogger(__name__)

# --- Always‑available orchestrator ------------------------------------------
try:
    from .orchestrator import Orchestrator  # noqa: F401
except Exception as err:  # pragma: no cover
    raise RuntimeError(f"Critical: failed to import Orchestrator: {err}") from err

__all__ = ["Orchestrator"]

# --- Optional graphs --------------------------------------------------------
def _try_import(opt_name: str):
    """Attempt to import an optional graph and expose it lazily."""
    try:
        mod = import_module(f".{opt_name}", package=__name__)
        globals()[opt_name] = mod  # type: ignore
        __all__.append(opt_name)
    except ModuleNotFoundError as err:
        logger.warning(
            "Optional graph '%s' unavailable (missing deps): %s", opt_name, err
        )

for _name in ("trading_graph", "setup"):
    _try_import(_name)
