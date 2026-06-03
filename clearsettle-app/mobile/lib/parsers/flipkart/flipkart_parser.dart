import 'dart:typed_data';

import 'package:excel/excel.dart';

import '../../../../core/utils/cs_logger.dart';
import '../abstract_marketplace_parser.dart';
import '../parser_result.dart';
import 'flipkart_column_aliases.dart';
import 'flipkart_sheet_detector.dart';

class FlipkartParser implements AbstractMarketplaceParser {
  @override
  String get marketplace => 'flipkart';

  @override
  String get parserVersion => '1.1.0';

  @override
  bool canParse(Uint8List bytes, String fileName) {
    final ext = fileName.toLowerCase();
    return ext.endsWith('.xlsx') || ext.endsWith('.xls');
  }

  @override
  ParseResult parseSync(Uint8List bytes, String fileName, String fileHash) {
    CsLogger.section('Flipkart Parser: $fileName  (${bytes.length} bytes)');
    final errors = <ParseError>[];
    final warnings = <ParseWarning>[];
    final sheetsFound = <String>[];

    Excel excel;
    try {
      excel = Excel.decodeBytes(bytes);
    } catch (e) {
      return ParseResult(
        marketplace: marketplace,
        parserVersion: parserVersion,
        fileHash: fileHash,
        fileName: fileName,
        parsedAt: DateTime.now(),
        orders: [],
        errors: [
          ParseError(
            code: 'DECODE_FAILED',
            message: 'Could not decode Excel file: $e',
            severity: ParseSeverity.critical,
          ),
        ],
        warnings: [],
        sheetsFound: [],
      );
    }

    if (excel.tables.isEmpty) {
      return ParseResult(
        marketplace: marketplace,
        parserVersion: parserVersion,
        fileHash: fileHash,
        fileName: fileName,
        parsedAt: DateTime.now(),
        orders: [],
        errors: [
          const ParseError(
            code: 'EMPTY_FILE',
            message: 'Excel file contains no sheets.',
            severity: ParseSeverity.critical,
          ),
        ],
        warnings: [],
        sheetsFound: [],
      );
    }

    List<ParsedOrder> orders = [];
    ParsedSummary? summary;

    final allSheets = excel.tables.keys.toList();
    CsLogger.info('Parser', 'Sheets in file', data: {
      'count': allSheets.length,
      'names': allSheets.join(' | '),
    });

    for (final sheetName in allSheets) {
      final sheet = excel.tables[sheetName]!;
      if (sheet.maxRows < 2) {
        CsLogger.info('Parser', 'Sheet skipped (too few rows)',
            data: {'sheet': sheetName, 'rows': sheet.maxRows});
        continue;
      }

      final rawHeaders = _extractHeaders(sheet);
      if (rawHeaders.isEmpty) {
        CsLogger.info('Parser', 'Sheet skipped (no headers)',
            data: {'sheet': sheetName});
        continue;
      }

      final type = FlipkartSheetDetector.detect(sheetName, rawHeaders);
      sheetsFound.add('$sheetName ($type)');
      CsLogger.info('Parser', 'Sheet classified',
          data: {'sheet': sheetName, 'type': type.name,
                 'cols': rawHeaders.where((h) => h.isNotEmpty).length});

      switch (type) {
        case SheetType.orders:
          final result = _parseOrdersSheet(
            sheet: sheet,
            headers: rawHeaders,
            sheetName: sheetName,
            errors: errors,
            warnings: warnings,
          );
          if (result.isNotEmpty) orders = result;

        case SheetType.summary:
          summary = _parseSummarySheet(
            sheet: sheet,
            headers: rawHeaders,
            sheetName: sheetName,
            warnings: warnings,
          );

        case SheetType.sku:
        case SheetType.ignore:
        case SheetType.unknown:
          // SKU sheet processed in Phase 2; unknown sheets warned only
          if (type == SheetType.unknown) {
            warnings.add(ParseWarning(
              code: 'UNKNOWN_SHEET',
              message: 'Sheet "$sheetName" could not be classified.',
            ));
          }
      }
    }

    if (orders.isEmpty && summary == null) {
      // Check if we at least got sheets (warnings from skipped sheets count as partial)
      final hasSkippedSheets = warnings.any(
        (w) => w.code == 'SHEET_SKIPPED_NO_ORDER_COLUMNS' || w.code == 'UNKNOWN_SHEET',
      );
      errors.add(ParseError(
        code: 'NO_PARSEABLE_DATA',
        message: 'No order or summary data could be extracted from this file. '
            '${hasSkippedSheets ? "Some sheets were skipped (see warnings). " : ""}'
            'Sheets found: ${sheetsFound.join(", ")}',
        // Only critical if there were no sheets at all — high if there were
        // sheets but none matched. Neither case should block backend processing.
        severity: sheetsFound.isEmpty ? ParseSeverity.critical : ParseSeverity.medium,
      ));
    }

    final result = ParseResult(
      marketplace: marketplace,
      parserVersion: parserVersion,
      fileHash: fileHash,
      fileName: fileName,
      parsedAt: DateTime.now(),
      orders: orders,
      summary: summary,
      errors: errors,
      warnings: warnings,
      sheetsFound: sheetsFound,
    );

    if (result.hasErrors) {
      CsLogger.error('Parser', 'Parse finished with errors', data: {
        'orders': orders.length,
        'errors': errors.map((e) => '${e.code}: ${e.message.substring(0, e.message.length.clamp(0, 80))}').join(' | '),
      });
    } else {
      CsLogger.info('Parser', 'Parse complete', data: {
        'orders': orders.length,
        'hasSummary': summary != null,
        'warnings': warnings.length,
        'sheets': sheetsFound.join(' | '),
      });
    }

    return result;
  }

