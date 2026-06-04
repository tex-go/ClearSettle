import 'dart:typed_data';

import '../entities/report_entities.dart';

abstract interface class ReportRepository {
  /// Pick a file from device and save it; returns the new report's ID
  Future<String> uploadReport({
    required String marketplace,
    required String reportType,
    required String fileName,
    required Uint8List bytes,
  });

  /// Parse a stored report; updates its Hive metadata on completion
  Future<ReportDetail> parseReport(String reportId);

  /// All locally stored reports, newest first
  List<ReportListItem> getReports();

  /// Full detail for one report (loads sidecar JSON from disk)
  Future<ReportDetail> getReportDetail(String reportId);

  /// Permanently delete report file + sidecar + Hive entry
  Future<void> deleteReport(String reportId);

  /// Pull the file list from the backend and sync any new/updated reports
  /// into the local Hive cache.  Safe to call on every app start.
  Future<void> syncRemoteReports();
}
