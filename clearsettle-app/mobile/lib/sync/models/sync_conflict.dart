import 'sync_payload.dart';

enum ConflictStrategy { localWins, remoteWins, merge, manual }

class SyncConflict {
  const SyncConflict({
    required this.id,
    required this.localPayload,
    required this.remotePayload,
    required this.detectedAt,
  });

  final String id;
  final SyncPayload localPayload;
  final SyncPayload remotePayload;
  final DateTime detectedAt;
}

class ConflictResolution {
  const ConflictResolution({
    required this.conflictId,
    required this.strategy,
    required this.resolvedPayload,
    required this.resolvedAt,
  });

  final String conflictId;
  final ConflictStrategy strategy;
  final SyncPayload resolvedPayload;
  final DateTime resolvedAt;
}
