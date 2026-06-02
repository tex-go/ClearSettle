import '../../domain/entities/dashboard_summary_entity.dart';
import '../../domain/repositories/dashboard_repository.dart';
import '../datasources/dashboard_local_datasource.dart';
import '../datasources/dashboard_remote_datasource.dart';

class DashboardRepositoryImpl implements DashboardRepository {
  const DashboardRepositoryImpl({
    required this.localDataSource,
    required this.remoteDataSource,
  });

  final DashboardLocalDataSource localDataSource;
  final DashboardRemoteDataSource remoteDataSource;

  @override
  Future<DashboardSummary> getSummary() async {
    final model = await remoteDataSource.getSummary();
    return model.toEntity();
  }

  @override
  Future<DashboardSummary?> getCachedSummary() {
    return localDataSource.getCachedSummary();
  }

  @override
  Future<void> cacheSummary(DashboardSummary summary) {
    return localDataSource.cacheSummary(summary);
  }
}
