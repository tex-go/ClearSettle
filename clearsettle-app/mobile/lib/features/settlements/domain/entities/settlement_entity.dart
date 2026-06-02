enum SettlementStatus {
  matched,
  mismatch,
  pending,
  underInvestigation,
}

extension SettlementStatusX on SettlementStatus {
  String get label => switch (this) {
        SettlementStatus.matched            => 'Matched',
        SettlementStatus.mismatch           => 'Mismatch',
        SettlementStatus.pending            => 'Pending',
        SettlementStatus.underInvestigation => 'Under Investigation',
      };
}

class SettlementEntity {
  const SettlementEntity({
    required this.id,
    required this.marketplace,
    required this.settlementDate,
    required this.expectedAmount,
    required this.receivedAmount,
    required this.status,
    this.notes,
  });

  final String id;
  final String marketplace;
  final DateTime settlementDate;
  final double expectedAmount;
  final double receivedAmount;
  final SettlementStatus status;
  final String? notes;

  double get difference => receivedAmount - expectedAmount;
  bool get isShort => difference < 0;
}
