import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/constants/route_constants.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_text_styles.dart';
import '../../../../core/utils/date_formatter.dart';
import '../../../../services/export/export_service.dart';
import '../../../../shared/widgets/app_error_widget.dart';
import '../../../../shared/widgets/loading_indicator.dart';
import '../../domain/entities/report_intelligence.dart';
import '../providers/report_detail_provider.dart';
import '../providers/reports_provider.dart';
import '../widgets/summary_financials_widget.dart';

class ReportDetailScreen extends ConsumerWidget {
  const ReportDetailScreen({super.key, required this.reportId});

  final String reportId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final detailAsync = ref.watch(reportDetailProvider(reportId));

    return Scaffold(
      appBar: AppBar(
        title: const Text('Report Detail'),
        actions: [
          detailAsync.when(
            loading: () => const SizedBox.shrink(),
            error: (_, __) => const SizedBox.shrink(),
            data: (detail) => _ExportButton(
              reportName: detail.report.fileName,
              detail: detail,
            ),
          ),
          IconButton(
            icon: const Icon(Icons.refresh_outlined),
            onPressed: () =>
                ref.read(reportDetailProvider(reportId).notifier).refresh(),
          ),
        ],
      ),
      body: detailAsync.when(
        loading: () => const LoadingIndicator(message: 'Loading report…'),
        error: (e, _) => AppErrorWidget(
          message: e.toString(),
          onRetry: () =>
              ref.read(reportDetailProvider(reportId).notifier).refresh(),
        ),
        data: (detail) {
          if (detail.report.isFailed) {
            return CustomScrollView(
              slivers: [
                SliverToBoxAdapter(
                  child: _HeaderCard(
                    fileName: detail.report.fileName,
                    marketplace: detail.report.marketplace,
                    uploadedAt: detail.report.uploadedAt,
                    parsedAt: detail.report.parsedAt,
                    fileSize: detail.report.fileSizeLabel,
                    parserVersion: detail.parseResult.parserVersion,
                  ),
                ),
                SliverToBoxAdapter(
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(16, 8, 16, 0),
                    child: _FailedReportCard(
                      errorMessage: detail.report.errorMessage,
                      onRetry: () => ref
                          .read(reportsProvider.notifier)
                          .retryParse(reportId),
                    ),
                  ),
                ),
                const SliverToBoxAdapter(child: SizedBox(height: 32)),
              ],
            );
          }

          return CustomScrollView(
            slivers: [
              SliverToBoxAdapter(
                child: _HeaderCard(
                  fileName: detail.report.fileName,
                  marketplace: detail.report.marketplace,
                  uploadedAt: detail.report.uploadedAt,
                  parsedAt: detail.report.parsedAt,
                  fileSize: detail.report.fileSizeLabel,
                  parserVersion: detail.parseResult.parserVersion,
                ),
              ),
              SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
                  child: _StatsRow(
                    orders: detail.report.totalOrders,
                    discrepancies: detail.report.discrepancyCount,
                    warnings: detail.parseResult.warnings.length,
                  ),
                ),
              ),
              SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
                  child: SummaryFinancialsWidget(summary: detail.summary),
                ),
              ),
              SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(16, 16, 16, 0),
                  child: _ActionButtons(reportId: reportId),
                ),
              ),
              // ── Intelligence Card (shown when available) ──────────────────
              if (detail.parseResult.intelligence != null)
                SliverToBoxAdapter(
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(16, 16, 16, 0),
                    child: _IntelligenceCard(
                      intelligence: detail.parseResult.intelligence!,
                    ),
                  ),
                ),
              const SliverToBoxAdapter(child: SizedBox(height: 32)),
            ],
          );
        },
      ),
    );
  }
}

// ── Export button (dropdown: PDF / Excel / CSV) ────────────────────────────

class _ExportButton extends ConsumerWidget {
  const _ExportButton({
    required this.reportName,
    required this.detail,
  });

  final String reportName;
  final dynamic detail; // ReportDetail

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final service = ref.read(exportServiceProvider);

