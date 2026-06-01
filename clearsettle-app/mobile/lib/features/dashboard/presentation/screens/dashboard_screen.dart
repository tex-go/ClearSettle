import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/constants/route_constants.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_text_styles.dart';
import '../../../../core/utils/currency_formatter.dart';
import '../../../../core/utils/date_formatter.dart';
import '../../../../shared/widgets/app_error_widget.dart';
import '../../../../shared/widgets/empty_state_widget.dart';
import '../../../../shared/widgets/loading_indicator.dart';
import '../../../alerts/domain/entities/alert_entity.dart';
import '../../../alerts/presentation/providers/alerts_provider.dart';
import '../../../auth/domain/entities/auth_entity.dart';
import '../../../auth/presentation/providers/auth_provider.dart';
import '../../../disputes/presentation/providers/disputes_provider.dart';
import '../../../settlements/domain/entities/settlement_entity.dart';
import '../../../settlements/presentation/providers/settlements_provider.dart';
import '../../domain/entities/dashboard_summary_entity.dart';
import '../providers/dashboard_provider.dart';
import '../widgets/marketplace_badge.dart';

class DashboardScreen extends ConsumerWidget {
  const DashboardScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final authState      = ref.watch(authProvider).valueOrNull;
    final dashboardAsync = ref.watch(dashboardProvider);
    final settlements    = ref.watch(settlementsProvider);
    final disputes       = ref.watch(disputesProvider);
    final alerts         = ref.watch(alertsProvider);

