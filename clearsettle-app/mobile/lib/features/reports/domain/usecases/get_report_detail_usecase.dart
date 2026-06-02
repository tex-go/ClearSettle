import '../entities/report_entities.dart';
import '../repositories/report_repository.dart';

class GetReportDetailUseCase {
  const GetReportDetailUseCase(this._repository);

  final ReportRepository _repository;

  Future<ReportDetail> call(String reportId) =>
      _repository.getReportDetail(reportId);
}