    return PopupMenuButton<_ExportFormat>(
      icon: const Icon(Icons.ios_share_outlined),
      tooltip: 'Export',
      onSelected: (fmt) => _export(context, service, fmt),
      itemBuilder: (_) => const [
        PopupMenuItem(
          value: _ExportFormat.pdf,
          child: _ExportMenuItem(
            icon: Icons.picture_as_pdf_outlined,
            label: 'Export PDF',
          ),
        ),
        PopupMenuItem(
          value: _ExportFormat.excel,
          child: _ExportMenuItem(
            icon: Icons.table_chart_outlined,
            label: 'Export Excel',
          ),
        ),
        PopupMenuItem(
          value: _ExportFormat.csv,
          child: _ExportMenuItem(
            icon: Icons.table_rows_outlined,
            label: 'Export Orders CSV',
          ),
        ),
      ],
    );
  }

  Future<void> _export(
    BuildContext context,
    ExportService service,
    _ExportFormat fmt,
  ) async {
    final messenger = ScaffoldMessenger.of(context);

    try {
      switch (fmt) {
        case _ExportFormat.pdf:
          await service.exportPdf(
            reportName: reportName,
            summary: detail.summary,
            orders: detail.orders,
            discrepancies: detail.discrepancies,
          );
        case _ExportFormat.excel:
          await service.exportExcel(
            reportName: reportName,
            summary: detail.summary,
            orders: detail.orders,
            discrepancies: detail.discrepancies,
          );
        case _ExportFormat.csv:
          await service.exportOrdersCsv(
            reportName: reportName,
            orders: detail.orders,
          );
      }
    } catch (e) {
      messenger.showSnackBar(
        SnackBar(content: Text('Export failed: $e')),
      );
    }
  }
}

enum _ExportFormat { pdf, excel, csv }

class _ExportMenuItem extends StatelessWidget {
  const _ExportMenuItem({required this.icon, required this.label});

  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Icon(icon, size: 18, color: AppColors.primary),
        const SizedBox(width: 10),
        Text(label),
      ],
    );
  }
}

// ── Header ─────────────────────────────────────────────────────────────────

class _HeaderCard extends StatelessWidget {
  const _HeaderCard({
    required this.fileName,
    required this.marketplace,
    required this.uploadedAt,
    required this.parsedAt,
    required this.fileSize,
    required this.parserVersion,
  });

  final String fileName;
  final String marketplace;
  final DateTime uploadedAt;
  final DateTime? parsedAt;
  final String fileSize;
  final String parserVersion;

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.all(16),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.divider),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.table_chart_outlined,
                  color: AppColors.primary, size: 22),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  fileName,
                  style: AppTextStyles.titleLarge,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          _InfoRow(
            icon: Icons.storefront_outlined,
            label: marketplace.toUpperCase(),
          ),
          _InfoRow(
            icon: Icons.upload_outlined,
            label: 'Uploaded ${DateFormatter.formatDate(uploadedAt)}',
          ),
          if (parsedAt != null)
            _InfoRow(
              icon: Icons.check_circle_outline,
              label: 'Parsed ${DateFormatter.formatRelative(parsedAt!)}',
            ),
          _InfoRow(icon: Icons.storage_outlined, label: fileSize),
          _InfoRow(
              icon: Icons.code_outlined, label: 'Parser v$parserVersion'),
        ],
      ),
    );
  }
}

class _InfoRow extends StatelessWidget {
  const _InfoRow({required this.icon, required this.label});

  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Row(
        children: [
          Icon(icon, size: 14, color: AppColors.textSecondary),
          const SizedBox(width: 6),
          Text(label, style: AppTextStyles.bodySmall),
        ],
      ),
    );
  }
}

// ── Stats ──────────────────────────────────────────────────────────────────

class _StatsRow extends StatelessWidget {
  const _StatsRow({
    required this.orders,
    required this.discrepancies,
    required this.warnings,
  });

