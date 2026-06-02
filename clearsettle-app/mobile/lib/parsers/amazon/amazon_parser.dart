import 'dart:typed_data';

import '../abstract_marketplace_parser.dart';
import '../parser_result.dart';

/// Amazon SP-API report parser — Phase 2
class AmazonParser implements AbstractMarketplaceParser {
  @override
  String get marketplace => 'amazon';

  @override
  String get parserVersion => '0.1.0-stub';

  @override
  bool canParse(Uint8List bytes, String fileName) {
    // Amazon settlement reports are TSV (tab-separated), not XLSX
    return fileName.toLowerCase().endsWith('.txt') ||
        fileName.toLowerCase().endsWith('.tsv');
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
          message: 'Amazon parser is not yet implemented (Phase 2).',
          severity: ParseSeverity.info,
        ),
      ],
      warnings: [],
    );
  }
}
