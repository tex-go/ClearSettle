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
    final connections    = ref.watch(platformConnectionProvider);

    return Scaffold(
      backgroundColor: Theme.of(context).scaffoldBackgroundColor,
      body: SafeArea(
        child: RefreshIndicator(
          color: AppColors.teal,
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
                    : _DashboardContent(
                        summary: summary,
                        settlements: settlements,
                        disputes: disputes,
                        alerts: alerts,
                        connections: connections,
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
        padding: const EdgeInsets.fromLTRB(4, 16, 8, 16),
        color: AppColors.primary,
        child: Row(
          children: [
            // Hamburger — opens side drawer
            IconButton(
              icon: const Icon(Icons.menu, color: AppColors.textInverse),
              onPressed: AppShell.openDrawer,
              tooltip: 'Menu',
            ),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    _greeting(),
                    style: AppTextStyles.labelMedium.copyWith(
                      color: AppColors.textInverse.withValues(alpha: 0.70),
                    ),
                  ),
                  const SizedBox(height: 1),
                  Text(
                    authState is AuthAuthenticated
                        ? (authState as AuthAuthenticated).sellerName
                        : 'Seller',
                    style: AppTextStyles.headlineLarge
                        .copyWith(color: AppColors.textInverse),
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
    required this.connections,
  });

  final DashboardSummary summary;
  final SettlementsState settlements;
  final DisputesState disputes;
  final AlertsState alerts;
  final AsyncValue<List<PlatformConnection>> connections;

  @override
  Widget build(BuildContext context) {
    final connectedList = connections.valueOrNull ?? [];
    final recoverableAmount =
        (disputes.totalClaimAmount - disputes.totalRecoveredAmount)
            .clamp(0.0, double.infinity);

    return SliverPadding(
      padding: const EdgeInsets.all(16),
      sliver: SliverList(
        delegate: SliverChildListDelegate([
          // Offline banner
          if (summary.isFromCache) ...[
            _OfflineBanner(lastSync: summary.lastSync),
            const SizedBox(height: 12),
          ],

          // Business profile card
          _BusinessProfileCard(
              summary: summary, connections: connectedList),
          const SizedBox(height: 12),

          // Alert banners (real data — shown only when actionable)
          _AlertBanners(
            recoverableAmount: recoverableAmount,
            bankMismatches: summary.reconUnresolved,
            onCommissionTap: () =>
                context.go(RouteConstants.commissionAudit),
            onBankTap: () =>
                context.go(RouteConstants.bankReconciliation),
          ),

          // ── Key Metrics ──────────────────────────────────────────────────
          const _SectionHeader('Key Metrics'),
          const SizedBox(height: 8),
          _KpiGrid(
            summary: summary,
            settlements: settlements,
            disputes: disputes,
            connections: connectedList,
          ),
          const SizedBox(height: 20),

          // ── Connected Marketplaces ────────────────────────────────────────
          _SectionHeaderWithAction(
            title: 'Connected Marketplaces',
            actionLabel: 'Manage',
            onAction: () => context.go(RouteConstants.connectedPlatforms),
          ),
          const SizedBox(height: 10),
          _MarketplaceCardsRow(connections: connectedList),
          const SizedBox(height: 20),

          // ── Settlement Trend ──────────────────────────────────────────────
          const _SectionHeader('Settlement Trend — 30 Days'),
          const SizedBox(height: 8),
          const _SettlementTrendSection(),
          const SizedBox(height: 20),

          // ── Platform Mix ─────────────────────────────────────────────────
          const _SectionHeader('Platform Mix'),
          const SizedBox(height: 8),
          const _PlatformMixSection(),
          const SizedBox(height: 20),

          // ── Today's Alerts ────────────────────────────────────────────────
          if (alerts.unreadCount > 0) ...[
            _SectionHeader('Today\'s Alerts  (${alerts.unreadCount})'),
            const SizedBox(height: 8),
            _AlertsPreview(alerts: alerts),
            const SizedBox(height: 20),
          ],

          // ── Quick Actions ─────────────────────────────────────────────────
          const _SectionHeader('Quick Actions'),
          const SizedBox(height: 8),
          const _QuickActionsGrid(),
          const SizedBox(height: 24),
        ]),
      ),
    );
  }
}

// ── Offline banner ────────────────────────────────────────────────────────────

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

// ── Business profile card ─────────────────────────────────────────────────────

class _BusinessProfileCard extends StatelessWidget {
  const _BusinessProfileCard({
    required this.summary,
    required this.connections,
  });

  final DashboardSummary summary;
  final List<PlatformConnection> connections;

  @override
  Widget build(BuildContext context) {
    final connected = connections.where((c) => c.isConnected).toList();
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: AppColors.divider),
      ),
      child: Row(
        children: [
          Container(
            width: 48,
            height: 48,
            decoration: BoxDecoration(
              color: AppColors.primary.withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(12),
            ),
            child: const Icon(Icons.store_outlined,
                color: AppColors.primary, size: 24),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(summary.organization,
                    style: AppTextStyles.titleLarge,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis),
                const SizedBox(height: 2),
                Text(summary.sellerName,
                    style: AppTextStyles.bodySmall
                        .copyWith(color: AppColors.textSecondary)),
                if (connected.isNotEmpty) ...[
                  const SizedBox(height: 6),
                  Wrap(
                    spacing: 6,
                    runSpacing: 4,
                    children: connected.map((c) {
                      final color = _platformColor(c.platform);
                      return Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 8, vertical: 3),
                        decoration: BoxDecoration(
                          color: color.withValues(alpha: 0.1),
                          borderRadius: BorderRadius.circular(6),
                          border: Border.all(
                              color: color.withValues(alpha: 0.3)),
                        ),
                        child: Text(
                          _platformLabel(c.platform),
                          style: AppTextStyles.labelSmall.copyWith(
                              color: color, fontWeight: FontWeight.w600),
                        ),
                      );
                    }).toList(),
                  ),
                ],
              ],
            ),
          ),
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(
                '${summary.totalReports}',
                style: AppTextStyles.headlineMedium.copyWith(
                  color: AppColors.primary,
                  fontWeight: FontWeight.w700,
                ),
              ),
              Text('Reports',
                  style: AppTextStyles.labelSmall
                      .copyWith(color: AppColors.textSecondary)),
            ],
          ),
        ],
      ),
    );
  }
}