  // ── Sheet extraction ────────────────────────────────────────────────────────

  List<String> _extractHeaders(Sheet sheet) {
    final rows = sheet.rows;
    if (rows.isEmpty) return [];

    // Keep ALL cells (no .where filter) so column indices stay aligned with
    // data rows. Some Flipkart files have a 1-row metadata header.
    for (final row in rows.take(5)) {
      final headers = row
          .map((cell) => _cellString(cell).toLowerCase().trim())
          .toList();
      if (headers.where((h) => h.isNotEmpty).length >= 3) return headers;
    }
    return [];
  }

  /// Finds the best header row for the Orders sheet by scoring alias matches.
  ///
  /// Flipkart quarterly payment reports use a multi-row header layout:
  ///   Row 1 — group labels: "Payment Details", "Transaction Summary", …
  ///   Row 2 — actual column names: "Order ID", "Sale Amount (Rs.)", …
  ///
  /// The simple "first row with ≥3 cells" picks the group-label row, causing
  /// ALL column lookups to fail. Scoring finds the row whose cell values best
  /// match known Flipkart column aliases.
  int _findOrdersHeaderRow(Sheet sheet) {
    final probeAliases = [
      ...FlipkartColumnAliases.orderId,
      ...FlipkartColumnAliases.grossAmount,
      ...FlipkartColumnAliases.netSettlement,
      ...FlipkartColumnAliases.settlementId,
      ...FlipkartColumnAliases.orderDate,
    ];

    int bestScore = 0;
    int bestIdx  = 0;

    for (int i = 0; i < sheet.rows.length && i < 5; i++) {
      final cells = sheet.rows[i]
          .map((c) => _cellString(c).toLowerCase().trim())
          .toList();
      if (cells.where((h) => h.isNotEmpty).length < 3) continue;

      int score = 0;
      for (final h in cells) {
        if (h.isEmpty) continue;
        for (final alias in probeAliases) {
          if (h == alias ||
              h.contains(alias) ||
              (alias.contains(h) && h.length >= 3)) {
            score++;
            break;
          }
        }
      }
      if (score > bestScore) {
        bestScore = score;
        bestIdx   = i;
      }
    }

    return bestIdx;
  }

