"""
Light-weight package init.

Only import modules whose dependencies are known to be present.
Heavier feeds (e.g. ones that transitively require yfinance or
other optional libraries) are lazily imported on first use.

This keeps `import tradingagents.dataflows` cheap so the
orchestrator CLI can run even in minimal environments.
"""

from importlib import import_module
import logging

logger = logging.getLogger(__name__)

__all__ = []

# Feeds that rely *only* on stdlib or already-installed deps
for _mod in ("hyperliquid_utils",):
    try:
        m = import_module(f".{_mod}", package=__name__)
        globals()[_mod] = m
        __all__.append(_mod)
    except Exception as err:  # pragma: no cover
        logger.warning("Failed to import %s: %s", _mod, err)

# Optional feeds — import on demand
def __getattr__(name: str):
    """Lazy-load optional dataflow modules."""
    if name in {"twitter_utils", "news_utils", "whale_alert_utils"}:
        try:
            m = import_module(f".{name}", package=__name__)
            globals()[name] = m
            return m
        except ModuleNotFoundError as err:
            raise AttributeError(
                f"Module '{name}' requires optional dependencies: {err}"
            ) from err
    raise AttributeError(name)
