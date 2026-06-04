import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/network/api_client.dart';
import '../../../../core/network/api_endpoints.dart';
import '../../../../core/utils/cs_logger.dart';
import '../../../../parsers/parser_result.dart';
import '../../../../reconciliation/reconciliation_result.dart';

// ── Provider ──────────────────────────────────────────────────────────────────

final reportRemoteDataSourceProvider = Provider<ReportRemoteDataSource>((ref) {
  return ReportRemoteDataSource(apiClient: ref.read(apiClientProvider));
});

// ── Upload response ───────────────────────────────────────────────────────────

class RemoteUploadResponse {
  const RemoteUploadResponse({
    required this.fileId,
    required this.originalFileName,
    required this.fileSizeBytes,
    required this.uploadStatus,
    required this.message,
    this.platform,
    this.platformConfidence,
    this.isDuplicate = false,
  });

  final String fileId;
  final String originalFileName;
  final int fileSizeBytes;
  final String uploadStatus;
  final String message;
  final String? platform;
  final double? platformConfidence;
  final bool isDuplicate;

  factory RemoteUploadResponse.fromJson(Map<String, dynamic> j) {
    final rawPreview = j['detection'] ?? j['preview'];
    final preview = rawPreview is Map<String, dynamic> ? rawPreview : null;
    return RemoteUploadResponse(
      fileId: j['id'] as String,
      originalFileName: j['original_file_name'] as String? ?? '',
      fileSizeBytes: (j['file_size_bytes'] as int?) ?? 0,
      uploadStatus: j['upload_status'] as String? ?? 'uploaded',
      message: j['message'] as String? ?? '',
      platform: preview?['detected_platform'] as String?,
      platformConfidence: (preview?['platform_confidence'] as num?)?.toDouble(),
      isDuplicate: j['duplicate'] as bool? ?? false,
    );
  }
}

// ── Processing status ─────────────────────────────────────────────────────────

class RemoteFileStatus {
  const RemoteFileStatus({
    required this.fileId,
    required this.status,
    required this.platform,
    required this.reportType,
    this.errorMessage,
    this.ledgerCount,
    this.processedAt,
  });

  final String fileId;
  final String status;   // uploaded | detecting | processing | done | failed | needs_review
  final String platform;
  final String reportType;
  final String? errorMessage;
  final int? ledgerCount;
  final DateTime? processedAt;

  bool get isDone     => status == 'done' || status == 'needs_review';
  bool get isFailed   => status == 'failed';
  bool get isTerminal => isDone || isFailed;

  factory RemoteFileStatus.fromJson(Map<String, dynamic> j) {
    final det = j['detection'] as Map<String, dynamic>?;
    return RemoteFileStatus(
      fileId: j['id'] as String,
      status: j['upload_status'] as String? ?? 'uploaded',
      platform: det?['detected_platform'] as String? ?? 'unknown',
      reportType: det?['detected_report_type'] as String? ?? 'unknown',
      errorMessage: j['error_message'] as String?,
      ledgerCount: det?['ledger_records_count'] as int?,
      processedAt: j['processed_at'] != null
          ? DateTime.tryParse(j['processed_at'] as String)
          : null,
    );
  }
}

// ── Data source ───────────────────────────────────────────────────────────────

class ReportRemoteDataSource {
  const ReportRemoteDataSource({required this.apiClient});

  final ApiClient apiClient;

  // ── Upload ──────────────────────────────────────────────────────────────────