    return Scaffold(
      backgroundColor: Theme.of(context).scaffoldBackgroundColor,
      body: SafeArea(
        child: RefreshIndicator(
          color: AppColors.primary,
          onRefresh: () async {
            ref.read(dashboardProvider.notifier).refresh();
            await ref.read(settlementsProvider.notifier).refresh();
            await ref.read(disputesProvider.notifier).refresh();
            await ref.read(alertsProvider.notifier).refresh();
          },
          child: CustomScrollView(
            physics: const AlwaysScrollableScrollPhysics(),
            slivers: [
              _DashboardAppBar(
                authState: authState,
                unreadCount: alerts.unreadCount,
                onSearch: () => context.push(RouteConstants.search),
                onAlerts: () => context.go(RouteConstants.alerts),
              ),
              dashboardAsync.when(
                loading: () => const SliverFillRemaining(
                    child: LoadingIndicator()),
                error: (e, _) => SliverFillRemaining(
                  child: AppErrorWidget(
                    message: 'Could not load dashboard.',
                    onRetry: () =>
                        ref.read(dashboardProvider.notifier).refresh(),
                  ),
                ),
                data: (summary) => summary == null
                    ? const SliverFillRemaining(
                        child: EmptyStateWidget(
                          icon: Icons.dashboard_outlined,
                          title: 'No data yet',
                          subtitle:
                              'Upload a settlement report to see your financial summary.',
                        ),
                      )
                    : _DashboardContent(
                        summary: summary,
                        settlements: settlements,
                        disputes: disputes,
                        alerts: alerts,
                      ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

// ── App bar ───────────────────────────────────────────────────────────────────

class _DashboardAppBar extends StatelessWidget {
  const _DashboardAppBar({
    required this.authState,
    required this.unreadCount,
    required this.onSearch,
    required this.onAlerts,
  });

  final AuthState? authState;
  final int unreadCount;
  final VoidCallback onSearch;
  final VoidCallback onAlerts;

  @override
  Widget build(BuildContext context) {
    return SliverToBoxAdapter(
      child: Container(
        padding: const EdgeInsets.fromLTRB(20, 20, 12, 16),
        color: AppColors.primary,
        child: Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    _greeting(),
                    style: AppTextStyles.bodyMedium.copyWith(
                      color: AppColors.textInverse.withValues(alpha: 0.75),
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    authState is AuthAuthenticated
                        ? (authState as AuthAuthenticated).sellerName
                        : 'Seller',
                    style: AppTextStyles.headlineLarge.copyWith(
                        color: AppColors.textInverse),
                  ),
                ],
              ),
            ),
            IconButton(
              icon: const Icon(Icons.search, color: AppColors.textInverse),
              onPressed: onSearch,
              tooltip: 'Search',
            ),
            Stack(
              clipBehavior: Clip.none,
              children: [
                IconButton(
                  icon: const Icon(Icons.notifications_outlined,
                      color: AppColors.textInverse),
                  onPressed: onAlerts,
                  tooltip: 'Alerts',
                ),
                if (unreadCount > 0)
                  Positioned(
                    top: 6,
                    right: 6,
                    child: Container(
                      width: 16,
                      height: 16,
                      decoration: const BoxDecoration(
                          color: AppColors.error, shape: BoxShape.circle),
                      child: Center(
                        child: Text(
                          unreadCount > 9 ? '9+' : '$unreadCount',
                          style: const TextStyle(
                              color: Colors.white,
                              fontSize: 9,
                              fontWeight: FontWeight.w700),
                        ),
                      ),
                    ),
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  String _greeting() {
    final h = DateTime.now().hour;
    if (h < 12) return 'Good morning,';
    if (h < 17) return 'Good afternoon,';
    return 'Good evening,';
  }
}

// ── Main content ──────────────────────────────────────────────────────────────

class _DashboardContent extends StatelessWidget {
  const _DashboardContent({
    required this.summary,
    required this.settlements,
    required this.disputes,
    required this.alerts,
  });

  final DashboardSummary summary;
  final SettlementsState settlements;
  final DisputesState disputes;
  final AlertsState alerts;

  @override
  Widget build(BuildContext context) {
    return SliverPadding(
      padding: const EdgeInsets.all(16),
      sliver: SliverList(
        delegate: SliverChildListDelegate([
          if (summary.isFromCache)
            _OfflineBanner(lastSync: summary.lastSync),
          if (summary.isFromCache) const SizedBox(height: 12),

          // Org card
          _OrgCard(summary: summary),
          const SizedBox(height: 16),

          // 6-KPI grid (PRD requirement)
          _KpiGrid(
            summary: summary,
            settlements: settlements,
            disputes: disputes,
          ),
          const SizedBox(height: 16),

          // Settlement trend chart
          const _SectionHeader('Settlement Trend — 30 Days'),
          const SizedBox(height: 8),
          const _SettlementTrendChart(),
          const SizedBox(height: 20),

          // Today's alerts
          if (alerts.unreadCount > 0) ...[
            _SectionHeader('Today\'s Alerts  (${alerts.unreadCount})'),
            const SizedBox(height: 8),
            _AlertsPreview(alerts: alerts),
            const SizedBox(height: 20),
          ],

          // Top discrepancies from settlements
          if (settlements.settlements.isNotEmpty) ...[
            const _SectionHeader('Top Discrepancies'),
            const SizedBox(height: 8),
            _DiscrepanciesCard(settlements: settlements),
            const SizedBox(height: 20),
          ],

          // Connected marketplaces
          const _SectionHeader('Connected Marketplaces'),
          const SizedBox(height: 10),
          _MarketplacesSection(summary: summary),
          const SizedBox(height: 24),
        ]),
      ),
    );
  }
}

// ── Widgets ───────────────────────────────────────────────────────────────────

class _OfflineBanner extends StatelessWidget {
  const _OfflineBanner({this.lastSync});
  final DateTime? lastSync;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: AppColors.warning.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppColors.warning.withValues(alpha: 0.3)),
      ),
      child: Row(
        children: [
          const Icon(Icons.cloud_off_outlined,
              color: AppColors.warning, size: 16),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              DateFormatter.formatLastSync(lastSync),
              style: AppTextStyles.bodySmall
                  .copyWith(color: AppColors.warning),
            ),
          ),
        ],
      ),
    );
  }
}

class _OrgCard extends StatelessWidget {
  const _OrgCard({required this.summary});
  final DashboardSummary summary;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.divider),
      ),
      child: Row(
        children: [
          Container(
            width: 42,
            height: 42,
            decoration: BoxDecoration(
              color: AppColors.primary.withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(10),
            ),
            child: const Icon(Icons.store_outlined,
                color: AppColors.primary, size: 22),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(summary.organization,
                    style: AppTextStyles.titleMedium,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis),
                const SizedBox(height: 2),
                Text(summary.sellerName,
                    style: AppTextStyles.bodySmall),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _SectionHeader extends StatelessWidget {
  const _SectionHeader(this.title);
  final String title;

  @override
  Widget build(BuildContext context) {
    return Text(title, style: AppTextStyles.titleMedium);
  }
}

// ── 6-KPI grid ────────────────────────────────────────────────────────────────

class _KpiGrid extends StatelessWidget {
  const _KpiGrid({
    required this.summary,
    required this.settlements,
    required this.disputes,
  });

  final DashboardSummary summary;
  final SettlementsState settlements;
  final DisputesState disputes;

  @override
  Widget build(BuildContext context) {
    final recoverableAmount = disputes.totalClaimAmount -
        disputes.totalRecoveredAmount;

    return Column(
      children: [
        Row(children: [
          Expanded(
            child: _KpiCard(
              label: 'Gross Revenue',
              value: CurrencyFormatter.formatCompact(summary.grossRevenue),
              icon: Icons.trending_up_outlined,
              iconColor: AppColors.positive,
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: _KpiCard(
              label: 'Net Settlement',
              value: CurrencyFormatter.formatCompact(summary.netSettlement),
              icon: Icons.account_balance_outlined,
              iconColor: AppColors.primary,
            ),
          ),
        ]),
        const SizedBox(height: 10),
        Row(children: [
          Expanded(
            child: _KpiCard(
              label: 'Expected',
              value: CurrencyFormatter.formatCompact(
                  settlements.totalExpected > 0
                      ? settlements.totalExpected
                      : summary.grossRevenue),
              icon: Icons.schedule_outlined,
              iconColor: AppColors.info,
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: _KpiCard(
              label: 'Received',
              value: CurrencyFormatter.formatCompact(
                  settlements.totalReceived > 0
                      ? settlements.totalReceived
                      : summary.netSettlement),
              icon: Icons.check_circle_outline,
              iconColor: AppColors.positive,
            ),
          ),
        ]),
        const SizedBox(height: 10),
        Row(children: [
          Expanded(
            child: _KpiCard(
              label: 'Recoverable',
              value: CurrencyFormatter.formatCompact(recoverableAmount),
              icon: Icons.restore_outlined,
              iconColor: AppColors.warning,
              highlight: recoverableAmount > 0,
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: _KpiCard(
              label: 'Open Disputes',
              value: disputes.openCount.toString(),
              icon: Icons.gavel_outlined,
              iconColor:
                  disputes.openCount > 0 ? AppColors.error : AppColors.neutral,
              highlight: disputes.openCount > 0,
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
    required this.iconColor,
    this.highlight = false,
  });

  final String label;
  final String value;
  final IconData icon;
  final Color iconColor;
  final bool highlight;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: highlight
            ? iconColor.withValues(alpha: 0.06)
            : Theme.of(context).colorScheme.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: highlight
              ? iconColor.withValues(alpha: 0.25)
              : AppColors.divider,
        ),
      ),
      child: Row(
        children: [
          Container(
            width: 34,
            height: 34,
            decoration: BoxDecoration(
              color: iconColor.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Icon(icon, size: 17, color: iconColor),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  value,
                  style: AppTextStyles.titleMedium
                      .copyWith(fontWeight: FontWeight.w700),
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

// ── Settlement trend chart ────────────────────────────────────────────────────

class _SettlementTrendChart extends StatelessWidget {
  const _SettlementTrendChart();

  // Stub 30-day settlement trend
  static List<FlSpot> get _spots {
    const values = [
      42000, 55000, 48000, 61000, 53000, 70000, 65000,
      58000, 72000, 80000, 75000, 68000, 82000, 90000,
      85000, 78000, 95000, 102000, 98000, 88000, 110000,
      105000, 115000, 108000, 120000, 115000, 125000, 118000, 130000, 125000,
    ];
    return List.generate(
        values.length, (i) => FlSpot(i.toDouble(), values[i] / 1000));
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 150,
      padding: const EdgeInsets.fromLTRB(8, 16, 16, 8),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.divider),
      ),
      child: LineChart(
        LineChartData(
          gridData: FlGridData(
            show: true,
            drawVerticalLine: false,
            horizontalInterval: 40,
            getDrawingHorizontalLine: (_) => const FlLine(
              color: AppColors.divider,
              strokeWidth: 1,
            ),
          ),
          titlesData: FlTitlesData(
            leftTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                reservedSize: 36,
                interval: 40,
                getTitlesWidget: (v, _) => Text(
                  '₹${v.toInt()}K',
                  style: const TextStyle(
                      fontSize: 9, color: AppColors.textSecondary),
                ),
              ),
            ),
            bottomTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                interval: 7,
                getTitlesWidget: (v, _) => Text(
                  'D${v.toInt() + 1}',
                  style: const TextStyle(
                      fontSize: 9, color: AppColors.textSecondary),
                ),
              ),
            ),
            topTitles:
                const AxisTitles(sideTitles: SideTitles(showTitles: false)),
            rightTitles:
                const AxisTitles(sideTitles: SideTitles(showTitles: false)),
          ),
          borderData: FlBorderData(show: false),
          lineBarsData: [
            LineChartBarData(
              spots: _spots,
              isCurved: true,
              color: AppColors.primary,
              barWidth: 2,
              dotData: const FlDotData(show: false),
              belowBarData: BarAreaData(
                show: true,
                color: AppColors.primary.withValues(alpha: 0.08),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ── Today's alerts preview ────────────────────────────────────────────────────

class _AlertsPreview extends StatelessWidget {
  const _AlertsPreview({required this.alerts});
  final AlertsState alerts;

  @override
  Widget build(BuildContext context) {
    final unread =
        alerts.alerts.where((a) => !a.isRead).take(3).toList();

    return Column(
      children: [
        ...unread.map((a) => _AlertRow(alert: a)),
        if (alerts.unreadCount > 3)
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: GestureDetector(
              onTap: () => context.go(RouteConstants.alerts),
              child: Text(
                'View all ${alerts.unreadCount} alerts →',
                style: AppTextStyles.bodySmall.copyWith(
                    color: AppColors.primary,
                    fontWeight: FontWeight.w600),
              ),
            ),
          ),
      ],
    );
  }
}

class _AlertRow extends StatelessWidget {
  const _AlertRow({required this.alert});
  final AlertEntity alert;

  @override
  Widget build(BuildContext context) {
    final color = _severityColor(alert.severity);
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.06),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: color.withValues(alpha: 0.2)),
      ),
      child: Row(
        children: [
          Icon(_typeIcon(alert.type), color: color, size: 16),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(alert.title,
                    style: AppTextStyles.bodySmall
                        .copyWith(fontWeight: FontWeight.w600)),
                Text(alert.marketplace,
                    style: AppTextStyles.labelSmall),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Color _severityColor(AlertSeverity s) => switch (s) {
        AlertSeverity.critical => AppColors.error,
        AlertSeverity.warning  => AppColors.warning,
        AlertSeverity.info     => AppColors.info,
      };

  IconData _typeIcon(AlertType t) => switch (t) {
        AlertType.settlementMismatch => Icons.account_balance_wallet_outlined,
        AlertType.highDeduction      => Icons.trending_down_outlined,
        AlertType.settlementDelay    => Icons.schedule_outlined,
        AlertType.disputeUpdate      => Icons.gavel_outlined,
        AlertType.syncFailure        => Icons.sync_problem_outlined,
      };
}

// ── Top discrepancies ─────────────────────────────────────────────────────────

class _DiscrepanciesCard extends StatelessWidget {
  const _DiscrepanciesCard({required this.settlements});
  final SettlementsState settlements;

  @override
  Widget build(BuildContext context) {
    final mismatches = settlements.settlements
        .where((s) =>
            s.difference < 0 &&
            s.status == SettlementStatus.mismatch)
        .toList()
      ..sort((a, b) => a.difference.compareTo(b.difference));
    final top = mismatches.take(3).toList();

    if (top.isEmpty) {
      return Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: AppColors.positive.withValues(alpha: 0.06),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: AppColors.positive.withValues(alpha: 0.2)),
        ),
        child: const Row(
          children: [
            Icon(Icons.check_circle_outline,
                color: AppColors.positive, size: 18),
            SizedBox(width: 10),
            Text('No mismatches in recent settlements.',
                style: TextStyle(color: AppColors.positive)),
          ],
        ),
      );
    }

    return Column(
      children: top
          .map((s) => Container(
                margin: const EdgeInsets.only(bottom: 8),
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: AppColors.error.withValues(alpha: 0.05),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(
                      color: AppColors.error.withValues(alpha: 0.2)),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.warning_amber_outlined,
                        color: AppColors.error, size: 16),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('${s.marketplace}  ·  ${s.id}',
                              style: AppTextStyles.bodySmall.copyWith(
                                  fontWeight: FontWeight.w600)),
                          Text('Ref: ${s.id}',
                              style: AppTextStyles.labelSmall),
                        ],
                      ),
                    ),
                    Text(
                      CurrencyFormatter.format(s.difference),
                      style: AppTextStyles.bodySmall.copyWith(
                          color: AppColors.error,
                          fontWeight: FontWeight.w700),
                    ),
                  ],
                ),
              ))
          .toList(),
    );
  }
}

// ── Marketplaces row ──────────────────────────────────────────────────────────

class _MarketplacesSection extends StatelessWidget {
  const _MarketplacesSection({required this.summary});
  final DashboardSummary summary;

  @override
  Widget build(BuildContext context) {
    if (summary.connectedMarketplaces.isEmpty) {
      return const Text('No marketplaces connected',
          style: AppTextStyles.bodySmall);
    }
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: summary.connectedMarketplaces
          .map((m) => MarketplaceBadge(platform: m))
          .toList(),
    );
  }
}
