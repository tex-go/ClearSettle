import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/constants/app_constants.dart';
import '../../storage/entities/sync_status_hive_object.dart';
import '../../storage/hive_manager.dart';
import 'sync_queue_manager.dart';

final syncQueueManagerProvider = Provider<SyncQueueManager>(
  (_) => SyncQueueManager(),
);

final syncServiceProvider = Provider<SyncService>((ref) {
  return SyncService(
    queueManager: ref.read(syncQueueManagerProvider),
  );
});

enum SyncState { idle, syncing, success, error }

class SyncService {
  SyncService({required this.queueManager});

  final SyncQueueManager queueManager;

  SyncState _state = SyncState.idle;
  SyncState get state => _state;

  Future<bool> isOnline() async {
    final result = await Connectivity().checkConnectivity();
    return result.any((r) => r != ConnectivityResult.none);
  }

  Future<void> syncIfOnline() async {
    if (_state == SyncState.syncing) return;
    final online = await isOnline();
    if (!online) return;
    await _processQueue();
  }

  Future<void> _processQueue() async {
    _state = SyncState.syncing;
    _updateSyncStatus('syncing');

    try {
      final pending = queueManager.getPendingItems();

      for (final item in pending) {
        try {
          // Phase 2: dispatch item to correct remote datasource
          // For now, mark as completed to avoid infinite retry growth
          await queueManager.markCompleted(item.id);
        } catch (e) {
          await queueManager.markFailed(item.id, e.toString());
        }
      }

      await queueManager.purgCompleted();
      _state = SyncState.success;
      _updateSyncStatus('success');
    } catch (e) {
      _state = SyncState.error;
      _updateSyncStatus('error', error: e.toString());
    }
  }

  void _updateSyncStatus(String status, {String? error}) {
    final box = HiveManager.syncStatusBox;
    const key = AppConstants.syncStatusKey;
    final existing = box.get(key);
    if (existing != null) {
      existing.status = status;
      existing.lastSyncAt = DateTime.now().toIso8601String();
      if (error != null) existing.lastError = error;
      existing.save();
    } else {
      box.put(
        key,
        SyncStatusHiveObject(
          id: key,
          entityType: 'global',
          status: status,
          lastSyncAt: DateTime.now().toIso8601String(),
          lastError: error,
        ),
      );
    }
  }

  DateTime? get lastSyncAt {
    final raw = HiveManager.syncStatusBox.get(AppConstants.syncStatusKey)?.lastSyncAt;
    return raw != null ? DateTime.tryParse(raw) : null;
  }
}
