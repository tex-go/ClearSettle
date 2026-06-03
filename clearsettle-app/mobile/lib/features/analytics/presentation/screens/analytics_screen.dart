import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/constants/route_constants.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_text_styles.dart';
import '../../../../core/utils/currency_formatter.dart';
import '../../../../parsers/parser_result.dart';
import '../../../../services/export/export_service.dart';
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
    final filter = ref.watch(analyticsFilterProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Analytics'),
        actions: [
          IconButton(
            icon: const Icon(Icons.search_outlined),
            onPressed: () => context.push(RouteConstants.search),
            tooltip: 'Search',
          ),
          analyticsAsync.when(
            loading: () => const SizedBox.shrink(),
            error: (_, __) => const SizedBox.shrink(),
            data: (summary) => summary.hasData
                ? _ExportButton(summary: summary, filter: filter)
                : const SizedBox.shrink(),
          ),
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
              loading: () =>
                  const LoadingIndicator(message: 'Computing analytics…'),
              error: (e, _) => AppErrorWidget(
                message: 'Analytics unavailable.',
                onRetry: () =>
                    ref.read(analyticsProvider.notifier).refresh(),
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

// ── Export button ──────────────────────────────────────────────────────────────

class _ExportButton extends ConsumerWidget {
  const _ExportButton({required this.summary, required this.filter});

  final AnalyticsSummary summary;
  final AnalyticsFilter filter;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final service = ref.read(exportServiceProvider);
    return PopupMenuButton<_Fmt>(
      icon: const Icon(Icons.ios_share_outlined),
      tooltip: 'Export',
      onSelected: (fmt) => _export(context, service, fmt),
      itemBuilder: (_) => const [
        PopupMenuItem(
          value: _Fmt.pdf,
          child: Row(children: [
            Icon(Icons.picture_as_pdf_outlined, size: 18),
            SizedBox(width: 10),
            Text('Export PDF'),
          ]),
        ),
        PopupMenuItem(
          value: _Fmt.excel,
          child: Row(children: [
            Icon(Icons.table_chart_outlined, size: 18),
            SizedBox(width: 10),
            Text('Export Excel'),
          ]),
        ),
        PopupMenuItem(
          value: _Fmt.csv,
          child: Row(children: [
            Icon(Icons.table_rows_outlined, size: 18),
            SizedBox(width: 10),
            Text('Export CSV'),
          ]),
        ),
      ],
    );
  }

  Future<void> _export(
      BuildContext context, ExportService service, _Fmt fmt) async {
    final messenger = ScaffoldMessenger.of(context);
    try {
      final ps = _toParsedSummary(summary);
      switch (fmt) {
        case _Fmt.pdf:
          await service.exportPdf(
            reportName: 'Analytics — ${filter.label}',
            summary: ps,
            orders: const [],
            discrepancies: const [],
          );
        case _Fmt.excel:
          await service.exportExcel(
            reportName: 'Analytics — ${filter.label}',
            summary: ps,
            orders: const [],
            discrepancies: const [],
          );
        case _Fmt.csv:
          await service.exportOrdersCsv(
            reportName: 'Analytics — ${filter.label}',
            orders: const [],
          );
      }
    } catch (e) {
      messenger.showSnackBar(SnackBar(content: Text('Export failed: $e')));
    }
  }

  ParsedSummary _toParsedSummary(AnalyticsSummary s) {
    return ParsedSummary(
      grossSales: s.totalGrossRevenue,
      netSales: s.totalGrossRevenue,
      netEarnings: s.totalNetSettlement,
      amountSettled: s.totalNetSettlement,
      totalCommission: s.feeDetail.commission,
      totalShipping: s.feeDetail.shippingFee,
      totalReverseShipping: s.feeDetail.reverseShippingFee,
      totalCollectionFees: s.feeDetail.collectionFee,
      totalFixedFees: s.feeDetail.fixedFee,
      totalGstOnFees: s.feeDetail.gstOnFees,
      totalTcs: s.feeDetail.tcs,
      totalTds: s.feeDetail.tds,
      totalOrders: s.totalOrders,
    );
  }
}

enum _Fmt { pdf, excel, csv }

// ── Analytics content ──────────────────────────────────────────────────────────

class _AnalyticsContent extends StatelessWidget {
  const _AnalyticsContent({required this.summary});

  final AnalyticsSummary summary;

  @override
  Widget build(BuildContext context) {
    // Fee trend = gross - net per period
    final feeTrend = List.generate(
      summary.revenueTrend.length,
      (i) {
        final rev = summary.revenueTrend[i];
        final net = i < summary.settlementTrend.length
            ? summary.settlementTrend[i].value
            : 0.0;
        return ChartPoint(
          x: rev.x,
          value: (rev.value - net).clamp(0, double.infinity),
          label: rev.label,
        );
      },
    );

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        // ── 6-KPI grid ───────────────────────────────────────────────────
        _KpiGrid(summary: summary),
        const SizedBox(height: 20),

        // ── Revenue & Settlement Trend ────────────────────────────────────
        _ChartCard(
          title: 'Revenue & Settlement Trend',
          subtitle: 'Gross revenue vs net settlement over time',
          child: RevenueTrendChart(
            revenueTrend: summary.revenueTrend,
            settlementTrend: summary.settlementTrend,
          ),
        ),
        const SizedBox(height: 16),

        // ── Fee Trend ─────────────────────────────────────────────────────
        _ChartCard(
          title: 'Fee Trend',
          subtitle: 'Total marketplace charges per period',
          child: FeeTrendChart(data: feeTrend),
        ),
        const SizedBox(height: 16),

        // ── Order Growth ──────────────────────────────────────────────────
        _ChartCard(
          title: 'Order Volume',
          subtitle: 'Orders processed per period',
          child: OrderGrowthChart(data: summary.orderGrowth),
        ),
        const SizedBox(height: 16),

        // ── Monthly Comparison ────────────────────────────────────────────
        if (summary.monthlyComparison.isNotEmpty) ...[
          _ChartCard(
            title: 'Monthly Comparison',
            subtitle: 'Gross · Net · Fees by calendar month',
            child: MonthlyComparisonChart(data: summary.monthlyComparison),
          ),
          const SizedBox(height: 16),
        ],

        // ── Marketplace Charge Distribution ───────────────────────────────
        _ChartCard(
          title: 'Marketplace Charge Distribution',
          subtitle: 'Breakdown of total deductions',
          child: FeeBreakdownChart(slices: summary.feeBreakdown),
        ),
        const SizedBox(height: 16),

        // ── Fee Analytics breakdown ───────────────────────────────────────
        _FeeAnalyticsCard(detail: summary.feeDetail, gross: summary.totalGrossRevenue),
        const SizedBox(height: 16),

        // ── Settlement Efficiency ─────────────────────────────────────────
        _EfficiencyCard(summary: summary),
        const SizedBox(height: 16),

        // ── Insights ─────────────────────────────────────────────────────
        _InsightsCard(insights: summary.insights),
        const SizedBox(height: 32),
      ],
    );
  }
}

