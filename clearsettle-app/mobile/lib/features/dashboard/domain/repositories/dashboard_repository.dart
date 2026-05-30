import '../entities/dashboard_summary_entity.dart';

abstract interface class DashboardRepository {
  Future<DashboardSummary> getSummary();
  Future<DashboardSummary?> getCachedSummary();
  Future<void> cacheSummary(DashboardSummary summary);
}
