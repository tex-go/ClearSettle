import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_text_styles.dart';
import '../../../../core/utils/currency_formatter.dart';
import '../../../../routing/app_shell.dart';
import '../../domain/entities/settlement_entity.dart';
import '../providers/settlements_provider.dart';

class SettlementsScreen extends ConsumerWidget {
  const SettlementsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state    = ref.watch(settlementsProvider);
    final notifier = ref.read(settlementsProvider.notifier);

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
              _header(context, state),
              _kpiRow(context, state),
              _filters(state, notifier),
              ..._body(context, state),
              const SliverToBoxAdapter(child: SizedBox(height: 24)),
            ],
          ),
        ),
      ),
    );
  }

  // ── Slivers ───────────────────────────────────────────────────────────────

  Widget _header(BuildContext context, SettlementsState state) {
    return SliverToBoxAdapter(
      child: Container(
        padding: const EdgeInsets.fromLTRB(20, 20, 20, 16),
        color: AppColors.primary,
        child: Row(
          children: [
            GestureDetector(
              onTap: AppShell.openDrawer,
              child: Container(
                width: 36,
                height: 36,
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: const Icon(Icons.menu_rounded,
                    size: 18, color: AppColors.textInverse),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Settlement Monitor',
                      style: AppTextStyles.headlineLarge
                          .copyWith(color: AppColors.textInverse)),
                  const SizedBox(height: 2),
                  Text(
                    '${state.mismatchCount} mismatch  ·  '
                    '${state.settlements.length} settlements',
                    style: AppTextStyles.bodySmall.copyWith(
                      color: AppColors.textInverse.withValues(alpha: 0.7),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _kpiRow(BuildContext context, SettlementsState state) {
    final diff     = state.totalDifference;
    final diffColor = diff >= 0 ? AppColors.positive : AppColors.error;

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
              child: _KpiCell(
                label: 'Expected',
                value: CurrencyFormatter.formatCompact(state.totalExpected),
                color: AppColors.textPrimary,
              ),
            ),
            Container(width: 1, height: 36, color: AppColors.divider),
            Expanded(
              child: _KpiCell(
                label: 'Received',
                value: CurrencyFormatter.formatCompact(state.totalReceived),
                color: AppColors.positive,
              ),
            ),
            Container(width: 1, height: 36, color: AppColors.divider),
            Expanded(
              child: _KpiCell(
                label: 'Difference',
                value:
                    '${diff >= 0 ? '+' : ''}${CurrencyFormatter.formatCompact(diff)}',
                color: diffColor,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _filters(SettlementsState state, SettlementsNotifier notifier) {
    const marketplaces = ['', 'Flipkart', 'Amazon', 'Meesho', 'Shopify'];
    const statuses = <SettlementStatus?>[
      null,
      SettlementStatus.mismatch,
      SettlementStatus.pending,
      SettlementStatus.underInvestigation,
      SettlementStatus.matched,
    ];

    return SliverToBoxAdapter(
      child: Column(
        children: [
          // Marketplace chips
          SizedBox(
            height: 44,
            child: ListView.separated(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.fromLTRB(16, 10, 16, 0),
              itemCount: marketplaces.length,
              separatorBuilder: (_, __) => const SizedBox(width: 8),
              itemBuilder: (ctx, i) {
                final mp       = marketplaces[i];
                final selected = (state.filterMarketplace ?? '') == mp;
                final label    = mp.isEmpty ? 'All Platforms' : mp;
                return _FilterChip(
                  label: label,
                  selected: selected,
                  onTap: () =>
                      notifier.setMarketplaceFilter(mp.isEmpty ? null : mp),
                );
              },
            ),
          ),
          // Status chips
          SizedBox(
            height: 44,
            child: ListView.separated(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.fromLTRB(16, 10, 16, 0),
              itemCount: statuses.length,
              separatorBuilder: (_, __) => const SizedBox(width: 8),
              itemBuilder: (ctx, i) {
                final s        = statuses[i];
                final selected = state.filterStatus == s;
                final label    = s?.label ?? 'All Status';
                return _FilterChip(
                  label: label,
                  selected: selected,
                  onTap: () => notifier.setStatusFilter(s),
                );
              },
            ),
          ),
        ],
      ),
    );
  }

  List<Widget> _body(BuildContext context, SettlementsState state) {
    final items = state.filtered;
    if (items.isEmpty) {
      return [const SliverFillRemaining(child: _EmptySettlements())];
    }
    return [
      SliverList(
        delegate: SliverChildBuilderDelegate(
          (ctx, i) => _SettlementTile(settlement: items[i]),
          childCount: items.length,
        ),
      ),
    ];
  }
}

// ── Sub-widgets ───────────────────────────────────────────────────────────────

class _KpiCell extends StatelessWidget {
  const _KpiCell(
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
                fontSize: 16, fontWeight: FontWeight.w700, color: color)),
        const SizedBox(height: 3),
        Text(label,
            style: AppTextStyles.labelSmall,
            textAlign: TextAlign.center),
      ],
    );
  }
}

class _FilterChip extends StatelessWidget {
  const _FilterChip(
      {required this.label,
      required this.selected,
      required this.onTap});

  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
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
            color: selected ? AppColors.textInverse : AppColors.primary,
          ),
        ),
      ),
    );
  }
}

