import 'package:flutter_test/flutter_test.dart';

import 'package:clearsettle_mobile/parsers/parser_result.dart';
import 'package:clearsettle_mobile/reconciliation/reconciliation_engine.dart';
import 'package:clearsettle_mobile/reconciliation/reconciliation_result.dart';

void main() {
  late ReconciliationEngine engine;

  setUp(() {
    engine = ReconciliationEngine();
  });

  ParseResult makeResult({
    List<ParsedOrder> orders = const [],
    ParsedSummary? summary,
  }) {
    return ParseResult(
      marketplace: 'flipkart',
      parserVersion: '1.0.0',
      fileHash: 'testhash',
      fileName: 'test.xlsx',
      parsedAt: DateTime.now(),
      orders: orders,
      summary: summary,
      errors: [],
      warnings: [],
    );
  }

  // ── Clean report ──────────────────────────────────────────────────────────

  group('clean report', () {
    test('produces no discrepancies for perfectly reconciled orders', () {
      // gross=1000, commission=100, collectionFee=20, shipping=50,
      // gst=30, tcs=10, tds=5 → totalFees=215 → expected net = 785
      final orders = [
        const ParsedOrder(
          orderId: 'OD001',
          grossAmount: 1000.0,
          commission: 100.0,
          collectionFee: 20.0,
          shippingFee: 50.0,
          gstOnFees: 30.0,
          tcs: 10.0,
          tds: 5.0,
          netSettlement: 785.0,
        ),
      ];
      final result = engine.reconcile(makeResult(orders: orders), 'R1');
      expect(result.isClean, isTrue);
      expect(result.discrepancyCount, equals(0));
    });

    test('metadata is correctly populated', () {
      final result = engine.reconcile(makeResult(), 'RPT-42');
      expect(result.reportId, equals('RPT-42'));
      expect(result.marketplace, equals('flipkart'));
      expect(result.reconciledAt, isA<DateTime>());
    });
  });

  // ── Settlement mismatch ───────────────────────────────────────────────────

  group('settlement validator', () {
    test('detects settlement variance > ₹1', () {
      final orders = [
        const ParsedOrder(
          orderId: 'OD002',
          grossAmount: 1000.0,
          commission: 100.0,
          netSettlement: 600.0, // expected ~900
        ),
      ];
      final result = engine.reconcile(makeResult(orders: orders), 'R2');
      expect(
        result.discrepancies.any(
            (d) => d.type == DiscrepancyType.settlementMismatch),
        isTrue,
      );
    });

    test('within ₹1 tolerance is not flagged', () {
      final orders = [
        const ParsedOrder(
          orderId: 'OD003',
          grossAmount: 500.0,
          commission: 50.0,
          netSettlement: 449.5, // expected 450 — variance 0.50
        ),
      ];
      final result = engine.reconcile(makeResult(orders: orders), 'R3');
      expect(
        result.discrepancies
            .any((d) => d.type == DiscrepancyType.settlementMismatch),
        isFalse,
      );
    });

    test('flags missing settlement when gross > 10 and net = 0', () {
      final orders = [
        const ParsedOrder(
          orderId: 'OD004',
          grossAmount: 500.0,
          netSettlement: 0.0,
        ),
      ];
      final result = engine.reconcile(makeResult(orders: orders), 'R4');
      expect(
        result.discrepancies
            .any((d) => d.type == DiscrepancyType.missingSettlement),
        isTrue,
      );
    });

    test('critical severity for variance >= ₹500', () {
      final orders = [
        const ParsedOrder(
          orderId: 'OD005',
          grossAmount: 5000.0,
          commission: 500.0,
          netSettlement: 3000.0, // expected 4500 → variance 1500
        ),
      ];
      final result = engine.reconcile(makeResult(orders: orders), 'R5');
      final mismatch = result.discrepancies.firstWhere(
        (d) => d.type == DiscrepancyType.settlementMismatch,
      );
      expect(mismatch.severity, equals(DiscrepancySeverity.critical));
    });
  });

  // ── Commission validator ──────────────────────────────────────────────────

  group('commission validator', () {
    test('no flag when commission rate not provided', () {
      final orders = [
        const ParsedOrder(
          orderId: 'OD010',
          grossAmount: 1000.0,
          commission: 200.0, // high but no rate to check against
          netSettlement: 800.0,
          rawCommissionRate: null,
        ),
      ];
      final result = engine.reconcile(makeResult(orders: orders), 'R10');
      expect(
        result.discrepancies
            .any((d) => d.type == DiscrepancyType.commissionOvercharge),
        isFalse,
      );
    });

    test('flags commission overcharge when actual > rate * gross', () {
      // Expected: 10% of 1000 = 100; actual = 150 → overcharge 50
      final orders = [
        const ParsedOrder(
          orderId: 'OD011',
          grossAmount: 1000.0,
          commission: 150.0,
          netSettlement: 700.0,
          rawCommissionRate: 10.0,
        ),
      ];
      final result = engine.reconcile(makeResult(orders: orders), 'R11');
      expect(
        result.discrepancies
            .any((d) => d.type == DiscrepancyType.commissionOvercharge),
        isTrue,
      );
    });

    test('no flag when commission exactly matches rate', () {
      final orders = [
        const ParsedOrder(
          orderId: 'OD012',
          grossAmount: 1000.0,
          commission: 100.0,  // exactly 10%
          netSettlement: 900.0,
          rawCommissionRate: 10.0,
        ),
      ];
      final result = engine.reconcile(makeResult(orders: orders), 'R12');
      expect(
        result.discrepancies
            .any((d) => d.type == DiscrepancyType.commissionOvercharge),
        isFalse,
      );
    });
  });

  // ── GST validator ─────────────────────────────────────────────────────────

  group('gst validator', () {
    test('no flag when GST = 18% of taxable base', () {
      // taxable = commission(100) + fixedFee(0) + collectionFee(0) = 100
      // expected GST = 18
      final orders = [
        const ParsedOrder(
          orderId: 'OD020',
          grossAmount: 1000.0,
          commission: 100.0,
          gstOnFees: 18.0,
          netSettlement: 882.0,
        ),
      ];
      final result = engine.reconcile(makeResult(orders: orders), 'R20');
      expect(
        result.discrepancies.any((d) => d.type == DiscrepancyType.gstMismatch),
        isFalse,
      );
    });

    test('flags GST mismatch when deviation > tolerance', () {
      // taxable = 100, expected GST = 18, actual = 30
      final orders = [
        const ParsedOrder(
          orderId: 'OD021',
          grossAmount: 1000.0,
          commission: 100.0,
          gstOnFees: 30.0, // should be 18
          netSettlement: 870.0,
        ),
      ];
      final result = engine.reconcile(makeResult(orders: orders), 'R21');
      expect(
        result.discrepancies.any((d) => d.type == DiscrepancyType.gstMismatch),
        isTrue,
      );
    });
  });

  // ── Fee validator ─────────────────────────────────────────────────────────

  group('fee validator', () {
    test('flags high reverse shipping > ₹200', () {
      final orders = [
        const ParsedOrder(
          orderId: 'OD030',
          grossAmount: 500.0,
          reverseShippingFee: 250.0,
          netSettlement: 250.0,
        ),
      ];
      final result = engine.reconcile(makeResult(orders: orders), 'R30');
      expect(
        result.discrepancies
            .any((d) => d.type == DiscrepancyType.highReverseShipping),
        isTrue,
      );
    });

    test('does not flag reverse shipping <= ₹200', () {
      final orders = [
        const ParsedOrder(
          orderId: 'OD031',
          grossAmount: 500.0,
          reverseShippingFee: 100.0,
          netSettlement: 400.0,
        ),
      ];
      final result = engine.reconcile(makeResult(orders: orders), 'R31');
      expect(
        result.discrepancies
            .any((d) => d.type == DiscrepancyType.highReverseShipping),
        isFalse,
      );
    });
  });

  // ── Deduplication ─────────────────────────────────────────────────────────

  group('deduplication', () {
    test('no duplicate discrepancies for same order + type', () {
      final orders = [
        const ParsedOrder(
          orderId: 'OD040',
          grossAmount: 1000.0,
          commission: 100.0,
          netSettlement: 100.0, // large variance
        ),
      ];
      final result = engine.reconcile(makeResult(orders: orders), 'R40');
      final mismatches = result.discrepancies
          .where((d) => d.type == DiscrepancyType.settlementMismatch)
          .toList();
      expect(mismatches, hasLength(1));
    });
  });

  // ── Aggregate metrics ─────────────────────────────────────────────────────

  group('aggregate metrics', () {
    test('totalVariance sums all discrepancy variances', () {
      final orders = [
        const ParsedOrder(
          orderId: 'OD050',
          grossAmount: 1000.0,
          commission: 100.0,
          netSettlement: 500.0, // variance ~400
        ),
        const ParsedOrder(
          orderId: 'OD051',
          grossAmount: 2000.0,
          commission: 200.0,
          netSettlement: 1000.0, // variance ~800
        ),
      ];
      final result = engine.reconcile(makeResult(orders: orders), 'R50');
      expect(result.totalVariance, greaterThan(0));
    });

    test('grossRevenue and netSettlement match summary', () {
      const summary = ParsedSummary(
        grossSales: 10000.0,
        netEarnings: 7500.0,
        totalOrders: 20,
      );
      final result = engine.reconcile(
          makeResult(orders: [], summary: summary), 'R60');
      expect(result.grossRevenue, equals(10000.0));
      expect(result.netSettlement, equals(7500.0));
      expect(result.totalOrders, equals(20));
    });
  });
}
