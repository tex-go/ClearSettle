import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/network/api_client.dart';
import '../../data/datasources/dashboard_local_datasource.dart';
import '../../data/datasources/dashboard_remote_datasource.dart';
import '../../data/repositories/dashboard_repository_impl.dart';
import '../../domain/entities/dashboard_summary_entity.dart';
import '../../domain/repositories/dashboard_repository.dart';
import '../../domain/usecases/get_dashboard_summary_usecase.dart';
import '../../../auth/domain/entities/auth_entity.dart';
import '../../../auth/presentation/providers/auth_provider.dart';

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
    // Resolve seller identity from auth state (not in /dashboard/summary payload)
    final authState = ref.read(authProvider).valueOrNull;
    final sellerName  = authState is AuthAuthenticated ? authState.sellerName  : '';
    final organisation = authState is AuthAuthenticated ? authState.organization : '';

    DashboardSummary? result;
    try {
      result = await _getSummary();
      // If the backend returns an empty summary (zeroes), prefer locally-aggregated
      // Hive data which is always up-to-date with parsed reports.
      if (_isEmptySummary(result)) {
        final hiveResult = await _local.buildFromHiveReports();
        if (hiveResult != null) result = hiveResult;
      }
    } catch (_) {
      result = await _local.getCachedSummary();
      result ??= await _local.buildFromHiveReports();
    }

    if (result == null) return null;

    // Inject seller identity when backend doesn't provide it
    return result.copyWith(
      sellerName:   result.sellerName.isEmpty   ? sellerName   : null,
      organization: result.organization.isEmpty ? organisation : null,
    );
  }

  static bool _isEmptySummary(DashboardSummary? s) =>
      s == null ||
      (s.grossRevenue == 0 && s.totalOrders == 0 && s.netSettlement == 0);

  Future<void> refresh() async {
    state = const AsyncValue.loading();
    state = await AsyncValue.guard(_fetchOrCache);
  }
}

final dashboardProvider =
    AsyncNotifierProvider<DashboardNotifier, DashboardSummary?>(
  DashboardNotifier.new,
);
