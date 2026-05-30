import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/network/api_client.dart';
import '../../data/datasources/dashboard_local_datasource.dart';
import '../../data/datasources/dashboard_remote_datasource.dart';
import '../../data/repositories/dashboard_repository_impl.dart';
import '../../domain/entities/dashboard_summary_entity.dart';
import '../../domain/repositories/dashboard_repository.dart';
import '../../domain/usecases/get_dashboard_summary_usecase.dart';

// — DI —

final dashboardLocalDataSourceProvider = Provider<DashboardLocalDataSource>(
  (_) => DashboardLocalDataSource(),
);

final dashboardRemoteDataSourceProvider = Provider<DashboardRemoteDataSource>(
  (ref) => DashboardRemoteDataSource(apiClient: ref.read(apiClientProvider)),
);

final dashboardRepositoryProvider = Provider<DashboardRepository>((ref) {
  return DashboardRepositoryImpl(
    localDataSource: ref.read(dashboardLocalDataSourceProvider),
    remoteDataSource: ref.read(dashboardRemoteDataSourceProvider),
  );
});

// — Notifier —

class DashboardNotifier extends AsyncNotifier<DashboardSummary?> {
  late final GetDashboardSummaryUseCase _getSummary;
  late final DashboardLocalDataSource _local;

  @override
  Future<DashboardSummary?> build() async {
    _getSummary =
        GetDashboardSummaryUseCase(ref.read(dashboardRepositoryProvider));
    _local = ref.read(dashboardLocalDataSourceProvider);
    return _fetchOrCache();
  }

  Future<DashboardSummary?> _fetchOrCache() async {
    try {
      // 1. Try remote
      return await _getSummary();
    } catch (_) {
      // 2. Try JSON cache from previous successful remote call
      final cached = await _local.getCachedSummary();
      if (cached != null) return cached;
      // 3. Build from locally-parsed Hive reports (offline-first)
      return _local.buildFromHiveReports();
    }
  }

  Future<void> refresh() async {
    state = const AsyncValue.loading();
    state = await AsyncValue.guard(_fetchOrCache);
  }
}

final dashboardProvider =
    AsyncNotifierProvider<DashboardNotifier, DashboardSummary?>(
  DashboardNotifier.new,
);
