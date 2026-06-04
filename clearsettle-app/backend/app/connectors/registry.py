"""
ConnectorRegistry — maps source_type + platform to connector classes.

Usage:
    registry = get_connector_registry()
    connector = registry.build("amazon", credentials=creds, ...)
    async for event in connector.fetch_canonical_events(company_id, ...):
        ...

Registering a new connector:
    from app.connectors.registry import connector_registry
    from app.models.canonical.events import SourceType

    @connector_registry.register(SourceType.MY_NEW_API, platform="mynewplatform")
    class MyNewConnector(IngestionConnector):
        ...
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Type

from app.models.canonical.events import SourceType

logger = logging.getLogger(__name__)

_ConnectorClass = Any  # Type[IngestionConnector]


class ConnectorRegistry:
    """Singleton registry: (source_type, platform) → connector class."""

    def __init__(self) -> None:
        self._map: Dict[str, _ConnectorClass] = {}

    def register(
        self,
        source_type: SourceType,
        *,
        platform: Optional[str] = None,
    ):
        """Class decorator to register a connector."""
        def decorator(cls: _ConnectorClass) -> _ConnectorClass:
            key = self._key(source_type, platform or getattr(cls, "platform", None))
            self._map[key] = cls
            logger.debug("Registered connector %s → %s", key, cls.__name__)
            return cls
        return decorator

    def get_class(
        self,
        source_type: SourceType,
        platform: Optional[str] = None,
    ) -> Optional[_ConnectorClass]:
        key = self._key(source_type, platform)
        return self._map.get(key) or self._map.get(self._key(source_type, None))

    def build(
        self,
        source_type: SourceType,
        platform: Optional[str] = None,
        **constructor_kwargs,
    ) -> Any:
        """Instantiate a connector. Raises KeyError if not registered."""
        cls = self.get_class(source_type, platform)
        if cls is None:
            raise KeyError(
                f"No connector registered for source_type={source_type!r} "
                f"platform={platform!r}.  Register one with @connector_registry.register()"
            )
        return cls(**constructor_kwargs)

    def is_supported(self, source_type: SourceType, platform: Optional[str] = None) -> bool:
        return self.get_class(source_type, platform) is not None

    def list_registered(self) -> Dict[str, str]:
        return {k: v.__name__ for k, v in self._map.items()}

    @staticmethod
    def _key(source_type: SourceType, platform: Optional[str]) -> str:
        plat = (platform or "").lower().strip()
        return f"{source_type.value}::{plat}" if plat else source_type.value


# Singleton instance
connector_registry = ConnectorRegistry()


def get_connector_registry() -> ConnectorRegistry:
    return connector_registry


# ── Auto-register all built-in connectors ────────────────────────────────────
# Import here so the decorators run at module load time.

def _register_builtins() -> None:
    try:
        from app.connectors.manual_upload import ManualUploadConnector  # noqa: F401
    except Exception as e:
        logger.warning("Could not auto-register ManualUploadConnector: %s", e)

    try:
        from app.connectors.amazon.connector import AmazonConnector  # noqa: F401
    except Exception as e:
        logger.debug("AmazonConnector not available: %s", e)

    try:
        from app.connectors.flipkart.connector import FlipkartConnector  # noqa: F401
    except Exception as e:
        logger.debug("FlipkartConnector not available: %s", e)

    try:
        from app.connectors.meesho.connector import MeeshoConnector  # noqa: F401
    except Exception as e:
        logger.debug("MeeshoConnector not available: %s", e)


_register_builtins()
