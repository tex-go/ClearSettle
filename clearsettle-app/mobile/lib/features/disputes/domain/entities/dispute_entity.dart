enum DisputeStatus {
  draft,
  submitted,
  inReview,
  accepted,
  rejected,
  recovered,
}

extension DisputeStatusX on DisputeStatus {
  String get label => switch (this) {
        DisputeStatus.draft      => 'Draft',
        DisputeStatus.submitted  => 'Submitted',
        DisputeStatus.inReview   => 'In Review',
        DisputeStatus.accepted   => 'Accepted',
        DisputeStatus.rejected   => 'Rejected',
        DisputeStatus.recovered  => 'Recovered',
      };

  bool get isTerminal =>
      this == DisputeStatus.accepted ||
      this == DisputeStatus.rejected ||
      this == DisputeStatus.recovered;
}

class DisputeEntity {
  const DisputeEntity({
    required this.id,
    required this.orderId,
    required this.marketplace,
    required this.status,
    required this.claimAmount,
    required this.recoveredAmount,
    required this.reason,
    required this.createdAt,
    required this.updatedAt,
    this.evidence = const [],
    this.notes,
  });

  final String id;
  final String orderId;
  final String marketplace;
  final DisputeStatus status;
  final double claimAmount;
  final double recoveredAmount;
  final String reason;
  final DateTime createdAt;
  final DateTime updatedAt;
  final List<String> evidence;
  final String? notes;
}