class _SettlementTile extends StatelessWidget {
  const _SettlementTile({required this.settlement});

  final SettlementEntity settlement;

  @override
  Widget build(BuildContext context) {
    final statusColor = _statusColor(settlement.status);
    final diff        = settlement.difference;
    final diffColor   = diff >= 0 ? AppColors.positive : AppColors.error;

    return Container(
      margin: const EdgeInsets.fromLTRB(16, 10, 16, 0),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: settlement.status == SettlementStatus.mismatch
              ? AppColors.error.withValues(alpha: 0.3)
              : AppColors.divider,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header row
          Row(
            children: [
              _Chip(settlement.marketplace, AppColors.primary),
              const SizedBox(width: 8),
              _StatusBadge(settlement.status, statusColor),
              const Spacer(),
              Text(
                _formatDate(settlement.settlementDate),
                style: AppTextStyles.labelSmall,
              ),
            ],
          ),
          const SizedBox(height: 12),
          // Amounts
          Row(
            children: [
              Expanded(
                child: _AmountCol(
                  label: 'Expected',
                  value: CurrencyFormatter.format(settlement.expectedAmount),
                  color: AppColors.textPrimary,
                ),
              ),
              Expanded(
                child: _AmountCol(
                  label: 'Received',
                  value: CurrencyFormatter.format(settlement.receivedAmount),
                  color: AppColors.positive,
                ),
              ),
              Expanded(
                child: _AmountCol(
                  label: 'Diff',
                  value:
                      '${diff >= 0 ? '+' : ''}${CurrencyFormatter.format(diff)}',
                  color: diffColor,
                ),
              ),
            ],
          ),
          // Notes
          if (settlement.notes != null) ...[
            const SizedBox(height: 8),
            const Divider(height: 1),
            const SizedBox(height: 8),
            Row(
              children: [
                Icon(
                  settlement.status == SettlementStatus.mismatch ||
                          settlement.status ==
                              SettlementStatus.underInvestigation
                      ? Icons.warning_amber_outlined
                      : Icons.info_outline,
                  size: 13,
                  color: statusColor,
                ),
                const SizedBox(width: 5),
                Expanded(
                  child: Text(
                    settlement.notes!,
                    style: AppTextStyles.labelSmall.copyWith(
                        color: statusColor, height: 1.4),
                  ),
                ),
              ],
            ),
          ],
          // Settlement ID
          const SizedBox(height: 8),
          Text('Ref: ${settlement.id}',
              style: AppTextStyles.labelSmall),
        ],
      ),
    );
  }

  Color _statusColor(SettlementStatus s) => switch (s) {
        SettlementStatus.matched            => AppColors.positive,
        SettlementStatus.mismatch           => AppColors.error,
        SettlementStatus.pending            => AppColors.warning,
        SettlementStatus.underInvestigation => AppColors.info,
      };

  String _formatDate(DateTime dt) =>
      '${dt.day}/${dt.month}/${dt.year}';
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
      child: Text(label,
          style: AppTextStyles.labelSmall
              .copyWith(color: color, fontWeight: FontWeight.w600)),
    );
  }
}

class _StatusBadge extends StatelessWidget {
  const _StatusBadge(this.status, this.color);
  final SettlementStatus status;
  final Color color;

  @override
  Widget build(BuildContext context) {
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
}

class _AmountCol extends StatelessWidget {
  const _AmountCol(
      {required this.label, required this.value, required this.color});
  final String label;
  final String value;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: AppTextStyles.labelSmall),
        const SizedBox(height: 2),
        Text(value,
            style: TextStyle(
                fontSize: 13, fontWeight: FontWeight.w600, color: color)),
      ],
    );
  }
}

class _EmptySettlements extends StatelessWidget {
  const _EmptySettlements();

  @override
  Widget build(BuildContext context) {
    return const Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.account_balance_wallet_outlined,
              size: 56, color: AppColors.textDisabled),
          SizedBox(height: 16),
          Text('No settlements found',
              style: TextStyle(
                  fontSize: 17,
                  fontWeight: FontWeight.w600,
                  color: AppColors.textPrimary)),
          SizedBox(height: 6),
          Text('Try adjusting your filters.',
              style: TextStyle(color: AppColors.textSecondary)),
        ],
      ),
    );
  }
}
