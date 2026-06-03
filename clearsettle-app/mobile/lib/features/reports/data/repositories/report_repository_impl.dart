import 'dart:developer' as dev;
import 'dart:typed_data';

import '../../../../core/errors/exceptions.dart';
import '../../../../parsers/parser_result.dart';
import '../../../../reconciliation/reconciliation_result.dart';
import '../../../../storage/entities/local_report_hive_object.dart';
import '../../../../storage/hive_manager.dart';
import '../../domain/entities/report_entities.dart';
import '../../domain/repositories/report_repository.dart';
import '../datasources/report_local_datasource.dart';
import '../datasources/report_remote_datasource.dart';

class ReportRepositoryImpl implements ReportRepository {
  const ReportRepositoryImpl({
    required this.localDataSource,
    required this.remoteDataSource,
  });

  final ReportLocalDataSource localDataSource;
  final ReportRemoteDataSource remoteDataSource;

  // ── Upload ────────────────────────────────────────────────────────────────
  // Strategy: try backend first → fall back to on-device parsing if unavailable.

  @override
  Future<String> uploadReport({
    required String marketplace,
    required String reportType,
    required String fileName,
    required Uint8List bytes,
  }) async {
    try {
      dev.log(
        '[INFO] Attempting backend upload | file=$fileName marketplace=$marketplace',
        name: 'ClearSettle.Repo',
      );

      // 1. POST to /ingestion/upload (multipart)
      final uploadResponse = await remoteDataSource.uploadFile(
        fileBytes: bytes,
        fileName: fileName,
        platformHint: marketplace != 'unknown' ? marketplace : null,
      );

      // 2. Save stub entry in Hive so the list screen shows the report immediately
      final hiveEntry = LocalReportHiveObject(
        id: uploadResponse.fileId,
        fileName: fileName,
        platform: uploadResponse.platform ?? marketplace,
        reportType: reportType,
        uploadedAt: DateTime.now().toIso8601String(),
        status: 'backend_processing',
        fileSize: uploadResponse.fileSizeBytes,
        fileHash: '',
      );
      await HiveManager.localReportBox.put(uploadResponse.fileId, hiveEntry);

      dev.log(
        '[INFO] Backend upload accepted | file_id=${uploadResponse.fileId} '
        'duplicate=${uploadResponse.isDuplicate}',
        name: 'ClearSettle.Repo',
      );

      return uploadResponse.fileId;
    } on NetworkException catch (e) {
      // Backend unreachable — fall back to on-device parsing
      dev.log(
        '[WARNING] Backend upload failed (network) — falling back to local parse | error=$e',
        name: 'ClearSettle.Repo',
      );
      return localDataSource.saveReport(
        marketplace: marketplace,
        reportType: reportType,
        fileName: fileName,
        bytes: bytes,
      );
    } on ServerException catch (e) {
      dev.log(
        '[WARNING] Backend upload failed (server) — falling back to local parse | error=$e',
        name: 'ClearSettle.Repo',
      );
      return localDataSource.saveReport(
        marketplace: marketplace,
        reportType: reportType,
        fileName: fileName,
        bytes: bytes,
      );
    }
  }

  // ── Parse ─────────────────────────────────────────────────────────────────
  // If the Hive entry has status 'backend_processing', poll the backend and
  // fetch summary + reconciliation. Otherwise run the local parser.

  @override
  Future<ReportDetail> parseReport(String reportId) async {
    final entry = HiveManager.localReportBox.get(reportId);
    if (entry == null) throw StateError('Report $reportId not found in local storage.');

    if (entry.status == 'backend_processing') {
      return _parseFromBackend(reportId, entry);
    }
    return localDataSource.parseReport(reportId);
  }