// ── Alert banners ─────────────────────────────────────────────────────────────

class _AlertBanners extends StatelessWidget {
  const _AlertBanners({
    required this.recoverableAmount,
    required this.bankMismatches,
    required this.onCommissionTap,
    required this.onBankTap,
  });

  final double recoverableAmount;
  final int bankMismatches;
  final VoidCallback onCommissionTap;
  final VoidCallback onBankTap;

  @override
  Widget build(BuildContext context) {
    final hasRecoverable = recoverableAmount > 0;
    final hasMismatches = bankMismatches > 0;
    if (!hasRecoverable && !hasMismatches) return const SizedBox.shrink();

    return Column(
      children: [
        if (hasRecoverable)
          _AlertBanner(
            icon: Icons.warning_amber_outlined,
            color: AppColors.warning,
            title: 'Commission Overcharge Detected',
            subtitle:
                '${CurrencyFormatter.formatCompact(recoverableAmount)} recoverable',
            actionLabel: 'Review Now',
            onAction: onCommissionTap,
          ),
        if (hasRecoverable && hasMismatches) const SizedBox(height: 8),
        if (hasMismatches)
          _AlertBanner(
            icon: Icons.account_balance_outlined,
            color: AppColors.error,
            title: 'Bank Reconciliation Mismatch',
            subtitle: '$bankMismatches unmatched credit${bankMismatches > 1 ? 's' : ''}',
            actionLabel: 'Reconcile',
            onAction: onBankTap,
          ),
        const SizedBox(height: 16),
      ],
    );
  }
}

class _AlertBanner extends StatelessWidget {
  const _AlertBanner({
    required this.icon,
    required this.color,
    required this.title,
    required this.subtitle,
    required this.actionLabel,
    required this.onAction,
  });

