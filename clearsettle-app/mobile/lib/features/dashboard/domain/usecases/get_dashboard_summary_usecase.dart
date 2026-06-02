import '../../../../core/errors/exceptions.dart';
import '../entities/dashboard_summary_entity.dart';
import '../repositories/dashboard_repository.dart';

class GetDashboardSummaryUseCase {
  const GetDashboardSummaryUseCase(this._repository);

  final DashboardRepository _repository;

  Future<DashboardSummary> call() async {
    try {
      final summary = await _repository.getSummary();
      await _repository.cacheSummary(summary);
      return summary;
    } on NetworkException {
      final cached = await _repository.getCachedSummary();
      if (cached != null) return cached.copyWith(isFromCache: true);
      rethrow;
    }
  }
}
