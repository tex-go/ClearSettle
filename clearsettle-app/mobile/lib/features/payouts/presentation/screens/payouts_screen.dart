import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_text_styles.dart';
import '../../../../core/utils/currency_formatter.dart';
import '../../../../shared/widgets/empty_state_widget.dart';
import '../../../../shared/widgets/skeleton_loader.dart' show SkeletonBox;
import '../../domain/entities/payout_entity.dart';
import '../providers/payouts_provider.dart';

/// Payouts screen — next payout card + paginated payout history.
class PayoutsScreen extends ConsumerWidget {
  const PayoutsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state   = ref.watch(payoutsProvider);
    final isDark  = Theme.of(context).brightness == Brightness.dark;
    final bgColor = isDark ? AppColors.backgroundDark : AppColors.background;

    return Scaffold(
      backgroundColor: bgColor,
      appBar: _buildAppBar(isDark),
      body: RefreshIndicator(
        color: AppColors.teal500,
        displacement: 60,
        onRefresh: () => ref.read(payoutsProvider.notifier).refresh(),
        child: state.isLoading
            ? const _PayoutsSkeleton()
            : state.error != null
                ? const Center(
                    child: EmptyStateWidget(
                      icon: Icons.error_outline,
                      title: 'Failed to load payouts',
                      subtitle: 'Pull down to retry.',
                    ),
                  )
                : _PayoutsBody(state: state, isDark: isDark),
      ),
    );
  }

  AppBar _buildAppBar(bool isDark) {
    return AppBar(
      backgroundColor: isDark ? AppColors.surfaceDark : AppColors.surface,
      surfaceTintColor: Colors.transparent,
      elevation: 0,
      toolbarHeight: AppSpacing.appBarHeight,
      title: Text('Payouts',
          style: TextStyle(
              fontFamily: 'Inter', fontSize: 18, fontWeight: FontWeight.w600,
              color: isDark ? AppColors.textPrimaryDark : AppColors.textPrimary)),
      centerTitle: false,
    );
  }
}

// ── Payouts body ──────────────────────────────────────────────────────────────

class _PayoutsBody extends StatelessWidget {
  const _PayoutsBody({required this.state, required this.isDark});
  final PayoutsState state;
  final bool isDark;

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.fromLTRB(
          AppSpacing.pageHorizontal, 16,
          AppSpacing.pageHorizontal, 32),
      children: [
        _NextPayoutCard(state: state, isDark: isDark),
        const SizedBox(height: AppSpacing.sectionGap),
        _HistorySection(history: state.history, isDark: isDark),
      ],
    );
  }
}

// ── Next payout card ──────────────────────────────────────────────────────────

class _NextPayoutCard extends StatelessWidget {
  const _NextPayoutCard({required this.state, required this.isDark});
  final PayoutsState state;
  final bool isDark;

  @override
  Widget build(BuildContext context) {
    final surfColor   = isDark ? AppColors.surfaceDark : AppColors.surface;
    final borderColor = isDark ? AppColors.borderDark  : AppColors.border;
    final textPrimary = isDark ? AppColors.textPrimaryDark : AppColors.textPrimary;
    final textMuted   = isDark ? AppColors.textMutedDark   : AppColors.textMuted;

    final dateStr = state.nextPayoutDate != null
        ? DateFormat('d MMM yyyy').format(state.nextPayoutDate!)
        : '—';

    return Semantics(
      label: 'Next payout: ${CurrencyFormatter.format(state.nextPayoutAmount)} '
          'expected on $dateStr',
      child: Container(
        padding: const EdgeInsets.all(AppSpacing.cardPadding),
        decoration: BoxDecoration(
          color: surfColor,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: borderColor),
          boxShadow: AppShadows.card,
        ),
        child: Row(
          children: [
            // Calendar icon
            Container(
              width: 48, height: 48,
              decoration: BoxDecoration(
                color: AppColors.teal500.withValues(alpha: 0.12),
                shape: BoxShape.circle,
              ),
              child: const Icon(Icons.calendar_today_rounded,
                  color: AppColors.teal500, size: 22),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Next Payout',
                      style: TextStyle(fontFamily: 'Inter',
                          fontSize: 11, color: textMuted)),
                  const SizedBox(height: 3),
                  Text(CurrencyFormatter.format(state.nextPayoutAmount),
                      style: TextStyle(
                        fontFamily: 'Inter', fontSize: 26,
                        fontWeight: FontWeight.w700, color: textPrimary,
                        fontFeatures: const [FontFeature.tabularFigures()],
                      )),
                  const SizedBox(height: 2),
                  Text('Expected on $dateStr',
                      style: TextStyle(fontFamily: 'Inter',
                          fontSize: 12, color: textMuted)),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ── Payout history section ────────────────────────────────────────────────────

class _HistorySection extends StatelessWidget {
  const _HistorySection({required this.history, required this.isDark});
  final List<PayoutEntity> history;
  final bool isDark;

  @override
  Widget build(BuildContext context) {
    final textPrimary = isDark ? AppColors.textPrimaryDark : AppColors.textPrimary;
    final textMuted   = isDark ? AppColors.textMutedDark   : AppColors.textMuted;
    final surfColor   = isDark ? AppColors.surfaceDark : AppColors.surface;
    final borderColor = isDark ? AppColors.borderDark  : AppColors.border;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Text('Payout History',
                style: TextStyle(fontFamily: 'Inter', fontSize: 16,
                    fontWeight: FontWeight.w600, color: textPrimary)),
            const Spacer(),
            TextButton(
              onPressed: () {},
              child: const Text('View All',
                  style: TextStyle(
                      fontFamily: 'Inter', fontSize: 13,
                      color: AppColors.teal500)),
            ),
          ],
        ),
        const SizedBox(height: 8),
        if (history.isEmpty)
          const EmptyStateWidget(
            icon: Icons.receipt_long_outlined,
            title: 'No payout history',
            subtitle: 'Your past payouts will appear here.',
          )
        else
          Container(
            decoration: BoxDecoration(
              color: surfColor,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: borderColor),
              boxShadow: AppShadows.card,
            ),
            child: Column(
              children: List.generate(history.length, (i) {
                final p = history[i];
                final isLast = i == history.length - 1;
                return _PayoutRow(
                  payout: p,
                  isDark: isDark,
                  showDivider: !isLast,
                  textPrimary: textPrimary,
                  textMuted: textMuted,
                );
              }),
            ),
          ),
      ],
    );
  }
}

