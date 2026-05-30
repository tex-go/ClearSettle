import 'dart:convert';

import 'package:uuid/uuid.dart';

import '../../core/config/app_config.dart';
import '../../storage/entities/pending_action_hive_object.dart';
import '../../storage/entities/sync_queue_hive_object.dart';
import '../../storage/hive_manager.dart';

class SyncQueueManager {
  static const _uuid = Uuid();

  Future<void> enqueue({
    required String actionType,
    required Map<String, dynamic> payload,
  }) async {
    final item = SyncQueueHiveObject(
      id: _uuid.v4(),
      actionType: actionType,
      payload: jsonEncode(payload),
      createdAt: DateTime.now().toIso8601String(),
    );
    await HiveManager.syncQueueBox.put(item.id, item);
  }

  Future<void> recordPendingAction({
    required String type,
    required String entity,
    required Map<String, dynamic> data,
  }) async {
    final action = PendingActionHiveObject(
      id: _uuid.v4(),
      type: type,
      entity: entity,
      data: jsonEncode(data),
      createdAt: DateTime.now().toIso8601String(),
    );
    await HiveManager.pendingActionsBox.put(action.id, action);
  }

  List<SyncQueueHiveObject> getPendingItems() {
    return HiveManager.syncQueueBox.values
        .where((item) =>
            item.status == 'pending' &&
            item.retryCount < AppConfig.maxSyncRetries)
        .toList()
      ..sort((a, b) => a.createdAt.compareTo(b.createdAt));
  }

  List<PendingActionHiveObject> getUnsyncedActions() {
    return HiveManager.pendingActionsBox.values
        .where((a) => !a.synced)
        .toList()
      ..sort((a, b) => a.createdAt.compareTo(b.createdAt));
  }

  Future<void> markCompleted(String id) async {
    final item = HiveManager.syncQueueBox.get(id);
    if (item != null) {
      item.status = 'completed';
      await item.save();
    }
  }

  Future<void> markFailed(String id, String error) async {
    final item = HiveManager.syncQueueBox.get(id);
    if (item != null) {
      item.retryCount += 1;
      item.errorMessage = error;
      item.status =
          item.retryCount >= AppConfig.maxSyncRetries ? 'failed' : 'pending';
      await item.save();
    }
  }

  Future<void> purgCompleted() async {
    final completed = HiveManager.syncQueueBox.values
        .where((i) => i.status == 'completed')
        .map((i) => i.key)
        .toList();
    await HiveManager.syncQueueBox.deleteAll(completed);
  }

  int get pendingCount => getPendingItems().length;
}
