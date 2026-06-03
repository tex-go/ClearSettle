import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:path_provider/path_provider.dart';
import 'package:share_plus/share_plus.dart';

import '../../../../core/constants/route_constants.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_text_styles.dart';
import '../../../../core/utils/currency_formatter.dart';
import '../../../../core/utils/date_formatter.dart';
import '../../../../parsers/parser_result.dart';
import '../../../../services/export/export_service.dart';
import '../../../../shared/widgets/app_error_widget.dart';
import '../../../../shared/widgets/loading_indicator.dart';
import '../../data/datasources/report_remote_datasource.dart';
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
      backgroundColor: AppColors.background,
      appBar: AppBar(
        backgroundColor: AppColors.surface,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        scrolledUnderElevation: 0.5,
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
            icon: const Icon(Icons.refresh_rounded),
            onPressed: () =>
                ref.read(reportDetailProvider(reportId).notifier).refresh(),
          ),
        ],
      ),
      body: detailAsync.when(
        loading: () => const LoadingIndicator(message: 'Loading report…'),

        error: (e, _) => AppErrorWidget(
          message: _friendlyError(e),
          onRetry: () =>
              ref.read(reportDetailProvider(reportId).notifier).refresh(),
        ),

        data: (detail) {
          // ── Still processing ──────────────────────────────────────────────
          if (detail.parseResult.parserVersion == 'pending') {
            return _ProcessingView(
              fileName: detail.report.fileName,
              onRefresh: () =>
                  ref.read(reportDetailProvider(reportId).notifier).refresh(),
            );
          }

          // ── Failed report ─────────────────────────────────────────────────
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

          // ── Parsed report (backend or local) ──────────────────────────────
          final summary   = detail.summary;
          final hasSummary = detail.parseResult.summary != null ||
              detail.report.grossRevenue > 0;
          final hasRealData = summary.grossSales > 0 || summary.totalOrders > 0;

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

              // ── Executive KPI Grid ──────────────────────────────────────────
              if (hasRealData)
                SliverToBoxAdapter(
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(16, 16, 16, 0),
                    child: _KpiGrid(summary: summary),
                  ),
                ),

              // ── Settlement Reconciliation ───────────────────────────────────
              if (hasRealData && summary.amountSettled > 0)
                SliverToBoxAdapter(
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
                    child: _SettlementReconCard(summary: summary),
                  ),
                ),

              // ── Tax Recovery Banner ─────────────────────────────────────────
              if (hasRealData && _totalRecoverable(summary) > 0)
                SliverToBoxAdapter(
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
                    child: _TaxRecoveryBanner(summary: summary),
                  ),
                ),

              // ── Return Intelligence ─────────────────────────────────────────
              if (hasRealData && summary.returnsValue > 0)
                SliverToBoxAdapter(
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
                    child: _ReturnIntelligenceCard(summary: summary),
                  ),
                ),

              // ── Detailed Breakdown ──────────────────────────────────────────
              if (hasSummary)
                SliverToBoxAdapter(
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
                    child: SummaryFinancialsWidget(summary: summary),
                  ),
                ),

              SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(16, 16, 16, 0),
                  child: _ActionButtons(reportId: reportId),
                ),
              ),
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
      icon: const Icon(Icons.ios_share_outlined, size: 20),
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
        Icon(icon, size: 18, color: AppColors.accent),
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
      margin: const EdgeInsets.fromLTRB(16, 8, 16, 0),
      decoration: BoxDecoration(
        gradient: AppColors.heroGradient,
        borderRadius: BorderRadius.circular(AppRadius.r5),
        boxShadow: AppShadows.heroCard,
      ),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // File name + icon
            Row(
              children: [
                Container(
                  width: 40,
                  height: 40,
                  decoration: BoxDecoration(
                    color: Colors.white.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: const Icon(Icons.table_chart_outlined,
                      color: Colors.white, size: 20),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Text(
                    fileName,
                    style: AppTextStyles.titleLarge
                        .copyWith(color: Colors.white),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            Container(height: 1, color: Colors.white.withValues(alpha: 0.1)),
            const SizedBox(height: 14),
            // Meta rows
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
                icon: Icons.code_outlined, label: 'Parser $parserVersion'),
          ],
        ),
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
          Icon(icon, size: 13, color: Colors.white60),
          const SizedBox(width: 7),
          Text(label,
              style: AppTextStyles.bodySmall.copyWith(color: Colors.white70)),
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
            color: AppColors.accent,
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
        borderRadius: BorderRadius.circular(AppRadius.r3),
        border: Border.all(color: color.withValues(alpha: 0.15)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 16, color: color),
          const SizedBox(width: 6),
          Flexible(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  value,
                  style: AppTextStyles.titleMedium
                      .copyWith(color: color, fontWeight: FontWeight.w700),
                  overflow: TextOverflow.ellipsis,
                ),
                Text(
                  label,
                  style: AppTextStyles.labelSmall,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

// ── Action buttons ─────────────────────────────────────────────────────────

class _ActionButtons extends ConsumerStatefulWidget {
  const _ActionButtons({required this.reportId});
  final String reportId;

  @override
  ConsumerState<_ActionButtons> createState() => _ActionButtonsState();
}

class _ActionButtonsState extends ConsumerState<_ActionButtons> {
  bool _generatingReport = false;

  Future<void> _generateReport() async {
    setState(() => _generatingReport = true);
    final messenger = ScaffoldMessenger.of(context);
    try {
      final remote = ref.read(reportRemoteDataSourceProvider);
      final bytes  = await remote.fetchHtmlReportBytes(widget.reportId);

      final dir  = await getTemporaryDirectory();
      final file = File('${dir.path}/clearsettle_report_${widget.reportId.substring(0, 8)}.html');
      await file.writeAsBytes(bytes);

      await Share.shareXFiles(
        [XFile(file.path, mimeType: 'text/html')],
        subject: 'ClearSettle Settlement Analytics Report',
        text: 'Your settlement analytics report — open in browser for the full interactive view.',
      );

      // Schedule cleanup after 60 seconds
      Future.delayed(const Duration(seconds: 60), () {
        file.deleteSync();
      });
    } catch (e) {
      if (mounted) {
        messenger.showSnackBar(
          SnackBar(
            content: Text('Report generation failed: $e'),
            backgroundColor: AppColors.error,
          ),
        );
      }
    } finally {
      if (mounted) setState(() => _generatingReport = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        // ── Generate Report — the V1 hero CTA ───────────────────────────────
        GestureDetector(
          onTap: _generatingReport ? null : _generateReport,
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 200),
            width: double.infinity,
            height: 54,
            decoration: BoxDecoration(
              gradient: _generatingReport
                  ? null
                  : const LinearGradient(
                      colors: [Color(0xFF0F172A), Color(0xFF134E4A)],
                      begin: Alignment.centerLeft,
                      end: Alignment.centerRight,
                    ),
              color: _generatingReport ? AppColors.surfaceVariant : null,
              borderRadius: BorderRadius.circular(AppRadius.r2),
              boxShadow: _generatingReport ? null : AppShadows.heroCard,
            ),
            child: _generatingReport
                ? const Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      SizedBox(
                        width: 18,
                        height: 18,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          color: AppColors.accent,
                        ),
                      ),
                      SizedBox(width: 12),
                      Text(
                        'Generating Report…',
                        style: TextStyle(
                          color: AppColors.textSecondary,
                          fontSize: 15,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ],
                  )
                : const Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.auto_awesome_rounded,
                          size: 18, color: AppColors.accentLight),
                      SizedBox(width: 10),
                      Text(
                        'Generate Analytics Report',
                        style: TextStyle(
                          color: Colors.white,
                          fontSize: 15,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ],
                  ),
          ),
        ),

        const SizedBox(height: 6),
        Text(
          'CFO · CA · Investor · Founder insights in one report',
          style: AppTextStyles.labelSmall.copyWith(
            color: AppColors.textMuted,
          ),
          textAlign: TextAlign.center,
        ),

        const SizedBox(height: 14),

        // ── Secondary CTAs ───────────────────────────────────────────────────
        Row(
          children: [
            Expanded(
              child: GestureDetector(
                onTap: () =>
                    context.push(RouteConstants.reconciliationPath(widget.reportId)),
                child: Container(
                  height: 46,
                  decoration: BoxDecoration(
                    color: AppColors.accent.withValues(alpha: 0.08),
                    borderRadius: BorderRadius.circular(AppRadius.r2),
                    border: Border.all(color: AppColors.accent.withValues(alpha: 0.2)),
                  ),
                  child: const Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.fact_check_outlined,
                          size: 16, color: AppColors.accent),
                      SizedBox(width: 7),
                      Text('Reconciliation',
                          style: TextStyle(
                              color: AppColors.accent,
                              fontSize: 13,
                              fontWeight: FontWeight.w600)),
                    ],
                  ),
                ),
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: GestureDetector(
                onTap: () => context
                    .push(RouteConstants.reportSettlementPath(widget.reportId)),
                child: Container(
                  height: 46,
                  decoration: BoxDecoration(
                    color: AppColors.surface,
                    borderRadius: BorderRadius.circular(AppRadius.r2),
                    border: Border.all(color: AppColors.divider),
                    boxShadow: AppShadows.card,
                  ),
                  child: const Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.receipt_long_outlined,
                          size: 16, color: AppColors.textSecondary),
                      SizedBox(width: 7),
                      Text('Settlements',
                          style: TextStyle(
                              color: AppColors.textPrimary,
                              fontSize: 13,
                              fontWeight: FontWeight.w600)),
                    ],
                  ),
                ),
              ),
            ),
          ],
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
        border: Border.all(color: AppColors.accent.withValues(alpha: 0.25)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header
          Row(
            children: [
              const Icon(Icons.auto_awesome, color: AppColors.accent, size: 18),
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
        color: AppColors.accent.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(6),
      ),
      child: Text(
        '${platform.toUpperCase()} ${(confidence * 100).toStringAsFixed(0)}%',
        style: AppTextStyles.labelSmall.copyWith(
          color: AppColors.accent,
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
        const Text('Quality Score', style: AppTextStyles.bodySmall),
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
            color: AppColors.textPrimary,
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

// ── Helpers ───────────────────────────────────────────────────────────────────

String _friendlyError(Object e) {
  final msg = e.toString();
  if (msg.contains('Parsed data not found') || msg.contains('Re-parse required')) {
    return 'Report details could not be loaded. Tap retry to re-fetch from the server.';
  }
  if (msg.contains('network') || msg.contains('SocketException') ||
      msg.contains('connection')) {
    return 'Cannot reach the server. Check your connection and try again.';
  }
  if (msg.contains('not found') || msg.contains('404')) {
    return 'This report was not found on the server. It may have been deleted.';
  }
  if (msg.contains('still being processed') || msg.contains('pending')) {
    return 'Your report is still being analyzed. Please wait a moment and retry.';
  }
  return 'Unable to load report details. Tap retry to try again.';
}

// ── Processing state ──────────────────────────────────────────────────────────

class _ProcessingView extends StatelessWidget {
  const _ProcessingView({
    required this.fileName,
    required this.onRefresh,
  });

  final String fileName;
  final VoidCallback onRefresh;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const SizedBox(
              width: 48,
              height: 48,
              child: CircularProgressIndicator(
                strokeWidth: 3,
                color: AppColors.accent,
              ),
            ),
            const SizedBox(height: 24),
            const Text(
              'Analyzing Report',
              style: AppTextStyles.headlineMedium,
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 8),
            Text(
              'Your report is still being analyzed by the intelligence pipeline.\nThis usually takes 5–30 seconds.',
              style: AppTextStyles.bodyMedium.copyWith(
                color: AppColors.textSecondary,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 6),
            Text(
              fileName,
              style: AppTextStyles.bodySmall.copyWith(
                color: AppColors.textMuted,
              ),
              textAlign: TextAlign.center,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
            const SizedBox(height: 28),
            ElevatedButton.icon(
              onPressed: onRefresh,
              icon: const Icon(Icons.refresh_outlined, size: 18),
              label: const Text('Refresh'),
              style: ElevatedButton.styleFrom(
                minimumSize: const Size(180, 46),
              ),
            ),
          ],
        ),
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

// ── Helper ─────────────────────────────────────────────────────────────────

double _totalRecoverable(ParsedSummary s) =>
    s.totalTcs + s.totalTds + s.totalGstOnFees;

// ── KPI Grid ───────────────────────────────────────────────────────────────

class _KpiGrid extends StatelessWidget {
  const _KpiGrid({required this.summary});
  final ParsedSummary summary;

  @override
  Widget build(BuildContext context) {
    final returnRate = summary.grossSales > 0
        ? (summary.returnsValue / summary.grossSales * 100).clamp(0.0, 100.0)
        : 0.0;
    final totalFees = summary.totalFees;
    final feeRatePct = summary.grossSales > 0
        ? (totalFees / summary.grossSales * 100).clamp(0.0, 100.0)
        : 0.0;
    final recoveryRate = summary.grossSales > 0
        ? (summary.netEarnings / summary.grossSales * 100).clamp(0.0, 100.0)
        : 0.0;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _SectionHeader(
          icon: Icons.bar_chart_rounded,
          label: 'Executive Summary',
          tag: '${summary.totalOrders} orders',
        ),
        const SizedBox(height: 10),
        GridView.count(
          crossAxisCount: 2,
          crossAxisSpacing: 8,
          mainAxisSpacing: 8,
          childAspectRatio: 1.7,
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          children: [
            _KpiCard(
              label: 'Gross Sales (GMV)',
              value: CurrencyFormatter.formatCompact(summary.grossSales),
              note: '100% of revenue',
              color: AppColors.info,
              icon: Icons.currency_rupee_rounded,
            ),
            _KpiCard(
              label: 'Total Orders',
              value: summary.totalOrders.toString(),
              note: '${summary.totalReturned} returns',
              color: AppColors.accent,
              icon: Icons.shopping_bag_outlined,
            ),
            _KpiCard(
              label: 'Return Rate',
              value: '${returnRate.toStringAsFixed(1)}%',
              note: CurrencyFormatter.formatCompact(summary.returnsValue),
              color: returnRate > 20 ? AppColors.danger : AppColors.warning,
              icon: Icons.undo_rounded,
            ),
            _KpiCard(
              label: 'Marketplace Fees',
              value: CurrencyFormatter.formatCompact(totalFees),
              note: '${feeRatePct.toStringAsFixed(1)}% of GMV',
              color: AppColors.warning,
              icon: Icons.account_balance_wallet_outlined,
            ),
            _KpiCard(
              label: 'Net Settlement',
              value: CurrencyFormatter.formatCompact(summary.netEarnings),
              note: '${recoveryRate.toStringAsFixed(1)}% recovery',
              color: AppColors.success,
              icon: Icons.account_balance_outlined,
            ),
            _KpiCard(
              label: 'Tax Credits',
              value: CurrencyFormatter.formatCompact(_totalRecoverable(summary)),
              note: 'File ITC/TDS claim',
              color: const Color(0xFF8B5CF6),
              icon: Icons.receipt_outlined,
            ),
          ],
        ),
      ],
    );
  }
}

class _KpiCard extends StatelessWidget {
  const _KpiCard({
    required this.label,
    required this.value,
    required this.note,
    required this.color,
    required this.icon,
  });
  final String label, value, note;
  final Color color;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(AppRadius.r3),
        border: Border.all(color: AppColors.divider),
        boxShadow: AppShadows.card,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [
            Icon(icon, size: 12, color: color),
            const SizedBox(width: 5),
            Expanded(child: Text(
              label.toUpperCase(),
              style: AppTextStyles.overline.copyWith(
                  color: AppColors.textMuted, letterSpacing: 0.5, fontSize: 9),
              maxLines: 1, overflow: TextOverflow.ellipsis,
            )),
          ]),
          const Spacer(),
          Text(value,
              style: AppTextStyles.metricMedium.copyWith(color: color, fontSize: 18)),
          const SizedBox(height: 2),
          Text(note,
              style: AppTextStyles.labelSmall.copyWith(color: AppColors.textMuted, fontSize: 10),
              maxLines: 1, overflow: TextOverflow.ellipsis),
        ],
      ),
    );
  }
}

