import '../parsers/parser_result.dart';
import 'reconciliation_result.dart';
import 'validators/commission_validator.dart';
import 'validators/fee_validator.dart';
import 'validators/gst_validator.dart';
import 'validators/settlement_validator.dart';

/// Aggregates all validator outputs and deduplicates by (type, orderId).
class DiscrepancyDetector {
  DiscrepancyDetector()
      : _commissionValidator = CommissionValidator(),
        _settlementValidator = SettlementValidator(),
        _feeValidator = FeeValidator(),
        _gstValidator = GstValidator();

  final CommissionValidator _commissionValidator;
  final SettlementValidator _settlementValidator;
  final FeeValidator _feeValidator;
  final GstValidator _gstValidator;

  List<Discrepancy> detect(List<ParsedOrder> orders) {
    final all = <Discrepancy>[
      ..._commissionValidator.validate(orders),
      ..._settlementValidator.validate(orders),
      ..._feeValidator.validate(orders),
      ..._gstValidator.validate(orders),
    ];

    // Deduplicate: keep the highest-severity entry per (type, orderId)
    final seen = <String, Discrepancy>{};
    for (final d in all) {
      final key = '${d.type.name}__${d.orderId ?? "__summary"}';
      final existing = seen[key];
      if (existing == null ||
          d.severity.index < existing.severity.index) {
        seen[key] = d;
      }
    }

    final result = seen.values.toList();
    // Sort: critical first, then by variance descending
    result.sort((a, b) {
      final sc = a.severity.index.compareTo(b.severity.index);
      if (sc != 0) return sc;
      return b.variance.compareTo(a.variance);
    });
    return result;
  }
}
