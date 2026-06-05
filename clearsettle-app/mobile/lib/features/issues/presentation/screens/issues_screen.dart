import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_text_styles.dart';
import '../../../../core/utils/currency_formatter.dart';
import '../../../../shared/widgets/bottom_sheets/sort_bottom_sheet.dart';
import '../../../../shared/widgets/empty_state_widget.dart';
import '../../../../shared/widgets/issue_card.dart';
import '../../../../shared/widgets/skeleton_loader.dart' show SkeletonBox;
import '../../domain/entities/issue_entity.dart';
import '../providers/issues_provider.dart';

/// Issues Center — lists all detected discrepancies.
///
/// Filter tabs: All | Missing Payments | Excess Fees | Pending Claims
/// Sorted by impact amount by default; user can toggle sort direction.
class IssuesScreen extends ConsumerWidget {
  const IssuesScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(issuesProvider);
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      backgroundColor:
          isDark ? AppColors.backgroundDark : AppColors.background,
      body: RefreshIndicator(
        color: AppColors.teal500,
        displacement: 60,
        onRefresh: () => ref.read(issuesProvider.notifier).refresh(),
        child: CustomScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          slivers: [
            _AppBar(onSortTap: () => _showSort(context, ref, state)),
            _FilterTabBar(state: state, ref: ref),
            if (state.isLoading)
              const _SkeletonList()
            else if (state.error != null)
              SliverFillRemaining(
                child: Center(
                  child: Text(state.error!,
                      style: TextStyle(
                          fontFamily: 'Inter',
                          fontSize: 14,
                          color: isDark
                              ? AppColors.textMutedDark
                              : AppColors.textMuted)),
                ),
              )
            else if (state.filteredIssues.isEmpty)
              const SliverFillRemaining(
                child: EmptyStateWidget(
                  icon: Icons.check_circle_outline_rounded,
                  title: 'No issues found',
                  subtitle: 'All detected discrepancies will appear here.',
                ),
              )
            else
              _IssueList(state: state),
          ],
        ),
      ),
    );
  }

  Future<void> _showSort(
      BuildContext context, WidgetRef ref, IssuesState state) async {
    final result = await SortBottomSheet.show(
      context,
      options: const [
        SortOption(label: 'Impact Amount', value: 'amount'),
        SortOption(label: 'Detection Date', value: 'date'),
        SortOption(label: 'Priority', value: 'priority'),
      ],
      selectedValue: state.sortByImpact ? 'amount' : 'date',
    );
    if (result != null) {
      ref.read(issuesProvider.notifier).setSortByImpact(
            high: result.order == SortOrder.descending,
          );
    }
  }
}

// ── App bar ───────────────────────────────────────────────────────────────────

class _AppBar extends StatelessWidget {
  const _AppBar({required this.onSortTap});
  final VoidCallback onSortTap;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final surfColor = isDark ? AppColors.surfaceDark : AppColors.surface;
    final textPrimary = isDark ? AppColors.textPrimaryDark : AppColors.textPrimary;
    final textMuted   = isDark ? AppColors.textMutedDark   : AppColors.textMuted;

    return SliverAppBar(
      pinned: true,
      backgroundColor: surfColor,
      surfaceTintColor: Colors.transparent,
      elevation: 0,
      toolbarHeight: AppSpacing.appBarHeight,
      title: Text('Issues',
          style: TextStyle(
              fontFamily: 'Inter',
              fontSize: 18,
              fontWeight: FontWeight.w600,
              color: textPrimary)),
      centerTitle: false,
      actions: [
        Semantics(
          label: 'Search issues',
          child: IconButton(
            icon: Icon(Icons.search_rounded, color: textMuted),
            onPressed: () {},
          ),
        ),
        Semantics(
          label: 'Sort issues',
          child: IconButton(
            icon: Icon(Icons.sort_rounded, color: textMuted),
            onPressed: onSortTap,
          ),
        ),
      ],
    );
  }
}

// ── Filter tab bar + impact row ────────────────────────────────────────────────

class _FilterTabBar extends StatelessWidget {
  const _FilterTabBar({required this.state, required this.ref});
  final IssuesState state;
  final WidgetRef ref;

  static const _filters = [
    IssueFilter.all,
    IssueFilter.missing,
    IssueFilter.excessFee,
    IssueFilter.pendingClaim,
  ];

  static const _labels = ['All', 'Missing', 'Excess Fees', 'Pending'];

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final surfColor   = isDark ? AppColors.surfaceDark : AppColors.surface;
    final borderColor = isDark ? AppColors.borderDark  : AppColors.border;
    final textPrimary = isDark ? AppColors.textPrimaryDark : AppColors.textPrimary;
    final textMuted   = isDark ? AppColors.textMutedDark   : AppColors.textMuted;

