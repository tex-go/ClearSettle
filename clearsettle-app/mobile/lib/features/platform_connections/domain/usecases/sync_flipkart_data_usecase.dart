import 'dart:convert';

import '../../../../reconciliation/reconciliation_engine.dart';
import '../../../../services/file_storage/file_storage_service.dart';
import '../../../../services/flipkart_api/flipkart_api_service.dart';
import '../../../../storage/entities/discrepancy_hive_object.dart';
import '../../../../storage/entities/local_report_hive_object.dart';
import '../../../../storage/entities/report_summary_hive_object.dart';
import '../../../../storage/hive_manager.dart';
import '../repositories/platform_connection_repository.dart';

class SyncFlipkartDataResult {
  const SyncFlipkartDataResult({
    required this.reportId,
    required this.ordersCount,
    required this.discrepancyCount,
    required this.grossRevenue,
    required this.netSettlement,
  });

  final String reportId;
  final int ordersCount;
  final int discrepancyCount;
  final double grossRevenue;
  final double netSettlement;
}

/// Fetches live seller data from the Flipkart API, runs reconciliation,
/// and persists results using the same Hive pipeline as manual report uploads.
class SyncFlipkartDataUseCase {
  const SyncFlipkartDataUseCase({
    required this.apiService,
    required this.reconciliationEngine,
    required this.fileStorage,
    required this.connectionRepository,
  });

  final FlipkartApiService apiService;
  final ReconciliationEngine reconciliationEngine;
  final FileStorageService fileStorage;
  final PlatformConnectionRepository connectionRepository;

  /// Syncs the last [daysBack] days of data (default: 30).
  Future<SyncFlipkartDataResult> execute({int daysBack = 30}) async {
    final to = DateTime.now();
    final from = to.subtract(Duration(days: daysBack));

    final syncResult = await apiService.fetchSellerData(from: from, to: to);
    final parseResult = syncResult.parseResult;

    final reportId = parseResult.fileHash; // uuid already generated in service
    final reconResult = reconciliationEngine.reconcile(parseResult, reportId);

    // Persist sidecar JSON (same format as manual uploads — readable by app)
    final sidecarJson = jsonEncode({
      'marketplace': parseResult.marketplace,
      'parser_version': parseResult.parserVersion,
      'file_hash': parseResult.fileHash,
      'file_name': parseResult.fileName,
      'parsed_at': parseResult.parsedAt.toIso8601String(),
      'sheets_found': parseResult.sheetsFound,
      'summary': parseResult.effectiveSummary.toJson(),
      'orders': parseResult.orders.map((o) => o.toJson()).toList(),
      'errors': <String>[],
      'warnings': <String>[],
      'reconciliation': reconResult.toJson(),
    });

    await fileStorage.saveParsedJson(
      marketplace: 'flipkart',
      reportId: reportId,
      json: sidecarJson,
    );

    final summary = parseResult.effectiveSummary;

    // Store as a LocalReportHiveObject so it appears in Reports list
    final entry = LocalReportHiveObject(
      id: reportId,
      fileName: parseResult.fileName,
      platform: 'flipkart',
      reportType: 'api_sync',
      uploadedAt: parseResult.parsedAt.toIso8601String(),
      status: 'parsed',
      filePath: null, // no physical file for API-sourced reports
      fileSize: sidecarJson.length,
      fileHash: parseResult.fileHash,
      parsedAt: parseResult.parsedAt.toIso8601String(),
      totalOrders: summary.totalOrders,
      grossRevenue: summary.grossSales,
      totalFees: summary.totalFees,
      netSettlement: summary.netEarnings,
      discrepancyCount: reconResult.discrepancyCount,
      parserVersion: parseResult.parserVersion,
    );
    await HiveManager.localReportBox.put(reportId, entry);

    // Persist summary
    final summaryObj = ReportSummaryHiveObject(
      reportId: reportId,
      marketplace: 'flipkart',
      totalOrders: reconResult.totalOrders,
      grossRevenue: reconResult.grossRevenue,
      totalFees: reconResult.totalFees,
      totalCommission: summary.totalCommission,
      totalShipping: summary.totalShipping,
      totalGstOnFees: summary.totalGstOnFees,
      totalTcs: summary.totalTcs,
      totalTds: summary.totalTds,
      netSettlement: reconResult.netSettlement,
      discrepancyCount: reconResult.discrepancyCount,
      criticalCount: reconResult.criticalCount,
      totalVariance: reconResult.totalVariance,
      reconciledAt: reconResult.reconciledAt.toIso8601String(),
      parserVersion: parseResult.parserVersion,
    );
    await HiveManager.reportSummaryBox.put(reportId, summaryObj);

    // Persist discrepancies
    for (int i = 0; i < reconResult.discrepancies.length; i++) {
      final d = reconResult.discrepancies[i];
      final key = '${reportId}_$i';
      await HiveManager.discrepancyBox.put(
        key,
        DiscrepancyHiveObject(
          id: key,
          reportId: reportId,
          type: d.type.name,
          severity: d.severity.name,
          description: d.description,
          expectedAmount: d.expectedAmount,
          actualAmount: d.actualAmount,
          variance: d.variance,
          createdAt: DateTime.now().toIso8601String(),
          orderId: d.orderId,
          feeType: d.feeType,
          ruleName: d.ruleName,
        ),
      );
    }

    // Stamp lastSyncAt on the connection record
    final connections = await connectionRepository.getConnections();
    final existing = connections.where((c) => c.platform == 'flipkart').firstOrNull;
    if (existing != null) {
      await connectionRepository.saveConnection(
        existing.copyWith(lastSyncAt: DateTime.now()),
      );
    }

    return SyncFlipkartDataResult(
      reportId: reportId,
      ordersCount: syncResult.ordersCount,
      discrepancyCount: reconResult.discrepancyCount,
      grossRevenue: reconResult.grossRevenue,
      netSettlement: reconResult.netSettlement,
    );
  }
}