  List<ParsedOrder> _parseOrdersSheet({
    required Sheet sheet,
    required List<String> headers, // kept for API compat; may be group-header row
    required String sheetName,
    required List<ParseError> errors,
    required List<ParseWarning> warnings,
  }) {
    // Use scoring to locate the real column-header row (row 2 for payment
    // reports, row 1 for standard P&L reports). Keep ALL cells so indices
    // align with data-row positions (empty spacer columns must not be skipped).
    final headerRowIdx = _findOrdersHeaderRow(sheet);
    final orderHeaders = headerRowIdx < sheet.rows.length
        ? sheet.rows[headerRowIdx]
            .map((c) => _cellString(c).toLowerCase().trim())
            .toList()
        : headers;

    final colMap = _buildColumnMap(orderHeaders);
    final orders = <ParsedOrder>[];

    final rows = sheet.rows;

    // Validate required columns are present
    final missingCols = <String>[];
    if (colMap[_kOrderId] == null) missingCols.add('Order ID');
    if (colMap[_kGrossAmount] == null) missingCols.add('Gross Amount');
    if (colMap[_kNetSettlement] == null) missingCols.add('Net Settlement');

    if (missingCols.length == 3) {
      // All three are missing — this sheet is not an order-level sheet.
      // Downgrade to WARNING (not high/critical) so other valid sheets in the
      // same file can still be parsed successfully. The report is not "failed".
      final foundHeaders = orderHeaders.where((h) => h.isNotEmpty).take(12).join(', ');
      warnings.add(ParseWarning(
        code: 'SHEET_SKIPPED_NO_ORDER_COLUMNS',
        message: 'Sheet "$sheetName" has no order-level columns '
            '(${missingCols.join(", ")} not found). '
            'Skipped. Headers found: $foundHeaders',
      ));
      return [];
    } else if (missingCols.isNotEmpty) {
      // Partial — warn but continue; missing columns will be null/zero
      warnings.add(ParseWarning(
        code: 'OPTIONAL_COLUMNS_MISSING',
        message: 'Sheet "$sheetName": columns not found — '
            '${missingCols.join(", ")}. Values will default to 0.',
      ));
    }

    for (int i = headerRowIdx + 1; i < rows.length; i++) {
      final row = rows[i];
      if (_isEmptyRow(row)) continue;

      try {
        final orderId = _str(row, colMap[_kOrderId]);
        final grossAmount = _num(row, colMap[_kGrossAmount]);
        final netSettlement = _num(row, colMap[_kNetSettlement]);

        // Skip rows that are clearly subtotals or labels (no order ID, no amounts)
        if (orderId == null && grossAmount == 0.0 && netSettlement == 0.0) continue;

        final order = ParsedOrder(
          orderId: orderId,
          settlementId: _str(row, colMap[_kSettlementId]),
          orderDate: _str(row, colMap[_kOrderDate]),
          sku: _str(row, colMap[_kSku]),
          productTitle: _str(row, colMap[_kProductTitle]),
          category: _str(row, colMap[_kCategory]),
          quantity: _numInt(row, colMap[_kQuantity]),
          grossAmount: grossAmount,
          commission: _num(row, colMap[_kCommission]).abs(),
          collectionFee: _num(row, colMap[_kCollectionFee]).abs(),
          shippingFee: _num(row, colMap[_kShippingFee]).abs(),
          reverseShippingFee: _num(row, colMap[_kReverseShippingFee]).abs(),
          fixedFee: _num(row, colMap[_kFixedFee]).abs(),
          pickPackFee: _num(row, colMap[_kPickPackFee]).abs(),
          gstOnFees: _num(row, colMap[_kGstOnFees]).abs(),
          tcs: _num(row, colMap[_kTcs]).abs(),
          tds: _num(row, colMap[_kTds]).abs(),
          netSettlement: netSettlement,
          status: _str(row, colMap[_kOrderStatus]),
          fulfilmentType: _str(row, colMap[_kFulfilmentType]),
          settlementDate: _str(row, colMap[_kSettlementDate]),
          rawCommissionRate: _numOrNull(row, colMap[_kCommissionRate]),
        );
        orders.add(order);
      } catch (e) {
        warnings.add(ParseWarning(
          code: 'ROW_PARSE_ERROR',
          message: 'Row ${i + 1}: $e',
          rowIndex: i,
        ));
      }
    }

    return orders;
  }

