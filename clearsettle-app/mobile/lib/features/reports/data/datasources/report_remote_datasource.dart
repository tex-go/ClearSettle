import 'dart:developer' as dev;

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/network/api_client.dart';
import '../../../../core/network/api_endpoints.dart';
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
    dev.log(
      '[INFO] Upload started | file=$fileName bytes=${fileBytes.length}',
      name: 'ClearSettle.Upload',
    );

    final fields = <String, String>{};
    if (platformHint != null) fields['platform'] = platformHint;
    if (reportTypeHint != null) fields['report_type'] = reportTypeHint;

    final response = await apiClient.uploadFile<Map<String, dynamic>>(
      ApiEndpoints.ingestionUpload,
      fileBytes: fileBytes,
      fileName: fileName,
      fields: fields.isEmpty ? null : fields,
    );

    final body = response.data as Map<String, dynamic>;
    final result = RemoteUploadResponse.fromJson(body);

    dev.log(
      '[INFO] Upload accepted | file_id=${result.fileId} '
      'status=${result.uploadStatus} platform=${result.platform} '
      'confidence=${result.platformConfidence?.toStringAsFixed(2)}',
      name: 'ClearSettle.Upload',
    );

    return result;
  }

  // ── Poll for completion ─────────────────────────────────────────────────────

  /// Polls GET /ingestion/files/{id} until status is terminal (done/failed).
  /// Throws [TimeoutException] if not complete within [maxWait].
  Future<RemoteFileStatus> pollUntilDone(
    String fileId, {
    Duration pollInterval = const Duration(seconds: 3),
    Duration maxWait = const Duration(minutes: 5),
  }) async {
    final deadline = DateTime.now().add(maxWait);

    dev.log(
      '[INFO] Polling backend for processing result | file_id=$fileId',
      name: 'ClearSettle.Upload',
    );

    while (DateTime.now().isBefore(deadline)) {
      await Future<void>.delayed(pollInterval);

      final response = await apiClient.get<Map<String, dynamic>>(
        ApiEndpoints.ingestionFile(fileId),
      );
      final status = RemoteFileStatus.fromJson(
        response.data as Map<String, dynamic>,
      );

      dev.log(
        '[INFO] Poll result | file_id=$fileId status=${status.status} '
        'platform=${status.platform}',
        name: 'ClearSettle.Upload',
      );

      if (status.isTerminal) return status;
    }

    throw TimeoutException(
      'Backend processing timed out after ${maxWait.inSeconds}s for file $fileId',
    );
  }

  // ── Fetch financial summary ─────────────────────────────────────────────────

  Future<ParsedSummary> fetchSummary(String fileId) async {
    final response = await apiClient.get<Map<String, dynamic>>(
      ApiEndpoints.ingestionSummary(fileId),
    );
    final j = response.data as Map<String, dynamic>;

    dev.log(
      '[INFO] Summary fetched | file_id=$fileId '
      'gross=${j['gross_revenue']} payout=${j['payout_total']} '
      'records=${j['total_records']}',
      name: 'ClearSettle.Upload',
    );

    // Backend returns aggregate fees_total; map to commission as the primary fee field.
    // tax_total → totalGstOnFees; remaining → totalCommission.
    final feesTotal = (j['fees_total'] as num?)?.toDouble() ?? 0.0;
    final taxTotal  = (j['tax_total']  as num?)?.toDouble() ?? 0.0;

    return ParsedSummary(
      grossSales:       (j['gross_revenue'] as num?)?.toDouble() ?? 0.0,
      returnsValue:     (j['returns_total'] as num?)?.toDouble() ?? 0.0,
      netSales:         (j['net_sales']     as num?)?.toDouble() ?? 0.0,
      totalCommission:  feesTotal - taxTotal,   // fees minus tax component
      totalGstOnFees:   taxTotal,
      netEarnings:      (j['payout_total']  as num?)?.toDouble() ?? 0.0,
      amountSettled:    (j['payout_total']  as num?)?.toDouble() ?? 0.0,
      totalOrders:      (j['unique_orders'] as int?) ?? 0,
    );
  }

  // ── Fetch reconciliation discrepancies ──────────────────────────────────────

  Future<ReconciliationResult> fetchReconciliation(
    String fileId,
    String marketplace,
  ) async {
    final response = await apiClient.get<Map<String, dynamic>>(
      ApiEndpoints.ingestionReconciliation(fileId),
      queryParameters: {'limit': 500},
    );
    final j = response.data as Map<String, dynamic>;
    final summaryJ = j['summary'] as Map<String, dynamic>? ?? {};
    final items = j['items'] as List? ?? [];

    dev.log(
      '[INFO] Reconciliation fetched | file_id=$fileId '
      'issues=${summaryJ['total_issues']} '
      'critical=${summaryJ['critical_count']} '
      'recoverable=${summaryJ['recoverable']}',
      name: 'ClearSettle.Upload',
    );

    final discrepancies = items.map((raw) {
      final i = raw as Map<String, dynamic>;
      final severity = _mapSeverity(i['severity'] as String? ?? 'info');
      final absVar = (i['abs_variance'] as num?)?.toDouble() ?? 0.0;
      final direction = i['direction'] as String? ?? '';
      return Discrepancy(
        type: DiscrepancyType.settlementMismatch,
        severity: severity,
        orderId: i['order_id'] as String?,
        description:
            '$direction | ₹${absVar.toStringAsFixed(2)} variance on ${i['platform'] ?? marketplace}',
        expectedAmount: (i['expected_amount'] as num?)?.toDouble() ?? 0.0,
        actualAmount: (i['actual_amount'] as num?)?.toDouble() ?? 0.0,
        ruleName: 'settlement_variance',
      );
    }).toList();

    final reconSummary = (j['summary'] as Map<String, dynamic>? ?? {});
    return ReconciliationResult(
      reportId: fileId,
      marketplace: marketplace,
      reconciledAt: DateTime.now(),
      totalOrders: (reconSummary['total_issues'] as int?) ?? 0,
      grossRevenue: 0.0,
      totalFees: 0.0,
      netSettlement: (reconSummary['recoverable'] as num?)?.toDouble() ?? 0.0,
      discrepancies: discrepancies,
      parseWarnings: [],
    );
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
