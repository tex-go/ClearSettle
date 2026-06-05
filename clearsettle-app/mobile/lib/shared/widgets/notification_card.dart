import 'package:flutter/material.dart';

import '../../core/theme/app_colors.dart';
import '../../core/theme/app_text_styles.dart';

enum NotificationType { missingPayment, excessFee, settlement, upload, recovery }

/// Notification list item with colored dot, marketplace icon, time stamp.
class NotificationCard extends StatelessWidget {
  const NotificationCard({
    super.key,
    required this.type,
    required this.title,
    required this.subtitle,
    required this.amount,
    required this.timeAgo,
    this.isRead = false,
    this.onTap,
  });

  final NotificationType type;
  final String title;
  final String subtitle;
  final String amount;
  final String timeAgo;
  final bool isRead;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final textPrimary = isDark ? AppColors.textPrimaryDark : AppColors.textPrimary;
    final textMuted   = isDark ? AppColors.textMutedDark   : AppColors.textMuted;
    final textSecond  = isDark ? AppColors.textSecondaryDark : AppColors.textSecondary;

    final dotColor   = _dotColor(type);
    final bgCard     = isDark ? AppColors.surfaceDark : AppColors.surface;
    final bgUnread   = isDark ? AppColors.surfaceElevatedDark : AppColors.surfaceVariant;

    return Semantics(
      label: '$title. $subtitle. $amount. $timeAgo',
      child: Material(
        color: isRead ? bgCard : bgUnread,
        child: InkWell(
          onTap: onTap,
          child: Padding(
            padding: const EdgeInsets.symmetric(
                horizontal: AppSpacing.cardPadding, vertical: 12),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Dot + icon stack
                Column(
                  children: [
                    Container(
                      width: 8,
                      height: 8,
                      margin: const EdgeInsets.only(top: 6),
                      decoration: BoxDecoration(
                        color: isRead
                            ? Colors.transparent
                            : dotColor,
                        shape: BoxShape.circle,
                        border: isRead
                            ? Border.all(color: textMuted.withValues(alpha: 0.3))
                            : null,
                      ),
                    ),
                  ],
                ),
                const SizedBox(width: 8),
                _TypeIcon(type: type, color: dotColor),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        title,
                        style: TextStyle(
                          fontFamily: 'Inter',
                          fontSize: 14,
                          fontWeight: isRead ? FontWeight.w400 : FontWeight.w600,
                          color: textPrimary,
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        subtitle,
                        style: TextStyle(
                          fontFamily: 'Inter',
                          fontSize: 12,
                          color: textSecond,
                        ),
                      ),
                      if (amount.isNotEmpty) ...[
                        const SizedBox(height: 2),
                        Text(
                          amount,
                          style: TextStyle(
                            fontFamily: 'Inter',
                            fontSize: 12,
                            fontWeight: FontWeight.w500,
                            color: textPrimary,
                            fontFeatures: const [FontFeature.tabularFigures()],
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
                const SizedBox(width: 8),
                Text(
                  timeAgo,
                  style: TextStyle(
                    fontFamily: 'Inter',
                    fontSize: 11,
                    color: textMuted,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  static Color _dotColor(NotificationType t) => switch (t) {
        NotificationType.missingPayment => AppColors.dotMissing,
        NotificationType.excessFee      => AppColors.dotExcessFee,
        NotificationType.settlement     => AppColors.dotSettlement,
        NotificationType.upload         => AppColors.dotUpload,
        NotificationType.recovery       => AppColors.dotRecovery,
      };
}

class _TypeIcon extends StatelessWidget {
  const _TypeIcon({required this.type, required this.color});
  final NotificationType type;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 36,
      height: 36,
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        shape: BoxShape.circle,
      ),
      child: Icon(_icon(type), color: color, size: 16),
    );
  }

  IconData _icon(NotificationType t) => switch (t) {
        NotificationType.missingPayment => Icons.money_off_outlined,
        NotificationType.excessFee      => Icons.local_offer_outlined,
        NotificationType.settlement     => Icons.check_circle_outline,
        NotificationType.upload         => Icons.upload_file_outlined,
        NotificationType.recovery       => Icons.savings_outlined,
      };
}