  Future<RemoteUploadResponse> uploadFile({
    required List<int> fileBytes,
    required String fileName,
    String? platformHint,
    String? reportTypeHint,
  }) async {
    CsLogger.uploadStarted(
      fileName: fileName,
      fileSizeBytes: fileBytes.length,
      marketplace: platformHint ?? 'auto-detect',
    );
    CsLogger.info('RemoteDS', 'POST /ingestion/upload', data: {
      'file_name':        fileName,
      'bytes':            fileBytes.length,
      'platform_hint':    platformHint ?? 'none',
      'report_type_hint': reportTypeHint ?? 'none',
    });

    final fields = <String, String>{};
    if (platformHint != null) fields['platform'] = platformHint;
    if (reportTypeHint != null) fields['report_type'] = reportTypeHint;

    try {
      CsLogger.uploadSent(fileName: fileName, bytes: fileBytes.length);
      final response = await apiClient.uploadFile<Map<String, dynamic>>(
        ApiEndpoints.ingestionUpload,
        fileBytes: fileBytes,
        fileName: fileName,
        fields: fields.isEmpty ? null : fields,
      );

      final body = response.data as Map<String, dynamic>;
      CsLogger.info('RemoteDS', 'Raw upload response', data: {
        'keys':          body.keys.join(', '),
        'id':            body['id'],
        'upload_status': body['upload_status'],
        'file_size_bytes': body['file_size_bytes'],
        'duplicate':     body['duplicate'],
      });

      final result = RemoteUploadResponse.fromJson(body);
      CsLogger.uploadAccepted(
        fileId:     result.fileId,
        status:     result.uploadStatus,
        isDuplicate: result.isDuplicate,
        platform:   result.platform,
        confidence: result.platformConfidence,
      );
      return result;
    } catch (e, st) {
      CsLogger.error('RemoteDS', 'Upload request FAILED', error: e, stack: st, data: {
        'file_name': fileName,
        'endpoint':  ApiEndpoints.ingestionUpload,
      });
      rethrow;
    }
  }

  // ── Poll for completion ─────────────────────────────────────────────────────

  Future<RemoteFileStatus> pollUntilDone(
    String fileId, {
    Duration pollInterval = const Duration(seconds: 3),
    Duration maxWait = const Duration(minutes: 5),
  }) async {
    final deadline  = DateTime.now().add(maxWait);
    final startTime = DateTime.now();
    int   pollCount = 0;

    CsLogger.info('Poll', 'Starting poll loop', data: {
      'file_id':          fileId,
      'poll_interval_s':  pollInterval.inSeconds,
      'max_wait_s':       maxWait.inSeconds,
      'endpoint':         ApiEndpoints.ingestionFile(fileId),
    });

    while (DateTime.now().isBefore(deadline)) {
      await Future<void>.delayed(pollInterval);
      pollCount++;
      final elapsed = DateTime.now().difference(startTime).inSeconds;

      try {
        final response = await apiClient.get<Map<String, dynamic>>(
          ApiEndpoints.ingestionFile(fileId),
        );
        final raw    = response.data as Map<String, dynamic>;
        final status = RemoteFileStatus.fromJson(raw);

        CsLogger.pollTick(
          fileId: fileId,
          status: status.status,
          elapsedSeconds: elapsed,
        );
        CsLogger.info('Poll', 'Poll #$pollCount response', data: {
          'file_id':        fileId,
          'status':         status.status,
          'platform':       status.platform,
          'report_type':    status.reportType,
          'ledger_count':   status.ledgerCount,
          'is_terminal':    status.isTerminal,
          'is_done':        status.isDone,
          'is_failed':      status.isFailed,
          'elapsed_s':      elapsed,
          'error_message':  status.errorMessage,
        });

        if (status.isTerminal) {
          CsLogger.pollDone(
            fileId: fileId,
            status: status.status,
            totalSeconds: elapsed,
          );
          return status;
        }
      } catch (e, st) {
        CsLogger.warning('Poll', 'Poll request failed — will retry', data: {
          'file_id':  fileId,
          'attempt':  pollCount,
          'error':    '$e',
          'elapsed_s': elapsed,
        });
      }
    }

    CsLogger.error('Poll', 'TIMEOUT — backend did not finish in ${maxWait.inSeconds}s', data: {
      'file_id':   fileId,
      'polls_made': pollCount,
    });
    throw TimeoutException(
      'Backend processing timed out after ${maxWait.inSeconds}s for file $fileId',
    );
  }

