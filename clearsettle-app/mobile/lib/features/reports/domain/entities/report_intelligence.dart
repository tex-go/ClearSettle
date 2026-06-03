library;

/// Domain entity mapping the 14-agent intelligence pipeline API response.
///
/// Returned by GET /ingestion/files/{id}/intelligence
/// Stored in ReportDetectionResult.detection_metadata['intelligence']

class ReportIntelligence {
  const ReportIntelligence({
    required this.pipelineId,
    required this.pipelineStatus,
    required this.platform,
    required this.platformConfidence,
    required this.reportType,
    required this.reportTypeLabel,
    required this.qualityScore,
    required this.totalRows,
    required this.grossSales,
    required this.netSettlement,
    required this.totalOrders,
    required this.feePercentage,
    required this.returnRate,
    required this.settlementEfficiency,
    required this.reconciliationStatus,
    required this.readinessScore,
    required this.discrepanciesFound,
    required this.totalRecoverable,
    required this.insightsCount,
    required this.criticalInsights,
    required this.opportunityAmount,
    required this.driftDetected,
    required this.needsManualReview,
    required this.insights,
    required this.recommendedActions,
    required this.totalDurationMs,
  });

  final String pipelineId;
  final String pipelineStatus;

  // Platform
  final String platform;
  final double platformConfidence;

  // Classification
  final String reportType;
  final String reportTypeLabel;

  // Quality
  final double qualityScore;
  final int totalRows;

  // Financials
  final double grossSales;
  final double netSettlement;
  final int totalOrders;
  final double feePercentage;
  final double returnRate;
  final double settlementEfficiency;

  // Readiness
  final String reconciliationStatus;
  final double readinessScore;

  // Reconciliation
  final int discrepanciesFound;
  final double totalRecoverable;

  // Insights
  final int insightsCount;
  final int criticalInsights;
  final double opportunityAmount;
  final List<IntelligenceInsight> insights;

  // Metadata
  final bool driftDetected;
  final bool needsManualReview;
  final List<String> recommendedActions;
  final double totalDurationMs;

  factory ReportIntelligence.fromJson(Map<String, dynamic> json) {
    final summary = json['summary'] as Map<String, dynamic>? ?? {};
    final insightsAgent = json['insights'] as Map<String, dynamic>? ?? {};
    final insightsList = (insightsAgent['insights'] as List<dynamic>? ?? [])
        .whereType<Map<String, dynamic>>()
        .map(IntelligenceInsight.fromJson)
        .toList();

    return ReportIntelligence(
      pipelineId: json['pipeline_id'] as String? ?? '',
      pipelineStatus: json['pipeline_status'] as String? ?? 'unknown',
      platform: summary['platform'] as String? ?? 'unknown',
      platformConfidence:
          (summary['platform_confidence'] as num?)?.toDouble() ?? 0.0,
      reportType: summary['report_type'] as String? ?? 'unknown',
      reportTypeLabel:
          summary['report_type_label'] as String? ?? 'Unknown Report',
      qualityScore:
          (summary['quality_score'] as num?)?.toDouble() ?? 0.0,
      totalRows: (summary['total_rows'] as num?)?.toInt() ?? 0,
      grossSales:
          double.tryParse(summary['gross_sales'] as String? ?? '0') ?? 0.0,
      netSettlement:
          double.tryParse(summary['net_settlement'] as String? ?? '0') ?? 0.0,
      totalOrders: (summary['total_orders'] as num?)?.toInt() ?? 0,
      feePercentage:
          (summary['fee_percentage'] as num?)?.toDouble() ?? 0.0,
      returnRate: (summary['return_rate'] as num?)?.toDouble() ?? 0.0,
      settlementEfficiency:
          (summary['settlement_efficiency'] as num?)?.toDouble() ?? 0.0,
      reconciliationStatus:
          summary['reconciliation_status'] as String? ?? 'single_report',
      readinessScore:
          (summary['reconciliation_readiness'] as num?)?.toDouble() ?? 0.0,
      discrepanciesFound:
          (summary['discrepancies_found'] as num?)?.toInt() ?? 0,
      totalRecoverable:
          double.tryParse(summary['total_recoverable'] as String? ?? '0') ??
              0.0,
      insightsCount: (summary['insights_count'] as num?)?.toInt() ?? 0,
      criticalInsights:
          (summary['critical_insights'] as num?)?.toInt() ?? 0,
      opportunityAmount:
          double.tryParse(summary['opportunity_amount'] as String? ?? '0') ??
              0.0,
      driftDetected: summary['drift_detected'] as bool? ?? false,
      needsManualReview: summary['needs_manual_review'] as bool? ?? false,
      insights: insightsList,
      recommendedActions: (json['recommended_actions'] as List<dynamic>? ?? [])
          .whereType<String>()
          .toList(),
      totalDurationMs:
          (summary['total_duration_ms'] as num?)?.toDouble() ?? 0.0,
    );
  }
}

class IntelligenceInsight {
  const IntelligenceInsight({
    required this.category,
    required this.severity,
    required this.title,
    required this.message,
    this.metricValue,
    this.action,
  });

  final String category;
  final String severity; // info / warning / critical
  final String title;
  final String message;
  final String? metricValue;
  final String? action;

  factory IntelligenceInsight.fromJson(Map<String, dynamic> json) {
    return IntelligenceInsight(
      category: json['category'] as String? ?? 'info',
      severity: json['severity'] as String? ?? 'info',
      title: json['title'] as String? ?? '',
      message: json['message'] as String? ?? '',
      metricValue: json['metric_value'] as String?,
      action: json['action'] as String?,
    );
  }
}
