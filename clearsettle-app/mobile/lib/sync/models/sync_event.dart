enum SyncEventType {
  started,
  progress,
  completed,
  failed,
  conflictDetected,
  conflictResolved,
  payloadPushed,
  payloadPulled,
}

class SyncEvent {
  const SyncEvent({
    required this.type,
    required this.timestamp,
    this.message,
    this.payload,
    this.error,
    this.progressPercent,
  });

  final SyncEventType type;
  final DateTime timestamp;
  final String? message;
  final dynamic payload;
  final String? error;
  final double? progressPercent;

  bool get isError => type == SyncEventType.failed;
  bool get isComplete => type == SyncEventType.completed;
}
