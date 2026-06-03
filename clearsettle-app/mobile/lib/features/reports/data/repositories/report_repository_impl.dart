import 'dart:typed_data';

import '../../../../core/errors/exceptions.dart';
import '../../../../core/utils/cs_logger.dart';
import '../../../../parsers/parser_result.dart';
import '../../../../reconciliation/reconciliation_result.dart';
import '../../../../storage/entities/local_report_hive_object.dart';
import '../../../../storage/hive_manager.dart';
import '../../domain/entities/report_entities.dart';
import '../../domain/repositories/report_repository.dart';
import '../datasources/report_local_datasource.dart';
import '../datasources/report_remote_datasource.dart';

/// Sentinel parser version written by _parseFromBackend().
/// Used to route getReportDetail() to the backend API path.
const _kBackendParserVersion = 'backend-v1';

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
      CsLogger.info('Repo', 'Attempting backend upload',
          data: {'file': fileName, 'marketplace': marketplace});

      final uploadResponse = await remoteDataSource.uploadFile(
        fileBytes: bytes,
        fileName: fileName,
        platformHint: marketplace != 'unknown' ? marketplace : null,
      );

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

      CsLogger.info('Repo', 'Backend upload accepted',
          data: {'file_id': uploadResponse.fileId, 'duplicate': uploadResponse.isDuplicate});

      return uploadResponse.fileId;
    } on NetworkException catch (e) {
      CsLogger.warning('Repo', 'Backend upload failed (network) — local parse fallback',
          data: {'error': '$e'});
      return localDataSource.saveReport(
        marketplace: marketplace,
        reportType: reportType,
        fileName: fileName,
        bytes: bytes,
      );
    } on ServerException catch (e) {
      CsLogger.warning('Repo', 'Backend upload failed (server) — local parse fallback',
          data: {'error': '$e'});
      return localDataSource.saveReport(
        marketplace: marketplace,
        reportType: reportType,
        fileName: fileName,
        bytes: bytes,
      );
    }
  }

  // ── Parse (initial processing after upload) ───────────────────────────────

  @override
  Future<ReportDetail> parseReport(String reportId) async {
    final entry = HiveManager.localReportBox.get(reportId);
    if (entry == null) {
      throw StateError('Report $reportId not found in local storage.');
    }

    if (entry.status == 'backend_processing') {
      return _parseFromBackend(reportId, entry);
    }
    return localDataSource.parseReport(reportId);
  }

  // ── Get Detail (re-open existing parsed report) ────────────────────────────
  //
  // RCA: _parseFromBackend() writes Hive metadata but never writes the sidecar
  // JSON file that localDataSource.getReportDetail() requires.
  //
  // Fix: detect backend-processed reports by parserVersion and rebuild
  // ReportDetail from backend APIs.  Falls back to cached Hive data when the
  // network is unavailable.  Local-parsed reports still use the sidecar path.

  @override
  Future<ReportDetail> getReportDetail(String reportId) async {
    final entry = HiveManager.localReportBox.get(reportId);
    if (entry == null) {
      throw StateError('Report $reportId not found in local storage.');
    }

    CsLogger.info('ReportDetail', 'Loading report',
        data: {'id': reportId, 'status': entry.status, 'parser': entry.parserVersion ?? 'local'});

    // ── Still being processed by backend ─────────────────────────────────────
    if (entry.status == 'backend_processing') {
      CsLogger.info('ReportDetail', 'Report still processing — returning pending detail');
      return _buildPendingDetail(entry);
    }

    // ── Backend-processed report ──────────────────────────────────────────────
    if (entry.parserVersion == _kBackendParserVersion) {
      return _getBackendDetail(reportId, entry);
    }

    // ── Local-parsed report: read from sidecar JSON ───────────────────────────
    try {
      return await localDataSource.getReportDetail(reportId);
    } catch (e) {
      // Sidecar JSON missing (e.g. device wiped, app reinstalled).
      // Fall back to Hive metadata — better than crashing.
      CsLogger.warning('ReportDetail', 'Sidecar JSON missing — using Hive fallback',
          data: {'id': reportId, 'error': '$e'});
      return _buildFromHiveOnly(entry);
    }
  }

  // ── Backend detail: fetch summary + reconciliation from API ──────────────

  Future<ReportDetail> _getBackendDetail(
    String reportId,
    LocalReportHiveObject entry,
  ) async {
    CsLogger.info('ReportDetail', 'Fetching backend data',
        data: {'id': reportId, 'platform': entry.platform});

    try {
      final results = await Future.wait([
        remoteDataSource.fetchSummary(reportId),
        remoteDataSource.fetchReconciliation(reportId, entry.platform),
      ]);

      final summary = results[0] as ParsedSummary;
      final recon   = results[1] as ReconciliationResult;

      CsLogger.info('ReportDetail', 'Backend data loaded',
          data: {'orders': summary.totalOrders, 'discrepancies': recon.discrepancyCount,
                 'gross': summary.grossSales});

      // Keep Hive in sync with latest backend data
      entry
        ..totalOrders     = summary.totalOrders
        ..grossRevenue    = summary.grossSales
        ..totalFees       = summary.totalFees
        ..netSettlement   = summary.netEarnings
        ..discrepancyCount = recon.discrepancyCount;
      await entry.save();

      return ReportDetail(
        report: _toListItem(entry),
        parseResult: _backendParseResult(entry, summary),
        reconciliationResult: recon,
      );
    } catch (e, st) {
      CsLogger.error('ReportDetail', 'Backend fetch failed — using Hive cache',
          error: e, stack: st);
      // Network unavailable — show what we already have in Hive
      return _buildFromHiveOnly(entry);
    }
  }

  // ── _parseFromBackend (called once at upload completion) ─────────────────

  Future<ReportDetail> _parseFromBackend(
    String reportId,
    LocalReportHiveObject entry,
  ) async {
    CsLogger.info('Repo', 'Polling backend', data: {'file_id': reportId});

    try {
      final status = await remoteDataSource.pollUntilDone(reportId);

      if (status.isFailed) {
        entry
          ..status       = 'failed'
          ..errorMessage = status.errorMessage ?? 'Backend processing failed';
        await entry.save();
        throw StateError(entry.errorMessage!);
      }

      final results = await Future.wait([
        remoteDataSource.fetchSummary(reportId),
        remoteDataSource.fetchReconciliation(
          reportId,
          status.platform.isNotEmpty ? status.platform : entry.platform,
        ),
      ]);

      final summary = results[0] as ParsedSummary;
      final recon   = results[1] as ReconciliationResult;

      CsLogger.info('Repo', 'Backend processing complete',
          data: {'platform': status.platform, 'orders': summary.totalOrders,
                 'discrepancies': recon.discrepancyCount});

      entry
        ..status          = 'parsed'
        ..platform        = status.platform.isNotEmpty ? status.platform : entry.platform
        ..reportType      = status.reportType.isNotEmpty ? status.reportType : entry.reportType
        ..parsedAt        = DateTime.now().toIso8601String()
        ..totalOrders     = summary.totalOrders
        ..grossRevenue    = summary.grossSales
        ..totalFees       = summary.totalFees
        ..netSettlement   = summary.netEarnings
        ..discrepancyCount = recon.discrepancyCount
        ..parserVersion   = _kBackendParserVersion
        ..errorMessage    = null;
      await entry.save();

      return ReportDetail(
        report: _toListItem(entry),
        parseResult: _backendParseResult(entry, summary),
        reconciliationResult: recon,
      );
    } catch (e) {
      if (e is StateError) rethrow;
      CsLogger.error('Repo', 'Backend fetch failed during parse', error: e);
      entry
        ..status       = 'failed'
        ..errorMessage = e.toString();
      await entry.save();
      rethrow;
    }
  }

  // ── Helpers ───────────────────────────────────────────────────────────────

  ParseResult _backendParseResult(
    LocalReportHiveObject entry,
    ParsedSummary summary,
  ) {
    return ParseResult(
      marketplace:   entry.platform,
      parserVersion: _kBackendParserVersion,
      fileHash:      entry.fileHash ?? '',
      fileName:      entry.fileName,
      parsedAt:      entry.parsedAt != null
          ? DateTime.tryParse(entry.parsedAt!) ?? DateTime.now()
          : DateTime.now(),
      orders:        const [],
      summary:       summary,
      errors:        const [],
      warnings:      const [],
      sheetsFound:   const ['backend_processed'],
    );
  }

  /// Builds a minimal ReportDetail from Hive metadata alone — used as an
  /// offline fallback when backend APIs are unreachable.
  ReportDetail _buildFromHiveOnly(LocalReportHiveObject entry) {
    CsLogger.info('ReportDetail', 'Building from Hive cache only',
        data: {'id': entry.id, 'gross': entry.grossRevenue});

    final summary = ParsedSummary(
      grossSales:   entry.grossRevenue,
      netEarnings:  entry.netSettlement,
      totalCommission: entry.totalFees,
      totalOrders:  entry.totalOrders,
    );

    return ReportDetail(
      report: _toListItem(entry),
      parseResult: ParseResult(
        marketplace:   entry.platform,
        parserVersion: entry.parserVersion ?? _kBackendParserVersion,
        fileHash:      '',
        fileName:      entry.fileName,
        parsedAt:      entry.parsedAt != null
            ? DateTime.tryParse(entry.parsedAt!) ?? DateTime.now()
            : DateTime.now(),
        orders:  const [],
        summary: summary,
        errors:  const [],
        warnings: const [],
        sheetsFound: const [],
      ),
      reconciliationResult: ReconciliationResult(
        reportId:     entry.id,
        marketplace:  entry.platform,
        reconciledAt: DateTime.now(),
        totalOrders:  entry.totalOrders,
        grossRevenue: entry.grossRevenue,
        totalFees:    entry.totalFees,
        netSettlement: entry.netSettlement,
        discrepancies: const [],
        parseWarnings: const [],
      ),
    );
  }

  /// Builds a pending ReportDetail for reports still being processed by backend.
  ReportDetail _buildPendingDetail(LocalReportHiveObject entry) {
    return ReportDetail(
      report: _toListItem(entry),
      parseResult: ParseResult(
        marketplace:   entry.platform,
        parserVersion: 'pending',
        fileHash:      '',
        fileName:      entry.fileName,
        parsedAt:      DateTime.now(),
        orders:  const [],
        summary: null,
        errors:  const [],
        warnings: const [],
        sheetsFound: const [],
      ),
      reconciliationResult: ReconciliationResult(
        reportId:      entry.id,
        marketplace:   entry.platform,
        reconciledAt:  DateTime.now(),
        totalOrders:   0,
        grossRevenue:  0,
        totalFees:     0,
        netSettlement: 0,
        discrepancies: const [],
        parseWarnings: const [],
      ),
    );
  }

  ReportListItem _toListItem(LocalReportHiveObject obj) {
    return ReportListItem(
      id:               obj.id,
      fileName:         obj.fileName,
      marketplace:      obj.platform,
      reportType:       obj.reportType,
      uploadedAt:       DateTime.tryParse(obj.uploadedAt) ?? DateTime.now(),
      status:           obj.status,
      fileSize:         obj.fileSize,
      totalOrders:      obj.totalOrders,
      grossRevenue:     obj.grossRevenue,
      netSettlement:    obj.netSettlement,
      discrepancyCount: obj.discrepancyCount,
      parsedAt:         obj.parsedAt != null ? DateTime.tryParse(obj.parsedAt!) : null,
      errorMessage:     obj.errorMessage,
      filePath:         obj.filePath,
    );
  }

  @override
  List<ReportListItem> getReports() => localDataSource.getReports();

  @override
  Future<void> deleteReport(String reportId) =>
      localDataSource.deleteReport(reportId);
}
