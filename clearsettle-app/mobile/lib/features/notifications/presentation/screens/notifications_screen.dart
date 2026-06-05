import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_text_styles.dart';
import '../../../../shared/widgets/empty_state_widget.dart';
import '../../../../shared/widgets/notification_card.dart';

// ── In-place provider (replace with feature provider when wiring backend) ─────

enum _NotifFilter { all, important, updates }

final _filterProvider = StateProvider<_NotifFilter>(
    (_) => _NotifFilter.all);

/// Notifications screen — typed alerts with read/unread states and filter tabs.
class NotificationsScreen extends ConsumerWidget {
  const NotificationsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final filter  = ref.watch(_filterProvider);
    final isDark  = Theme.of(context).brightness == Brightness.dark;
    final bgColor = isDark ? AppColors.backgroundDark : AppColors.background;

    const all = _mockNotifications;
    final shown = switch (filter) {
      _NotifFilter.all       => all,
      _NotifFilter.important => all
          .where((n) =>
              n.type == NotificationType.missingPayment ||
              n.type == NotificationType.excessFee)
          .toList(),
      _NotifFilter.updates   => all
          .where((n) =>
              n.type == NotificationType.settlement ||
              n.type == NotificationType.upload)
          .toList(),
    };

    return Scaffold(
      backgroundColor: bgColor,
      body: CustomScrollView(
        slivers: [
          _AppBar(isDark: isDark),
          _FilterTabs(
              current: filter,
              onSelect: (f) =>
                  ref.read(_filterProvider.notifier).state = f,
              isDark: isDark),
          shown.isEmpty
              ? const SliverFillRemaining(
                  child: EmptyStateWidget(
                    icon: Icons.notifications_none_rounded,
                    title: 'No notifications',
                    subtitle:
                        'You\'re all caught up! New alerts will appear here.',
                  ),
                )
              : _NotifList(notifications: shown),
        ],
      ),
    );
  }
}

// ── App bar ───────────────────────────────────────────────────────────────────

class _AppBar extends StatelessWidget {
  const _AppBar({required this.isDark});
  final bool isDark;

  @override
  Widget build(BuildContext context) {
    final textPrimary = isDark ? AppColors.textPrimaryDark : AppColors.textPrimary;
    final textMuted   = isDark ? AppColors.textMutedDark   : AppColors.textMuted;
    return SliverAppBar(
      pinned: true,
      backgroundColor: isDark ? AppColors.surfaceDark : AppColors.surface,
      surfaceTintColor: Colors.transparent,
      elevation: 0,
      toolbarHeight: AppSpacing.appBarHeight,
      title: Text('Notifications',
          style: TextStyle(fontFamily: 'Inter', fontSize: 18,
              fontWeight: FontWeight.w600, color: textPrimary)),
      centerTitle: false,
      actions: [
        IconButton(
          icon: Icon(Icons.more_horiz_rounded, color: textMuted),
          onPressed: () {},
          tooltip: 'Options',
        ),
      ],
    );
  }
}

// ── Filter tabs ───────────────────────────────────────────────────────────────

class _FilterTabs extends StatelessWidget {
  const _FilterTabs({
    required this.current,
    required this.onSelect,
    required this.isDark,
  });

  final _NotifFilter current;
  final ValueChanged<_NotifFilter> onSelect;
  final bool isDark;

  @override
  Widget build(BuildContext context) {
    final surfColor   = isDark ? AppColors.surfaceDark : AppColors.surface;
    final borderColor = isDark ? AppColors.borderDark  : AppColors.border;
    final textMuted   = isDark ? AppColors.textMutedDark : AppColors.textMuted;

    const tabs = [
      (_NotifFilter.all,       'All'),
      (_NotifFilter.important, 'Important'),
      (_NotifFilter.updates,   'Updates'),
    ];

    return SliverToBoxAdapter(
      child: Container(
        color: surfColor,
        decoration: BoxDecoration(
          border: Border(bottom: BorderSide(color: borderColor)),
        ),
        padding: const EdgeInsets.symmetric(
            horizontal: AppSpacing.pageHorizontal),
        child: Row(
          children: tabs.map((t) {
            final isActive = current == t.$1;
            return Semantics(
              label: t.$2,
              selected: isActive,
              child: GestureDetector(
                onTap: () => onSelect(t.$1),
                child: Container(
                  margin: const EdgeInsets.only(right: 24),
                  padding: const EdgeInsets.symmetric(vertical: 13),
                  decoration: BoxDecoration(
                    border: Border(
                      bottom: BorderSide(
                        color: isActive ? AppColors.teal500 : Colors.transparent,
                        width: 2,
                      ),
                    ),
                  ),
                  child: Text(
                    t.$2,
                    style: TextStyle(
                      fontFamily: 'Inter', fontSize: 13,
                      fontWeight: isActive ? FontWeight.w600 : FontWeight.w400,
                      color: isActive ? AppColors.teal500 : textMuted,
                    ),
                  ),
                ),
              ),
            );
          }).toList(),
        ),
      ),
    );
  }
}

// ── Notification list ─────────────────────────────────────────────────────────

class _NotifList extends StatelessWidget {
  const _NotifList({required this.notifications});
  final List<_NotifData> notifications;

  @override
  Widget build(BuildContext context) {
    return SliverList.separated(
      itemCount: notifications.length,
      separatorBuilder: (context, _) {
        final isDark = Theme.of(context).brightness == Brightness.dark;
        return Divider(
          height: 1,
          color: isDark ? AppColors.borderDark : AppColors.border,
        );
      },
      itemBuilder: (_, i) {
        final n = notifications[i];
        return NotificationCard(
          type: n.type,
          title: n.title,
          subtitle: n.subtitle,
          amount: n.amount,
          timeAgo: n.timeAgo,
          isRead: n.isRead,
        );
      },
    );
  }
}

// ── Mock data ─────────────────────────────────────────────────────────────────

class _NotifData {
  const _NotifData({
    required this.type,
    required this.title,
    required this.subtitle,
    required this.amount,
    required this.timeAgo,
    this.isRead = false,
  });
  final NotificationType type;
  final String title, subtitle, amount, timeAgo;
  final bool isRead;
}

const _mockNotifications = [
  _NotifData(
    type: NotificationType.missingPayment,
    title: 'Missing payment detected',
    subtitle: 'Amazon — Order ID: 405-857Sxxxx',
    amount: '₹8,420',
    timeAgo: '2m ago',
  ),
  _NotifData(
    type: NotificationType.excessFee,
    title: 'Excess fee detected',
    subtitle: 'Flipkart — Shipping Fee',
    amount: '₹2,143',
    timeAgo: '1h ago',
  ),
  _NotifData(
    type: NotificationType.settlement,
    title: 'Settlement completed',
    subtitle: 'Meesho payout of ₹1,87,750',
    amount: '₹1,87,750',
    timeAgo: '3h ago',
    isRead: true,
  ),
  _NotifData(
    type: NotificationType.upload,
    title: 'Report uploaded successfully',
    subtitle: 'Amazon_May_2025.xlsx',
    amount: '',
    timeAgo: '5h ago',
    isRead: true,
  ),
  _NotifData(
    type: NotificationType.recovery,
    title: 'Recovery opportunity found',
    subtitle: 'Potential recovery detected',
    amount: '₹12,890',
    timeAgo: '1d ago',
    isRead: true,
  ),
];