// ── 6-KPI grid ─────────────────────────────────────────────────────────────────

class _KpiGrid extends StatelessWidget {
  const _KpiGrid({required this.summary});

  final AnalyticsSummary summary;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Row(children: [
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
        ]),
        const SizedBox(height: 10),
        Row(children: [
          Expanded(
            child: _KpiCard(
              label: 'Marketplace Charges',
              value: CurrencyFormatter.formatCompact(summary.totalFees),
              icon: Icons.receipt_outlined,
              color: AppColors.negative,
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: _KpiCard(
              label: 'Charge %',
              value: '${summary.chargePercentage.toStringAsFixed(1)}%',
              icon: Icons.percent_outlined,
              color: summary.chargePercentage > 20
                  ? AppColors.warning
                  : AppColors.info,
            ),
          ),
        ]),
        const SizedBox(height: 10),
        Row(children: [
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
              label: 'Avg Order Value',
              value: CurrencyFormatter.formatCompact(summary.avgOrderValue),
              icon: Icons.bar_chart_outlined,
              color: AppColors.accent,
            ),
          ),
        ]),
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
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
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
                  style: AppTextStyles.titleLarge
                      .copyWith(fontWeight: FontWeight.w700, color: color),
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

// ── Chart card container ────────────────────────────────────────────────────────

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
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
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