  final int orders;
  final int discrepancies;
  final int warnings;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Expanded(
          child: _StatChip(
            icon: Icons.shopping_bag_outlined,
            label: 'Orders',
            value: orders.toString(),
            color: AppColors.primary,
          ),
        ),
        const SizedBox(width: 8),
        Expanded(
          child: _StatChip(
            icon: Icons.warning_amber_outlined,
            label: 'Discrepancies',
            value: discrepancies.toString(),
            color: discrepancies > 0 ? AppColors.warning : AppColors.success,
          ),
        ),
        const SizedBox(width: 8),
        Expanded(
          child: _StatChip(
            icon: Icons.info_outline,
            label: 'Warnings',
            value: warnings.toString(),
            color:
                warnings > 0 ? AppColors.warning : AppColors.textSecondary,
          ),
        ),
      ],
    );
  }
}

class _StatChip extends StatelessWidget {
  const _StatChip({
    required this.icon,
    required this.label,
    required this.value,
    required this.color,
  });

  final IconData icon;
  final String label;
  final String value;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(10),
      ),
      child: Row(
        children: [
          Icon(icon, size: 16, color: color),
          const SizedBox(width: 6),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                value,
                style: AppTextStyles.titleMedium
                    .copyWith(color: color, fontWeight: FontWeight.w700),
              ),
              Text(label, style: AppTextStyles.labelSmall),
            ],
          ),
        ],
      ),
    );
  }
}

// ── Action buttons ─────────────────────────────────────────────────────────

class _ActionButtons extends StatelessWidget {
  const _ActionButtons({required this.reportId});

  final String reportId;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        SizedBox(
          width: double.infinity,
          height: 48,
          child: ElevatedButton.icon(
            onPressed: () =>
                context.push(RouteConstants.reconciliationPath(reportId)),
            icon: const Icon(Icons.fact_check_outlined, size: 18),
            label: const Text('View Reconciliation'),
          ),
        ),
        const SizedBox(height: 10),
        SizedBox(
          width: double.infinity,
          height: 48,
          child: OutlinedButton.icon(
            onPressed: () => context
                .push(RouteConstants.reportSettlementPath(reportId)),
            icon: const Icon(Icons.receipt_long_outlined, size: 18),
            label: const Text('View Settlements'),
          ),
        ),
      ],
    );
  }
}

// ── Intelligence Card ──────────────────────────────────────────────────────

class _IntelligenceCard extends StatelessWidget {
  const _IntelligenceCard({required this.intelligence});

  final ReportIntelligence intelligence;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.teal.withValues(alpha: 0.3)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header
          Row(
            children: [
              const Icon(Icons.auto_awesome, color: AppColors.teal, size: 18),
              const SizedBox(width: 8),
              Text(
                'Intelligence Analysis',
                style: AppTextStyles.titleMedium
                    .copyWith(fontWeight: FontWeight.w700),
              ),
              const Spacer(),
              _PlatformBadge(
                platform: intelligence.platform,
                confidence: intelligence.platformConfidence,
              ),
            ],
          ),
          const SizedBox(height: 4),
          Text(
            intelligence.reportTypeLabel,
            style: AppTextStyles.bodySmall
                .copyWith(color: AppColors.textSecondary),
          ),
          const SizedBox(height: 14),
          const Divider(height: 1),
          const SizedBox(height: 14),

          // Quality score
          _QualityScoreRow(score: intelligence.qualityScore),
          const SizedBox(height: 12),

          // Key metrics
          _MetricsGrid(intelligence: intelligence),
          const SizedBox(height: 12),

          // Readiness badge
          _ReadinessBadge(
            status: intelligence.reconciliationStatus,
            score: intelligence.readinessScore,
          ),

          // Discrepancies
          if (intelligence.discrepanciesFound > 0) ...[
            const SizedBox(height: 10),
            _DiscrepancyRow(
              count: intelligence.discrepanciesFound,
              recoverable: intelligence.totalRecoverable,
            ),
          ],

