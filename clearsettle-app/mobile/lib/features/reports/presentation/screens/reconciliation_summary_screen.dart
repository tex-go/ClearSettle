import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_text_styles.dart';
import '../../../../core/utils/currency_formatter.dart';
import '../../../../reconciliation/reconciliation_result.dart';
import '../../../../shared/widgets/app_error_widget.dart';
import '../../../../shared/widgets/empty_state_widget.dart';
import '../../../../shared/widgets/loading_indicator.dart';
import '../providers/report_detail_provider.dart';
import '../widgets/discrepancy_card.dart';

class ReconciliationSummaryScreen extends ConsumerWidget {
  const ReconciliationSummaryScreen({super.key, required this.reportId});

  final String reportId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final detailAsync = ref.watch(reportDetailProvider(reportId));

    return Scaffold(
      backgroundColor: AppColors.backgroundLight,
      appBar: AppBar(title: const Text('Reconciliation')),
      body: detailAsync.when(
        loading: () =>
            const LoadingIndicator(message: 'Loading reconciliation…'),
        error: (e, _) => AppErrorWidget(message: e.toString()),
        data: (detail) {
          final recon = detail.reconciliationResult;
          return CustomScrollView(
            slivers: [
              SliverToBoxAdapter(
                child: _ReconHeader(recon: recon),
              ),
              SliverToBoxAdapter(
                child: _BreakdownGrid(recon: recon),
              ),
              SliverPadding(
                padding: const EdgeInsets.fromLTRB(16, 16, 16, 0),
                sliver: SliverToBoxAdapter(
                  child: Text(
                    recon.isClean
                        ? 'No Discrepancies Found'
                        : 'Discrepancies (${recon.discrepancyCount})',
                    style: AppTextStyles.titleLarge,
                  ),
                ),
              ),
              if (recon.isClean)
                const SliverFillRemaining(
                  child: EmptyStateWidget(
                    icon: Icons.verified_outlined,
                    title: 'All clear!',
                    subtitle:
                        'No fee overcharges or settlement mismatches detected.',
                  ),
                )
              else
                SliverPadding(
                  padding: const EdgeInsets.fromLTRB(16, 12, 16, 32),
                  sliver: SliverList(
                    delegate: SliverChildBuilderDelegate(
                      (context, index) => DiscrepancyCard(
                        discrepancy: recon.discrepancies[index],
                      ),
                      childCount: recon.discrepancies.length,
                    ),
                  ),
                ),
            ],
          );
        },
      ),
    );
  }
}

class _ReconHeader extends StatelessWidget {
  const _ReconHeader({required this.recon});

  final ReconciliationResult recon;

  @override
  Widget build(BuildContext context) {
    final hasIssues = !recon.isClean;
    return Container(
      margin: const EdgeInsets.all(16),
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: hasIssues
              ? [const Color(0xFF7B2D00), const Color(0xFFB34700)]
              : [AppColors.primary, AppColors.primaryLight],
        ),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                hasIssues
                    ? Icons.warning_amber_rounded
                    : Icons.verified_rounded,
                color: AppColors.textInverse,
                size: 24,
              ),
              const SizedBox(width: 10),
              Text(
                hasIssues ? 'Issues Found' : 'Clean Report',
                style: AppTextStyles.headlineMedium.copyWith(
                  color: AppColors.textInverse,
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              _HeaderStat(
                label: 'Orders',
                value: recon.totalOrders.toString(),
              ),
              _HeaderStat(
                label: 'Discrepancies',
                value: recon.discrepancyCount.toString(),
              ),
              _HeaderStat(
                label: 'Total Variance',
                value: CurrencyFormatter.formatCompact(recon.totalVariance),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _HeaderStat extends StatelessWidget {
  const _HeaderStat({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            value,
            style: const TextStyle(
              color: AppColors.textInverse,
              fontSize: 22,
              fontWeight: FontWeight.w700,
            ),
          ),
          Text(
            label,
            style: TextStyle(
              color: AppColors.textInverse.withValues(alpha: 0.75),
              fontSize: 11,
            ),
          ),
        ],
      ),
    );
  }
}

class _BreakdownGrid extends StatelessWidget {
  const _BreakdownGrid({required this.recon});

  final ReconciliationResult recon;

  @override
  Widget build(BuildContext context) {
    final counts = _countBySeverity(recon.discrepancies);
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Row(
        children: [
          Expanded(
            child: _SeverityBox(
              label: 'Critical',
              count: counts[DiscrepancySeverity.critical] ?? 0,
              color: AppColors.error,
            ),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: _SeverityBox(
              label: 'High',
              count: counts[DiscrepancySeverity.high] ?? 0,
              color: const Color(0xFFE65100),
            ),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: _SeverityBox(
              label: 'Medium',
              count: counts[DiscrepancySeverity.medium] ?? 0,
              color: AppColors.warning,
            ),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: _SeverityBox(
              label: 'Low',
              count: counts[DiscrepancySeverity.low] ?? 0,
              color: AppColors.textSecondary,
            ),
          ),
        ],
      ),
    );
  }

  Map<DiscrepancySeverity, int> _countBySeverity(
      List<Discrepancy> discrepancies) {
    final map = <DiscrepancySeverity, int>{};
    for (final d in discrepancies) {
      map[d.severity] = (map[d.severity] ?? 0) + 1;
    }
    return map;
  }
}

class _SeverityBox extends StatelessWidget {
  const _SeverityBox({
    required this.label,
    required this.count,
    required this.color,
  });

  final String label;
  final int count;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 12),
      decoration: BoxDecoration(
        color: count > 0 ? color.withValues(alpha: 0.08) : AppColors.surfaceVariant,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(
          color: count > 0
              ? color.withValues(alpha: 0.25)
              : AppColors.divider,
        ),
      ),
      child: Column(
        children: [
          Text(
            count.toString(),
            style: AppTextStyles.headlineMedium.copyWith(
              color: count > 0 ? color : AppColors.textDisabled,
              fontWeight: FontWeight.w700,
            ),
          ),
          Text(label, style: AppTextStyles.labelSmall),
        ],
      ),
    );
  }
}