  final IconData icon;
  final Color color;
  final String title;
  final String subtitle;
  final String actionLabel;
  final VoidCallback onAction;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(14, 12, 12, 12),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.07),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withValues(alpha: 0.25)),
      ),
      child: Row(
        children: [
          Icon(icon, color: color, size: 20),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title,
                    style: AppTextStyles.bodySmall.copyWith(
                        color: color, fontWeight: FontWeight.w700)),
                const SizedBox(height: 2),
                Text(subtitle,
                    style: AppTextStyles.labelSmall
                        .copyWith(color: color.withValues(alpha: 0.8))),
              ],
            ),
          ),
          const SizedBox(width: 8),
          GestureDetector(
            onTap: onAction,
            child: Container(
              padding:
                  const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
              decoration: BoxDecoration(
                color: color,
                borderRadius: BorderRadius.circular(7),
              ),
              child: Text(
                actionLabel,
                style: AppTextStyles.labelSmall.copyWith(
                  color: Colors.white,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// ── Section headers ───────────────────────────────────────────────────────────

class _SectionHeader extends StatelessWidget {
  const _SectionHeader(this.title);
  final String title;

  @override
  Widget build(BuildContext context) {
    return Text(title, style: AppTextStyles.titleMedium);
  }
}

class _SectionHeaderWithAction extends StatelessWidget {
  const _SectionHeaderWithAction({
    required this.title,
    required this.actionLabel,
    required this.onAction,
  });

  final String title;
  final String actionLabel;
  final VoidCallback onAction;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Expanded(
            child: Text(title, style: AppTextStyles.titleMedium)),
        GestureDetector(
          onTap: onAction,
          child: Text(
            actionLabel,
            style: AppTextStyles.labelMedium.copyWith(
              color: AppColors.teal,
              fontWeight: FontWeight.w600,
            ),
          ),
        ),
      ],
    );
  }
}

// ── 8-KPI grid ────────────────────────────────────────────────────────────────

class _KpiGrid extends StatelessWidget {
  const _KpiGrid({
    required this.summary,
    required this.settlements,
    required this.disputes,
    required this.connections,
  });

  final DashboardSummary summary;
  final SettlementsState settlements;
  final DisputesState disputes;
  final List<PlatformConnection> connections;

  @override
  Widget build(BuildContext context) {
    final recoverableAmount =
        (disputes.totalClaimAmount - disputes.totalRecoveredAmount)
            .clamp(0.0, double.infinity);
    final connectedCount = connections.where((c) => c.isConnected).length;

    final items = [
      _KpiData(
        label: 'Total GMV',
        value: CurrencyFormatter.formatCompact(summary.grossRevenue),
        icon: Icons.trending_up_outlined,
        iconColor: AppColors.positive,
      ),
      _KpiData(
        label: 'Net Settlement',
        value: CurrencyFormatter.formatCompact(summary.netSettlement),
        icon: Icons.account_balance_outlined,
        iconColor: AppColors.primary,
      ),
      _KpiData(
        label: 'Payout Received',
        value: CurrencyFormatter.formatCompact(
            settlements.totalReceived > 0
                ? settlements.totalReceived
                : summary.payoutsTransferred),
        icon: Icons.check_circle_outline,
        iconColor: AppColors.positive,
      ),
      _KpiData(
        label: 'Pending Payout',
        value: CurrencyFormatter.formatCompact(summary.payoutsPending),
        icon: Icons.schedule_outlined,
        iconColor: AppColors.info,
        highlight: summary.payoutsPending > 0,
      ),
      _KpiData(
        label: 'Total Orders',
        value: summary.totalOrders.toString(),
        icon: Icons.shopping_bag_outlined,
        iconColor: AppColors.primary,
      ),
      _KpiData(
        label: 'Platforms',
        value: connectedCount > 0
            ? '$connectedCount Connected'
            : 'None',
        icon: Icons.electrical_services_outlined,
        iconColor: connectedCount > 0 ? AppColors.teal : AppColors.neutral,
      ),
      _KpiData(
        label: 'Recoverable',
        value: CurrencyFormatter.formatCompact(recoverableAmount),
        icon: Icons.restore_outlined,
        iconColor: AppColors.warning,
        highlight: recoverableAmount > 0,
      ),
      _KpiData(
        label: 'Bank Mismatches',
        value: summary.reconUnresolved.toString(),
        icon: Icons.account_balance_outlined,
        iconColor: summary.reconUnresolved > 0
            ? AppColors.error
            : AppColors.neutral,
        highlight: summary.reconUnresolved > 0,
      ),
    ];

    return Column(
      children: [
        for (int i = 0; i < items.length; i += 2)
          Padding(
            padding: EdgeInsets.only(bottom: i < items.length - 2 ? 10 : 0),
            child: Row(
              children: [
                Expanded(child: _KpiCard(data: items[i])),
                const SizedBox(width: 10),
                Expanded(
                    child: i + 1 < items.length
                        ? _KpiCard(data: items[i + 1])
                        : const SizedBox()),
              ],
            ),
          ),
      ],
    );
  }
}

class _KpiData {
  const _KpiData({
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
}

class _KpiCard extends StatelessWidget {
  const _KpiCard({required this.data});
  final _KpiData data;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: data.highlight
            ? data.iconColor.withValues(alpha: 0.06)
            : Theme.of(context).colorScheme.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: data.highlight
              ? data.iconColor.withValues(alpha: 0.25)
              : AppColors.divider,
        ),
      ),
      child: Row(
        children: [
          Container(
            width: 34,
            height: 34,
            decoration: BoxDecoration(
              color: data.iconColor.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Icon(data.icon, size: 17, color: data.iconColor),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(data.value,
                    style: AppTextStyles.titleMedium
                        .copyWith(fontWeight: FontWeight.w700),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis),
                Text(data.label, style: AppTextStyles.labelSmall),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

// ── Connected marketplace cards ───────────────────────────────────────────────

class _MarketplaceMeta {
  const _MarketplaceMeta({
    required this.id,
    required this.name,
    required this.color,
    required this.icon,
    this.canConnect = false,
  });
  final String id;
  final String name;
  final Color color;
  final IconData icon;
  final bool canConnect;
}

const _allMarketplaces = [
  _MarketplaceMeta(
      id: 'amazon',
      name: 'Amazon',
      color: AppColors.amazon,
      icon: Icons.store_outlined,
      canConnect: true),
  _MarketplaceMeta(
      id: 'flipkart',
      name: 'Flipkart',
      color: AppColors.flipkart,
      icon: Icons.shopping_bag_outlined,
      canConnect: true),
  _MarketplaceMeta(
      id: 'meesho',
      name: 'Meesho',
      color: AppColors.meesho,
      icon: Icons.local_mall_outlined),
  _MarketplaceMeta(
      id: 'myntra',
      name: 'Myntra',
      color: AppColors.myntra,
      icon: Icons.checkroom_outlined),
  _MarketplaceMeta(
      id: 'ajio',
      name: 'AJIO',
      color: AppColors.ajio,
      icon: Icons.style_outlined),
  _MarketplaceMeta(
      id: 'nykaa',
      name: 'Nykaa',
      color: AppColors.nykaa,
      icon: Icons.spa_outlined),
  _MarketplaceMeta(
      id: 'snapdeal',
      name: 'Snapdeal',
      color: AppColors.snapdeal,
      icon: Icons.flash_on_outlined),
  _MarketplaceMeta(
      id: 'jiomart',
      name: 'JioMart',
      color: AppColors.jiomart,
      icon: Icons.shopping_cart_outlined),
];

class _MarketplaceCardsRow extends StatelessWidget {
  const _MarketplaceCardsRow({required this.connections});
  final List<PlatformConnection> connections;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 120,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        itemCount: _allMarketplaces.length,
        separatorBuilder: (_, __) => const SizedBox(width: 10),
        itemBuilder: (context, i) {
          final meta = _allMarketplaces[i];
          final conn = connections.where((c) => c.platform == meta.id).firstOrNull;
          final isConnected = conn?.isConnected ?? false;
          return _MarketplaceCard(
            meta: meta,
            isConnected: isConnected,
            lastSyncAt: conn?.lastSyncAt,
            onTap: () => context.go(RouteConstants.connectedPlatforms),
          );
        },
      ),
    );
  }
}

class _MarketplaceCard extends StatelessWidget {
  const _MarketplaceCard({
    required this.meta,
    required this.isConnected,
    required this.onTap,
    this.lastSyncAt,
  });

  final _MarketplaceMeta meta;
  final bool isConnected;
  final DateTime? lastSyncAt;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final statusColor = isConnected
        ? AppColors.teal
        : meta.canConnect
            ? AppColors.warning
            : AppColors.neutral;
    final statusLabel = isConnected
        ? 'Active'
        : meta.canConnect
            ? 'Connect'
            : 'Soon';

    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: 130,
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surface,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: isConnected
                ? AppColors.teal.withValues(alpha: 0.3)
                : AppColors.divider,
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Row(
              children: [
                Container(
                  width: 30,
                  height: 30,
                  decoration: BoxDecoration(
                    color: meta.color.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(7),
                  ),
                  child: Icon(meta.icon, color: meta.color, size: 16),
                ),
                const Spacer(),
                Container(
                  padding: const EdgeInsets.symmetric(
                      horizontal: 6, vertical: 2),
                  decoration: BoxDecoration(
                    color: statusColor.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(5),
                  ),
                  child: Text(
                    statusLabel,
                    style: TextStyle(
                      fontSize: 9,
                      fontWeight: FontWeight.w700,
                      color: statusColor,
                    ),
                  ),
                ),
              ],
            ),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(meta.name,
                    style: AppTextStyles.labelMedium
                        .copyWith(fontWeight: FontWeight.w700),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis),
                const SizedBox(height: 2),
                Text(
                  isConnected && lastSyncAt != null
                      ? DateFormatter.formatLastSync(lastSyncAt)
                      : meta.canConnect
                          ? 'Tap to connect'
                          : 'Coming soon',
                  style: AppTextStyles.labelSmall.copyWith(
                    color: AppColors.textSecondary,
                    fontSize: 9,
                  ),
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

// ── Settlement trend chart ────────────────────────────────────────────────────

class _SettlementTrendSection extends ConsumerWidget {
  const _SettlementTrendSection();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final trendAsync = ref.watch(settlementTrendProvider);

    return Container(
      height: 160,
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.divider),
      ),
      child: trendAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (_, __) => const _ChartEmptyState(
          icon: Icons.sync_problem_outlined,
          message: 'Unable to load trend data. Pull down to retry.',
        ),
        data: (spots) => spots.isEmpty
            ? const _ChartEmptyState(
                icon: Icons.show_chart_outlined,
                message:
                    'No settlement data yet.\nUpload a report or sync a marketplace.',
              )
            : Padding(
                padding: const EdgeInsets.fromLTRB(8, 16, 16, 8),
                child: _buildLineChart(spots),
              ),
      ),
    );
  }

  Widget _buildLineChart(List<FlSpot> spots) {
    final maxY = spots.map((s) => s.y).reduce((a, b) => a > b ? a : b);
    final interval = (maxY / 3).ceilToDouble().clamp(1.0, double.infinity);

    return LineChart(
      LineChartData(
        gridData: FlGridData(
          show: true,
          drawVerticalLine: false,
          horizontalInterval: interval,
          getDrawingHorizontalLine: (_) => const FlLine(
            color: AppColors.divider,
            strokeWidth: 1,
          ),
        ),
        titlesData: FlTitlesData(
          leftTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              reservedSize: 40,
              interval: interval,
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
              interval: (spots.length / 5).ceilToDouble().clamp(1, 10),
              getTitlesWidget: (v, _) => Text(
                'D${v.toInt() + 1}',
                style: const TextStyle(
                    fontSize: 9, color: AppColors.textSecondary),
              ),
            ),
          ),
          topTitles: const AxisTitles(
              sideTitles: SideTitles(showTitles: false)),
          rightTitles: const AxisTitles(
              sideTitles: SideTitles(showTitles: false)),
        ),
        borderData: FlBorderData(show: false),
        lineBarsData: [
          LineChartBarData(
            spots: spots,
            isCurved: true,
            color: AppColors.teal,
            barWidth: 2.5,
            dotData: const FlDotData(show: false),
            belowBarData: BarAreaData(
              show: true,
              color: AppColors.teal.withValues(alpha: 0.08),
            ),
          ),
        ],
      ),
    );
  }
}

