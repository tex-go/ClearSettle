import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/constants/route_constants.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_text_styles.dart';
import '../../../../core/utils/currency_formatter.dart';
import '../../domain/entities/dispute_entity.dart';
import '../providers/disputes_provider.dart';

class DisputesScreen extends ConsumerWidget {
  const DisputesScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state    = ref.watch(disputesProvider);
    final notifier = ref.read(disputesProvider.notifier);

    if (state.isLoading) {
      return const Scaffold(
        body: Center(child: CircularProgressIndicator()),
      );
    }

    return Scaffold(
      backgroundColor: Theme.of(context).scaffoldBackgroundColor,
      body: SafeArea(
        child: RefreshIndicator(
          color: AppColors.primary,
          onRefresh: notifier.refresh,
          child: CustomScrollView(
            physics: const AlwaysScrollableScrollPhysics(),
            slivers: [
              _header(state),
              _summaryBanner(context, state),
              _filterBar(state, notifier),
              ..._body(context, state),
              const SliverToBoxAdapter(child: SizedBox(height: 24)),
            ],
          ),
        ),
      ),
    );
  }

  // ── Sliver helpers ────────────────────────────────────────────────────────

  Widget _header(DisputesState state) {
    return SliverToBoxAdapter(
      child: Container(
        padding: const EdgeInsets.fromLTRB(20, 20, 20, 16),
        color: AppColors.primary,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Dispute Tracking',
              style: AppTextStyles.headlineLarge.copyWith(
                  color: AppColors.textInverse),
            ),
            const SizedBox(height: 2),
            Text(
              '${state.openCount} open  ·  ${state.disputes.length} total',
              style: AppTextStyles.bodySmall.copyWith(
                color: AppColors.textInverse.withValues(alpha: 0.7),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _summaryBanner(BuildContext context, DisputesState state) {
    return SliverToBoxAdapter(
      child: Container(
        margin: const EdgeInsets.fromLTRB(16, 16, 16, 0),
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surface,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: AppColors.divider),
        ),
        child: Row(
          children: [
            Expanded(
              child: _StatCell(
                label: 'Total Claimed',
                value: CurrencyFormatter.formatCompact(state.totalClaimAmount),
                color: AppColors.warning,
              ),
            ),
            Container(width: 1, height: 36, color: AppColors.divider),
            Expanded(
              child: _StatCell(
                label: 'Recovered',
                value: CurrencyFormatter.formatCompact(
                    state.totalRecoveredAmount),
                color: AppColors.positive,
              ),
            ),
            Container(width: 1, height: 36, color: AppColors.divider),
            Expanded(
              child: _StatCell(
                label: 'Pending',
                value: CurrencyFormatter.formatCompact(
                    state.totalClaimAmount - state.totalRecoveredAmount),
                color: AppColors.info,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _filterBar(DisputesState state, DisputesNotifier notifier) {
    const statuses = <DisputeStatus?>[
      null,
      DisputeStatus.submitted,
      DisputeStatus.inReview,
      DisputeStatus.accepted,
      DisputeStatus.recovered,
      DisputeStatus.rejected,
      DisputeStatus.draft,
    ];
    return SliverToBoxAdapter(
      child: SizedBox(
        height: 46,
        child: ListView.separated(
          scrollDirection: Axis.horizontal,
          padding: const EdgeInsets.fromLTRB(16, 10, 16, 0),
          itemCount: statuses.length,
          separatorBuilder: (_, __) => const SizedBox(width: 8),
          itemBuilder: (ctx, i) {
            final s        = statuses[i];
            final selected = state.filterStatus == s;
            final label    = s?.label ?? 'All';
            return GestureDetector(
              onTap: () => notifier.setStatusFilter(s),
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 200),
                padding: const EdgeInsets.symmetric(
                    horizontal: 14, vertical: 6),
                decoration: BoxDecoration(
                  color: selected
                      ? AppColors.primary
                      : AppColors.primary.withValues(alpha: 0.08),
                  borderRadius: BorderRadius.circular(20),
                ),
                child: Text(
                  label,
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                    color: selected
                        ? AppColors.textInverse
                        : AppColors.primary,
                  ),
                ),
              ),
            );
          },
        ),
      ),
    );
  }

  List<Widget> _body(BuildContext context, DisputesState state) {
    if (state.filtered.isEmpty) {
      return [
        const SliverFillRemaining(child: _EmptyDisputes()),
      ];
    }
    return [
      SliverList(
        delegate: SliverChildBuilderDelegate(
          (ctx, i) {
            final d = state.filtered[i];
            return _DisputeTile(
              dispute: d,
              onTap: () =>
                  context.push(RouteConstants.disputeDetailPath(d.id)),
            );
          },
          childCount: state.filtered.length,
        ),
      ),
    ];
  }
}

// ── Sub-widgets ───────────────────────────────────────────────────────────────

class _StatCell extends StatelessWidget {
  const _StatCell(
      {required this.label, required this.value, required this.color});

  final String label;
  final String value;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Text(value,
            style: TextStyle(
                fontSize: 17, fontWeight: FontWeight.w700, color: color)),
        const SizedBox(height: 3),
        Text(label,
            style: AppTextStyles.labelSmall,
            textAlign: TextAlign.center),
      ],
    );
  }
}

class _DisputeTile extends StatelessWidget {
  const _DisputeTile({required this.dispute, required this.onTap});

  final DisputeEntity dispute;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        margin: const EdgeInsets.fromLTRB(16, 10, 16, 0),
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surface,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: AppColors.divider),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                _Chip(dispute.marketplace, AppColors.primary),
                const SizedBox(width: 8),
                _StatusChip(dispute.status),
                const Spacer(),
                Text(
                  CurrencyFormatter.format(dispute.claimAmount),
                  style: AppTextStyles.bodyMedium
                      .copyWith(fontWeight: FontWeight.w700),
                ),
              ],
            ),
            const SizedBox(height: 10),
            Text('Order ${dispute.orderId}',
                style: AppTextStyles.bodyMedium
                    .copyWith(fontWeight: FontWeight.w600)),
            const SizedBox(height: 4),
            Text(
              dispute.reason,
              style: AppTextStyles.bodySmall.copyWith(height: 1.4),
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
            if (dispute.recoveredAmount > 0) ...[
              const SizedBox(height: 8),
              Row(
                children: [
                  const Icon(Icons.check_circle_outline,
                      color: AppColors.positive, size: 14),
                  const SizedBox(width: 4),
                  Text(
                    '${CurrencyFormatter.format(dispute.recoveredAmount)} recovered',
                    style: AppTextStyles.labelSmall
                        .copyWith(color: AppColors.positive),
                  ),
                ],
              ),
            ],
            const SizedBox(height: 8),
            Row(
              children: [
                Text('ID: ${dispute.id}',
                    style: AppTextStyles.labelSmall),
                const Spacer(),
                Text(_formatDate(dispute.updatedAt),
                    style: AppTextStyles.labelSmall),
                const SizedBox(width: 4),
                const Icon(Icons.chevron_right,
                    color: AppColors.textDisabled, size: 16),
              ],
            ),
          ],
        ),
      ),
    );
  }

  String _formatDate(DateTime dt) {
    final diff = DateTime.now().difference(dt).inDays;
    if (diff == 0) return 'Today';
    if (diff == 1) return 'Yesterday';
    return '${dt.day}/${dt.month}/${dt.year}';
  }
}

