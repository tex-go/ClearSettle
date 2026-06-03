import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_text_styles.dart';
import '../../domain/entities/alert_entity.dart';
import '../providers/alerts_provider.dart';

class AlertsScreen extends ConsumerWidget {
  const AlertsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(alertsProvider);

    return Scaffold(
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Alerts'),
            if (!state.isLoading && state.unreadCount > 0)
              Text(
                '${state.unreadCount} unread',
                style: AppTextStyles.labelSmall.copyWith(
                  color: AppColors.textInverse.withValues(alpha: 0.7),
                ),
              ),
          ],
        ),
        actions: [
          if (state.unreadCount > 0)
            TextButton(
              onPressed: () =>
                  ref.read(alertsProvider.notifier).markAllRead(),
              child: const Text(
                'Mark all read',
                style: TextStyle(
                    color: AppColors.textInverse, fontSize: 13),
              ),
            ),
        ],
      ),
      body: state.isLoading
          ? const Center(child: CircularProgressIndicator())
          : state.alerts.isEmpty
              ? const _EmptyAlerts()
              : _AlertList(
                  alerts: state.alerts,
                  onMarkRead: (id) =>
                      ref.read(alertsProvider.notifier).markRead(id),
                  onTap: (alert) {
                    ref.read(alertsProvider.notifier).markRead(alert.id);
                    if (alert.actionRoute != null) {
                      context.push(alert.actionRoute!);
                    }
                  },
                ),
    );
  }
}

// ── Alert list ────────────────────────────────────────────────────────────────

class _AlertList extends StatelessWidget {
  const _AlertList({
    required this.alerts,
    required this.onMarkRead,
    required this.onTap,
  });

  final List<AlertEntity> alerts;
  final void Function(String id) onMarkRead;
  final void Function(AlertEntity alert) onTap;

  @override
  Widget build(BuildContext context) {
    // Group: unread first, then read
    final unread = alerts.where((a) => !a.isRead).toList();
    final read   = alerts.where((a) => a.isRead).toList();

    return RefreshIndicator(
      color: AppColors.primary,
      onRefresh: () async {}, // backed by provider auto-load
      child: ListView(
        padding: const EdgeInsets.symmetric(vertical: 8),
        children: [
          if (unread.isNotEmpty) ...[
            _GroupHeader('New  ·  ${unread.length}'),
            ...unread.map((a) => _AlertTile(
                  alert: a,
                  onTap: () => onTap(a),
                  onMarkRead: () => onMarkRead(a.id),
                )),
          ],
          if (read.isNotEmpty) ...[
            const _GroupHeader('Earlier'),
            ...read.map((a) => _AlertTile(
                  alert: a,
                  onTap: () => onTap(a),
                  onMarkRead: () => onMarkRead(a.id),
                )),
          ],
        ],
      ),
    );
  }
}

class _GroupHeader extends StatelessWidget {
  const _GroupHeader(this.label);
  final String label;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
      child: Text(
        label.toUpperCase(),
        style: AppTextStyles.labelSmall.copyWith(letterSpacing: 1.1),
      ),
    );
  }
}

// ── Single alert tile ─────────────────────────────────────────────────────────

class _AlertTile extends StatelessWidget {
  const _AlertTile({
    required this.alert,
    required this.onTap,
    required this.onMarkRead,
  });

  final AlertEntity alert;
  final VoidCallback onTap;
  final VoidCallback onMarkRead;

  @override
  Widget build(BuildContext context) {
    final color  = _severityColor(alert.severity);
    final bg     = Theme.of(context).colorScheme.surface;
    final unread = !alert.isRead;

    return Dismissible(
      key: ValueKey(alert.id),
      direction: DismissDirection.endToStart,
      background: Container(
        alignment: Alignment.centerRight,
        padding: const EdgeInsets.only(right: 20),
        color: AppColors.success.withValues(alpha: 0.15),
        child: const Icon(Icons.done_all, color: AppColors.success),
      ),
      onDismissed: (_) => onMarkRead(),
      child: GestureDetector(
        onTap: onTap,
        child: Container(
          margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
          decoration: BoxDecoration(
            color: unread
                ? color.withValues(alpha: 0.06)
                : bg,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: unread
                  ? color.withValues(alpha: 0.25)
                  : AppColors.divider,
            ),
          ),
          child: Padding(
            padding: const EdgeInsets.all(14),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Icon badge
                Container(
                  width: 38,
                  height: 38,
                  decoration: BoxDecoration(
                    color: color.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Icon(_typeIcon(alert.type), color: color, size: 18),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Expanded(
                            child: Text(
                              alert.title,
                              style: AppTextStyles.bodyMedium.copyWith(
                                fontWeight: unread
                                    ? FontWeight.w600
                                    : FontWeight.w500,
                              ),
                            ),
                          ),
                          if (unread)
                            Container(
                              width: 8,
                              height: 8,
                              decoration: BoxDecoration(
                                  color: color, shape: BoxShape.circle),
                            ),
                        ],
                      ),
                      const SizedBox(height: 4),
                      Text(
                        alert.message,
                        style: AppTextStyles.bodySmall
                            .copyWith(height: 1.45),
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                      ),
                      const SizedBox(height: 6),
                      Row(
                        children: [
                          _MarketplaceChip(alert.marketplace),
                          const Spacer(),
                          Text(
                            _timeAgo(alert.createdAt),
                            style: AppTextStyles.labelSmall,
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Color _severityColor(AlertSeverity s) {
    return switch (s) {
      AlertSeverity.critical => AppColors.error,
      AlertSeverity.warning  => AppColors.warning,
      AlertSeverity.info     => AppColors.info,
    };
  }

  IconData _typeIcon(AlertType t) {
    return switch (t) {
      AlertType.settlementMismatch => Icons.account_balance_wallet_outlined,
      AlertType.highDeduction      => Icons.trending_down_outlined,
      AlertType.settlementDelay    => Icons.schedule_outlined,
      AlertType.disputeUpdate      => Icons.gavel_outlined,
      AlertType.syncFailure        => Icons.sync_problem_outlined,
    };
  }

  String _timeAgo(DateTime dt) {
    final diff = DateTime.now().difference(dt);
    if (diff.inMinutes < 60) return '${diff.inMinutes}m ago';
    if (diff.inHours < 24)   return '${diff.inHours}h ago';
    return '${diff.inDays}d ago';
  }
}

class _MarketplaceChip extends StatelessWidget {
  const _MarketplaceChip(this.name);
  final String name;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: AppColors.primary.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(6),
      ),
      child: Text(
        name,
        style: AppTextStyles.labelSmall.copyWith(
          color: AppColors.primary,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }
}

// ── Empty state ───────────────────────────────────────────────────────────────

class _EmptyAlerts extends StatelessWidget {
  const _EmptyAlerts();

  @override
  Widget build(BuildContext context) {
    return const Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.notifications_none_outlined,
              size: 64, color: AppColors.textDisabled),
          SizedBox(height: 16),
          Text('All caught up!',
              style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.w600,
                  color: AppColors.textPrimary)),
          SizedBox(height: 6),
          Text('No alerts at the moment.',
              style: TextStyle(color: AppColors.textSecondary)),
        ],
      ),
    );
  }
}
