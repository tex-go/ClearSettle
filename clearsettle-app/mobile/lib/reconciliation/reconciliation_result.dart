import '../parsers/parser_result.dart';

enum DiscrepancyType {
  commissionOvercharge,
  feeUnknown,
  feeSuspect,
  settlementMismatch,
  gstMismatch,
  missingSettlement,
  highReverseShipping,
}

enum DiscrepancySeverity { critical, high, medium, low }

class Discrepancy {
  const Discrepancy({
    required this.type,
    required this.severity,
    required this.orderId,
    required this.description,
    required this.expectedAmount,
    required this.actualAmount,
    this.feeType,
    this.ruleName,
  });

  final DiscrepancyType type;
  final DiscrepancySeverity severity;
  final String? orderId;
  final String description;
  final double expectedAmount;
  final double actualAmount;
  final String? feeType;
  final String? ruleName;

  double get variance => (actualAmount - expectedAmount).abs();

  String get typeLabel {
    switch (type) {
      case DiscrepancyType.commissionOvercharge:
        return 'Commission Overcharge';
      case DiscrepancyType.feeUnknown:
        return 'Unknown Fee';
      case DiscrepancyType.feeSuspect:
        return 'Suspect Deduction';
      case DiscrepancyType.settlementMismatch:
        return 'Settlement Mismatch';
      case DiscrepancyType.gstMismatch:
        return 'GST Mismatch';
      case DiscrepancyType.missingSettlement:
        return 'Missing Settlement';
      case DiscrepancyType.highReverseShipping:
        return 'High Reverse Shipping';
    }
  }

  Map<String, dynamic> toJson() => {
        'type': type.name,
        'severity': severity.name,
        'order_id': orderId,
        'description': description,
        'expected_amount': expectedAmount,
        'actual_amount': actualAmount,
        'variance': variance,
        'fee_type': feeType,
        'rule_name': ruleName,
      };

  factory Discrepancy.fromJson(Map<String, dynamic> j) => Discrepancy(
        type: DiscrepancyType.values.firstWhere(
          (t) => t.name == j['type'],
          orElse: () => DiscrepancyType.feeUnknown,
        ),
        severity: DiscrepancySeverity.values.firstWhere(
          (s) => s.name == j['severity'],
          orElse: () => DiscrepancySeverity.medium,
        ),
        orderId: j['order_id'] as String?,
        description: j['description'] as String,
        expectedAmount: (j['expected_amount'] as num?)?.toDouble() ?? 0.0,
        actualAmount: (j['actual_amount'] as num?)?.toDouble() ?? 0.0,
        feeType: j['fee_type'] as String?,
        ruleName: j['rule_name'] as String?,
      );
}

class ReconciliationResult {
  const ReconciliationResult({
    required this.reportId,
    required this.marketplace,
    required this.reconciledAt,
    required this.totalOrders,
    required this.grossRevenue,
    required this.totalFees,
    required this.netSettlement,
    required this.discrepancies,
    required this.parseWarnings,
  });

  final String reportId;
  final String marketplace;
  final DateTime reconciledAt;
  final int totalOrders;
  final double grossRevenue;
  final double totalFees;
  final double netSettlement;
  final List<Discrepancy> discrepancies;
  final List<ParseWarning> parseWarnings;

  int get discrepancyCount => discrepancies.length;
  int get criticalCount =>
      discrepancies.where((d) => d.severity == DiscrepancySeverity.critical).length;
  int get highCount =>
      discrepancies.where((d) => d.severity == DiscrepancySeverity.high).length;

  double get totalVariance =>
      discrepancies.fold(0.0, (sum, d) => sum + d.variance);

  bool get isClean => discrepancies.isEmpty;

  Map<String, dynamic> toJson() => {
        'report_id': reportId,
        'marketplace': marketplace,
        'reconciled_at': reconciledAt.toIso8601String(),
        'total_orders': totalOrders,
        'gross_revenue': grossRevenue,
        'total_fees': totalFees,
        'net_settlement': netSettlement,
        'discrepancies': discrepancies.map((d) => d.toJson()).toList(),
        'parse_warnings': parseWarnings.map((w) => w.code).toList(),
      };

  factory ReconciliationResult.fromJson(Map<String, dynamic> j) =>
      ReconciliationResult(
        reportId: j['report_id'] as String,
        marketplace: j['marketplace'] as String,
        reconciledAt: DateTime.parse(j['reconciled_at'] as String),
        totalOrders: (j['total_orders'] as int?) ?? 0,
        grossRevenue: (j['gross_revenue'] as num?)?.toDouble() ?? 0.0,
        totalFees: (j['total_fees'] as num?)?.toDouble() ?? 0.0,
        netSettlement: (j['net_settlement'] as num?)?.toDouble() ?? 0.0,
        discrepancies: ((j['discrepancies'] as List?) ?? [])
            .map((d) => Discrepancy.fromJson(d as Map<String, dynamic>))
            .toList(),
        parseWarnings: [],
      );
}