          // Insights (up to 3)
          if (intelligence.insights.isNotEmpty) ...[
            const SizedBox(height: 12),
            const Divider(height: 1),
            const SizedBox(height: 10),
            Text(
              'Key Insights',
              style: AppTextStyles.labelSmall
                  .copyWith(fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 6),
            ...intelligence.insights
                .take(3)
                .map((i) => _InsightTile(insight: i)),
          ],
        ],
      ),
    );
  }
}

class _PlatformBadge extends StatelessWidget {
  const _PlatformBadge({required this.platform, required this.confidence});

  final String platform;
  final double confidence;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: AppColors.primary.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(6),
      ),
      child: Text(
        '${platform.toUpperCase()} ${(confidence * 100).toStringAsFixed(0)}%',
        style: AppTextStyles.labelSmall.copyWith(
          color: AppColors.primary,
          fontWeight: FontWeight.w700,
          fontSize: 10,
        ),
      ),
    );
  }
}

class _QualityScoreRow extends StatelessWidget {
  const _QualityScoreRow({required this.score});

  final double score;

  Color get _color {
    if (score >= 80) return AppColors.success;
    if (score >= 50) return AppColors.warning;
    return AppColors.error;
  }

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Text('Quality Score', style: AppTextStyles.bodySmall),
        const Spacer(),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 3),
          decoration: BoxDecoration(
            color: _color.withValues(alpha: 0.12),
            borderRadius: BorderRadius.circular(20),
          ),
          child: Text(
            '${score.toStringAsFixed(0)}/100',
            style: AppTextStyles.labelSmall.copyWith(
              color: _color,
              fontWeight: FontWeight.w700,
            ),
          ),
        ),
      ],
    );
  }
}

class _MetricsGrid extends StatelessWidget {
  const _MetricsGrid({required this.intelligence});

  final ReportIntelligence intelligence;

  String _fmt(double v) {
    if (v >= 10000000) return '₹${(v / 10000000).toStringAsFixed(1)}Cr';
    if (v >= 100000) return '₹${(v / 100000).toStringAsFixed(1)}L';
    if (v >= 1000) return '₹${(v / 1000).toStringAsFixed(1)}K';
    return '₹${v.toStringAsFixed(0)}';
  }

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Expanded(
          child: _MetricCell(
            label: 'Gross Sales',
            value: _fmt(intelligence.grossSales),
          ),
        ),
        Expanded(
          child: _MetricCell(
            label: 'Net Settlement',
            value: _fmt(intelligence.netSettlement),
          ),
        ),
        Expanded(
          child: _MetricCell(
            label: 'Orders',
            value: intelligence.totalOrders.toString(),
          ),
        ),
      ],
    );
  }
}

class _MetricCell extends StatelessWidget {
  const _MetricCell({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Text(
          value,
          style: AppTextStyles.titleMedium.copyWith(
            fontWeight: FontWeight.w700,
            color: AppColors.primary,
          ),
        ),
        Text(label, style: AppTextStyles.labelSmall),
      ],
    );
  }
}

class _ReadinessBadge extends StatelessWidget {
  const _ReadinessBadge({required this.status, required this.score});

  final String status;
  final double score;

  Color get _color {
    if (status == 'full_reconciliation_ready') return AppColors.success;
    if (status == 'partial_reconciliation') return AppColors.warning;
    return AppColors.neutral;
  }

  String get _label {
    switch (status) {
      case 'full_reconciliation_ready':
        return 'Full Recon Ready';
      case 'partial_reconciliation':
        return 'Partial Recon';
      case 'single_report':
        return 'Single Report';
      default:
        return 'Insufficient Data';
    }
  }

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Icon(Icons.fact_check_outlined, size: 14, color: _color),
        const SizedBox(width: 6),
        Text(
          '$_label — ${score.toStringAsFixed(0)}%',
          style: AppTextStyles.bodySmall.copyWith(color: _color),
        ),
      ],
    );
  }
}

