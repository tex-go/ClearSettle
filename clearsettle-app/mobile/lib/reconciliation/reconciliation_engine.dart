import '../parsers/parser_result.dart';
import 'discrepancy_detector.dart';
import 'reconciliation_result.dart';

/// Orchestrates reconciliation for a fully parsed report.
/// Runs all validators, aggregates discrepancies, and returns an
/// auditable [ReconciliationResult].
class ReconciliationEngine {
  ReconciliationEngine() : _detector = DiscrepancyDetector();

  final DiscrepancyDetector _detector;

  ReconciliationResult reconcile(ParseResult parseResult, String reportId) {
    final summary = parseResult.effectiveSummary;
    final discrepancies = _detector.detect(parseResult.orders);

    return ReconciliationResult(
      reportId: reportId,
      marketplace: parseResult.marketplace,
      reconciledAt: DateTime.now(),
      totalOrders: summary.totalOrders > 0
          ? summary.totalOrders
          : parseResult.orders.length,
      grossRevenue: summary.grossSales,
      totalFees: summary.totalFees,
      netSettlement: summary.netEarnings,
      discrepancies: discrepancies,
      parseWarnings: parseResult.warnings,
    );
  }
}