// ── Settlement Reconciliation ──────────────────────────────────────────────

class _SettlementReconCard extends StatelessWidget {
  const _SettlementReconCard({required this.summary});
  final ParsedSummary summary;

  @override
  Widget build(BuildContext context) {
    final expected = summary.grossSales
        - summary.returnsValue
        - summary.cancellationsValue
        - summary.totalFees;
    final actual   = summary.amountSettled;
    final variance = actual - expected;
    final isFav    = variance >= 0;

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(AppRadius.r3),
        border: Border.all(color: AppColors.divider),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const _SectionHeader(
              icon: Icons.compare_arrows_rounded, label: 'Settlement Reconciliation'),
          const SizedBox(height: 12),
          Row(children: [
            Expanded(child: _ReconStat(label: 'Expected',
                value: CurrencyFormatter.format(expected), color: AppColors.info)),
            Expanded(child: _ReconStat(label: 'Received',
                value: CurrencyFormatter.format(actual), color: AppColors.success)),
            Expanded(child: _ReconStat(
                label: isFav ? 'Favourable' : 'Shortfall',
                value: '${isFav ? '+' : '-'}${CurrencyFormatter.formatCompact(variance.abs())}',
                color: isFav ? AppColors.success : AppColors.danger)),
          ]),
          if (variance != 0) ...[
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                  color: isFav ? AppColors.success100 : AppColors.danger100,
                  borderRadius: BorderRadius.circular(8)),
              child: Row(children: [
                Icon(isFav ? Icons.check_circle_outline : Icons.warning_amber_rounded,
                    size: 14, color: isFav ? AppColors.success : AppColors.danger),
                const SizedBox(width: 8),
                Expanded(child: Text(
                  isFav
                      ? 'Settlement exceeds expected — likely includes adjustments.'
                      : 'Settlement shortfall detected. Raise a dispute with the marketplace.',
                  style: AppTextStyles.labelSmall.copyWith(
                      color: isFav ? AppColors.success : AppColors.danger),
                )),
              ]),
            ),
          ],
        ],
      ),
    );
  }
}

