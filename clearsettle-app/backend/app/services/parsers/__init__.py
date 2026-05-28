"""Parser framework: BaseParser, registry, and platform adapters."""
from app.services.parsers.base import BaseParser, ParseResult, LedgerRecord
from app.services.parsers.registry import get_parser, PARSER_REGISTRY

__all__ = ["BaseParser", "ParseResult", "LedgerRecord", "get_parser", "PARSER_REGISTRY"]