  Future<ReportDetail> _parseFromBackend(
    String reportId,
    LocalReportHiveObject entry,
  ) async {
    dev.log(
      '[INFO] Polling backend for processing result | file_id=$reportId',
      name: 'ClearSettle.Repo',
    );

    try {
      // 1. Poll until backend finishes
      final status = await remoteDataSource.pollUntilDone(reportId);

      if (status.isFailed) {
        entry
          ..status = 'failed'
          ..errorMessage = status.errorMessage ?? 'Backend processing failed';
        await entry.save();
        throw StateError(entry.errorMessage!);
      }

      // 2. Fetch summary + reconciliation concurrently
      final results = await Future.wait([
        remoteDataSource.fetchSummary(reportId),
        remoteDataSource.fetchReconciliation(
          reportId,
          status.platform.isNotEmpty ? status.platform : entry.platform,
        ),
      ]);

      final summary = results[0] as ParsedSummary;
      final reconResult = results[1] as ReconciliationResult;

      dev.log(
        '[INFO] Backend parse complete | file_id=$reportId '
        'platform=${status.platform} type=${status.reportType} '
        'orders=${summary.totalOrders} discrepancies=${reconResult.discrepancyCount}',
        name: 'ClearSettle.Repo',
      );

      // 3. Update Hive entry with real data
      entry
        ..status = 'parsed'
        ..platform = status.platform.isNotEmpty ? status.platform : entry.platform
        ..reportType = status.reportType.isNotEmpty ? status.reportType : entry.reportType
        ..parsedAt = DateTime.now().toIso8601String()
        ..totalOrders = summary.totalOrders
        ..grossRevenue = summary.grossSales
        ..totalFees = summary.totalFees
        ..netSettlement = summary.netEarnings
        ..discrepancyCount = reconResult.discrepancyCount
        ..parserVersion = 'backend-v1'
        ..errorMessage = null;
      await entry.save();

      // 4. Construct a ParseResult with backend summary (no per-order rows for mobile)
      final parseResult = ParseResult(
        marketplace: entry.platform,
        parserVersion: 'backend-v1',
        fileHash: entry.fileHash ?? '',
        fileName: entry.fileName,
        parsedAt: DateTime.now(),
        orders: const [],
        summary: summary,
        errors: const [],
        warnings: const [],
        sheetsFound: const ['backend_processed'],
      );

      return ReportDetail(
        report: _toListItem(entry),
        parseResult: parseResult,
        reconciliationResult: reconResult,
      );
    } catch (e) {
      if (e is StateError) rethrow;

      dev.log(
        '[ERROR] Backend fetch failed during parse | file_id=$reportId error=$e',
        name: 'ClearSettle.Repo',
      );

      // Mark as failed so the user can see the error
      entry
        ..status = 'failed'
        ..errorMessage = e.toString();
      await entry.save();
      rethrow;
    }
  }

  // ── Read ──────────────────────────────────────────────────────────────────

  @override
  List<ReportListItem> getReports() => localDataSource.getReports();

  @override
  Future<ReportDetail> getReportDetail(String reportId) =>
      localDataSource.getReportDetail(reportId);

  @override
  Future<void> deleteReport(String reportId) =>
      localDataSource.deleteReport(reportId);

  // ── Helpers ───────────────────────────────────────────────────────────────

  ReportListItem _toListItem(LocalReportHiveObject obj) {
    return ReportListItem(
      id: obj.id,
      fileName: obj.fileName,
      marketplace: obj.platform,
      reportType: obj.reportType,
      uploadedAt: DateTime.tryParse(obj.uploadedAt) ?? DateTime.now(),
      status: obj.status,
      fileSize: obj.fileSize,
      totalOrders: obj.totalOrders,
      grossRevenue: obj.grossRevenue,
      netSettlement: obj.netSettlement,
      discrepancyCount: obj.discrepancyCount,
      parsedAt: obj.parsedAt != null ? DateTime.tryParse(obj.parsedAt!) : null,
      errorMessage: obj.errorMessage,
      filePath: obj.filePath,
    );
  }
}