class _ReconStat extends StatelessWidget {
  const _ReconStat({required this.label, required this.value, required this.color});
  final String label, value;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Column(children: [
      Text(label.toUpperCase(),
          style: AppTextStyles.overline.copyWith(color: AppColors.textMuted, fontSize: 9)),
      const SizedBox(height: 4),
      Text(value,
          style: AppTextStyles.titleSmall.copyWith(color: color, fontWeight: FontWeight.w700)),
    ]);
  }
}

// ── Tax Recovery Banner ────────────────────────────────────────────────────

class _TaxRecoveryBanner extends StatelessWidget {
  const _TaxRecoveryBanner({required this.summary});
  final ParsedSummary summary;

  String _breakdown(ParsedSummary s) {
    final parts = <String>[];
    if (s.totalTcs > 0) parts.add('TCS ${CurrencyFormatter.formatCompact(s.totalTcs)}');
    if (s.totalTds > 0) parts.add('TDS ${CurrencyFormatter.formatCompact(s.totalTds)}');
    if (s.totalGstOnFees > 0) {
      parts.add('GST ITC ${CurrencyFormatter.formatCompact(s.totalGstOnFees)}');
    }
    return parts.isEmpty
        ? 'All fully claimable.'
        : '${parts.join(' · ')} — all fully claimable.';
  }

