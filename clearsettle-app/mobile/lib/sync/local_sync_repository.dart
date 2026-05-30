import 'dart:async';

import 'models/sync_conflict.dart';
import 'models/sync_event.dart';
import 'models/sync_payload.dart';
import 'repositories/sync_repository.dart';

/// No-op sync repository for offline-only mode.
/// Records all payloads to in-memory queue; no remote calls.
/// Swap with a cloud adapter when sync target is confirmed.
class LocalSyncRepository implements SyncRepository {
  final List<SyncPayload> _queue = [];
  final _eventController = StreamController<SyncEvent>.broadcast();

  @override
  Future<SyncStatus> getStatus() async => SyncStatus(
        state: SyncStatusState.idle,
        pendingCount: _queue.length,
        lastSyncAt: null,
      );

  @override
  Future<void> push(List<SyncPayload> payloads) async {
    _queue.addAll(payloads);
    _eventController.add(SyncEvent(
      type: SyncEventType.payloadPushed,
      timestamp: DateTime.now(),
      message: '${payloads.length} payloads queued locally',
    ));
  }

  @override
  Future<List<SyncPayload>> pull({DateTime? since}) async => [];

  @override
  Future<void> resolveConflict(ConflictResolution resolution) async {}

  @override
  Stream<SyncEvent> get events => _eventController.stream;

  @override
  Future<bool> isReachable() async => false;

  @override
  Future<void> dispose() async => _eventController.close();

  List<SyncPayload> get pendingQueue => List.unmodifiable(_queue);
  int get pendingCount => _queue.length;
  void clearQueue() => _queue.clear();
}
