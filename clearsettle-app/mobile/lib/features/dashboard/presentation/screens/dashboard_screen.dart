import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/constants/route_constants.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_text_styles.dart';
import '../../../../core/utils/currency_formatter.dart';
import '../../../../core/utils/date_formatter.dart';
import '../../../../routing/app_shell.dart';
import '../../../../shared/widgets/app_error_widget.dart';
import '../../../../shared/widgets/empty_state_widget.dart';
import '../../../../shared/widgets/glass_card.dart';
import '../../../../shared/widgets/loading_indicator.dart';
import '../../../alerts/domain/entities/alert_entity.dart';
import '../../../alerts/presentation/providers/alerts_provider.dart';
import '../../../auth/domain/entities/auth_entity.dart';
import '../../../auth/presentation/providers/auth_provider.dart';
import '../../../disputes/presentation/providers/disputes_provider.dart';
import '../../../platform_connections/domain/entities/platform_connection.dart';
import '../../../platform_connections/presentation/providers/platform_connection_provider.dart';
import '../../../settlements/presentation/providers/settlements_provider.dart';
import '../../domain/entities/dashboard_summary_entity.dart';
import '../providers/dashboard_provider.dart';
import '../providers/settlement_trend_provider.dart';

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
      backgroundColor: AppColors.background,
      body: RefreshIndicator(
        color: AppColors.accent,
        displacement: 60,
        onRefresh: () async {
          ref.read(dashboardProvider.notifier).refresh();
          await ref.read(settlementsProvider.notifier).refresh();
          await ref.read(disputesProvider.notifier).refresh();
          await ref.read(alertsProvider.notifier).refresh();
        },
        child: CustomScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          slivers: [
            // ── Top bar ─────────────────────────────────────────────────
            _TopBar(authState: authState, alerts: alerts),

            // ── Content ─────────────────────────────────────────────────
            dashboardAsync.when(
              loading: () =>
                  const SliverFillRemaining(child: LoadingIndicator()),
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
                            'Upload a settlement report or connect a marketplace to see your financial summary.',
                      ),
                    )
                  : _DashboardBody(
                      summary: summary,
                      settlements: settlements,
                      disputes: disputes,
                      alerts: alerts,
                    ),
            ),
          ],
        ),
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Top bar — clean white header, no colored background
// ─────────────────────────────────────────────────────────────────────────────

class _TopBar extends StatelessWidget {
  const _TopBar({required this.authState, required this.alerts});

  final AuthState? authState;
  final AlertsState alerts;