// ── Fee analytics breakdown ────────────────────────────────────────────────────

class _FeeAnalyticsCard extends StatelessWidget {
  const _FeeAnalyticsCard({required this.detail, required this.gross});

  final FeeDetail detail;
  final double gross;

  @override
  Widget build(BuildContext context) {
    final fees = [
      ('Commission', detail.commission, AppColors.primary),
      ('Fixed Fee', detail.fixedFee, AppColors.info),
      ('Collection Fee', detail.collectionFee, AppColors.accent),
      ('Shipping Fee', detail.shippingFee, AppColors.warning),
      ('Reverse Shipping', detail.reverseShippingFee, AppColors.negative),
      ('GST on Fees', detail.gstOnFees, const Color(0xFFF5A623)),
      ('TDS', detail.tds, const Color(0xFF9C27B0)),
      ('TCS', detail.tcs, AppColors.error),
    ].where((f) => f.$2 > 0).toList();

    if (fees.isEmpty) return const SizedBox.shrink();

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.divider),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('Fee Analytics', style: AppTextStyles.titleLarge),
          const SizedBox(height: 2),
          const Text(
            'Per-category marketplace deductions',
            style: AppTextStyles.bodySmall,
          ),
          const SizedBox(height: 16),
          ...fees.map((f) => _FeeRow(
                label: f.$1,
                amount: f.$2,
                color: f.$3,
                gross: gross,
              )),
        ],
      ),
    );
  }
}

class _FeeRow extends StatelessWidget {
  const _FeeRow({
    required this.label,
    required this.amount,
    required this.color,
    required this.gross,
  });

  final String label;
  final double amount;
  final Color color;
  final double gross;

  @override
  Widget build(BuildContext context) {
    final pct = gross > 0 ? (amount / gross * 100) : 0.0;
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 8,
                height: 8,
                decoration:
                    BoxDecoration(color: color, shape: BoxShape.circle),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(label, style: AppTextStyles.bodyMedium),
              ),
              Text(
                CurrencyFormatter.format(amount),
                style: AppTextStyles.labelMedium
                    .copyWith(fontWeight: FontWeight.w600),
              ),
              const SizedBox(width: 8),
              SizedBox(
                width: 44,
                child: Text(
                  '${pct.toStringAsFixed(1)}%',
                  textAlign: TextAlign.end,
                  style: AppTextStyles.labelSmall
                      .copyWith(color: AppColors.textSecondary),
                ),
              ),
            ],
          ),
          const SizedBox(height: 4),
          ClipRRect(
            borderRadius: BorderRadius.circular(2),
            child: LinearProgressIndicator(
              value: gross > 0 ? (amount / gross).clamp(0.0, 1.0) : 0,
              minHeight: 4,
              backgroundColor: AppColors.divider,
              valueColor: AlwaysStoppedAnimation<Color>(color),
            ),
          ),
        ],
      ),
    );
  }
}

// ── Settlement efficiency ───────────────────────────────────────────────────────

class _EfficiencyCard extends StatelessWidget {
  const _EfficiencyCard({required this.summary});

  final AnalyticsSummary summary;

