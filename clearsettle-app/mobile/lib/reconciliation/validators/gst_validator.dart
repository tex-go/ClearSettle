import '../../parsers/parser_result.dart';
import '../reconciliation_result.dart';

/// Validates GST on marketplace fees = 18% of (commission + fixed fees + collection fees).
/// Tolerance: 2% relative or ₹2 absolute — whichever is larger — to account
/// for rounding in platform-generated reports.
class GstValidator {
  static const double _gstRate = 0.18;
  static const double _tolerancePct = 0.02;
  static const double _toleranceAbs = 2.0;

  List<Discrepancy> validate(List<ParsedOrder> orders) {
    final discrepancies = <Discrepancy>[];

    for (final order in orders) {
      // GST applies to commission + fixed fees + collection fees
      final taxableBase =
          order.commission + order.fixedFee + order.collectionFee;
      if (taxableBase <= 0) continue;

      final expectedGst = taxableBase * _gstRate;
      final actualGst = order.gstOnFees;

      final variance = (actualGst - expectedGst).abs();
      final relativeTolerance = expectedGst * _tolerancePct;
      final tolerance =
          relativeTolerance > _toleranceAbs ? relativeTolerance : _toleranceAbs;

      if (variance > tolerance) {
        discrepancies.add(Discrepancy(
          type: DiscrepancyType.gstMismatch,
          severity: variance > 50 ? DiscrepancySeverity.high : DiscrepancySeverity.medium,
          orderId: order.orderId,
          description:
              'GST on fees ₹${actualGst.toStringAsFixed(2)} vs expected '
              '₹${expectedGst.toStringAsFixed(2)} '
              '(18% of taxable base ₹${taxableBase.toStringAsFixed(2)})',
          expectedAmount: expectedGst,
          actualAmount: actualGst,
          ruleName: 'gst_on_fees_18pct',
        ));
      }
    }
    return discrepancies;
  }
}
