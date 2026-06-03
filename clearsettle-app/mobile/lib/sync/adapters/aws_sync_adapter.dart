import 'dart:async';

import '../models/sync_conflict.dart';
import '../models/sync_event.dart';
import '../models/sync_payload.dart';
import '../repositories/sync_repository.dart';

// Phase 3: add aws_amplify or custom REST client.
// Targets API Gateway + DynamoDB or AppSync.
class AWSSyncAdapter implements SyncRepository {
  AWSSyncAdapter({
    required String apiGatewayUrl,
    required String region,
    required String accessKeyId,
    required String secretAccessKey,
  })  : _apiUrl = apiGatewayUrl,
        _region = region;

  final String _apiUrl;
  final String _region;

  @override
  Future<SyncStatus> getStatus() async => const SyncStatus(
        state: SyncStatusState.idle,
        errorMessage: 'AWS adapter not yet implemented.',
      );

  @override
  Future<void> push(List<SyncPayload> payloads) =>
      Future.error('AWSSyncAdapter.push not implemented');

  @override
  Future<List<SyncPayload>> pull({DateTime? since}) =>
      Future.error('AWSSyncAdapter.pull not implemented');

  @override
  Future<void> resolveConflict(ConflictResolution resolution) =>
      Future.error('AWSSyncAdapter.resolveConflict not implemented');

  @override
  Stream<SyncEvent> get events => const Stream.empty();

  @override
  Future<bool> isReachable() async => false;

  @override
  Future<void> dispose() async {}

  @override
  String toString() =>
      'AWSSyncAdapter(url=$_apiUrl, region=$_region)';
}