class _DiscrepancyRow extends StatelessWidget {
  const _DiscrepancyRow({required this.count, required this.recoverable});

  final int count;
  final double recoverable;

  String _fmt(double v) {
    if (v >= 100000) return '₹${(v / 100000).toStringAsFixed(1)}L';
    if (v >= 1000) return '₹${(v / 1000).toStringAsFixed(1)}K';
    return '₹${v.toStringAsFixed(0)}';
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      decoration: BoxDecoration(
        color: AppColors.warning.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        children: [
          const Icon(Icons.warning_amber_outlined,
              size: 14, color: AppColors.warning),
          const SizedBox(width: 6),
          Expanded(
            child: Text(
              '$count discrepancies found',
              style: AppTextStyles.bodySmall,
            ),
          ),
          if (recoverable > 0)
            Text(
              '${_fmt(recoverable)} recoverable',
              style: AppTextStyles.labelSmall.copyWith(
                color: AppColors.success,
                fontWeight: FontWeight.w600,
              ),
            ),
        ],
      ),
    );
  }
}

class _InsightTile extends StatelessWidget {
  const _InsightTile({required this.insight});

  final IntelligenceInsight insight;

  Color get _color {
    switch (insight.severity) {
      case 'critical':
        return AppColors.error;
      case 'warning':
        return AppColors.warning;
      default:
        return AppColors.info;
    }
  }

  IconData get _icon {
    switch (insight.severity) {
      case 'critical':
        return Icons.error_outline;
      case 'warning':
        return Icons.warning_amber_outlined;
      default:
        return Icons.info_outline;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(_icon, size: 14, color: _color),
          const SizedBox(width: 6),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  insight.title,
                  style: AppTextStyles.bodySmall.copyWith(
                    fontWeight: FontWeight.w600,
                    color: _color,
                  ),
                ),
                if (insight.metricValue != null)
                  Text(
                    insight.metricValue!,
                    style: AppTextStyles.labelSmall,
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

// ── Failed report detail ────────────────────────────────────────────────────

class _FailedReportCard extends StatelessWidget {
  const _FailedReportCard({
    required this.errorMessage,
    required this.onRetry,
  });

  final String? errorMessage;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.error.withValues(alpha: 0.06),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.error.withValues(alpha: 0.3)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.error_outline, color: AppColors.error, size: 20),
              const SizedBox(width: 8),
              Text(
                'Parse Failed',
                style: AppTextStyles.titleMedium
                    .copyWith(color: AppColors.error, fontWeight: FontWeight.w700),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Text(
            errorMessage ??
                'The report could not be parsed. '
                'Please check the file format and try again.',
            style: AppTextStyles.bodySmall,
          ),
          const SizedBox(height: 12),
          const Divider(height: 1),
          const SizedBox(height: 12),
          Text(
            'Common causes',
            style: AppTextStyles.bodySmall
                .copyWith(fontWeight: FontWeight.w600),
          ),
          const SizedBox(height: 6),
          for (final tip in const [
            'Corrupted or password-protected Excel file',
            'Missing required columns (Order ID, Gross Amount, Net Settlement)',
            'Sheet names do not match the expected Flipkart format',
            'File contains only a summary sheet — no order rows',
          ])
            Padding(
              padding: const EdgeInsets.only(bottom: 4),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('• ', style: AppTextStyles.labelSmall),
                  Expanded(
                    child: Text(tip, style: AppTextStyles.labelSmall),
                  ),
                ],
              ),
            ),
          const SizedBox(height: 14),
          SizedBox(
            width: double.infinity,
            height: 44,
            child: OutlinedButton.icon(
              onPressed: onRetry,
              style: OutlinedButton.styleFrom(
                foregroundColor: AppColors.error,
                side: BorderSide(
                    color: AppColors.error.withValues(alpha: 0.5)),
              ),
              icon: const Icon(Icons.refresh_outlined, size: 16),
              label: const Text('Retry Parse'),
            ),
          ),
        ],
      ),
    );
  }
}
