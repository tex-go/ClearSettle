import '../repositories/report_repository.dart';

class DeleteReportUseCase {
  const DeleteReportUseCase(this._repository);

  final ReportRepository _repository;

  Future<void> call(String reportId) => _repository.deleteReport(reportId);
}