  ParsedSummary? _parseSummarySheet({
    required Sheet sheet,
    required List<String> headers,
    required String sheetName,
    required List<ParseWarning> warnings,
  }) {
    // Summary sheets are key-value: col0=label, col1=value
    final rows = sheet.rows;
    const labelCol = 0;
    final valueCol = headers.length > 1 ? 1 : 0;

    final kv = <String, double>{};

    for (final row in rows.skip(1)) {
      if (row.length <= labelCol) continue;
      final label = _cellString(row[labelCol]).toLowerCase().trim();
      if (label.isEmpty) continue;
      final value = _parseDouble(_cellString(
          row.length > valueCol ? row[valueCol] : null));

      kv[label] = value;
    }

    if (kv.isEmpty) return null;

    return ParsedSummary(
      grossSales: _kvLookup(kv, FlipkartColumnAliases.summaryGrossSales),
      returnsValue: _kvLookup(kv, FlipkartColumnAliases.summaryReturns).abs(),
      cancellationsValue: _kvLookup(kv, FlipkartColumnAliases.summaryCancellations).abs(),
      netSales: _kvLookup(kv, FlipkartColumnAliases.summaryNetSales),
      totalCommission: _kvLookup(kv, FlipkartColumnAliases.summaryCommission).abs(),
      totalShipping: _kvLookup(kv, FlipkartColumnAliases.summaryShipping).abs(),
      totalReverseShipping: _kvLookup(kv, FlipkartColumnAliases.summaryReverseShipping).abs(),
      totalCollectionFees: _kvLookup(kv, FlipkartColumnAliases.summaryCollectionFees).abs(),
      totalFixedFees: _kvLookup(kv, FlipkartColumnAliases.summaryFixedFees).abs(),
      totalGstOnFees: _kvLookup(kv, FlipkartColumnAliases.summaryGstOnFees).abs(),
      totalTcs: _kvLookup(kv, FlipkartColumnAliases.summaryTcs).abs(),
      totalTds: _kvLookup(kv, FlipkartColumnAliases.summaryTds).abs(),
      netEarnings: _kvLookup(kv, FlipkartColumnAliases.summaryNetEarnings),
      amountSettled: _kvLookup(kv, FlipkartColumnAliases.summaryAmountSettled),
      amountPending: _kvLookup(kv, FlipkartColumnAliases.summaryAmountPending),
      totalOrders: _kvLookup(kv, FlipkartColumnAliases.summaryTotalOrders).toInt(),
    );
  }

  // ── Column mapping ──────────────────────────────────────────────────────────

  static const String _kOrderId = 'order_id';
  static const String _kSettlementId = 'settlement_id';
  static const String _kOrderDate = 'order_date';
  static const String _kSettlementDate = 'settlement_date';
  static const String _kSku = 'sku';
  static const String _kProductTitle = 'product_title';
  static const String _kCategory = 'category';
  static const String _kQuantity = 'quantity';
  static const String _kOrderStatus = 'order_status';
  static const String _kFulfilmentType = 'fulfilment_type';
  static const String _kGrossAmount = 'gross_amount';
  static const String _kCommission = 'commission';
  static const String _kCollectionFee = 'collection_fee';
  static const String _kShippingFee = 'shipping_fee';
  static const String _kReverseShippingFee = 'reverse_shipping_fee';
  static const String _kFixedFee = 'fixed_fee';
  static const String _kPickPackFee = 'pick_pack_fee';
  static const String _kGstOnFees = 'gst_on_fees';
  static const String _kTcs = 'tcs';
  static const String _kTds = 'tds';
  static const String _kNetSettlement = 'net_settlement';
  static const String _kCommissionRate = 'commission_rate';

