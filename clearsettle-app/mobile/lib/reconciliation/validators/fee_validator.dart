import '../../parsers/flipkart/flipkart_column_aliases.dart';
import '../../parsers/parser_result.dart';
import '../reconciliation_result.dart';

/// Flags suspect fee types (e.g. Wallet Redeem) and abnormally high
/// reverse shipping charges that should be disputed.
class FeeValidator {
  static const double _reverseShippingAlertThreshold = 200.0;

  List<Discrepancy> validate(List<ParsedOrder> orders) {
    final discrepancies = <Discrepancy>[];

    for (final order in orders) {
      // High reverse shipping
      if (order.reverseShippingFee > _reverseShippingAlertThreshold) {
        discrepancies.add(Discrepancy(
          type: DiscrepancyType.highReverseShipping,
          severity: DiscrepancySeverity.medium,
          orderId: order.orderId,
          description:
              'Reverse shipping fee ₹${order.reverseShippingFee.toStringAsFixed(2)} '
              'exceeds alert threshold ₹$_reverseShippingAlertThreshold.',
          expectedAmount: _reverseShippingAlertThreshold,
          actualAmount: order.reverseShippingFee,
          ruleName: 'high_reverse_shipping',
        ));
      }
    }

    return discrepancies;
  }

  /// Called with raw fee-type labels from the GST Details sheet (future use)
  List<Discrepancy> validateFeeTypes(
    List<String> feeLabels,
    String? orderId,
  ) {
    final discrepancies = <Discrepancy>[];

    for (final label in feeLabels) {
      final normalized = label.toLowerCase().trim();

      if (FlipkartColumnAliases.suspectFeeTypes.contains(normalized)) {
        discrepancies.add(Discrepancy(
          type: DiscrepancyType.feeSuspect,
          severity: DiscrepancySeverity.critical,
          orderId: orderId,
          description:
              '"${label}" is a non-standard deduction. '
              'Raise dispute with Flipkart Seller Support.',
          expectedAmount: 0.0,
          actualAmount: 0.0,
          feeType: label,
          ruleName: 'suspect_fee_type',
        ));
      } else if (!FlipkartColumnAliases.knownFeeTypes.contains(normalized)) {
        discrepancies.add(Discrepancy(
          type: DiscrepancyType.feeUnknown,
          severity: DiscrepancySeverity.low,
          orderId: orderId,
          description:
              '"$label" is not in the known fee catalog. Verify with marketplace.',
          expectedAmount: 0.0,
          actualAmount: 0.0,
          feeType: label,
          ruleName: 'unknown_fee_type',
        ));
      }
    }
    return discrepancies;
  }
}
