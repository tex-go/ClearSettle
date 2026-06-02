import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/constants/app_constants.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_text_styles.dart';
import '../../domain/entities/analytics_entity.dart';
import '../providers/analytics_provider.dart';

class AnalyticsFilterBar extends ConsumerWidget {
  const AnalyticsFilterBar({super.key});

  static const _dateFilters = [
    (DateRangeFilter.today, 'Today'),
    (DateRangeFilter.yesterday, 'Yesterday'),
    (DateRangeFilter.last7Days, '7D'),
    (DateRangeFilter.last30Days, '30D'),
    (DateRangeFilter.thisMonth, 'This Month'),
    (DateRangeFilter.lastMonth, 'Last Month'),
    (DateRangeFilter.last6Months, '6M'),
    (DateRangeFilter.allTime, 'All'),
    (DateRangeFilter.custom, 'Custom…'),
  ];

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final filter = ref.watch(analyticsFilterProvider);
    final notifier = ref.read(analyticsFilterProvider.notifier);

    return Container(
      color: Theme.of(context).colorScheme.surface,
      child: Column(
        children: [
          // Date range chips
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            child: Row(
              children: _dateFilters.map((entry) {
                final (range, label) = entry;
                final selected = filter.dateRange == range;
                return Padding(
                  padding: const EdgeInsets.only(right: 6),
                  child: _FilterChip(
                    label: selected && range == DateRangeFilter.custom
                        ? filter.label
                        : label,
                    selected: selected,
                    onTap: () => range == DateRangeFilter.custom
                        ? _pickCustomRange(context, ref, notifier, filter)
                        : notifier.setDateRange(range),
                  ),
                );
              }).toList(),
            ),
          ),
          // Marketplace + status row
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            padding: const EdgeInsets.fromLTRB(12, 0, 12, 8),
            child: Row(
              children: [
                _FilterChip(
                  label: filter.marketplace != null
                      ? AppConstants.marketplaceDisplayNames[filter.marketplace] ??
                          filter.marketplace!
                      : 'All Markets',
                  selected: filter.marketplace != null,
                  onTap: () => _showMarketplacePicker(context, ref, filter),
                ),
                const SizedBox(width: 6),
                _FilterChip(
                  label: _settlementLabel(filter.settlementStatus),
                  selected: filter.settlementStatus != SettlementFilter.all,
                  onTap: () => notifier.setSettlement(
                    SettlementFilter.values[
                        (filter.settlementStatus.index + 1) %
                            SettlementFilter.values.length],
                  ),
                ),
                const SizedBox(width: 6),
                _FilterChip(
                  label: _discrepancyLabel(filter.discrepancyStatus),
                  selected: filter.discrepancyStatus != DiscrepancyFilter.all,
                  onTap: () => notifier.setDiscrepancy(
                    DiscrepancyFilter.values[
                        (filter.discrepancyStatus.index + 1) %
                            DiscrepancyFilter.values.length],
                  ),
                ),
                if (notifier.hasActiveFilter) ...[
                  const SizedBox(width: 6),
                  _FilterChip(
                    label: '✕ Clear',
                    selected: false,
                    onTap: notifier.reset,
                    isReset: true,
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _pickCustomRange(
    BuildContext context,
    WidgetRef ref,
    AnalyticsFilterNotifier notifier,
    AnalyticsFilter current,
  ) async {
    final now = DateTime.now();
    final picked = await showDateRangePicker(
      context: context,
      firstDate: DateTime(2020),
      lastDate: now,
      initialDateRange: current.dateRange == DateRangeFilter.custom &&
              current.customStart != null
          ? DateTimeRange(
              start: current.customStart!,
              end: current.customEnd ?? now,
            )
          : DateTimeRange(
              start: now.subtract(const Duration(days: 29)),
              end: now,
            ),
      builder: (ctx, child) => Theme(
        data: Theme.of(ctx).copyWith(
          colorScheme: Theme.of(ctx).colorScheme.copyWith(
                primary: AppColors.primary,
              ),
        ),
        child: child!,
      ),
    );
    if (picked != null) {
      notifier.setCustomDateRange(picked.start, picked.end);
    }
  }

  void _showMarketplacePicker(
    BuildContext context,
    WidgetRef ref,
    AnalyticsFilter filter,
  ) {
    final notifier = ref.read(analyticsFilterProvider.notifier);
    final options = ['All', ...AppConstants.marketplaceDisplayNames.keys];
    showModalBottomSheet<void>(
      context: context,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
      ),
      builder: (_) => ListView.separated(
        shrinkWrap: true,
        padding: const EdgeInsets.symmetric(vertical: 12),
        itemCount: options.length,
        separatorBuilder: (_, __) => const Divider(height: 1),
        itemBuilder: (ctx, i) {
          final key = options[i] == 'All' ? null : options[i];
          final name = key == null
              ? 'All Marketplaces'
              : AppConstants.marketplaceDisplayNames[key] ?? key;
          final selected = filter.marketplace == key;
          return ListTile(
            title: Text(name),
            trailing: selected ? const Icon(Icons.check) : null,
            onTap: () {
              notifier.setMarketplace(key);
              Navigator.of(ctx).pop();
            },
          );
        },
      ),
    );
  }

  String _settlementLabel(SettlementFilter f) => switch (f) {
        SettlementFilter.all => 'All Settlements',
        SettlementFilter.settled => 'Settled',
        SettlementFilter.pending => 'Pending',
      };

  String _discrepancyLabel(DiscrepancyFilter f) => switch (f) {
        DiscrepancyFilter.all => 'All Reports',
        DiscrepancyFilter.hasIssues => 'Has Issues',
        DiscrepancyFilter.clean => 'Clean',
      };
}

class _FilterChip extends StatelessWidget {
  const _FilterChip({
    required this.label,
    required this.selected,
    required this.onTap,
    this.isReset = false,
  });

  final String label;
  final bool selected;
  final VoidCallback onTap;
  final bool isReset;

  @override
  Widget build(BuildContext context) {
    final bg = selected
        ? AppColors.primary.withValues(alpha: 0.12)
        : isReset
            ? AppColors.error.withValues(alpha: 0.08)
            : Theme.of(context).colorScheme.surfaceContainerHighest;
    final border = selected
        ? AppColors.primary
        : isReset
            ? AppColors.error.withValues(alpha: 0.4)
            : AppColors.divider;
    final textColor = selected
        ? AppColors.primary
        : isReset
            ? AppColors.error
            : Theme.of(context).colorScheme.onSurface;

    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
        decoration: BoxDecoration(
          color: bg,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: border),
        ),
        child: Text(
          label,
          style: AppTextStyles.labelMedium.copyWith(color: textColor),
        ),
      ),
    );
  }
}