  @override
  Widget build(BuildContext context) {
    final total = _totalRecoverable(summary);
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: const Color(0x0F8B5CF6),
        borderRadius: BorderRadius.circular(AppRadius.r3),
        border: const Border(left: BorderSide(color: Color(0xFF8B5CF6), width: 3)),
      ),
      child: Row(children: [
        const Icon(Icons.savings_outlined, size: 20, color: Color(0xFF8B5CF6)),
        const SizedBox(width: 12),
        Expanded(child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Tax Credits — ${CurrencyFormatter.format(total)} Recoverable',
              style: AppTextStyles.titleSmall.copyWith(
                  color: const Color(0xFF8B5CF6), fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: 4),
            Text(_breakdown(summary),
                style: AppTextStyles.labelSmall.copyWith(color: AppColors.textSecondary)),
            const SizedBox(height: 4),
            const Text('Claim during next ITR / GSTR filing.',
                style: TextStyle(
                    fontSize: 10, color: Color(0xFF8B5CF6), fontWeight: FontWeight.w500)),
          ],
        )),
      ]),
    );
  }
}

// ── Return Intelligence ────────────────────────────────────────────────────

class _ReturnIntelligenceCard extends StatelessWidget {
  const _ReturnIntelligenceCard({required this.summary});
  final ParsedSummary summary;