class _PayoutRow extends StatelessWidget {
  const _PayoutRow({
    required this.payout,
    required this.isDark,
    required this.showDivider,
    required this.textPrimary,
    required this.textMuted,
  });

  final PayoutEntity payout;
  final bool isDark, showDivider;
  final Color textPrimary, textMuted;

  @override
  Widget build(BuildContext context) {
    final borderColor = isDark ? AppColors.borderDark : AppColors.border;
    final statusColor = _statusColor(payout.status);

    return Semantics(
      label: '${DateFormat('d MMM yyyy').format(payout.date)}, '
          '${CurrencyFormatter.format(payout.amount)}, '
          '${payout.status.name}',
      child: Column(
        children: [
          Padding(
            padding: const EdgeInsets.symmetric(
                horizontal: AppSpacing.cardPadding, vertical: 14),
            child: Row(
              children: [
                Expanded(
                  flex: 3,
                  child: Text(
                    DateFormat('d MMM yyyy').format(payout.date),
                    style: TextStyle(fontFamily: 'Inter', fontSize: 13,
                        color: textPrimary),
                  ),
                ),
                Expanded(
                  flex: 3,
                  child: Text(
                    CurrencyFormatter.format(payout.amount),
                    style: TextStyle(
                      fontFamily: 'Inter', fontSize: 13,
                      fontWeight: FontWeight.w600, color: textPrimary,
                      fontFeatures: const [FontFeature.tabularFigures()],
                    ),
                    textAlign: TextAlign.right,
                  ),
                ),
                const SizedBox(width: 12),
                _StatusChip(status: payout.status, color: statusColor),
              ],
            ),
          ),
          if (showDivider)
            Divider(height: 1, color: borderColor, indent: 16, endIndent: 16),
        ],
      ),
    );
  }

  static Color _statusColor(PayoutStatus s) => switch (s) {
        PayoutStatus.paid    => AppColors.teal500,
        PayoutStatus.pending => AppColors.warning,
        PayoutStatus.failed  => AppColors.danger,
      };
}

class _StatusChip extends StatelessWidget {
  const _StatusChip({required this.status, required this.color});
  final PayoutStatus status;
  final Color color;

  @override
  Widget build(BuildContext context) {
    final label = status.name[0].toUpperCase() + status.name.substring(1);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(100),
        border: Border.all(color: color.withValues(alpha: 0.30)),
      ),
      child: Text(label,
          style: TextStyle(fontFamily: 'Inter', fontSize: 11,
              fontWeight: FontWeight.w600, color: color)),
    );
  }
}

// ── Skeleton ──────────────────────────────────────────────────────────────────

class _PayoutsSkeleton extends StatelessWidget {
  const _PayoutsSkeleton();

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
      children: const [
        SkeletonBox(width: double.infinity, height: 96, radius: 16),
        SizedBox(height: 24),
        SkeletonBox(width: double.infinity, height: 240, radius: 12),
      ],
    );
  }
}