  Map<String, int?> _buildColumnMap(List<String> headers) {
    return {
      _kOrderId: _findColumn(headers, FlipkartColumnAliases.orderId),
      _kSettlementId: _findColumn(headers, FlipkartColumnAliases.settlementId),
      _kOrderDate: _findColumn(headers, FlipkartColumnAliases.orderDate),
      _kSettlementDate: _findColumn(headers, FlipkartColumnAliases.settlementDate),
      _kSku: _findColumn(headers, FlipkartColumnAliases.sku),
      _kProductTitle: _findColumn(headers, FlipkartColumnAliases.productTitle),
      _kCategory: _findColumn(headers, FlipkartColumnAliases.category),
      _kQuantity: _findColumn(headers, FlipkartColumnAliases.quantity),
      _kOrderStatus: _findColumn(headers, FlipkartColumnAliases.orderStatus),
      _kFulfilmentType: _findColumn(headers, FlipkartColumnAliases.fulfilmentType),
      _kGrossAmount: _findColumn(headers, FlipkartColumnAliases.grossAmount),
      _kCommission: _findColumn(headers, FlipkartColumnAliases.commission),
      _kCollectionFee: _findColumn(headers, FlipkartColumnAliases.collectionFee),
      _kShippingFee: _findColumn(headers, FlipkartColumnAliases.shippingFee),
      _kReverseShippingFee: _findColumn(headers, FlipkartColumnAliases.reverseShippingFee),
      _kFixedFee: _findColumn(headers, FlipkartColumnAliases.fixedFee),
      _kPickPackFee: _findColumn(headers, FlipkartColumnAliases.pickPackFee),
      _kGstOnFees: _findColumn(headers, FlipkartColumnAliases.gstOnFees),
      _kTcs: _findColumn(headers, FlipkartColumnAliases.tcs),
      _kTds: _findColumn(headers, FlipkartColumnAliases.tds),
      _kNetSettlement: _findColumn(headers, FlipkartColumnAliases.netSettlement),
      _kCommissionRate: _findColumn(headers, FlipkartColumnAliases.commissionRate),
    };
  }

  int? _findColumn(List<String> headers, List<String> aliases) {
    for (final alias in aliases) {
      // 1. Exact match
      final exact = headers.indexOf(alias);
      if (exact != -1) return exact;
      // 2. Header contains alias
      for (int i = 0; i < headers.length; i++) {
        if (headers[i].contains(alias)) return i;
      }
      // 3. Alias contains header (for short headers like 'sku')
      for (int i = 0; i < headers.length; i++) {
        if (alias.contains(headers[i]) && headers[i].length >= 3) return i;
      }
    }
    return null;
  }

  // ── Cell extraction helpers ─────────────────────────────────────────────────

  String _cellString(Data? cell) {
    if (cell == null) return '';
    final v = cell.value;
    if (v == null) return '';
    if (v is TextCellValue) return (v.value.text ?? '').trim();
    if (v is IntCellValue) return v.value.toString();
    if (v is DoubleCellValue) return v.value.toString();
    if (v is BoolCellValue) return v.value.toString();
    if (v is DateCellValue) {
      return '${v.year.toString().padLeft(4, '0')}-'
          '${v.month.toString().padLeft(2, '0')}-'
          '${v.day.toString().padLeft(2, '0')}';
    }
    if (v is DateTimeCellValue) {
      final dt = v.asDateTimeLocal();
      return dt.toIso8601String().split('T').first;
    }
    return v.toString().trim();
  }

  String? _str(List<Data?> row, int? col) {
    if (col == null || col >= row.length) return null;
    final s = _cellString(row[col]);
    return s.isEmpty ? null : s;
  }

  double _num(List<Data?> row, int? col) =>
      _numOrNull(row, col) ?? 0.0;

  double? _numOrNull(List<Data?> row, int? col) {
    if (col == null || col >= row.length) return null;
    return _parseDoubleOrNull(_cellString(row[col]));
  }

  int _numInt(List<Data?> row, int? col) {
    if (col == null || col >= row.length) return 1;
    final v = row[col]?.value;
    if (v is IntCellValue) return v.value;
    return _parseDouble(_cellString(row[col])).toInt().clamp(1, 99999);
  }

  double _parseDouble(String raw) => _parseDoubleOrNull(raw) ?? 0.0;

  double? _parseDoubleOrNull(String raw) {
    final cleaned = raw
        .replaceAll('₹', '')
        .replaceAll(',', '')
        .replaceAll(' ', '')
        .trim();
    if (cleaned.isEmpty ||
        cleaned == '-' ||
        cleaned.toLowerCase() == 'n/a' ||
        cleaned.toLowerCase() == 'null') { return null; }
    return double.tryParse(cleaned);
  }

  bool _isEmptyRow(List<Data?> row) =>
      row.every((c) => _cellString(c).isEmpty);

  double _kvLookup(Map<String, double> kv, List<String> aliases) {
    for (final alias in aliases) {
      // Exact match
      if (kv.containsKey(alias)) return kv[alias]!;
      // Partial match
      for (final key in kv.keys) {
        if (key.contains(alias) || alias.contains(key)) return kv[key]!;
      }
    }
    return 0.0;
  }
}
