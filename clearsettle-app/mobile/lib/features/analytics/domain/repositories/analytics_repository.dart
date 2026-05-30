import '../entities/analytics_entity.dart';

abstract interface class AnalyticsRepository {
  Future<AnalyticsSummary> getSummary(AnalyticsFilter filter);
}