class _ChartEmptyState extends StatelessWidget {
  const _ChartEmptyState({required this.icon, required this.message});
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
          Text(
            message,
            textAlign: TextAlign.center,
            style: AppTextStyles.bodySmall
                .copyWith(color: AppColors.textSecondary),
          ),
        ],
      ),
    );
  }
}

// ── Platform mix chart ────────────────────────────────────────────────────────

class _PlatformMixSection extends ConsumerWidget {
  const _PlatformMixSection();

  static const _platformColors = {
    'amazon':   AppColors.amazon,
    'flipkart': AppColors.flipkart,
    'meesho':   AppColors.meesho,
    'myntra':   AppColors.myntra,
    'ajio':     AppColors.ajio,
    'nykaa':    AppColors.nykaa,
    'snapdeal': AppColors.snapdeal,
    'jiomart':  AppColors.jiomart,
  };

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final mixAsync = ref.watch(platformMixProvider);

    return Container(
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.divider),
      ),
      child: mixAsync.when(
        loading: () =>
            const SizedBox(height: 160, child: Center(child: CircularProgressIndicator())),
        error: (_, __) => const SizedBox(
          height: 120,
          child: _ChartEmptyState(
            icon: Icons.pie_chart_outline,
            message: 'Unable to load platform data.',
          ),
        ),
        data: (mix) => mix.isEmpty
            ? const SizedBox(
                height: 120,
                child: _ChartEmptyState(
                  icon: Icons.pie_chart_outline,
                  message:
                      'No platform data yet.\nConnect a marketplace to see your mix.',
                ),
              )
            : Padding(
                padding: const EdgeInsets.all(16),
                child: Row(
                  children: [
                    // Donut chart
                    SizedBox(
                      width: 120,
                      height: 120,
                      child: PieChart(
                        PieChartData(
                          centerSpaceRadius: 36,
                          sectionsSpace: 2,
                          sections: mix.entries.map((e) {
                            final color = _platformColors[e.key] ??
                                AppColors.neutral;
                            return PieChartSectionData(
                              value: e.value,
                              color: color,
                              radius: 28,
                              showTitle: false,
                            );
                          }).toList(),
                        ),
                      ),
                    ),
                    const SizedBox(width: 20),
                    // Legend
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        mainAxisSize: MainAxisSize.min,
                        children: mix.entries.map((e) {
                          final color = _platformColors[e.key] ??
                              AppColors.neutral;
                          final label = _allMarketplaces
                              .where((m) => m.id == e.key)
                              .map((m) => m.name)
                              .firstOrNull ?? e.key;
                          return Padding(
                            padding: const EdgeInsets.only(bottom: 8),
                            child: Row(
                              children: [
                                Container(
                                  width: 10,
                                  height: 10,
                                  decoration: BoxDecoration(
                                    color: color,
                                    shape: BoxShape.circle,
                                  ),
                                ),
                                const SizedBox(width: 8),
                                Expanded(
                                  child: Text(label,
                                      style: AppTextStyles.labelSmall,
                                      overflow: TextOverflow.ellipsis),
                                ),
                                Text(
                                  '${e.value.toStringAsFixed(1)}%',
                                  style: AppTextStyles.labelSmall.copyWith(
                                    fontWeight: FontWeight.w700,
                                    color: color,
                                  ),
                                ),
                              ],
                            ),
                          );
                        }).toList(),
                      ),
                    ),
                  ],
                ),
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
                    color: AppColors.teal, fontWeight: FontWeight.w600),
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
        AlertType.settlementMismatch =>
          Icons.account_balance_wallet_outlined,
        AlertType.highDeduction      => Icons.trending_down_outlined,
        AlertType.settlementDelay    => Icons.schedule_outlined,
        AlertType.disputeUpdate      => Icons.gavel_outlined,
        AlertType.syncFailure        => Icons.sync_problem_outlined,
      };
}

