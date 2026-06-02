import '../models/sync_conflict.dart';
import '../models/sync_event.dart';
import '../models/sync_payload.dart';

enum SyncStatusState { idle, syncing, success, error, offline }

class SyncStatus {
  const SyncStatus({
    required this.state,
    this.lastSyncAt,
    this.pendingCount = 0,
    this.errorMessage,
  });

  final SyncStatusState state;
  final DateTime? lastSyncAt;
  final int pendingCount;
  final String? errorMessage;

  bool get isIdle => state == SyncStatusState.idle;
  bool get isSyncing => state == SyncStatusState.syncing;
  bool get hasError => state == SyncStatusState.error;
}

/// Cloud-agnostic sync repository.
/// Implement this interface for Firebase, Supabase, AWS, or any future target.
/// Adapters live in lib/sync/adapters/.
abstract interface class SyncRepository {
  /// Returns the current sync status
  Future<SyncStatus> getStatus();

  /// Push local mutations to remote
  Future<void> push(List<SyncPayload> payloads);

  /// Pull remote changes since [since] (null = full sync)
  Future<List<SyncPayload>> pull({DateTime? since});

  /// Apply a resolved conflict
  Future<void> resolveConflict(ConflictResolution resolution);

  /// Stream of real-time sync events from the backend
  Stream<SyncEvent> get events;

  /// Ping the remote to check connectivity
  Future<bool> isReachable();

  /// Close the connection / cleanup resources
  Future<void> dispose();
}
