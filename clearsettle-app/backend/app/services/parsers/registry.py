"""
Parser Registry.

Maps parser_name strings (as stored in report_schema_versions.parser_name
and detection results) to the concrete parser class instances.

Usage:
    parser = get_parser("FlipkartPLParser")
    result = parser.parse(file_bytes)

To add a new parser:
  1. Create a subclass of BaseParser in the appropriate platform folder
  2. Set parser_name, platform, report_type class attributes
  3. Add an entry to PARSER_REGISTRY below
"""
from __future__ import annotations

from typing import Dict, Optional, Type

from app.services.parsers.base import BaseParser


def _build_registry() -> Dict[str, Type[BaseParser]]:
    from app.services.parsers.flipkart.pl_parser      import FlipkartPLParser
    from app.services.parsers.flipkart.payment_parser import FlipkartPaymentParser
    from app.services.parsers.amazon.settlement_parser import AmazonSettlementParser
    from app.services.parsers.meesho.payment_parser   import MeeshoPaymentParser

    return {
        cls.parser_name: cls
        for cls in [
            FlipkartPLParser,
            FlipkartPaymentParser,
            AmazonSettlementParser,
            MeeshoPaymentParser,
        ]
    }


# Lazy-initialised registry (avoids circular imports at module load time)
_REGISTRY: Optional[Dict[str, Type[BaseParser]]] = None


@property
def PARSER_REGISTRY() -> Dict[str, Type[BaseParser]]:
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = _build_registry()
    return _REGISTRY


def get_parser(parser_name: str) -> BaseParser:
    """
    Instantiate and return the parser for the given parser_name.
    Falls back to a GenericParser that emits a single error record
    if the name is not registered.
    """
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = _build_registry()

    cls = _REGISTRY.get(parser_name)
    if cls is None:
        return _GenericParser(parser_name=parser_name)
    return cls()


# ── Fallback parser for unknown/unregistered parser names ────────────────────

class _GenericParser(BaseParser):
    """Used when no matching parser exists; records the gap without crashing."""

    def __init__(self, parser_name: str = "GenericParser"):
        self.parser_name = parser_name

    def parse(self, file_bytes: bytes, **kwargs):
        result = self._make_result()
        result.errors.append(
            f"No parser registered for '{self.parser_name}'. "
            "Register a concrete BaseParser subclass in parsers/registry.py."
        )
        return result
