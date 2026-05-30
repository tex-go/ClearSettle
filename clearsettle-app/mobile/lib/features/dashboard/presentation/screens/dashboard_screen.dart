import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

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
      backgroundColor: AppColors.backgroundLight,
      body: SafeArea(
        child: RefreshIndicator(
          color: AppColors.primary,
          onRefresh: () => ref.read(dashboardProvider.notifier).refresh(),
          child: CustomScrollView(
            physics: const AlwaysScrollableScrollPhysics(),
            slivers: [
              _buildAppBar(authState),
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
                    ? SliverFillRemaining(
                        child: EmptyStateWidget(
                          icon: Icons.dashboard_outlined,
                          title: 'No data yet',
                          subtitle:
                              'Connect a marketplace to see your settlement summary.',
                        ),
                      )
                    : _buildContent(summary),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildAppBar(dynamic authState) {
    return SliverToBoxAdapter(
      child: Container(
        padding: const EdgeInsets.fromLTRB(20, 20, 20, 16),
        decoration: const BoxDecoration(
          color: AppColors.primary,
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        _getGreeting(),
                        style: AppTextStyles.bodyMedium.copyWith(
                          color: AppColors.textInverse.withOpacity(0.75),
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        authState is dynamic && authState.isAuthenticated
                            ? (authState as dynamic).sellerName
                            : 'Seller',
                        style: AppTextStyles.headlineLarge.copyWith(
                          color: AppColors.textInverse,
                        ),
                      ),
                    ],
                  ),
                ),
                Container(
                  width: 40,
                  height: 40,
                  decoration: BoxDecoration(
                    color: AppColors.textInverse.withOpacity(0.1),
                    shape: BoxShape.circle,
                  ),
                  child: const Icon(
                    Icons.notifications_outlined,
                    color: AppColors.textInverse,
                    size: 22,
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildContent(DashboardSummary summary) {
    return SliverPadding(
      padding: const EdgeInsets.all(16),
      sliver: SliverList(
        delegate: SliverChildListDelegate([
          if (summary.isFromCache) _buildOfflineBanner(summary.lastSync),
          if (summary.isFromCache) const SizedBox(height: 12),
          _buildOrgCard(summary),
          const SizedBox(height: 16),
          _buildNetSettlementCard(summary),
          const SizedBox(height: 16),
          _buildStatsRow(summary),
          const SizedBox(height: 20),
          _buildMarketplacesSection(summary),
          const SizedBox(height: 24),
        ]),
      ),
    );
  }

  Widget _buildOfflineBanner(DateTime? lastSync) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: AppColors.warning.withOpacity(0.1),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppColors.warning.withOpacity(0.3)),
      ),
      child: Row(
        children: [
          const Icon(Icons.cloud_off_outlined, color: AppColors.warning, size: 16),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              DateFormatter.formatLastSync(lastSync),
              style: AppTextStyles.bodySmall.copyWith(color: AppColors.warning),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildOrgCard(DashboardSummary summary) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.divider),
      ),
      child: Row(
        children: [
          Container(
            width: 42,
            height: 42,
            decoration: BoxDecoration(
              color: AppColors.primary.withOpacity(0.1),
              borderRadius: BorderRadius.circular(10),
            ),
            child: const Icon(Icons.store_outlined, color: AppColors.primary, size: 22),
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
                Text(
                  summary.sellerName,
                  style: AppTextStyles.bodySmall,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildNetSettlementCard(DashboardSummary summary) {
    final isPositive = summary.netSettlement >= 0;
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            AppColors.primary,
            AppColors.primaryLight,
          ],
        ),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Net Settlement',
            style: AppTextStyles.bodyMedium.copyWith(
              color: AppColors.textInverse.withOpacity(0.8),
            ),
          ),
          const SizedBox(height: 8),
          Text(
            CurrencyFormatter.format(summary.netSettlement),
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
                color: isPositive
                    ? AppColors.success
                    : AppColors.error,
                size: 14,
              ),
              const SizedBox(width: 4),
              Text(
                isPositive ? 'Positive settlement' : 'Net payable',
                style: AppTextStyles.bodySmall.copyWith(
                  color: AppColors.textInverse.withOpacity(0.75),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildStatsRow(DashboardSummary summary) {
    return Row(
      children: [
        Expanded(
          child: SummaryCard(
            label: 'Uploaded Reports',
            value: summary.totalReports.toString(),
            icon: Icons.description_outlined,
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: SummaryCard(
            label: 'Total Orders',
            value: _formatCount(summary.totalOrders),
            icon: Icons.shopping_bag_outlined,
          ),
        ),
      ],
    );
  }

  Widget _buildMarketplacesSection(DashboardSummary summary) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('Connected Marketplaces', style: AppTextStyles.titleMedium),
        const SizedBox(height: 10),
        if (summary.connectedMarketplaces.isEmpty)
          Text(
            'No marketplaces connected',
            style: AppTextStyles.bodySmall,
          )
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

  String _getGreeting() {
    final hour = DateTime.now().hour;
    if (hour < 12) return 'Good morning,';
    if (hour < 17) return 'Good afternoon,';
    return 'Good evening,';
  }

  String _formatCount(int count) {
    if (count >= 100000) return '${(count / 100000).toStringAsFixed(1)}L';
    if (count >= 1000) return '${(count / 1000).toStringAsFixed(1)}K';
    return count.toString();
  }
}