  // ── Fetch financial summary ─────────────────────────────────────────────────

  Future<ParsedSummary> fetchSummary(String fileId) async {
    CsLogger.info('Summary', 'GET /ingestion/files/$fileId/summary', data: {'file_id': fileId});
    try {
      final response = await apiClient.get<Map<String, dynamic>>(
        ApiEndpoints.ingestionSummary(fileId),
      );
      final j = response.data as Map<String, dynamic>;

      // Log the full raw response so we can see exactly what the backend returns
      CsLogger.info('Summary', 'Raw summary response from backend', data: {
        'file_id':       fileId,
        'total_records': j['total_records'],
        'unique_orders': j['unique_orders'],
        'gross_revenue': j['gross_revenue'],
        'returns_total': j['returns_total'],
        'fees_total':    j['fees_total'],
        'tax_total':     j['tax_total'],
        'payout_total':  j['payout_total'],
        'net_sales':     j['net_sales'],
        'net_settlement': j['net_settlement'],
        'platform':      j['platform'],
        'report_type':   j['report_type'],
        'all_keys':      j.keys.join(', '),
      });

      final feesTotal  = (j['fees_total'] as num?)?.toDouble() ?? 0.0;
      final taxTotal   = (j['tax_total']  as num?)?.toDouble() ?? 0.0;
      final grossSales = (j['gross_revenue'] as num?)?.toDouble() ?? 0.0;
      final orders     = (j['unique_orders'] as int?) ?? 0;
      final payout     = (j['payout_total']  as num?)?.toDouble() ?? 0.0;

      CsLogger.summaryReceived(
        fileId:       fileId,
        totalRecords: (j['total_records'] as int?) ?? 0,
        uniqueOrders: orders,
        grossRevenue: grossSales,
        payoutTotal:  payout,
      );

      return ParsedSummary(
        grossSales:      grossSales,
        returnsValue:    (j['returns_total'] as num?)?.toDouble() ?? 0.0,
        netSales:        (j['net_sales']     as num?)?.toDouble() ?? 0.0,
        totalCommission: feesTotal - taxTotal,
        totalGstOnFees:  taxTotal,
        netEarnings:     payout,
        amountSettled:   payout,
        totalOrders:     orders,
      );
    } catch (e, st) {
      CsLogger.error('Summary', 'fetchSummary FAILED', error: e, stack: st, data: {'file_id': fileId});
      rethrow;
    }
  }

  // ── Fetch reconciliation discrepancies ──────────────────────────────────────