// ── Quick actions ─────────────────────────────────────────────────────────────

class _QuickActionsGrid extends StatelessWidget {
  const _QuickActionsGrid();

  @override
  Widget build(BuildContext context) {
    final actions = [
      _ActionData(
        icon: Icons.sync_outlined,
        label: 'Sync All',
        color: AppColors.teal,
        onTap: () => context.go(RouteConstants.connectedPlatforms),
      ),
      _ActionData(
        icon: Icons.upload_file_outlined,
        label: 'Upload Reports',
        color: AppColors.primary,
        onTap: () => context.go(RouteConstants.reports),
      ),
      _ActionData(
        icon: Icons.electrical_services_outlined,
        label: 'Connect Marketplace',
        color: AppColors.info,
        onTap: () => context.go(RouteConstants.connectedPlatforms),
      ),
      _ActionData(
        icon: Icons.account_balance_outlined,
        label: 'Run Reconciliation',
        color: AppColors.warning,
        onTap: () => context.go(RouteConstants.bankReconciliation),
      ),
      _ActionData(
        icon: Icons.gavel_outlined,
        label: 'Create Dispute',
        color: AppColors.error,
        onTap: () => context.go(RouteConstants.disputes),
      ),
      _ActionData(
        icon: Icons.receipt_outlined,
        label: 'Generate GST',
        color: AppColors.purple,
        onTap: () => context.go(RouteConstants.gst),
      ),
    ];

    return Column(
      children: [
        for (int i = 0; i < actions.length; i += 2)
          Padding(
            padding: EdgeInsets.only(bottom: i < actions.length - 2 ? 10 : 0),
            child: Row(
              children: [
                Expanded(child: _ActionButton(data: actions[i])),
                const SizedBox(width: 10),
                Expanded(
                    child: i + 1 < actions.length
                        ? _ActionButton(data: actions[i + 1])
                        : const SizedBox()),
              ],
            ),
          ),
      ],
    );
  }
}

