import 'dart:convert';

import 'package:crypto/crypto.dart';
import 'package:flutter/foundation.dart';
import 'package:uuid/uuid.dart';

import '../../../../parsers/flipkart/flipkart_parser.dart';
import '../../../../parsers/parser_registry.dart';
import '../../../../parsers/parser_result.dart';
import '../../../../reconciliation/reconciliation_engine.dart';
import '../../../../reconciliation/reconciliation_result.dart';
import '../../../../services/file_storage/file_storage_service.dart';
import '../../../../storage/entities/discrepancy_hive_object.dart';
import '../../../../storage/entities/local_report_hive_object.dart';
import '../../../../storage/entities/report_summary_hive_object.dart';
import '../../../../storage/hive_manager.dart';
import '../../domain/entities/report_entities.dart';

class _ParseRequest {
  const _ParseRequest({
    required this.bytes,
    required this.fileName,
    required this.fileHash,
    required this.marketplace,
  });
  final Uint8List bytes;
  final String fileName;
  final String fileHash;
  final String marketplace;
}

// Top-level isolate function — must be top-level or static
ParseResult _runParser(_ParseRequest req) {
  final parser = ParserRegistry.forMarketplace(req.marketplace) ?? FlipkartParser();
  return parser.parseSync(req.bytes, req.fileName, req.fileHash);
}

class ReportLocalDataSource {
  ReportLocalDataSource({
    required this.fileStorage,
    required this.reconciliationEngine,
  });

  final FileStorageService fileStorage;
  final ReconciliationEngine reconciliationEngine;
  static const _uuid = Uuid();

  // ── Upload ────────────────────────────────────────────────────────────────

  Future<String> saveReport({
    required String marketplace,
    required String reportType,
    required String fileName,
    required Uint8List bytes,
  }) async {
    final id = _uuid.v4();
    final hash = sha256.convert(bytes).toString();
    final storedFileName = '${id}_$fileName';

    final filePath = await fileStorage.saveReport(
      marketplace: marketplace,
      fileName: storedFileName,
      bytes: bytes,
    );

    final entry = LocalReportHiveObject(
      id: id,
      fileName: fileName,
      platform: marketplace,
      reportType: reportType,
      uploadedAt: DateTime.now().toIso8601String(),
      status: 'pending_parse',
      filePath: filePath,
      fileSize: bytes.length,
      fileHash: hash,
    );
    await HiveManager.localReportBox.put(id, entry);
    return id;
  }

  // ── Parse ────────────────────────────────────────────────────────────────

  Future<ReportDetail> parseReport(String reportId) async {
    final entry = HiveManager.localReportBox.get(reportId);
    if (entry == null) throw StateError('Report $reportId not found in local storage.');

    // Mark as parsing
    entry.status = 'parsing';
    await entry.save();

    try {
      final bytes = await fileStorage.readReport(entry.filePath ?? '');
      if (bytes == null) {
        throw StateError('Report file not found at ${entry.filePath}');
      }

      final hash = entry.fileHash ?? sha256.convert(bytes).toString();

      // Run parser in isolate so UI stays responsive
      final parseResult = await compute(
        _runParser,
        _ParseRequest(
          bytes: Uint8List.fromList(bytes),
          fileName: entry.fileName,
          fileHash: hash,
          marketplace: entry.platform,
        ),
      );

      // Reconcile on main isolate (fast — pure Dart)
      final reconResult = reconciliationEngine.reconcile(parseResult, reportId);

      // Persist sidecar JSON
      await _saveSidecarJson(entry.platform, reportId, parseResult, reconResult);

      // Update Hive metadata
      final summary = parseResult.effectiveSummary;
      entry
        ..status = parseResult.hasErrors ? 'failed' : 'parsed'
        ..parsedAt = DateTime.now().toIso8601String()
        ..totalOrders = summary.totalOrders > 0
            ? summary.totalOrders
            : parseResult.orders.length
        ..grossRevenue = summary.grossSales
        ..totalFees = summary.totalFees
        ..netSettlement = summary.netEarnings
        ..discrepancyCount = reconResult.discrepancyCount
        ..parserVersion = parseResult.parserVersion
        ..errorMessage = parseResult.errors.isEmpty
            ? null
            : parseResult.errors.first.message;
      await entry.save();

      // Persist summary and discrepancies
      await _persistSummary(entry.platform, reportId, reconResult, parseResult.parserVersion);
      await _persistDiscrepancies(reportId, reconResult.discrepancies);

      return ReportDetail(
        report: _toListItem(entry),
        parseResult: parseResult,
        reconciliationResult: reconResult,
      );
    } catch (e) {
      entry
        ..status = 'failed'
        ..errorMessage = e.toString();
      await entry.save();
      rethrow;
    }
  }

  // ── Read ────────────────────────────────────────────────────────────────

  List<ReportListItem> getReports() {
    return HiveManager.localReportBox.values
        .map(_toListItem)
        .toList()
      ..sort((a, b) => b.uploadedAt.compareTo(a.uploadedAt));
  }

