import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/constants/route_constants.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_text_styles.dart';
import '../../../../core/utils/date_formatter.dart';
import '../../../../shared/widgets/app_error_widget.dart';
import '../../../../shared/widgets/loading_indicator.dart';
import '../providers/report_detail_provider.dart';
import '../widgets/summary_financials_widget.dart';

class ReportDetailScreen extends ConsumerWidget {
  const ReportDetailScreen({super.key, required this.reportId});

  final String reportId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final detailAsync = ref.watch(reportDetailProvider(reportId));

    return Scaffold(
      backgroundColor: AppColors.backgroundLight,
      appBar: AppBar(
        title: const Text('Report Detail'),
        actions: [
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
        data: (detail) => CustomScrollView(
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
            const SliverToBoxAdapter(child: SizedBox(height: 32)),
          ],
        ),
      ),
    );
  }
}

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
        color: AppColors.surface,
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
              label: marketplace.toUpperCase()),
          _InfoRow(
              icon: Icons.upload_outlined,
              label: 'Uploaded ${DateFormatter.formatDate(uploadedAt)}'),
          if (parsedAt != null)
            _InfoRow(
                icon: Icons.check_circle_outline,
                label: 'Parsed ${DateFormatter.formatRelative(parsedAt!)}'),
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
            color: warnings > 0 ? AppColors.warning : AppColors.textSecondary,
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
              Text(value,
                  style: AppTextStyles.titleMedium
                      .copyWith(color: color, fontWeight: FontWeight.w700)),
              Text(label, style: AppTextStyles.labelSmall),
            ],
          ),
        ],
      ),
    );
  }
}

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
            onPressed: () => context.push(
              RouteConstants.reconciliationPath(reportId),
            ),
            icon: const Icon(Icons.fact_check_outlined, size: 18),
            label: const Text('View Reconciliation'),
          ),
        ),
        const SizedBox(height: 10),
        SizedBox(
          width: double.infinity,
          height: 48,
          child: OutlinedButton.icon(
            onPressed: () =>
                context.push(RouteConstants.settlementDetailPath(reportId)),
            icon: const Icon(Icons.receipt_long_outlined, size: 18),
            label: const Text('View Settlements'),
          ),
        ),
      ],
    );
  }
}
