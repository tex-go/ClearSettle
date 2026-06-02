import 'dart:typed_data';

import '../repositories/report_repository.dart';

class UploadReportUseCase {
  const UploadReportUseCase(this._repository);

  final ReportRepository _repository;

  Future<String> call({
    required String marketplace,
    required String reportType,
    required String fileName,
    required Uint8List bytes,
  }) {
    return _repository.uploadReport(
      marketplace: marketplace,
      reportType: reportType,
      fileName: fileName,
      bytes: bytes,
    );
  }
}
