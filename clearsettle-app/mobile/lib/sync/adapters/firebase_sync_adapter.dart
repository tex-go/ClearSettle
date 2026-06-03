import 'dart:async';

import '../models/sync_conflict.dart';
import '../models/sync_event.dart';
import '../models/sync_payload.dart';
import '../repositories/sync_repository.dart';

// Phase 3: add firebase_core + cloud_firestore to pubspec,
// implement each method using FirebaseFirestore.instance.
class FirebaseSyncAdapter implements SyncRepository {
  FirebaseSyncAdapter({
    required String projectId,
    required String collectionPath,
  })  : _projectId = projectId,
        _collectionPath = collectionPath;

  final String _projectId;
  final String _collectionPath;

  @override
  Future<SyncStatus> getStatus() async => const SyncStatus(
        state: SyncStatusState.idle,
        errorMessage: 'Firebase adapter not yet implemented.',
      );

  @override
  Future<void> push(List<SyncPayload> payloads) =>
      Future.error('FirebaseSyncAdapter.push not implemented');

  @override
  Future<List<SyncPayload>> pull({DateTime? since}) =>
      Future.error('FirebaseSyncAdapter.pull not implemented');

  @override
  Future<void> resolveConflict(ConflictResolution resolution) =>
      Future.error('FirebaseSyncAdapter.resolveConflict not implemented');

  @override
  Stream<SyncEvent> get events => const Stream.empty();

  @override
  Future<bool> isReachable() async => false;

  @override
  Future<void> dispose() async {}

  @override
  String toString() =>
      'FirebaseSyncAdapter(project=$_projectId, collection=$_collectionPath)';
}
