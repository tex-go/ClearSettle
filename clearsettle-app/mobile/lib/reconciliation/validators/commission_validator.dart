import '../../parsers/parser_result.dart';
import '../reconciliation_result.dart';

/// Validates actual commission vs expected rate × gross amount.
/// Flags overcharges exceeding ₹1 tolerance.
class CommissionValidator {
  static const double _toleranceRupees = 1.0;

  List<Discrepancy> validate(List<ParsedOrder> orders) {
    final discrepancies = <Discrepancy>[];

    for (final order in orders) {
      if (order.grossAmount <= 0) continue;

      // Only validate when commission rate is available in the report
      if (order.rawCommissionRate == null) continue;

      final expectedCommission =
          (order.rawCommissionRate! / 100.0) * order.grossAmount;
      final variance = order.commission - expectedCommission;

      if (variance > _toleranceRupees) {
        discrepancies.add(Discrepancy(
          type: DiscrepancyType.commissionOvercharge,
          severity: variance > 50 ? DiscrepancySeverity.high : DiscrepancySeverity.medium,
          orderId: order.orderId,
          description:
              'Commission ₹${order.commission.toStringAsFixed(2)} exceeds '
              'expected ₹${expectedCommission.toStringAsFixed(2)} '
              '(rate ${order.rawCommissionRate}% on ₹${order.grossAmount.toStringAsFixed(2)})',
          expectedAmount: expectedCommission,
          actualAmount: order.commission,
          ruleName: 'commission_rate_check',
        ));
      }
    }
    return discrepancies;
  }
}
