import 'dart:async';

import '../models/sync_conflict.dart';
import '../models/sync_event.dart';
import '../models/sync_payload.dart';
import '../repositories/sync_repository.dart';

// Phase 3: add supabase_flutter to pubspec,
// implement using Supabase.instance.client.
class SupabaseSyncAdapter implements SyncRepository {
  SupabaseSyncAdapter({
    required String supabaseUrl,
    required String supabaseAnonKey,
    required String tableName,
  })  : _url = supabaseUrl,
        _tableName = tableName;

  final String _url;
  final String _tableName;

  @override
  Future<SyncStatus> getStatus() async => const SyncStatus(
        state: SyncStatusState.idle,
        message: 'Supabase adapter not yet implemented.',
      );

  @override
  Future<void> push(List<SyncPayload> payloads) =>
      Future.error('SupabaseSyncAdapter.push not implemented');

  @override
  Future<List<SyncPayload>> pull({DateTime? since}) =>
      Future.error('SupabaseSyncAdapter.pull not implemented');

  @override
  Future<void> resolveConflict(ConflictResolution resolution) =>
      Future.error('SupabaseSyncAdapter.resolveConflict not implemented');

  @override
  Stream<SyncEvent> get events => const Stream.empty();

  @override
  Future<bool> isReachable() async => false;

  @override
  Future<void> dispose() async {}

  @override
  String toString() =>
      'SupabaseSyncAdapter(url=$_url, table=$_tableName)';
}