    return SliverToBoxAdapter(
      child: Container(
        color: surfColor,
        child: Column(
          children: [
            // Filter tabs
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(
                  horizontal: AppSpacing.pageHorizontal),
              child: Row(
                children: List.generate(_filters.length, (i) {
                  final f = _filters[i];
                  final isActive = state.filter == f;
                  final count = state.countFor(f);
                  return _FilterTab(
                    label: _labels[i],
                    count: count,
                    isActive: isActive,
                    onTap: () =>
                        ref.read(issuesProvider.notifier).setFilter(f),
                    textPrimary: textPrimary,
                    textMuted: textMuted,
                  );
                }),
              ),
            ),

            // Impact summary row
            Container(
              padding: const EdgeInsets.fromLTRB(
                  AppSpacing.pageHorizontal, 10,
                  AppSpacing.pageHorizontal, 12),
              decoration: BoxDecoration(
                border: Border(bottom: BorderSide(color: borderColor)),
              ),
              child: Row(
                children: [
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Total Impact',
                          style: TextStyle(
                              fontFamily: 'Inter',
                              fontSize: 11,
                              color: textMuted)),
                      Semantics(
                        label: 'Total impact amount: '
                            '${CurrencyFormatter.format(state.totalImpact)} rupees',
                        child: Text(
                          CurrencyFormatter.format(state.totalImpact),
                          style: TextStyle(
                            fontFamily: 'Inter',
                            fontSize: 20,
                            fontWeight: FontWeight.w700,
                            color: textPrimary,
                            fontFeatures: const [FontFeature.tabularFigures()],
                          ),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _FilterTab extends StatelessWidget {
  const _FilterTab({
    required this.label,
    required this.count,
    required this.isActive,
    required this.onTap,
    required this.textPrimary,
    required this.textMuted,
  });

  final String label;
  final int count;
  final bool isActive;
  final VoidCallback onTap;
  final Color textPrimary, textMuted;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label: '$label, $count issues',
      selected: isActive,
      child: GestureDetector(
        onTap: onTap,
        child: Container(
          margin: const EdgeInsets.only(right: 20, bottom: 0),
          padding: const EdgeInsets.symmetric(vertical: 12),
          decoration: BoxDecoration(
            border: Border(
              bottom: BorderSide(
                color: isActive ? AppColors.teal500 : Colors.transparent,
                width: 2,
              ),
            ),
          ),
          child: Text(
            count > 0 ? '$label ($count)' : label,
            style: TextStyle(
              fontFamily: 'Inter',
              fontSize: 13,
              fontWeight: isActive ? FontWeight.w600 : FontWeight.w400,
              color: isActive ? AppColors.teal500 : textMuted,
            ),
          ),
        ),
      ),
    );
  }
}

// ── Issue list ────────────────────────────────────────────────────────────────

class _IssueList extends StatelessWidget {
  const _IssueList({required this.state});
  final IssuesState state;

  static const _marketplaceColors = {
    'amazon':   AppColors.amazon,
    'flipkart': AppColors.flipkart,
    'meesho':   AppColors.meesho,
    'myntra':   AppColors.myntra,
  };

  @override
  Widget build(BuildContext context) {
    final issues = state.filteredIssues;
    return SliverPadding(
      padding: const EdgeInsets.fromLTRB(
          AppSpacing.pageHorizontal, 12,
          AppSpacing.pageHorizontal, 32),
      sliver: SliverList.separated(
        itemCount: issues.length,
        separatorBuilder: (_, __) =>
            const SizedBox(height: AppSpacing.cardGap),
        itemBuilder: (context, i) {
          final issue = issues[i];
          final color = _marketplaceColors[issue.marketplaceId] ??
              AppColors.neutral;
          return IssueCard(
            marketplace: issue.marketplace,
            marketplaceColor: color,
            issueType: issue.typeLabel,
            amount: issue.amount,
            detailLabel: issue.detailLabel,
            detailValue: issue.detailValue,
            detectedOn:
                'Detected on ${DateFormat('d MMM yyyy').format(issue.detectedAt)}',
            priority: issue.priority,
          );
        },
      ),
    );
  }
}

// ── Skeleton loading ──────────────────────────────────────────────────────────

class _SkeletonList extends StatelessWidget {
  const _SkeletonList();

  @override
  Widget build(BuildContext context) {
    return SliverPadding(
      padding: const EdgeInsets.fromLTRB(
          AppSpacing.pageHorizontal, 12,
          AppSpacing.pageHorizontal, 32),
      sliver: SliverList.separated(
        itemCount: 5,
        separatorBuilder: (_, __) =>
            const SizedBox(height: AppSpacing.cardGap),
        itemBuilder: (_, __) => const _IssueCardSkeleton(),
      ),
    );
  }
}

class _IssueCardSkeleton extends StatelessWidget {
  const _IssueCardSkeleton();

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final bg = isDark ? AppColors.surfaceDark : AppColors.surface;
    return Container(
      height: 94,
      padding: const EdgeInsets.all(AppSpacing.cardPadding),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
            color: isDark ? AppColors.borderDark : AppColors.border),
      ),
      child: const SkeletonBox(width: double.infinity, height: 62, radius: 8),
    );
  }
}