  Future<ReportDetail> getReportDetail(String reportId) async {
    final entry = HiveManager.localReportBox.get(reportId);
    if (entry == null) throw StateError('Report $reportId not found.');

    final jsonStr = await fileStorage.readParsedJson(
      marketplace: entry.platform,
      reportId: reportId,
    );
    if (jsonStr == null) throw StateError('Parsed data not found for $reportId. Re-parse required.');

    final jsonMap = jsonDecode(jsonStr) as Map<String, dynamic>;
    final parseResult = _parseResultFromJson(jsonMap, entry);
    final reconResult = _reconResultFromJson(jsonMap, reportId, entry.platform);

    return ReportDetail(
      report: _toListItem(entry),
      parseResult: parseResult,
      reconciliationResult: reconResult,
    );
  }

  // ── Delete ────────────────────────────────────────────────────────────────

  Future<void> deleteReport(String reportId) async {
    final entry = HiveManager.localReportBox.get(reportId);
    if (entry == null) return;

    await fileStorage.deleteReport(
      marketplace: entry.platform,
      reportId: reportId,
      filePath: entry.filePath ?? '',
    );

    // Remove Hive entries
    await HiveManager.localReportBox.delete(reportId);
    await HiveManager.reportSummaryBox.delete(reportId);

    // Remove all discrepancies for this report
    final keys = HiveManager.discrepancyBox.keys
        .where((k) => k.toString().startsWith('${reportId}_'))
        .toList();
    await HiveManager.discrepancyBox.deleteAll(keys);
  }

  // ── Persistence helpers ───────────────────────────────────────────────────

  Future<void> _saveSidecarJson(
    String marketplace,
    String reportId,
    ParseResult parseResult,
    ReconciliationResult reconResult,
  ) async {
    final json = jsonEncode({
      'marketplace': parseResult.marketplace,
      'parser_version': parseResult.parserVersion,
      'file_hash': parseResult.fileHash,
      'file_name': parseResult.fileName,
      'parsed_at': parseResult.parsedAt.toIso8601String(),
      'sheets_found': parseResult.sheetsFound,
      'summary': parseResult.effectiveSummary.toJson(),
      'orders': parseResult.orders.map((o) => o.toJson()).toList(),
      'errors': parseResult.errors.map((e) => e.message).toList(),
      'warnings': parseResult.warnings.map((w) => w.message).toList(),
      'reconciliation': reconResult.toJson(),
    });
    await fileStorage.saveParsedJson(
      marketplace: marketplace,
      reportId: reportId,
      json: json,
    );
  }

  Future<void> _persistSummary(
    String marketplace,
    String reportId,
    ReconciliationResult reconResult,
    String parserVersion,
  ) async {
    final summary = ReportSummaryHiveObject(
      reportId: reportId,
      marketplace: marketplace,
      totalOrders: reconResult.totalOrders,
      grossRevenue: reconResult.grossRevenue,
      totalFees: reconResult.totalFees,
      totalCommission: 0.0,
      totalShipping: 0.0,
      totalGstOnFees: 0.0,
      totalTcs: 0.0,
      totalTds: 0.0,
      netSettlement: reconResult.netSettlement,
      discrepancyCount: reconResult.discrepancyCount,
      criticalCount: reconResult.criticalCount,
      totalVariance: reconResult.totalVariance,
      reconciledAt: reconResult.reconciledAt.toIso8601String(),
      parserVersion: parserVersion,
    );
    await HiveManager.reportSummaryBox.put(reportId, summary);
  }

  Future<void> _persistDiscrepancies(
    String reportId,
    List<Discrepancy> discrepancies,
  ) async {
    final box = HiveManager.discrepancyBox;
    for (int i = 0; i < discrepancies.length; i++) {
      final d = discrepancies[i];
      final key = '${reportId}_$i';
      final obj = DiscrepancyHiveObject(
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
      );
      await box.put(key, obj);
    }
  }

  // ── Mapping helpers ───────────────────────────────────────────────────────

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

  ParseResult _parseResultFromJson(
    Map<String, dynamic> json,
    LocalReportHiveObject entry,
  ) {
    final ordersJson = (json['orders'] as List?) ?? [];
    final orders = ordersJson
        .map((o) => ParsedOrder.fromJson(o as Map<String, dynamic>))
        .toList();
    final summaryJson = json['summary'] as Map<String, dynamic>?;

    return ParseResult(
      marketplace: json['marketplace'] as String? ?? entry.platform,
      parserVersion: json['parser_version'] as String? ?? '1.0.0',
      fileHash: json['file_hash'] as String? ?? '',
      fileName: json['file_name'] as String? ?? entry.fileName,
      parsedAt: DateTime.tryParse(json['parsed_at'] as String? ?? '') ??
          DateTime.now(),
      orders: orders,
      summary: summaryJson != null
          ? ParsedSummary.fromJson(summaryJson)
          : null,
      errors: [],
      warnings: [],
      sheetsFound: List<String>.from(json['sheets_found'] as List? ?? []),
    );
  }

  ReconciliationResult _reconResultFromJson(
    Map<String, dynamic> json,
    String reportId,
    String marketplace,
  ) {
    final reconJson = json['reconciliation'] as Map<String, dynamic>?;
    if (reconJson != null) {
      return ReconciliationResult.fromJson(reconJson);
    }
    return ReconciliationResult(
      reportId: reportId,
      marketplace: marketplace,
      reconciledAt: DateTime.now(),
      totalOrders: 0,
      grossRevenue: 0,
      totalFees: 0,
      netSettlement: 0,
      discrepancies: [],
      parseWarnings: [],
    );
  }
}
