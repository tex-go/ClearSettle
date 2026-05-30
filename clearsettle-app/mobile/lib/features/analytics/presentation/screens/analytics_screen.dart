import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_text_styles.dart';
import '../../../../core/utils/currency_formatter.dart';
import '../../../../shared/widgets/app_error_widget.dart';
import '../../../../shared/widgets/empty_state_widget.dart';
import '../../../../shared/widgets/loading_indicator.dart';
import '../../domain/entities/analytics_entity.dart';
import '../providers/analytics_provider.dart';
import '../widgets/analytics_filter_bar.dart';
import '../widgets/revenue_trend_chart.dart';

class AnalyticsScreen extends ConsumerWidget {
  const AnalyticsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final analyticsAsync = ref.watch(analyticsProvider);

    return Scaffold(
      backgroundColor: Theme.of(context).scaffoldBackgroundColor,
      appBar: AppBar(
        title: const Text('Analytics'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh_outlined),
            onPressed: () => ref.read(analyticsProvider.notifier).refresh(),
          ),
        ],
      ),
      body: Column(
        children: [
          const AnalyticsFilterBar(),
          const Divider(height: 1),
          Expanded(
            child: analyticsAsync.when(
              loading: () => const LoadingIndicator(message: 'Computing analytics…'),
              error: (e, _) => AppErrorWidget(
                message: 'Analytics unavailable.',
                onRetry: () => ref.read(analyticsProvider.notifier).refresh(),
              ),
              data: (summary) => summary.hasData
                  ? _AnalyticsContent(summary: summary)
                  : const EmptyStateWidget(
                      icon: Icons.bar_chart_outlined,
                      title: 'No analytics data',
                      subtitle:
                          'Upload and parse at least one settlement report to see analytics.',
                    ),
            ),
          ),
        ],
      ),
    );
  }
}

class _AnalyticsContent extends StatelessWidget {
  const _AnalyticsContent({required this.summary});

  final AnalyticsSummary summary;

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        _KpiRow(summary: summary),
        const SizedBox(height: 20),
        _ChartCard(
          title: 'Revenue & Settlement Trend',
          subtitle: 'Gross revenue vs net settlement over time',
          child: RevenueTrendChart(
            revenueTrend: summary.revenueTrend,
            settlementTrend: summary.settlementTrend,
          ),
        ),
        const SizedBox(height: 16),
        _ChartCard(
          title: 'Order Growth',
          subtitle: 'Total orders processed per period',
          child: OrderGrowthChart(data: summary.orderGrowth),
        ),
        const SizedBox(height: 16),
        _ChartCard(
          title: 'Fee Breakdown',
          subtitle: 'Distribution of marketplace deductions',
          child: FeeBreakdownChart(slices: summary.feeBreakdown),
        ),
        const SizedBox(height: 16),
        _SettlementRateCard(
          rate: summary.avgSettlementRate,
          grossRevenue: summary.totalGrossRevenue,
          netSettlement: summary.totalNetSettlement,
          totalFees: summary.totalFees,
        ),
        const SizedBox(height: 32),
      ],
    );
  }
}

class _KpiRow extends StatelessWidget {
  const _KpiRow({required this.summary});

  final AnalyticsSummary summary;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Row(
          children: [
            Expanded(
              child: _KpiCard(
                label: 'Gross Revenue',
                value: CurrencyFormatter.formatCompact(summary.totalGrossRevenue),
                icon: Icons.trending_up,
                color: AppColors.primary,
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: _KpiCard(
                label: 'Net Settlement',
                value: CurrencyFormatter.formatCompact(summary.totalNetSettlement),
                icon: Icons.account_balance_outlined,
                color: AppColors.positive,
              ),
            ),
          ],
        ),
        const SizedBox(height: 10),
        Row(
          children: [
            Expanded(
              child: _KpiCard(
                label: 'Total Orders',
                value: summary.totalOrders.toString(),
                icon: Icons.shopping_bag_outlined,
                color: AppColors.info,
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: _KpiCard(
                label: 'Discrepancies',
                value: summary.totalDiscrepancies.toString(),
                icon: Icons.warning_amber_outlined,
                color: summary.totalDiscrepancies > 0
                    ? AppColors.warning
                    : AppColors.success,
              ),
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
    required this.icon,
    required this.color,
  });

  final String label;
  final String value;
  final IconData icon;
  final Color color;

  @override
  Widget build(BuildContext context) {
    final surface = Theme.of(context).colorScheme.surface;
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.divider),
      ),
      child: Row(
        children: [
          Container(
            width: 36,
            height: 36,
            decoration: BoxDecoration(
              color: color.withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Icon(icon, color: color, size: 18),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  value,
                  style: AppTextStyles.titleLarge.copyWith(
                    fontWeight: FontWeight.w700,
                    color: color,
                  ),
                ),
                Text(label, style: AppTextStyles.labelSmall),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _ChartCard extends StatelessWidget {
  const _ChartCard({
    required this.title,
    required this.subtitle,
    required this.child,
  });

  final String title;
  final String subtitle;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    final surface = Theme.of(context).colorScheme.surface;
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.divider),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: AppTextStyles.titleLarge),
          const SizedBox(height: 2),
          Text(subtitle, style: AppTextStyles.bodySmall),
          const SizedBox(height: 16),
          child,
        ],
      ),
    );
  }
}

class _SettlementRateCard extends StatelessWidget {
  const _SettlementRateCard({
    required this.rate,
    required this.grossRevenue,
    required this.netSettlement,
    required this.totalFees,
  });

  final double rate;
  final double grossRevenue;
  final double netSettlement;
  final double totalFees;

  @override
  Widget build(BuildContext context) {
    final surface = Theme.of(context).colorScheme.surface;
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.divider),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('Settlement Efficiency', style: AppTextStyles.titleLarge),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      '${rate.toStringAsFixed(1)}%',
                      style: AppTextStyles.displayMedium.copyWith(
                        color: rate >= 80
                            ? AppColors.success
                            : rate >= 60
                                ? AppColors.warning
                                : AppColors.error,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                    const Text(
                      'of gross revenue settled',
                      style: AppTextStyles.bodySmall,
                    ),
                  ],
                ),
              ),
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  _EffRow(
                    label: 'Total Fees',
                    value: CurrencyFormatter.formatCompact(totalFees),
                    color: AppColors.negative,
                  ),
                  const SizedBox(height: 4),
                  _EffRow(
                    label: 'Fee Rate',
                    value: grossRevenue > 0
                        ? '${(totalFees / grossRevenue * 100).toStringAsFixed(1)}%'
                        : '0%',
                    color: AppColors.warning,
                  ),
                ],
              ),
            ],
          ),
          const SizedBox(height: 12),
          ClipRRect(
            borderRadius: BorderRadius.circular(4),
            child: LinearProgressIndicator(
              value: grossRevenue > 0 ? (netSettlement / grossRevenue).clamp(0, 1) : 0,
              minHeight: 8,
              backgroundColor: AppColors.error.withValues(alpha: 0.15),
              valueColor: AlwaysStoppedAnimation<Color>(
                rate >= 80
                    ? AppColors.success
                    : rate >= 60
                        ? AppColors.warning
                        : AppColors.error,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _EffRow extends StatelessWidget {
  const _EffRow({required this.label, required this.value, required this.color});

  final String label;
  final String value;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(label, style: AppTextStyles.labelSmall),
        const SizedBox(width: 6),
        Text(
          value,
          style: AppTextStyles.labelMedium.copyWith(
            color: color,
            fontWeight: FontWeight.w700,
          ),
        ),
      ],
    );
  }
}
