import 'dart:typed_data';

import 'abstract_marketplace_parser.dart';
import 'amazon/amazon_parser.dart';
import 'flipkart/flipkart_parser.dart';
import 'meesho/meesho_parser.dart';

/// Central registry — maps marketplace ids to parser factories.
/// Add new parsers here as new marketplaces are onboarded.
abstract final class ParserRegistry {
  static final Map<String, AbstractMarketplaceParser Function()> _factories = {
    'flipkart': FlipkartParser.new,
    'amazon': AmazonParser.new,
    'meesho': MeeshoParser.new,
  };

  /// Returns the parser for [marketplace], or null if not registered.
  static AbstractMarketplaceParser? forMarketplace(String marketplace) {
    final factory = _factories[marketplace.toLowerCase()];
    return factory?.call();
  }

  /// Auto-detects the correct parser by probing [bytes] and [fileName].
  /// Returns the first parser whose [canParse] returns true.
  static AbstractMarketplaceParser? detect(Uint8List bytes, String fileName) {
    // Priority: Flipkart first (most common), then others
    for (final factory in _factories.values) {
      final parser = factory();
      if (parser.canParse(bytes, fileName)) return parser;
    }
    return null;
  }

  /// All registered marketplace ids.
  static List<String> get marketplaces => _factories.keys.toList();
}
