import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/constants/app_constants.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_text_styles.dart';
import '../../domain/entities/analytics_entity.dart';
import '../providers/analytics_provider.dart';

class AnalyticsFilterBar extends ConsumerWidget {
  const AnalyticsFilterBar({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final filter = ref.watch(analyticsFilterProvider);
    final notifier = ref.read(analyticsFilterProvider.notifier);

    return Container(
      color: Theme.of(context).colorScheme.surface,
      child: Column(
        children: [
          // Date range row
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            child: Row(
              children: DateRangeFilter.values.map((range) {
                final selected = filter.dateRange == range;
                return Padding(
                  padding: const EdgeInsets.only(right: 6),
                  child: _Chip(
                    label: _dateLabel(range),
                    selected: selected,
                    onTap: () => notifier.setDateRange(range),
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
                _Chip(
                  label: filter.marketplace != null
                      ? AppConstants.marketplaceDisplayNames[filter.marketplace] ??
                          filter.marketplace!
                      : 'All Markets',
                  selected: filter.marketplace != null,
                  onTap: () => _showMarketplacePicker(context, ref, filter),
                ),
                const SizedBox(width: 6),
                _Chip(
                  label: _settlementLabel(filter.settlementStatus),
                  selected: filter.settlementStatus != SettlementFilter.all,
                  onTap: () => _cycleSettlement(notifier, filter),
                ),
                const SizedBox(width: 6),
                _Chip(
                  label: _discrepancyLabel(filter.discrepancyStatus),
                  selected: filter.discrepancyStatus != DiscrepancyFilter.all,
                  onTap: () => _cycleDiscrepancy(notifier, filter),
                ),
                const SizedBox(width: 6),
                if (_hasActiveFilter(filter))
                  _Chip(
                    label: '✕ Clear',
                    selected: false,
                    onTap: notifier.reset,
                    isReset: true,
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  bool _hasActiveFilter(AnalyticsFilter f) =>
      f.marketplace != null ||
      f.settlementStatus != SettlementFilter.all ||
      f.discrepancyStatus != DiscrepancyFilter.all ||
      f.dateRange != DateRangeFilter.last6Months;

  String _dateLabel(DateRangeFilter r) {
    switch (r) {
      case DateRangeFilter.last7Days:
        return '7D';
      case DateRangeFilter.last30Days:
        return '30D';
      case DateRangeFilter.last3Months:
        return '3M';
      case DateRangeFilter.last6Months:
        return '6M';
      case DateRangeFilter.allTime:
        return 'All';
    }
  }

  String _settlementLabel(SettlementFilter f) {
    switch (f) {
      case SettlementFilter.all:
        return 'All Settlements';
      case SettlementFilter.settled:
        return 'Settled';
      case SettlementFilter.pending:
        return 'Pending';
    }
  }

  String _discrepancyLabel(DiscrepancyFilter f) {
    switch (f) {
      case DiscrepancyFilter.all:
        return 'All Reports';
      case DiscrepancyFilter.hasIssues:
        return 'Has Issues';
      case DiscrepancyFilter.clean:
        return 'Clean';
    }
  }

  void _cycleSettlement(
      AnalyticsFilterNotifier notifier, AnalyticsFilter filter) {
    final next = SettlementFilter.values[
        (filter.settlementStatus.index + 1) % SettlementFilter.values.length];
    notifier.setSettlement(next);
  }

  void _cycleDiscrepancy(
      AnalyticsFilterNotifier notifier, AnalyticsFilter filter) {
    final next = DiscrepancyFilter.values[
        (filter.discrepancyStatus.index + 1) % DiscrepancyFilter.values.length];
    notifier.setDiscrepancy(next);
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
}

class _Chip extends StatelessWidget {
  const _Chip({
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
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
        decoration: BoxDecoration(
          color: selected
              ? AppColors.primary.withValues(alpha: 0.12)
              : isReset
                  ? AppColors.error.withValues(alpha: 0.08)
                  : Theme.of(context).colorScheme.surfaceContainerHighest,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: selected
                ? AppColors.primary
                : isReset
                    ? AppColors.error.withValues(alpha: 0.4)
                    : AppColors.divider,
          ),
        ),
        child: Text(
          label,
          style: AppTextStyles.labelMedium.copyWith(
            color: selected
                ? AppColors.primary
                : isReset
                    ? AppColors.error
                    : Theme.of(context).colorScheme.onSurface,
          ),
        ),
      ),
    );
  }
}