class _Chip extends StatelessWidget {
  const _Chip(this.label, this.color);
  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(6),
      ),
      child: Text(
        label,
        style: AppTextStyles.labelSmall
            .copyWith(color: color, fontWeight: FontWeight.w600),
      ),
    );
  }
}

class _StatusChip extends StatelessWidget {
  const _StatusChip(this.status);
  final DisputeStatus status;

  @override
  Widget build(BuildContext context) {
    final color = _color(status);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(6),
      ),
      child: Text(
        status.label,
        style: AppTextStyles.labelSmall
            .copyWith(color: color, fontWeight: FontWeight.w600),
      ),
    );
  }

  Color _color(DisputeStatus s) => switch (s) {
        DisputeStatus.draft     => AppColors.textSecondary,
        DisputeStatus.submitted => AppColors.info,
        DisputeStatus.inReview  => AppColors.warning,
        DisputeStatus.accepted  => AppColors.positive,
        DisputeStatus.rejected  => AppColors.error,
        DisputeStatus.recovered => AppColors.accent,
      };
}

class _EmptyDisputes extends StatelessWidget {
  const _EmptyDisputes();

  @override
  Widget build(BuildContext context) {
    return const Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.gavel_outlined, size: 56, color: AppColors.textDisabled),
          SizedBox(height: 16),
          Text('No disputes found',
              style: TextStyle(
                  fontSize: 17,
                  fontWeight: FontWeight.w600,
                  color: AppColors.textPrimary)),
          SizedBox(height: 6),
          Text('No disputes match the selected filter.',
              style: TextStyle(color: AppColors.textSecondary)),
        ],
      ),
    );
  }
}
