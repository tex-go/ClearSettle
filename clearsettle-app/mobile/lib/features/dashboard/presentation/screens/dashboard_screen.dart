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
import '../../../auth/presentation/providers/auth_provider.dart';
import '../../domain/entities/dashboard_summary_entity.dart';
import '../providers/dashboard_provider.dart';
import '../widgets/marketplace_badge.dart';
import '../widgets/summary_card.dart';

class DashboardScreen extends ConsumerWidget {
  const DashboardScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final authState = ref.watch(authProvider).valueOrNull;
    final dashboardAsync = ref.watch(dashboardProvider);

    return Scaffold(
      backgroundColor: Theme.of(context).scaffoldBackgroundColor,
      body: SafeArea(
        child: RefreshIndicator(
          color: AppColors.primary,
          onRefresh: () => ref.read(dashboardProvider.notifier).refresh(),
          child: CustomScrollView(
            physics: const AlwaysScrollableScrollPhysics(),
            slivers: [
              _DashboardAppBar(
                authState: authState,
                onSearch: () => context.push(RouteConstants.search),
              ),
              dashboardAsync.when(
                loading: () => const SliverFillRemaining(
                  child: LoadingIndicator(),
                ),
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
                    : _DashboardContent(summary: summary),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _DashboardAppBar extends StatelessWidget {
  const _DashboardAppBar({required this.authState, required this.onSearch});

  final dynamic authState;
  final VoidCallback onSearch;

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
                    authState?.sellerName ?? 'Seller',
                    style: AppTextStyles.headlineLarge.copyWith(
                      color: AppColors.textInverse,
                    ),
                  ),
                ],
              ),
            ),
            IconButton(
              icon: const Icon(Icons.search, color: AppColors.textInverse),
              onPressed: onSearch,
              tooltip: 'Search',
            ),
            IconButton(
              icon: const Icon(Icons.notifications_outlined,
                  color: AppColors.textInverse),
              onPressed: () {},
              tooltip: 'Notifications',
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

class _DashboardContent extends StatelessWidget {
  const _DashboardContent({required this.summary});

  final DashboardSummary summary;

  @override
  Widget build(BuildContext context) {
    return SliverPadding(
      padding: const EdgeInsets.all(16),
      sliver: SliverList(
        delegate: SliverChildListDelegate([
          if (summary.isFromCache) _OfflineBanner(lastSync: summary.lastSync),
          if (summary.isFromCache) const SizedBox(height: 12),
          _OrgCard(summary: summary),
          const SizedBox(height: 16),
          _NetSettlementCard(value: summary.netSettlement),
          const SizedBox(height: 12),
          _KpiGrid(summary: summary),
          const SizedBox(height: 20),
          _MarketplacesSection(summary: summary),
          const SizedBox(height: 24),
        ]),
      ),
    );
  }
}

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
              style:
                  AppTextStyles.bodySmall.copyWith(color: AppColors.warning),
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
                Text(
                  summary.organization,
                  style: AppTextStyles.titleMedium,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                const SizedBox(height: 2),
                Text(summary.sellerName, style: AppTextStyles.bodySmall),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _NetSettlementCard extends StatelessWidget {
  const _NetSettlementCard({required this.value});

  final double value;

  @override
  Widget build(BuildContext context) {
    final isPositive = value >= 0;
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [AppColors.primary, AppColors.primaryLight],
        ),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Net Settlement',
            style: AppTextStyles.bodyMedium.copyWith(
              color: AppColors.textInverse.withValues(alpha: 0.8),
            ),
          ),
          const SizedBox(height: 8),
          Text(
            CurrencyFormatter.format(value),
            style: const TextStyle(
              color: AppColors.textInverse,
              fontSize: 32,
              fontWeight: FontWeight.w700,
              letterSpacing: -0.5,
            ),
          ),
          const SizedBox(height: 4),
          Row(
            children: [
              Icon(
                isPositive ? Icons.arrow_upward : Icons.arrow_downward,
                color: isPositive ? AppColors.success : AppColors.error,
                size: 14,
              ),
              const SizedBox(width: 4),
              Text(
                isPositive ? 'Positive settlement' : 'Net payable',
                style: AppTextStyles.bodySmall.copyWith(
                  color: AppColors.textInverse.withValues(alpha: 0.75),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _KpiGrid extends StatelessWidget {
  const _KpiGrid({required this.summary});

  final DashboardSummary summary;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Row(
          children: [
            Expanded(
              child: SummaryCard(
                label: 'Gross Revenue',
                value: CurrencyFormatter.formatCompact(summary.grossRevenue),
                icon: Icons.trending_up_outlined,
                iconColor: AppColors.positive,
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: SummaryCard(
                label: 'Total Fees',
                value: CurrencyFormatter.formatCompact(summary.totalFees),
                icon: Icons.account_balance_outlined,
                iconColor: AppColors.negative,
              ),
            ),
          ],
        ),
        const SizedBox(height: 10),
        Row(
          children: [
            Expanded(
              child: SummaryCard(
                label: 'Total Reports',
                value: summary.totalReports.toString(),
                icon: Icons.description_outlined,
                iconColor: AppColors.info,
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: SummaryCard(
                label: 'Total Orders',
                value: _compact(summary.totalOrders),
                icon: Icons.shopping_bag_outlined,
                iconColor: AppColors.primary,
              ),
            ),
          ],
        ),
      ],
    );
  }

  String _compact(int n) {
    if (n >= 100000) return '${(n / 100000).toStringAsFixed(1)}L';
    if (n >= 1000) return '${(n / 1000).toStringAsFixed(1)}K';
    return n.toString();
  }
}

class _MarketplacesSection extends StatelessWidget {
  const _MarketplacesSection({required this.summary});

  final DashboardSummary summary;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('Connected Marketplaces', style: AppTextStyles.titleMedium),
        const SizedBox(height: 10),
        if (summary.connectedMarketplaces.isEmpty)
          Text('No marketplaces connected', style: AppTextStyles.bodySmall)
        else
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: summary.connectedMarketplaces
                .map((m) => MarketplaceBadge(platform: m))
                .toList(),
          ),
      ],
    );
  }
}
