import 'dart:typed_data';

import 'package:excel/excel.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:clearsettle_mobile/parsers/flipkart/flipkart_parser.dart';
import 'package:clearsettle_mobile/parsers/parser_result.dart';

void main() {
  late FlipkartParser parser;

  setUp(() {
    parser = FlipkartParser();
  });

  // ── canParse ──────────────────────────────────────────────────────────────

  group('canParse', () {
    test('accepts .xlsx', () {
      expect(parser.canParse(Uint8List(0), 'report.xlsx'), isTrue);
    });

    test('accepts .xls', () {
      expect(parser.canParse(Uint8List(0), 'report.xls'), isTrue);
    });

    test('rejects .csv', () {
      expect(parser.canParse(Uint8List(0), 'report.csv'), isFalse);
    });

    test('rejects .pdf', () {
      expect(parser.canParse(Uint8List(0), 'report.pdf'), isFalse);
    });

    test('case-insensitive extension', () {
      expect(parser.canParse(Uint8List(0), 'REPORT.XLSX'), isTrue);
    });
  });

  // ── Corrupt / empty files ─────────────────────────────────────────────────

  group('corrupt / empty input', () {
    test('returns critical error for random bytes', () {
      final result = parser.parseSync(
        Uint8List.fromList(List.generate(512, (i) => i % 256)),
        'corrupt.xlsx',
        'fakehash',
      );
      expect(result.hasCriticalErrors, isTrue);
      expect(result.orders, isEmpty);
    });

    test('returns critical error for empty bytes', () {
      final result =
          parser.parseSync(Uint8List(0), 'empty.xlsx', 'fakehash');
      expect(result.hasCriticalErrors, isTrue);
    });

    test('returns error for Excel with no sheets', () {
      final excel = Excel.createExcel();
      // Remove the default sheet
      excel.delete('Sheet1');
      final bytes = Uint8List.fromList(excel.encode()!);
      final result = parser.parseSync(bytes, 'nosheet.xlsx', 'fakehash');
      expect(result.hasCriticalErrors, isTrue);
    });
  });

  // ── Missing columns ───────────────────────────────────────────────────────

  group('missing columns', () {
    test('emits high-severity error when all key columns absent', () {
      final excel = Excel.createExcel();
      final sheet = excel['Orders'];
      sheet.appendRow([
        TextCellValue('SKU'),
        TextCellValue('Title'),
      ]);
      sheet.appendRow([
        TextCellValue('SKU001'),
        TextCellValue('T-Shirt'),
      ]);
      final bytes = Uint8List.fromList(excel.encode()!);
      final result = parser.parseSync(bytes, 'nocols.xlsx', 'fakehash');

      expect(
        result.errors.any((e) =>
            e.severity == ParseSeverity.high ||
            e.severity == ParseSeverity.critical),
        isTrue,
      );
    });
  });

  // ── Standard order sheet parsing ──────────────────────────────────────────

  group('standard Flipkart orders sheet', () {
    Uint8List _buildStandardExcel({
      String orderId = 'OD12345678901',
      double grossAmount = 1000.0,
      double commission = 100.0,
      double collectionFee = 20.0,
      double shippingFee = 50.0,
      double gst = 30.0,
      double tcs = 10.0,
      double tds = 5.0,
      double netSettlement = 785.0,
    }) {
      final excel = Excel.createExcel();
      final sheet = excel['Orders'];
      sheet.appendRow([
        TextCellValue('Order ID'),
        TextCellValue('Order Date'),
        TextCellValue('Seller SKU'),
        TextCellValue('Product Title'),
        TextCellValue('Gross Amount'),
        TextCellValue('Commission (Rs.)'),
        TextCellValue('Collection Fee (Rs.)'),
        TextCellValue('Shipping Fee (Rs.)'),
        TextCellValue('GST on MP Fees (Rs.)'),
        TextCellValue('TCS (Rs.)'),
        TextCellValue('TDS (Rs.)'),
        TextCellValue('Net Earnings'),
      ]);
      sheet.appendRow([
        TextCellValue(orderId),
        TextCellValue('2025-01-15'),
        TextCellValue('SKU-001'),
        TextCellValue('Blue Kurti - L'),
        DoubleCellValue(grossAmount),
        DoubleCellValue(commission),
        DoubleCellValue(collectionFee),
        DoubleCellValue(shippingFee),
        DoubleCellValue(gst),
        DoubleCellValue(tcs),
        DoubleCellValue(tds),
        DoubleCellValue(netSettlement),
      ]);
      return Uint8List.fromList(excel.encode()!);
    }

    test('parses one order correctly', () {
      final bytes = _buildStandardExcel();
      final result = parser.parseSync(bytes, 'standard.xlsx', 'hash1');

      expect(result.orders, hasLength(1));
      final order = result.orders.first;

      expect(order.orderId, equals('OD12345678901'));
      expect(order.grossAmount, equals(1000.0));
      expect(order.commission, equals(100.0));
      expect(order.collectionFee, equals(20.0));
      expect(order.shippingFee, equals(50.0));
      expect(order.gstOnFees, equals(30.0));
      expect(order.tcs, equals(10.0));
      expect(order.tds, equals(5.0));
      expect(order.netSettlement, equals(785.0));
      expect(order.sku, equals('SKU-001'));
    });

    test('records marketplace and parser version', () {
      final result = parser.parseSync(
          _buildStandardExcel(), 'test.xlsx', 'hash2');
      expect(result.marketplace, equals('flipkart'));
      expect(result.parserVersion, isNotEmpty);
    });

    test('sets file hash from parameter', () {
      const hash = 'abc123def456';
      final result = parser.parseSync(
          _buildStandardExcel(), 'test.xlsx', hash);
      expect(result.fileHash, equals(hash));
    });

    test('skips empty rows', () {
      final excel = Excel.createExcel();
      final sheet = excel['Orders'];
      sheet.appendRow([
        TextCellValue('Order ID'),
        TextCellValue('Gross Amount'),
        TextCellValue('Net Earnings'),
      ]);
      sheet.appendRow([TextCellValue(''), TextCellValue(''), TextCellValue('')]);
      sheet.appendRow([
        TextCellValue('OD999'),
        DoubleCellValue(500.0),
        DoubleCellValue(400.0),
      ]);
      final bytes = Uint8List.fromList(excel.encode()!);
      final result = parser.parseSync(bytes, 'gaps.xlsx', 'h');
      expect(result.orders, hasLength(1));
      expect(result.orders.first.orderId, equals('OD999'));
    });
  });

  // ── Malformed amounts ─────────────────────────────────────────────────────

  group('malformed amounts', () {
    test('handles rupee symbol in cell string', () {
      final excel = Excel.createExcel();
      final sheet = excel['Orders'];
      sheet.appendRow([
        TextCellValue('Order ID'),
        TextCellValue('Gross Amount'),
        TextCellValue('Net Earnings'),
      ]);
      sheet.appendRow([
        TextCellValue('OD1'),
        TextCellValue('₹1,500.00'),
        TextCellValue('₹1,200.50'),
      ]);
      final bytes = Uint8List.fromList(excel.encode()!);
      final result = parser.parseSync(bytes, 'rupee.xlsx', 'h');
      expect(result.orders, hasLength(1));
      expect(result.orders.first.grossAmount, equals(1500.0));
      expect(result.orders.first.netSettlement, closeTo(1200.5, 0.01));
    });

    test('treats N/A as zero', () {
      final excel = Excel.createExcel();
      final sheet = excel['Orders'];
      sheet.appendRow([
        TextCellValue('Order ID'),
        TextCellValue('Gross Amount'),
        TextCellValue('Net Earnings'),
      ]);
      sheet.appendRow([
        TextCellValue('OD2'),
        TextCellValue('N/A'),
        TextCellValue('-'),
      ]);
      final bytes = Uint8List.fromList(excel.encode()!);
      final result = parser.parseSync(bytes, 'na.xlsx', 'h');
      expect(result.orders.first.grossAmount, equals(0.0));
      expect(result.orders.first.netSettlement, equals(0.0));
    });

    test('handles comma-formatted numbers', () {
      final excel = Excel.createExcel();
      final sheet = excel['Orders'];
      sheet.appendRow([
        TextCellValue('Order ID'),
        TextCellValue('Gross Amount'),
        TextCellValue('Net Earnings'),
      ]);
      sheet.appendRow([
        TextCellValue('OD3'),
        TextCellValue('2,50,000.00'),
        TextCellValue('1,85,000.00'),
      ]);
      final bytes = Uint8List.fromList(excel.encode()!);
      final result = parser.parseSync(bytes, 'commas.xlsx', 'h');
      expect(result.orders.first.grossAmount, equals(250000.0));
    });
  });

  // ── Column alias matching ─────────────────────────────────────────────────

  group('column alias matching', () {
    test('matches "Sale Amount (Rs.)" as gross amount', () {
      final excel = Excel.createExcel();
      final sheet = excel['Orders'];
      sheet.appendRow([
        TextCellValue('Order ID'),
        TextCellValue('Sale Amount (Rs.)'),
        TextCellValue('Net Earnings'),
      ]);
      sheet.appendRow([
        TextCellValue('OD10'),
        DoubleCellValue(800.0),
        DoubleCellValue(650.0),
      ]);
      final bytes = Uint8List.fromList(excel.encode()!);
      final result = parser.parseSync(bytes, 'alias.xlsx', 'h');
      expect(result.orders.first.grossAmount, equals(800.0));
    });

    test('matches "Marketplace Fee (Rs.)" as commission', () {
      final excel = Excel.createExcel();
      final sheet = excel['Orders'];
      sheet.appendRow([
        TextCellValue('Order ID'),
        TextCellValue('Gross Amount'),
        TextCellValue('Marketplace Fee (Rs.)'),
        TextCellValue('Net Earnings'),
      ]);
      sheet.appendRow([
        TextCellValue('OD11'),
        DoubleCellValue(500.0),
        DoubleCellValue(75.0),
        DoubleCellValue(425.0),
      ]);
      final bytes = Uint8List.fromList(excel.encode()!);
      final result = parser.parseSync(bytes, 'mktfee.xlsx', 'h');
      expect(result.orders.first.commission, equals(75.0));
    });
  });

  // ── Large file performance ─────────────────────────────────────────────────

  group('performance', () {
    test('parses 1000-row file within 30 seconds', () {
      final excel = Excel.createExcel();
      final sheet = excel['Orders'];
      sheet.appendRow([
        TextCellValue('Order ID'),
        TextCellValue('Gross Amount'),
        TextCellValue('Commission (Rs.)'),
        TextCellValue('Net Earnings'),
      ]);
      for (int i = 0; i < 1000; i++) {
        sheet.appendRow([
          TextCellValue('OD${1000000 + i}'),
          DoubleCellValue(500.0 + i),
          DoubleCellValue(50.0),
          DoubleCellValue(450.0 + i),
        ]);
      }
      final bytes = Uint8List.fromList(excel.encode()!);

      final stopwatch = Stopwatch()..start();
      final result = parser.parseSync(bytes, 'large.xlsx', 'hash_large');
      stopwatch.stop();

      expect(result.orders, hasLength(1000));
      expect(stopwatch.elapsed.inSeconds, lessThan(30));
    });
  });

  // ── Summary sheet ─────────────────────────────────────────────────────────

  group('summary sheet parsing', () {
    test('extracts gross sales from summary-named sheet', () {
      final excel = Excel.createExcel();
      final sheet = excel['Overall Summary'];
      sheet.appendRow([TextCellValue('Metric'), TextCellValue('Amount')]);
      sheet.appendRow([
        TextCellValue('Gross Sales'),
        DoubleCellValue(50000.0),
      ]);
      sheet.appendRow([
        TextCellValue('Net Earnings'),
        DoubleCellValue(38000.0),
      ]);
      final bytes = Uint8List.fromList(excel.encode()!);
      final result = parser.parseSync(bytes, 'summary.xlsx', 'hs');

      expect(result.summary, isNotNull);
      expect(result.summary!.grossSales, equals(50000.0));
      expect(result.summary!.netEarnings, equals(38000.0));
    });
  });
}