  Future<ReconciliationResult> fetchReconciliation(
    String fileId,
    String marketplace,
  ) async {
    CsLogger.info('Recon', 'GET /ingestion/files/$fileId/reconciliation', data: {'file_id': fileId});
    try {
      final response = await apiClient.get<Map<String, dynamic>>(
        ApiEndpoints.ingestionReconciliation(fileId),
        queryParameters: {'limit': 500},
      );
      final j        = response.data as Map<String, dynamic>;
      final summaryJ = j['summary'] as Map<String, dynamic>? ?? {};
      final items    = j['items'] as List? ?? [];

      CsLogger.info('Recon', 'Reconciliation response', data: {
        'file_id':        fileId,
        'total_issues':   summaryJ['total_issues'],
        'critical_count': summaryJ['critical_count'],
        'recoverable':    summaryJ['recoverable'],
        'items_count':    items.length,
      });

      final discrepancies = items.map((raw) {
        final i         = raw as Map<String, dynamic>;
        final severity  = _mapSeverity(i['severity'] as String? ?? 'info');
        final absVar    = (i['abs_variance'] as num?)?.toDouble() ?? 0.0;
        final direction = i['direction'] as String? ?? '';
        return Discrepancy(
          type: DiscrepancyType.settlementMismatch,
          severity: severity,
          orderId: i['order_id'] as String?,
          description:
              '$direction | ₹${absVar.toStringAsFixed(2)} variance on ${i['platform'] ?? marketplace}',
          expectedAmount: (i['expected_amount'] as num?)?.toDouble() ?? 0.0,
          actualAmount:   (i['actual_amount']   as num?)?.toDouble() ?? 0.0,
          ruleName: 'settlement_variance',
        );
      }).toList();

      final reconSummary = j['summary'] as Map<String, dynamic>? ?? {};
      return ReconciliationResult(
        reportId:     fileId,
        marketplace:  marketplace,
        reconciledAt: DateTime.now(),
        totalOrders:  (reconSummary['total_issues'] as int?) ?? 0,
        grossRevenue: 0.0,
        totalFees:    0.0,
        netSettlement: (reconSummary['recoverable'] as num?)?.toDouble() ?? 0.0,
        discrepancies: discrepancies,
        parseWarnings: [],
      );
    } catch (e, st) {
      CsLogger.error('Recon', 'fetchReconciliation FAILED', error: e, stack: st,
          data: {'file_id': fileId});
      rethrow;
    }
  }

  // ── Fetch remote file list ──────────────────────────────────────────────────

  /// Fetches the paginated list of all uploaded files from the backend.
  /// Used to sync the reports list on app startup (replacing stale Hive-only state).
  Future<List<RemoteFileStatus>> fetchFiles({
    String? platform,
    int page = 1,
    int limit = 100,
  }) async {
    final qp = <String, dynamic>{'page': page, 'limit': limit};
    if (platform != null) qp['platform'] = platform;

    CsLogger.info('RemoteDS', 'GET /ingestion/files', data: qp);
    try {
      final response = await apiClient.get<Map<String, dynamic>>(
        ApiEndpoints.ingestionFiles,
        queryParameters: qp,
      );
      final body  = response.data as Map<String, dynamic>;
      final items = body['items'] as List? ?? [];
      CsLogger.info('RemoteDS', 'fetchFiles returned ${items.length} items');
      return items.map((raw) {
        final j = raw as Map<String, dynamic>;
        return RemoteFileStatus(
          fileId:      j['id'] as String,
          status:      j['upload_status'] as String? ?? 'done',
          platform:    (j['detection'] as Map<String, dynamic>?)?['detected_platform'] as String? ?? 'unknown',
          reportType:  (j['detection'] as Map<String, dynamic>?)?['detected_report_type'] as String? ?? 'unknown',
          errorMessage: j['error_message'] as String?,
          ledgerCount: (j['detection'] as Map<String, dynamic>?)?['ledger_records_count'] as int?,
          processedAt: j['processed_at'] != null
              ? DateTime.tryParse(j['processed_at'] as String)
              : null,
        );
      }).toList();
    } catch (e, st) {
      CsLogger.error('RemoteDS', 'fetchFiles FAILED', error: e, stack: st);
      rethrow;
    }
  }

  /// Fetches the HTML analytics report as raw bytes.
  /// Caller saves to a temp file and shares via share_plus.
  Future<List<int>> fetchHtmlReportBytes(String fileId) async {
    final bytes = await apiClient.getBytes(
      ApiEndpoints.ingestionReport(fileId),
    );
    if (bytes.isEmpty) {
      throw Exception('Empty report response from server.');
    }
    return bytes;
  }

  DiscrepancySeverity _mapSeverity(String s) {
    switch (s) {
      case 'critical':
        return DiscrepancySeverity.critical;
      case 'warning':
        return DiscrepancySeverity.high;
      default:
        return DiscrepancySeverity.medium;
    }
  }
}

class TimeoutException implements Exception {
  const TimeoutException(this.message);
  final String message;
  @override
  String toString() => 'TimeoutException: $message';
}
