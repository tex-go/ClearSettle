enum AlertType {
  settlementMismatch,
  highDeduction,
  settlementDelay,
  disputeUpdate,
  syncFailure,
}

enum AlertSeverity { critical, warning, info }

class AlertEntity {
  const AlertEntity({
    required this.id,
    required this.type,
    required this.severity,
    required this.title,
    required this.message,
    required this.marketplace,
    required this.createdAt,
    required this.isRead,
    this.actionRoute,
    this.metadata,
  });

  final String id;
  final AlertType type;
  final AlertSeverity severity;
  final String title;
  final String message;
  final String marketplace;
  final DateTime createdAt;
  final bool isRead;
  final String? actionRoute;
  final Map<String, dynamic>? metadata;

  AlertEntity copyWith({bool? isRead}) => AlertEntity(
        id: id,
        type: type,
        severity: severity,
        title: title,
        message: message,
        marketplace: marketplace,
        createdAt: createdAt,
        isRead: isRead ?? this.isRead,
        actionRoute: actionRoute,
        metadata: metadata,
      );
}
