import '../../parsers/parser_result.dart';
import '../reconciliation_result.dart';

/// Validates: expected_net = gross − total_fees ≈ net_settlement.
/// Variance > ₹1 is flagged as a discrepancy.
/// Orders with gross > 0 but net_settlement == 0 are flagged as missing settlement.
class SettlementValidator {
  static const double _toleranceRupees = 1.0;
  static const double _missingSettlementThreshold = 10.0;

  List<Discrepancy> validate(List<ParsedOrder> orders) {
    final discrepancies = <Discrepancy>[];

    for (final order in orders) {
      if (order.grossAmount <= 0) continue;

      // Missing settlement
      if (order.netSettlement == 0.0 &&
          order.grossAmount > _missingSettlementThreshold) {
        discrepancies.add(Discrepancy(
          type: DiscrepancyType.missingSettlement,
          severity: DiscrepancySeverity.high,
          orderId: order.orderId,
          description:
              'Order has gross amount ₹${order.grossAmount.toStringAsFixed(2)} '
              'but zero net settlement recorded.',
          expectedAmount: order.expectedNet,
          actualAmount: 0.0,
          ruleName: 'missing_settlement',
        ));
        continue;
      }

      // Settlement variance
      final variance = order.settlementVariance;
      if (variance > _toleranceRupees) {
        discrepancies.add(Discrepancy(
          type: DiscrepancyType.settlementMismatch,
          severity: _classifyVariance(variance),
          orderId: order.orderId,
          description:
              'Net settlement ₹${order.netSettlement.toStringAsFixed(2)} differs '
              'from expected ₹${order.expectedNet.toStringAsFixed(2)} '
              '(variance ₹${variance.toStringAsFixed(2)})',
          expectedAmount: order.expectedNet,
          actualAmount: order.netSettlement,
          ruleName: 'settlement_variance_check',
        ));
      }
    }
    return discrepancies;
  }

  DiscrepancySeverity _classifyVariance(double variance) {
    if (variance >= 500) return DiscrepancySeverity.critical;
    if (variance >= 100) return DiscrepancySeverity.high;
    if (variance >= 10) return DiscrepancySeverity.medium;
    return DiscrepancySeverity.low;
  }
}