  @override
  Widget build(BuildContext context) {
    final returnRate = summary.grossSales > 0
        ? (summary.returnsValue / summary.grossSales * 100).clamp(0.0, 100.0)
        : 0.0;
    final isHigh = returnRate > 20;

    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(AppRadius.r3),
        border: Border.all(
            color: isHigh ? AppColors.danger.withValues(alpha: 0.3) : AppColors.divider),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _SectionHeader(
            icon: Icons.undo_rounded, label: 'Return Intelligence',
            tag: isHigh ? 'HIGH PRIORITY' : null,
            tagColor: isHigh ? AppColors.danger : null,
          ),
          const SizedBox(height: 12),
          Row(children: [
            Expanded(child: _ReturnStat(
                label: 'Return Value',
                value: CurrencyFormatter.formatCompact(summary.returnsValue),
                sub: '${returnRate.toStringAsFixed(1)}% of GMV',
                color: isHigh ? AppColors.danger : AppColors.warning)),
            Expanded(child: _ReturnStat(
                label: 'Reverse Ship',
                value: CurrencyFormatter.formatCompact(summary.totalReverseShipping),
                sub: 'logistics cost',
                color: AppColors.warning)),
            Expanded(child: _ReturnStat(
                label: 'Returns',
                value: summary.totalReturned > 0
                    ? summary.totalReturned.toString()
                    : '—',
                sub: 'of ${summary.totalOrders}',
                color: AppColors.textSecondary)),
          ]),
          if (isHigh) ...[
            const SizedBox(height: 10),
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                  color: AppColors.danger100, borderRadius: BorderRadius.circular(8)),
              child: Row(children: [
                const Icon(Icons.warning_amber_rounded, size: 14, color: AppColors.danger),
                const SizedBox(width: 8),
                Expanded(child: Text(
                  'Return rate above 20%. Check sizing, descriptions, and packaging quality.',
                  style: AppTextStyles.labelSmall.copyWith(color: AppColors.danger),
                )),
              ]),
            ),
          ],
        ],
      ),
    );
  }
}

