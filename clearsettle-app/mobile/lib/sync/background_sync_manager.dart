import 'dart:async';

import 'package:connectivity_plus/connectivity_plus.dart';

import 'conflict_resolver.dart';
import 'models/sync_conflict.dart';
import 'models/sync_event.dart';
import 'repositories/sync_repository.dart';

enum SyncManagerState { idle, running, paused, stopped }

/// Orchestrates background sync: watches connectivity, batches payloads,
/// delegates conflicts, and exposes a state stream.
///
/// Phase 3: wire a real [SyncRepository] implementation.
class BackgroundSyncManager {
  BackgroundSyncManager({
    required SyncRepository repository,
    ConflictResolver? conflictResolver,
    Duration syncInterval = const Duration(minutes: 15),
  })  : _repository = repository,
        _conflictResolver = conflictResolver ?? LastWriteWinsResolver(),
        _syncInterval = syncInterval;

  final SyncRepository _repository;
  final ConflictResolver _conflictResolver;
  final Duration _syncInterval;

  final _stateController = StreamController<SyncManagerState>.broadcast();
  final _eventController = StreamController<SyncEvent>.broadcast();

  Timer? _timer;
  StreamSubscription<List<ConnectivityResult>>? _connectivitySub;
  SyncManagerState _state = SyncManagerState.idle;

  Stream<SyncManagerState> get stateStream => _stateController.stream;
  Stream<SyncEvent> get eventStream => _eventController.stream;
  SyncManagerState get state => _state;

  Future<void> start() async {
    if (_state == SyncManagerState.running) return;
    _setState(SyncManagerState.running);

    // Schedule periodic sync
    _timer = Timer.periodic(_syncInterval, (_) => triggerSync());

    // React to connectivity changes
    _connectivitySub = Connectivity().onConnectivityChanged.listen((results) {
      final online = results.any((r) => r != ConnectivityResult.none);
      if (online && _state == SyncManagerState.running) {
        triggerSync();
      }
    });

    // Initial sync attempt
    await triggerSync();
  }

  Future<void> triggerSync() async {
    final reachable = await _repository.isReachable();
    if (!reachable) {
      _emit(SyncEvent(
        type: SyncEventType.failed,
        timestamp: DateTime.now(),
        error: 'Remote unreachable',
      ));
      return;
    }

    _emit(SyncEvent(type: SyncEventType.started, timestamp: DateTime.now()));

    try {
      // Phase 3: pull pending payloads from local SyncQueue
      // and push via _repository.push(payloads)
      _emit(SyncEvent(
        type: SyncEventType.completed,
        timestamp: DateTime.now(),
        message: 'Sync complete',
      ));
    } catch (e) {
      _emit(SyncEvent(
        type: SyncEventType.failed,
        timestamp: DateTime.now(),
        error: e.toString(),
      ));
    }
  }

  Future<void> pause() async => _setState(SyncManagerState.paused);

  Future<void> stop() async {
    _timer?.cancel();
    await _connectivitySub?.cancel();
    await _repository.dispose();
    _setState(SyncManagerState.stopped);
  }

  Future<ConflictResolution> resolveConflict(SyncConflict conflict) async {
    final resolution = await _conflictResolver.resolve(conflict);
    await _repository.resolveConflict(resolution);
    _emit(SyncEvent(
      type: SyncEventType.conflictResolved,
      timestamp: DateTime.now(),
      message: 'Conflict resolved: ${resolution.strategy.name}',
    ));
    return resolution;
  }

  void _setState(SyncManagerState s) {
    _state = s;
    _stateController.add(s);
  }

  void _emit(SyncEvent event) => _eventController.add(event);

  Future<void> dispose() async {
    await stop();
    await _stateController.close();
    await _eventController.close();
  }
}