class _ActionData {
  const _ActionData({
    required this.icon,
    required this.label,
    required this.color,
    required this.onTap,
  });
  final IconData icon;
  final String label;
  final Color color;
  final VoidCallback onTap;
}

class _ActionButton extends StatelessWidget {
  const _ActionButton({required this.data});
  final _ActionData data;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: data.color.withValues(alpha: 0.08),
      borderRadius: BorderRadius.circular(12),
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: data.onTap,
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: data.color.withValues(alpha: 0.2)),
          ),
          child: Row(
            children: [
              Container(
                width: 32,
                height: 32,
                decoration: BoxDecoration(
                  color: data.color.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Icon(data.icon, color: data.color, size: 17),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  data.label,
                  style: AppTextStyles.labelMedium.copyWith(
                    color: data.color,
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

// ── Helper functions ──────────────────────────────────────────────────────────

Color _platformColor(String platform) => switch (platform) {
      'amazon'   => AppColors.amazon,
      'flipkart' => AppColors.flipkart,
      'meesho'   => AppColors.meesho,
      'myntra'   => AppColors.myntra,
      'ajio'     => AppColors.ajio,
      'nykaa'    => AppColors.nykaa,
      'snapdeal' => AppColors.snapdeal,
      'jiomart'  => AppColors.jiomart,
      _          => AppColors.neutral,
    };

String _platformLabel(String platform) => switch (platform) {
      'amazon'   => 'Amazon',
      'flipkart' => 'Flipkart',
      'meesho'   => 'Meesho',
      'myntra'   => 'Myntra',
      'ajio'     => 'AJIO',
      'nykaa'    => 'Nykaa',
      'snapdeal' => 'Snapdeal',
      'jiomart'  => 'JioMart',
      _          => platform,
    };
