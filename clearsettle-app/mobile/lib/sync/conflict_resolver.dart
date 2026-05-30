import 'models/sync_conflict.dart';

/// Pluggable conflict resolution strategy.
/// Implementations decide which payload wins when local and remote diverge.
abstract interface class ConflictResolver {
  Future<ConflictResolution> resolve(SyncConflict conflict);
}

/// Last-write-wins: newer timestamp always wins.
class LastWriteWinsResolver implements ConflictResolver {
  @override
  Future<ConflictResolution> resolve(SyncConflict conflict) async {
    final localNewer = conflict.localPayload.timestamp
        .isAfter(conflict.remotePayload.timestamp);

    return ConflictResolution(
      conflictId: conflict.id,
      strategy: ConflictStrategy.localWins,
      resolvedPayload:
          localNewer ? conflict.localPayload : conflict.remotePayload,
      resolvedAt: DateTime.now(),
    );
  }
}

/// Remote always wins — useful for read-only local caches.
class RemoteWinsResolver implements ConflictResolver {
  @override
  Future<ConflictResolution> resolve(SyncConflict conflict) async {
    return ConflictResolution(
      conflictId: conflict.id,
      strategy: ConflictStrategy.remoteWins,
      resolvedPayload: conflict.remotePayload,
      resolvedAt: DateTime.now(),
    );
  }
}