  @override
  Widget build(BuildContext context) {
    final sellerName = authState is AuthAuthenticated
        ? (authState as AuthAuthenticated).sellerName
        : 'Admin';
    final initial = sellerName.isNotEmpty ? sellerName[0].toUpperCase() : 'A';

    return SliverToBoxAdapter(
      child: Container(
        color: AppColors.surface,
        padding: const EdgeInsets.fromLTRB(20, 56, 20, 16),
        child: Row(
          children: [
            // Hamburger
            GestureDetector(
              onTap: AppShell.openDrawer,
              child: Container(
                width: 38,
                height: 38,
                decoration: BoxDecoration(
                  color: AppColors.surfaceVariant,
                  borderRadius: BorderRadius.circular(10),
                ),
                child: const Icon(Icons.menu_rounded,
                    size: 18, color: AppColors.textSecondary),
              ),
            ),

            const SizedBox(width: 14),

            // Greeting + name
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(_greeting(),
                      style: AppTextStyles.labelMedium.copyWith(
                          color: AppColors.textSecondary)),
                  const SizedBox(height: 1),
                  Text(
                    'Welcome back, $sellerName',
                    style: AppTextStyles.headlineSmall,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ],
              ),
            ),

            // Search
            _TopBarAction(
              icon: Icons.search_rounded,
              onTap: () => context.push(RouteConstants.search),
            ),
            const SizedBox(width: 8),

            // Alerts badge
            Stack(
              clipBehavior: Clip.none,
              children: [
                _TopBarAction(
                  icon: Icons.notifications_outlined,
                  onTap: () => context.go(RouteConstants.alerts),
                ),
                if (alerts.unreadCount > 0)
                  Positioned(
                    top: -2,
                    right: -2,
                    child: Container(
                      width: 16,
                      height: 16,
                      decoration: const BoxDecoration(
                          color: AppColors.error, shape: BoxShape.circle),
                      child: Center(
                        child: Text(
                          alerts.unreadCount > 9
                              ? '9+'
                              : '${alerts.unreadCount}',
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

            const SizedBox(width: 8),

            // Avatar
            Container(
              width: 38,
              height: 38,
              decoration: BoxDecoration(
                gradient: AppColors.heroGradient,
                borderRadius: BorderRadius.circular(10),
              ),
              child: Center(
                child: Text(initial,
                    style: const TextStyle(
                        color: Colors.white,
                        fontWeight: FontWeight.w700,
                        fontSize: 15)),
              ),
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

class _TopBarAction extends StatelessWidget {
  const _TopBarAction({required this.icon, required this.onTap});
  final IconData icon;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: 38,
        height: 38,
        decoration: BoxDecoration(
          color: AppColors.surfaceVariant,
          borderRadius: BorderRadius.circular(10),
        ),
        child: Icon(icon, size: 18, color: AppColors.textSecondary),
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Dashboard body — all content sections
// ─────────────────────────────────────────────────────────────────────────────

class _DashboardBody extends ConsumerWidget {
  const _DashboardBody({
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
  Widget build(BuildContext context, WidgetRef ref) {
    final connectedList =
        ref.watch(platformConnectionProvider).valueOrNull ?? [];
    final recoverableAmount =
        (disputes.totalClaimAmount - disputes.totalRecoveredAmount)
            .clamp(0.0, double.infinity);

    return SliverPadding(
      padding: const EdgeInsets.fromLTRB(20, 0, 20, 32),
      sliver: SliverList(
        delegate: SliverChildListDelegate([
          // Offline banner
          if (summary.isFromCache) ...[
            const SizedBox(height: 12),
            _OfflineBanner(lastSync: summary.lastSync),
          ],

          // ── Hero card ────────────────────────────────────────────────
          const SizedBox(height: 16),
          _HeroCard(
            summary: summary,
            recoverableAmount: recoverableAmount,
          ),

          // ── Guidance banner (no data yet) ────────────────────────────
          if (summary.grossRevenue == 0 && summary.totalOrders == 0) ...[
            const SizedBox(height: 14),
            _GuidanceBanner(hasConnections: connectedList.isNotEmpty),
          ],

          // ── Key Metrics ──────────────────────────────────────────────
          SectionHeader(
            title: 'Key Metrics',
            margin: const EdgeInsets.fromLTRB(0, 24, 0, 12),
          ),
          _MetricsGrid(
            summary: summary,
            settlements: settlements,
            recoverableAmount: recoverableAmount,
          ),

          // ── Connected Marketplaces ───────────────────────────────────
          SectionHeader(
            title: 'Connected Marketplaces',
            actionLabel: 'Manage',
            onAction: () => context.go(RouteConstants.connectedPlatforms),
            margin: const EdgeInsets.fromLTRB(0, 24, 0, 12),
          ),
          _MarketplaceRow(connections: connectedList),

          // ── Settlement Trend ─────────────────────────────────────────
          SectionHeader(
            title: 'Settlement Trend — 30 Days',
            margin: const EdgeInsets.fromLTRB(0, 24, 0, 12),
          ),
          const _TrendChartCard(),

          // ── Platform Mix ─────────────────────────────────────────────
          SectionHeader(
            title: 'Platform Mix',
            margin: const EdgeInsets.fromLTRB(0, 24, 0, 12),
          ),
          const _PlatformMixCard(),

          // ── Action banners ───────────────────────────────────────────
          if (recoverableAmount > 0 || summary.reconUnresolved > 0) ...[
            const SizedBox(height: 24),
            _ActionBanners(
              recoverableAmount: recoverableAmount,
              bankMismatches: summary.reconUnresolved,
            ),
          ],

          // ── Recent Alerts ────────────────────────────────────────────
          if (alerts.unreadCount > 0) ...[
            SectionHeader(
              title: 'Recent Alerts',
              actionLabel: 'View all',
              onAction: () => context.go(RouteConstants.alerts),
              margin: const EdgeInsets.fromLTRB(0, 24, 0, 12),
            ),
            _AlertsList(alerts: alerts),
          ],

          // ── Quick Actions ────────────────────────────────────────────
          SectionHeader(
            title: 'Quick Actions',
            margin: const EdgeInsets.fromLTRB(0, 24, 0, 12),
          ),
          _QuickActionsGrid(context: context),
        ]),
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Hero card — gradient navy→teal, 3 top metrics
// ─────────────────────────────────────────────────────────────────────────────

class _HeroCard extends StatelessWidget {
  const _HeroCard({
    required this.summary,
    required this.recoverableAmount,
  });

  final DashboardSummary summary;
  final double recoverableAmount;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        gradient: AppColors.heroGradient,
        borderRadius: BorderRadius.circular(AppRadius.r6),
        boxShadow: AppShadows.heroCard,
      ),
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header row
            Row(
              children: [
                const Icon(Icons.analytics_outlined,
                    color: Colors.white54, size: 16),
                const SizedBox(width: 6),
                Text('Financial Overview',
                    style: AppTextStyles.labelMedium.copyWith(
                        color: Colors.white60)),
                const Spacer(),
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(
                    color: AppColors.accent.withValues(alpha: 0.2),
                    borderRadius: BorderRadius.circular(6),
                    border: Border.all(
                        color: AppColors.accent.withValues(alpha: 0.3)),
                  ),
                  child: Text(
                    summary.isFromCache ? 'Cached' : 'Live',
                    style: TextStyle(
                        fontSize: 10,
                        fontWeight: FontWeight.w600,
                        color: AppColors.accentLight),
                  ),
                ),
              ],
            ),

            const SizedBox(height: 20),

            // Primary metric — Total GMV
            Text('Total GMV',
                style: AppTextStyles.labelMedium
                    .copyWith(color: Colors.white60)),
            const SizedBox(height: 4),
            Text(
              CurrencyFormatter.format(summary.grossRevenue),
              style: AppTextStyles.displayMedium.copyWith(
                  color: Colors.white, letterSpacing: -0.8),
            ),

            const SizedBox(height: 20),
            Container(height: 1, color: Colors.white.withValues(alpha: 0.1)),
            const SizedBox(height: 20),

            // Secondary metrics row
            Row(
              children: [
                _HeroMetric(
                  label: 'Net Settlement',
                  value: CurrencyFormatter.formatCompact(summary.netSettlement),
                  color: AppColors.accentLight,
                ),
                _HeroMetricDivider(),
                _HeroMetric(
                  label: 'Pending Payout',
                  value: CurrencyFormatter.formatCompact(summary.payoutsPending),
                  color: Colors.white,
                ),
                _HeroMetricDivider(),
                _HeroMetric(
                  label: 'Recoverable',
                  value: CurrencyFormatter.formatCompact(recoverableAmount),
                  color: recoverableAmount > 0
                      ? const Color(0xFFFCD34D)
                      : Colors.white,
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _HeroMetric extends StatelessWidget {
  const _HeroMetric(
      {required this.label, required this.value, required this.color});
  final String label;
  final String value;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label,
              style: AppTextStyles.labelSmall
                  .copyWith(color: Colors.white54, fontSize: 10)),
          const SizedBox(height: 4),
          Text(value,
              style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.w700,
                  color: color,
                  letterSpacing: -0.3),
              maxLines: 1,
              overflow: TextOverflow.ellipsis),
        ],
      ),
    );
  }
}

class _HeroMetricDivider extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      width: 1,
      height: 36,
      margin: const EdgeInsets.symmetric(horizontal: 12),
      color: Colors.white.withValues(alpha: 0.12),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Metrics grid — 2 columns of MetricCard tiles
// ─────────────────────────────────────────────────────────────────────────────

class _MetricsGrid extends StatelessWidget {
  const _MetricsGrid({
    required this.summary,
    required this.settlements,
    required this.recoverableAmount,
  });

  final DashboardSummary summary;
  final SettlementsState settlements;
  final double recoverableAmount;

  @override
  Widget build(BuildContext context) {
    final payoutReceived = settlements.totalReceived > 0
        ? settlements.totalReceived
        : summary.payoutsTransferred;

    final items = [
      _MetricDef(
        label: 'Total GMV',
        value: CurrencyFormatter.formatCompact(summary.grossRevenue),
        icon: Icons.trending_up_rounded,
        iconColor: AppColors.accent,
      ),
      _MetricDef(
        label: 'Total Orders',
        value: summary.totalOrders.toString(),
        icon: Icons.shopping_bag_outlined,
        iconColor: AppColors.info,
      ),
      _MetricDef(
        label: 'Net Settlement',
        value: CurrencyFormatter.formatCompact(summary.netSettlement),
        icon: Icons.account_balance_outlined,
        iconColor: AppColors.success,
      ),
      _MetricDef(
        label: 'Payout Received',
        value: CurrencyFormatter.formatCompact(payoutReceived),
        icon: Icons.check_circle_outline_rounded,
        iconColor: AppColors.success,
      ),
      _MetricDef(
        label: 'Pending Payout',
        value: CurrencyFormatter.formatCompact(summary.payoutsPending),
        icon: Icons.schedule_outlined,
        iconColor: summary.payoutsPending > 0
            ? AppColors.warning
            : AppColors.textMuted,
      ),
      _MetricDef(
        label: 'Recoverable',
        value: CurrencyFormatter.formatCompact(recoverableAmount),
        icon: Icons.restore_outlined,
        iconColor: recoverableAmount > 0
            ? AppColors.warning
            : AppColors.textMuted,
      ),
      _MetricDef(
        label: 'Reports',
        value: summary.totalReports.toString(),
        icon: Icons.description_outlined,
        iconColor: AppColors.purple,
      ),
      _MetricDef(
        label: 'Bank Mismatches',
        value: summary.reconUnresolved.toString(),
        icon: Icons.warning_amber_rounded,
        iconColor: summary.reconUnresolved > 0
            ? AppColors.error
            : AppColors.textMuted,
      ),
    ];

    return Column(
      children: [
        for (int i = 0; i < items.length; i += 2)
          Padding(
            padding: EdgeInsets.only(bottom: i < items.length - 2 ? 10 : 0),
            child: Row(
              children: [
                Expanded(child: _buildCard(items[i])),
                const SizedBox(width: 10),
                Expanded(
                    child: i + 1 < items.length
                        ? _buildCard(items[i + 1])
                        : const SizedBox()),
              ],
            ),
          ),
      ],
    );
  }

  Widget _buildCard(_MetricDef d) {
    return MetricCard(
      label: d.label,
      value: d.value,
      icon: d.icon,
      iconColor: d.iconColor,
    );
  }
}

class _MetricDef {
  const _MetricDef({
    required this.label,
    required this.value,
    required this.icon,
    required this.iconColor,
  });
  final String label;
  final String value;
  final IconData icon;
  final Color iconColor;
}

// ─────────────────────────────────────────────────────────────────────────────
// Marketplace row
// ─────────────────────────────────────────────────────────────────────────────

class _MarketplaceRow extends StatelessWidget {
  const _MarketplaceRow({required this.connections});
  final List<PlatformConnection> connections;

  static const _all = [
    _MktMeta('amazon',   'Amazon',   AppColors.amazon,   Icons.store_outlined),
    _MktMeta('flipkart', 'Flipkart', AppColors.flipkart, Icons.shopping_bag_outlined),
    _MktMeta('meesho',   'Meesho',   AppColors.meesho,   Icons.local_mall_outlined),
    _MktMeta('myntra',   'Myntra',   AppColors.myntra,   Icons.checkroom_outlined),
    _MktMeta('ajio',     'AJIO',     AppColors.ajio,     Icons.style_outlined),
    _MktMeta('nykaa',    'Nykaa',    AppColors.nykaa,    Icons.spa_outlined),
  ];

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 108,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        itemCount: _all.length,
        separatorBuilder: (_, __) => const SizedBox(width: 10),
        itemBuilder: (context, i) {
          final m = _all[i];
          final conn =
              connections.where((c) => c.platform == m.id).firstOrNull;
          final isConnected = conn?.isConnected ?? false;
          return _MarketplaceCard(
            meta: m,
            isConnected: isConnected,
            lastSyncAt: conn?.lastSyncAt,
            onTap: () => context.go(RouteConstants.connectedPlatforms),
          );
        },
      ),
    );
  }
}

class _MktMeta {
  const _MktMeta(this.id, this.name, this.color, this.icon);
  final String id;
  final String name;
  final Color color;
  final IconData icon;
}

class _MarketplaceCard extends StatelessWidget {
  const _MarketplaceCard({
    required this.meta,
    required this.isConnected,
    required this.onTap,
    this.lastSyncAt,
  });

  final _MktMeta meta;
  final bool isConnected;
  final DateTime? lastSyncAt;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final statusColor = isConnected ? AppColors.success : AppColors.textMuted;
    final statusLabel = isConnected ? 'Active' : 'Connect';

    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: 120,
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: AppColors.surface,
          borderRadius: BorderRadius.circular(AppRadius.r4),
          border: Border.all(
            color: isConnected
                ? AppColors.success.withValues(alpha: 0.25)
                : AppColors.divider,
          ),
          boxShadow: AppShadows.card,
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Row(
              children: [
                Container(
                  width: 28,
                  height: 28,
                  decoration: BoxDecoration(
                    color: meta.color.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(7),
                  ),
                  child: Icon(meta.icon, color: meta.color, size: 14),
                ),
                const Spacer(),
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 5, vertical: 2),
                  decoration: BoxDecoration(
                    color: statusColor.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Text(
                    statusLabel,
                    style: TextStyle(
                        fontSize: 9,
                        fontWeight: FontWeight.w700,
                        color: statusColor),
                  ),
                ),
              ],
            ),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(meta.name,
                    style: AppTextStyles.titleSmall
                        .copyWith(fontWeight: FontWeight.w700, fontSize: 12),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis),
                const SizedBox(height: 2),
                Text(
                  isConnected && lastSyncAt != null
                      ? DateFormatter.formatLastSync(lastSyncAt)
                      : 'Tap to connect',
                  style: AppTextStyles.labelSmall
                      .copyWith(fontSize: 9, color: AppColors.textMuted),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Settlement trend chart
// ─────────────────────────────────────────────────────────────────────────────

class _TrendChartCard extends ConsumerWidget {
  const _TrendChartCard();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final trendAsync = ref.watch(settlementTrendProvider);

    return AppCard(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
      child: SizedBox(
        height: 160,
        child: trendAsync.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (_, __) => _ChartEmpty(
            icon: Icons.sync_problem_outlined,
            message: 'Unable to load trend data.',
          ),
          data: (spots) => spots.isEmpty
              ? _ChartEmpty(
                  icon: Icons.show_chart_outlined,
                  message: 'No settlement data yet.',
                )
              : _LineChart(spots: spots),
        ),
      ),
    );
  }
}

class _LineChart extends StatelessWidget {
  const _LineChart({required this.spots});
  final List<FlSpot> spots;

  @override
  Widget build(BuildContext context) {
    final maxY = spots.map((s) => s.y).reduce((a, b) => a > b ? a : b);
    final interval = (maxY / 3).ceilToDouble().clamp(1.0, double.infinity);

    return LineChart(
      LineChartData(
        gridData: FlGridData(
          show: true,
          drawVerticalLine: false,
          horizontalInterval: interval,
          getDrawingHorizontalLine: (_) => const FlLine(
              color: AppColors.divider, strokeWidth: 1),
        ),
        titlesData: FlTitlesData(
          leftTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              reservedSize: 40,
              interval: interval,
              getTitlesWidget: (v, _) => Text('₹${v.toInt()}K',
                  style: const TextStyle(
                      fontSize: 9, color: AppColors.textMuted)),
            ),
          ),
          bottomTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              interval: (spots.length / 5).ceilToDouble().clamp(1, 10),
              getTitlesWidget: (v, _) => Text('D${v.toInt() + 1}',
                  style: const TextStyle(
                      fontSize: 9, color: AppColors.textMuted)),
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
            spots: spots,
            isCurved: true,
            color: AppColors.accent,
            barWidth: 2.5,
            dotData: const FlDotData(show: false),
            belowBarData: BarAreaData(
              show: true,
              gradient: LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: [
                  AppColors.accent.withValues(alpha: 0.15),
                  AppColors.accent.withValues(alpha: 0.0),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _ChartEmpty extends StatelessWidget {
  const _ChartEmpty({required this.icon, required this.message});
  final IconData icon;
  final String message;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 28, color: AppColors.textMuted),
          const SizedBox(height: 8),
          Text(message,
              style: AppTextStyles.bodySmall,
              textAlign: TextAlign.center),
        ],
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Platform mix donut chart
// ─────────────────────────────────────────────────────────────────────────────

class _PlatformMixCard extends ConsumerWidget {
  const _PlatformMixCard();

  static const _colors = {
    'amazon':   AppColors.amazon,
    'flipkart': AppColors.flipkart,
    'meesho':   AppColors.meesho,
    'myntra':   AppColors.myntra,
    'ajio':     AppColors.ajio,
    'nykaa':    AppColors.nykaa,
    'snapdeal': AppColors.snapdeal,
    'jiomart':  AppColors.jiomart,
  };

  static const _names = {
    'amazon':   'Amazon',
    'flipkart': 'Flipkart',
    'meesho':   'Meesho',
    'myntra':   'Myntra',
    'ajio':     'AJIO',
    'nykaa':    'Nykaa',
    'snapdeal': 'Snapdeal',
    'jiomart':  'JioMart',
  };

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final mixAsync = ref.watch(platformMixProvider);

    return AppCard(
      child: mixAsync.when(
        loading: () =>
            const SizedBox(height: 120, child: Center(child: CircularProgressIndicator())),
        error: (_, __) => const SizedBox(
          height: 80,
          child: _ChartEmpty(icon: Icons.pie_chart_outline, message: 'Unable to load.'),
        ),
        data: (mix) => mix.isEmpty
            ? const SizedBox(
                height: 80,
                child: _ChartEmpty(
                    icon: Icons.pie_chart_outline,
                    message: 'No platform data yet.'),
              )
            : Row(
                children: [
                  SizedBox(
                    width: 110,
                    height: 110,
                    child: PieChart(
                      PieChartData(
                        centerSpaceRadius: 32,
                        sectionsSpace: 2,
                        sections: mix.entries.map((e) {
                          final c = _colors[e.key] ?? AppColors.neutral;
                          return PieChartSectionData(
                            value: e.value,
                            color: c,
                            radius: 26,
                            showTitle: false,
                          );
                        }).toList(),
                      ),
                    ),
                  ),
                  const SizedBox(width: 20),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisSize: MainAxisSize.min,
                      children: mix.entries.map((e) {
                        final c = _colors[e.key] ?? AppColors.neutral;
                        final name = _names[e.key] ?? e.key;
                        return Padding(
                          padding: const EdgeInsets.only(bottom: 8),
                          child: Row(
                            children: [
                              Container(
                                  width: 8,
                                  height: 8,
                                  decoration: BoxDecoration(
                                      color: c, shape: BoxShape.circle)),
                              const SizedBox(width: 8),
                              Expanded(
                                  child: Text(name,
                                      style: AppTextStyles.labelMedium,
                                      overflow: TextOverflow.ellipsis)),
                              Text('${e.value.toStringAsFixed(1)}%',
                                  style: AppTextStyles.labelMedium.copyWith(
                                      fontWeight: FontWeight.w700, color: c)),
                            ],
                          ),
                        );
                      }).toList(),
                    ),
                  ),
                ],
              ),
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Action banners — commission / bank mismatch alerts
// ─────────────────────────────────────────────────────────────────────────────

class _ActionBanners extends StatelessWidget {
  const _ActionBanners({
    required this.recoverableAmount,
    required this.bankMismatches,
  });

  final double recoverableAmount;
  final int bankMismatches;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        if (recoverableAmount > 0)
          _ActionBanner(
            icon: Icons.warning_amber_rounded,
            color: AppColors.warning,
            title: 'Commission Overcharge Detected',
            subtitle:
                '${CurrencyFormatter.formatCompact(recoverableAmount)} recoverable',
            onTap: () => context.go(RouteConstants.commissionAudit),
          ),
        if (recoverableAmount > 0 && bankMismatches > 0)
          const SizedBox(height: 8),
        if (bankMismatches > 0)
          _ActionBanner(
            icon: Icons.account_balance_outlined,
            color: AppColors.error,
            title: 'Bank Reconciliation Mismatch',
            subtitle:
                '$bankMismatches unmatched credit${bankMismatches > 1 ? 's' : ''}',
            onTap: () => context.go(RouteConstants.bankReconciliation),
          ),
      ],
    );
  }
}

class _ActionBanner extends StatelessWidget {
  const _ActionBanner({
    required this.icon,
    required this.color,
    required this.title,
    required this.subtitle,
    required this.onTap,
  });

  final IconData icon;
  final Color color;
  final String title;
  final String subtitle;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.06),
          borderRadius: BorderRadius.circular(AppRadius.r3),
          border: Border.all(color: color.withValues(alpha: 0.2)),
        ),
        child: Row(
          children: [
            Container(
              width: 36,
              height: 36,
              decoration: BoxDecoration(
                  color: color.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(9)),
              child: Icon(icon, color: color, size: 18),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(title,
                      style: AppTextStyles.titleSmall
                          .copyWith(color: color, fontSize: 13)),
                  const SizedBox(height: 2),
                  Text(subtitle,
                      style: AppTextStyles.labelSmall
                          .copyWith(color: color.withValues(alpha: 0.75))),
                ],
              ),
            ),
            Icon(Icons.arrow_forward_ios_rounded,
                size: 14, color: color.withValues(alpha: 0.6)),
          ],
        ),
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Alerts list
// ─────────────────────────────────────────────────────────────────────────────

class _AlertsList extends StatelessWidget {
  const _AlertsList({required this.alerts});
  final AlertsState alerts;

  @override
  Widget build(BuildContext context) {
    final unread = alerts.alerts.where((a) => !a.isRead).take(3).toList();

    return Column(
      children: unread.map((a) {
        final color = _severityColor(a.severity);
        return Container(
          margin: const EdgeInsets.only(bottom: 8),
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: color.withValues(alpha: 0.05),
            borderRadius: BorderRadius.circular(AppRadius.r3),
            border: Border.all(color: color.withValues(alpha: 0.15)),
          ),
          child: Row(
            children: [
              Icon(_typeIcon(a.type), color: color, size: 16),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(a.title,
                        style: AppTextStyles.titleSmall
                            .copyWith(fontSize: 13)),
                    Text(a.marketplace,
                        style: AppTextStyles.labelSmall),
                  ],
                ),
              ),
            ],
          ),
        );
      }).toList(),
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

// ─────────────────────────────────────────────────────────────────────────────
// Quick actions grid
// ─────────────────────────────────────────────────────────────────────────────

class _QuickActionsGrid extends StatelessWidget {
  const _QuickActionsGrid({required this.context});
  final BuildContext context;

  @override
  Widget build(BuildContext _) {
    final actions = [
      _Action(Icons.upload_file_outlined, 'Upload Reports',
          AppColors.accent, () => context.go(RouteConstants.reports)),
      _Action(Icons.sync_outlined, 'Sync All',
          AppColors.info, () => context.go(RouteConstants.connectedPlatforms)),
      _Action(Icons.account_balance_outlined, 'Reconcile',
          AppColors.warning, () => context.go(RouteConstants.bankReconciliation)),
      _Action(Icons.gavel_outlined, 'Disputes',
          AppColors.error, () => context.go(RouteConstants.disputes)),
      _Action(Icons.electrical_services_outlined, 'Connect',
          AppColors.purple, () => context.go(RouteConstants.connectedPlatforms)),
      _Action(Icons.receipt_outlined, 'GST Report',
          AppColors.success, () => context.go(RouteConstants.gst)),
    ];

    return Column(
      children: [
        for (int i = 0; i < actions.length; i += 2)
          Padding(
            padding: EdgeInsets.only(bottom: i < actions.length - 2 ? 10 : 0),
            child: Row(
              children: [
                Expanded(child: _ActionTile(action: actions[i])),
                const SizedBox(width: 10),
                Expanded(
                    child: i + 1 < actions.length
                        ? _ActionTile(action: actions[i + 1])
                        : const SizedBox()),
              ],
            ),
          ),
      ],
    );
  }
}

class _Action {
  const _Action(this.icon, this.label, this.color, this.onTap);
  final IconData icon;
  final String label;
  final Color color;
  final VoidCallback onTap;
}

class _ActionTile extends StatelessWidget {
  const _ActionTile({required this.action});
  final _Action action;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: action.color.withValues(alpha: 0.06),
      borderRadius: BorderRadius.circular(AppRadius.r3),
      child: InkWell(
        borderRadius: BorderRadius.circular(AppRadius.r3),
        onTap: action.onTap,
        splashColor: action.color.withValues(alpha: 0.08),
        child: Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(AppRadius.r3),
            border: Border.all(color: action.color.withValues(alpha: 0.15)),
          ),
          child: Row(
            children: [
              Container(
                width: 32,
                height: 32,
                decoration: BoxDecoration(
                  color: action.color.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Icon(action.icon, color: action.color, size: 16),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  action.label,
                  style: AppTextStyles.labelMedium.copyWith(
                    color: action.color,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Guidance banner — shown when no financial data yet
// ─────────────────────────────────────────────────────────────────────────────

class _GuidanceBanner extends StatelessWidget {
  const _GuidanceBanner({required this.hasConnections});
  final bool hasConnections;

  @override
  Widget build(BuildContext context) {
    final msg = hasConnections
        ? 'Flipkart is connected. Go to Reports and upload your settlement Excel file to see financial data.'
        : 'Connect a marketplace and upload a settlement report to see your financial summary here.';
    return GestureDetector(
      onTap: () => context.go(RouteConstants.reports),
      child: Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: AppColors.accent.withValues(alpha: 0.05),
          borderRadius: BorderRadius.circular(AppRadius.r3),
          border: Border.all(color: AppColors.accent.withValues(alpha: 0.15)),
        ),
        child: Row(
          children: [
            Container(
              width: 32,
              height: 32,
              decoration: BoxDecoration(
                color: AppColors.accent.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(8),
              ),
              child: const Icon(Icons.upload_file_outlined,
                  color: AppColors.accent, size: 16),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Text(msg,
                  style: AppTextStyles.bodySmall
                      .copyWith(color: AppColors.textSecondary)),
            ),
            const Icon(Icons.arrow_forward_ios_rounded,
                color: AppColors.accent, size: 13),
          ],
        ),
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Offline banner
// ─────────────────────────────────────────────────────────────────────────────

class _OfflineBanner extends StatelessWidget {
  const _OfflineBanner({this.lastSync});
  final DateTime? lastSync;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: AppColors.warning.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(AppRadius.r2),
        border: Border.all(color: AppColors.warning.withValues(alpha: 0.2)),
      ),
      child: Row(
        children: [
          const Icon(Icons.cloud_off_outlined, color: AppColors.warning, size: 15),
          const SizedBox(width: 8),
          Expanded(
            child: Text(DateFormatter.formatLastSync(lastSync),
                style: AppTextStyles.bodySmall
                    .copyWith(color: AppColors.warning)),
          ),
        ],
      ),
    );
  }
}
