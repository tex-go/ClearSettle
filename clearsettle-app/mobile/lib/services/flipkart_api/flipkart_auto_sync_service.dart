import 'dart:async';

import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../features/platform_connections/data/repositories/platform_connection_repository_impl.dart';
import '../../features/platform_connections/domain/usecases/sync_flipkart_data_usecase.dart';
import '../../features/reports/presentation/providers/reports_provider.dart';
import '../../reconciliation/reconciliation_engine.dart';
import '../../services/file_storage/file_storage_service.dart';
import 'flipkart_api_service.dart';

final flipkartAutoSyncProvider = Provider<FlipkartAutoSyncService>((ref) {
  final service = FlipkartAutoSyncService(ref);
  ref.onDispose(service.dispose);
  service.start();
  return service;
});

/// Watches app-start and connectivity events, triggering a Flipkart API sync
/// whenever the seller is connected and data is stale (> 30 minutes old).
class FlipkartAutoSyncService {
  FlipkartAutoSyncService(this._ref);

  final Ref _ref;
  StreamSubscription<List<ConnectivityResult>>? _connectivitySub;
  bool _syncing = false;

  static const _staleThreshold = Duration(minutes: 30);

  void start() {
    // Attempt an initial sync shortly after app startup
    Future.delayed(const Duration(seconds: 3), _syncIfStale);

    // Re-sync whenever connectivity is restored
    _connectivitySub = Connectivity().onConnectivityChanged.listen((results) {
      final online = results.any((r) => r != ConnectivityResult.none);
      if (online) _syncIfStale();
    });
  }

  Future<void> _syncIfStale() async {
    if (_syncing) return;

    try {
      final repo = PlatformConnectionRepositoryImpl();
      final connections = await repo.getConnections();
      final flipkart =
          connections.where((c) => c.platform == 'flipkart').firstOrNull;

      if (flipkart == null || !flipkart.isConnected) return;

      final lastSync = flipkart.lastSyncAt;
      final isStale = lastSync == null ||
          DateTime.now().difference(lastSync) > _staleThreshold;

      if (!isStale) return;

      _syncing = true;
      await _runSync(repo);
    } catch (_) {
      // Auto-sync failures are silent — user can trigger manually
    } finally {
      _syncing = false;
    }
  }

  Future<void> _runSync(PlatformConnectionRepositoryImpl repo) async {
    final useCase = SyncFlipkartDataUseCase(
      apiService: _ref.read(flipkartApiServiceProvider),
      reconciliationEngine: ReconciliationEngine(),
      fileStorage: _ref.read(fileStorageServiceProvider),
      connectionRepository: repo,
    );

    await useCase.execute();

    // Refresh the reports list so the new sync report appears immediately
    _ref.read(reportsProvider.notifier).refresh();
  }

  void dispose() {
    _connectivitySub?.cancel();
  }
}
