import '../entities/report_entities.dart';
import '../repositories/report_repository.dart';

class GetReportsUseCase {
  const GetReportsUseCase(this._repository);

  final ReportRepository _repository;

  List<ReportListItem> call() => _repository.getReports();
}