  @override
  Widget build(BuildContext context) {
    final rate = summary.avgSettlementRate;
    final rateColor = rate >= 80
        ? AppColors.success
        : rate >= 60
            ? AppColors.warning
            : AppColors.error;

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
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
                        color: rateColor,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                    const Text('of gross revenue settled',
                        style: AppTextStyles.bodySmall),
                  ],
                ),
              ),
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  _EffRow(
                    label: 'Total Fees',
                    value: CurrencyFormatter.formatCompact(summary.totalFees),
                    color: AppColors.negative,
                  ),
                  const SizedBox(height: 4),
                  _EffRow(
                    label: 'Charge Rate',
                    value:
                        '${summary.chargePercentage.toStringAsFixed(1)}%',
                    color: AppColors.warning,
                  ),
                  const SizedBox(height: 4),
                  _EffRow(
                    label: 'Avg Order',
                    value: CurrencyFormatter.formatCompact(
                        summary.avgOrderValue),
                    color: AppColors.info,
                  ),
                ],
              ),
            ],
          ),
          const SizedBox(height: 12),
          ClipRRect(
            borderRadius: BorderRadius.circular(4),
            child: LinearProgressIndicator(
              value: summary.totalGrossRevenue > 0
                  ? (summary.totalNetSettlement / summary.totalGrossRevenue)
                      .clamp(0.0, 1.0)
                  : 0,
              minHeight: 8,
              backgroundColor: AppColors.error.withValues(alpha: 0.15),
              valueColor: AlwaysStoppedAnimation<Color>(rateColor),
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

// ── Insights card ──────────────────────────────────────────────────────────────

class _InsightsCard extends StatelessWidget {
  const _InsightsCard({required this.insights});

  final InsightSummary insights;

  @override
  Widget build(BuildContext context) {
    final items = [
      if (insights.highestRevenueMonth != null)
        _InsightItem(
          icon: Icons.emoji_events_outlined,
          color: AppColors.positive,
          label: 'Highest Revenue',
          value: insights.highestRevenueMonth!,
        ),
      if (insights.highestFeeMonth != null)
        _InsightItem(
          icon: Icons.warning_amber_outlined,
          color: AppColors.warning,
          label: 'Highest Fee Month',
          value: insights.highestFeeMonth!,
        ),
      if (insights.lowestSettlementMonth != null)
        _InsightItem(
          icon: Icons.arrow_downward_outlined,
          color: AppColors.negative,
          label: 'Lowest Settlement',
          value: insights.lowestSettlementMonth!,
        ),
      _InsightItem(
        icon: Icons.percent_outlined,
        color: AppColors.info,
        label: 'Avg Commission',
        value: '${insights.avgCommissionPct.toStringAsFixed(1)}%',
      ),
      _InsightItem(
        icon: Icons.account_balance_wallet_outlined,
        color: AppColors.primary,
        label: 'Total Charges',
        value: CurrencyFormatter.formatCompact(
            insights.totalMarketplaceCharges),
      ),
    ];

    if (items.isEmpty) return const SizedBox.shrink();

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.divider),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('Insights', style: AppTextStyles.titleLarge),
          const SizedBox(height: 2),
          const Text('Auto-generated from your data',
              style: AppTextStyles.bodySmall),
          const SizedBox(height: 16),
          ...items,
        ],
      ),
    );
  }
}

class _InsightItem extends StatelessWidget {
  const _InsightItem({
    required this.icon,
    required this.color,
    required this.label,
    required this.value,
  });

  final IconData icon;
  final Color color;
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Row(
        children: [
          Container(
            width: 34,
            height: 34,
            decoration: BoxDecoration(
              color: color.withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Icon(icon, size: 16, color: color),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Text(label, style: AppTextStyles.bodyMedium),
          ),
          Text(
            value,
            style: AppTextStyles.titleMedium.copyWith(
              fontWeight: FontWeight.w700,
              color: color,
            ),
          ),
        ],
      ),
    );
  }
}
