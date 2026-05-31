import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../reconciliation/reconciliation_engine.dart';
import '../../../../services/file_storage/file_storage_service.dart';
import '../../../../services/flipkart_api/flipkart_api_service.dart';
import '../../../../services/oauth/flipkart_oauth_service.dart';
import '../../../reports/presentation/providers/reports_provider.dart';
import '../../data/repositories/platform_connection_repository_impl.dart';
import '../../domain/entities/platform_connection.dart';
import '../../domain/usecases/connect_flipkart_usecase.dart';
import '../../domain/usecases/disconnect_platform_usecase.dart';
import '../../domain/usecases/get_connections_usecase.dart';
import '../../domain/usecases/sync_flipkart_data_usecase.dart';

final _repoProvider =
    Provider((_) => PlatformConnectionRepositoryImpl());

final platformConnectionProvider = AsyncNotifierProvider<
    PlatformConnectionNotifier,
    List<PlatformConnection>>(PlatformConnectionNotifier.new);

class PlatformConnectionNotifier
    extends AsyncNotifier<List<PlatformConnection>> {
  late PlatformConnectionRepositoryImpl _repo;

  @override
  Future<List<PlatformConnection>> build() async {
    _repo = ref.read(_repoProvider);
    return GetConnectionsUseCase(_repo).execute();
  }

  Future<void> connectFlipkart() async {
    state = const AsyncLoading();
    state = await AsyncValue.guard(() async {
      final oauthService = ref.read(flipkartOAuthServiceProvider);
      await ConnectFlipkartUseCase(
        oauthService: oauthService,
        repository: _repo,
      ).execute();
      return GetConnectionsUseCase(_repo).execute();
    });
  }

  Future<void> disconnect(String platform) async {
    state = const AsyncLoading();
    state = await AsyncValue.guard(() async {
      final oauthService = ref.read(flipkartOAuthServiceProvider);
      await DisconnectPlatformUseCase(
        repository: _repo,
        oauthService: oauthService,
      ).execute(platform);
      return GetConnectionsUseCase(_repo).execute();
    });
  }

  /// Pulls live order data from the Flipkart API, reconciles it, and
  /// persists it as a synthetic report in Hive — same pipeline as manual upload.
  Future<SyncFlipkartDataResult> syncFlipkartData({int daysBack = 30}) async {
    final useCase = SyncFlipkartDataUseCase(
      apiService: ref.read(flipkartApiServiceProvider),
      reconciliationEngine: ReconciliationEngine(),
      fileStorage: ref.read(fileStorageServiceProvider),
      connectionRepository: _repo,
    );
    final result = await useCase.execute(daysBack: daysBack);
    // Refresh connection list to show updated lastSyncAt
    state = await AsyncValue.guard(() => GetConnectionsUseCase(_repo).execute());
    // Refresh reports list so the new API sync report appears immediately
    ref.read(reportsProvider.notifier).refresh();
    return result;
  }
}
