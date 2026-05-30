import 'dart:typed_data';

import '../abstract_marketplace_parser.dart';
import '../parser_result.dart';

/// Meesho settlement report parser — Phase 2
class MeeshoParser implements AbstractMarketplaceParser {
  @override
  String get marketplace => 'meesho';

  @override
  String get parserVersion => '0.1.0-stub';

  @override
  bool canParse(Uint8List bytes, String fileName) {
    return fileName.toLowerCase().endsWith('.xlsx') ||
        fileName.toLowerCase().endsWith('.xls');
  }

  @override
  ParseResult parseSync(Uint8List bytes, String fileName, String fileHash) {
    return ParseResult(
      marketplace: marketplace,
      parserVersion: parserVersion,
      fileHash: fileHash,
      fileName: fileName,
      parsedAt: DateTime.now(),
      orders: [],
      errors: [
        const ParseError(
          code: 'NOT_IMPLEMENTED',
          message: 'Meesho parser is not yet implemented (Phase 2).',
          severity: ParseSeverity.info,
        ),
      ],
      warnings: [],
    );
  }
}