class _ReturnStat extends StatelessWidget {
  const _ReturnStat({
    required this.label, required this.value,
    required this.sub, required this.color,
  });
  final String label, value, sub;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Column(children: [
      Text(label.toUpperCase(),
          style: AppTextStyles.overline.copyWith(color: AppColors.textMuted, fontSize: 9),
          textAlign: TextAlign.center),
      const SizedBox(height: 4),
      Text(value,
          style: AppTextStyles.titleSmall.copyWith(color: color, fontWeight: FontWeight.w700),
          textAlign: TextAlign.center),
      Text(sub,
          style: AppTextStyles.labelSmall.copyWith(color: AppColors.textMuted, fontSize: 10),
          textAlign: TextAlign.center),
    ]);
  }
}

// ── Section header helper ──────────────────────────────────────────────────

class _SectionHeader extends StatelessWidget {
  const _SectionHeader({
    required this.icon, required this.label, this.tag, this.tagColor,
  });
  final IconData icon;
  final String label;
  final String? tag;
  final Color? tagColor;

  @override
  Widget build(BuildContext context) {
    return Row(children: [
      Icon(icon, size: 14, color: AppColors.accent),
      const SizedBox(width: 7),
      Text(label, style: AppTextStyles.titleSmall.copyWith(fontWeight: FontWeight.w700)),
      if (tag != null) ...[
        const Spacer(),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
          decoration: BoxDecoration(
            color: (tagColor ?? AppColors.warning).withValues(alpha: 0.1),
            borderRadius: BorderRadius.circular(4),
            border: Border.all(color: (tagColor ?? AppColors.warning).withValues(alpha: 0.3)),
          ),
          child: Text(tag!,
              style: TextStyle(
                  fontSize: 9, fontWeight: FontWeight.w700,
                  color: tagColor ?? AppColors.warning, letterSpacing: 0.3)),
        ),
      ],
    ]);
  }
}
