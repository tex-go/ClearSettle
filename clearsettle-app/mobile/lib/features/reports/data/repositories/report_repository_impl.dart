import 'dart:typed_data';

import '../../domain/entities/report_entities.dart';
import '../../domain/repositories/report_repository.dart';
import '../datasources/report_local_datasource.dart';

class ReportRepositoryImpl implements ReportRepository {
  const ReportRepositoryImpl({required this.localDataSource});

  final ReportLocalDataSource localDataSource;

  @override
  Future<String> uploadReport({
    required String marketplace,
    required String reportType,
    required String fileName,
    required Uint8List bytes,
  }) {
    return localDataSource.saveReport(
      marketplace: marketplace,
      reportType: reportType,
      fileName: fileName,
      bytes: bytes,
    );
  }

  @override
  Future<ReportDetail> parseReport(String reportId) =>
      localDataSource.parseReport(reportId);

  @override
  List<ReportListItem> getReports() => localDataSource.getReports();

  @override
  Future<ReportDetail> getReportDetail(String reportId) =>
      localDataSource.getReportDetail(reportId);

  @override
  Future<void> deleteReport(String reportId) =>
      localDataSource.deleteReport(reportId);
}
