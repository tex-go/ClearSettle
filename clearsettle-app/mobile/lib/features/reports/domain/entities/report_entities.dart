import '../../../../parsers/parser_result.dart';
import '../../../../reconciliation/reconciliation_result.dart';

/// Lightweight domain model for the reports list screen
class ReportListItem {
  const ReportListItem({
    required this.id,
    required this.fileName,
    required this.marketplace,
    required this.reportType,
    required this.uploadedAt,
    required this.status,
    required this.fileSize,
    this.totalOrders = 0,
    this.grossRevenue = 0.0,
    this.netSettlement = 0.0,
    this.discrepancyCount = 0,
    this.parsedAt,
    this.errorMessage,
    this.filePath,
  });

  final String id;
  final String fileName;
  final String marketplace;
  final String reportType;
  final DateTime uploadedAt;
  final String status;
  final int fileSize;
  final int totalOrders;
  final double grossRevenue;
  final double netSettlement;
  final int discrepancyCount;
  final DateTime? parsedAt;
  final String? errorMessage;
  final String? filePath;

  bool get isParsed => status == 'parsed';
  bool get isFailed => status == 'failed';
  bool get isParsing => status == 'parsing';
  bool get isPendingParse => status == 'pending_parse';

  String get fileSizeLabel {
    if (fileSize < 1024) return '${fileSize}B';
    if (fileSize < 1024 * 1024) return '${(fileSize / 1024).toStringAsFixed(1)}KB';
    return '${(fileSize / (1024 * 1024)).toStringAsFixed(1)}MB';
  }
}

/// Full detail model once a report has been parsed
class ReportDetail {
  const ReportDetail({
    required this.report,
    required this.parseResult,
    required this.reconciliationResult,
  });

  final ReportListItem report;
  final ParseResult parseResult;
  final ReconciliationResult reconciliationResult;

  ParsedSummary get summary => parseResult.effectiveSummary;
  List<ParsedOrder> get orders => parseResult.orders;
  List<Discrepancy> get discrepancies => reconciliationResult.discrepancies;
}
