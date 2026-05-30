import 'dart:typed_data';

import 'parser_result.dart';

abstract interface class AbstractMarketplaceParser {
  /// Marketplace identifier (lowercase): 'flipkart', 'amazon', 'meesho'
  String get marketplace;

  /// Semver parser version — recorded in ParseResult for auditability
  String get parserVersion;

  /// Returns true if this parser can handle the given file
  bool canParse(Uint8List bytes, String fileName);

  /// Synchronous parse — called inside an isolate via compute()
  ParseResult parseSync(Uint8List bytes, String fileName, String fileHash);
}
