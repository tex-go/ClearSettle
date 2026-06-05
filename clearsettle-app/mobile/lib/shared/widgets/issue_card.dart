import 'package:flutter/material.dart';

import '../../core/theme/app_colors.dart';
import '../../core/theme/app_text_styles.dart';
import '../../core/utils/currency_formatter.dart';
import 'pressable_card.dart';
import 'priority_badge.dart';

/// Issue card — shown in Issues Center list.
///
/// Layout:
///   Row 1: marketplace logo + name + type | amount
///   Row 2: icon + detail text
///   Row 3: detected-on date | priority badge | chevron
class IssueCard extends StatelessWidget {
  const IssueCard({
    super.key,
    required this.marketplace,
    required this.marketplaceColor,
    required this.issueType,
    required this.amount,
    required this.detailLabel,
    required this.detailValue,
    required this.detectedOn,
    required this.priority,
    this.onTap,
  });

  final String marketplace;
  final Color marketplaceColor;
  final String issueType;
  final double amount;
  final String detailLabel;  // "Order ID" or "Fee Type"
  final String detailValue;
  final String detectedOn;   // "Detected on 15 May 2025"
  final IssuePriority priority;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final textPrimary = isDark ? AppColors.textPrimaryDark : AppColors.textPrimary;
    final textMuted   = isDark ? AppColors.textMutedDark   : AppColors.textMuted;
    final textSecond  = isDark ? AppColors.textSecondaryDark : AppColors.textSecondary;

    return Semantics(
      label: '$marketplace $issueType, amount ${CurrencyFormatter.format(amount)}, '
          '${PriorityBadge.fromString(priority.name).name} priority, $detectedOn',
      child: PressableCard(
        onTap: onTap,
        padding: const EdgeInsets.symmetric(
            horizontal: AppSpacing.cardPadding, vertical: 12),
        margin: EdgeInsets.zero,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Row 1: marketplace + amount
            Row(
              children: [
                _MarketplaceLogo(color: marketplaceColor, name: marketplace),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        marketplace,
                        style: TextStyle(
                          fontFamily: 'Inter',
                          fontSize: 14,
                          fontWeight: FontWeight.w600,
                          color: textPrimary,
                        ),
                      ),
                      Text(
                        issueType,
                        style: TextStyle(
                          fontFamily: 'Inter',
                          fontSize: 12,
                          color: textSecond,
                        ),
                      ),
                    ],
                  ),
                ),
                Semantics(
                  label: 'Amount: ${CurrencyFormatter.format(amount)}',
                  child: Text(
                    CurrencyFormatter.format(amount),
                    style: TextStyle(
                      fontFamily: 'Inter',
                      fontSize: 15,
                      fontWeight: FontWeight.w700,
                      color: textPrimary,
                      fontFeatures: const [FontFeature.tabularFigures()],
                    ),
                  ),
                ),
              ],
            ),

            const SizedBox(height: 8),

            // Row 2: detail
            Row(
              children: [
                Icon(_detailIcon(detailLabel), size: 13, color: textMuted),
                const SizedBox(width: 4),
                Expanded(
                  child: Text(
                    '$detailLabel: $detailValue',
                    style: TextStyle(
                      fontFamily: 'Inter',
                      fontSize: 11,
                      color: textMuted,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              ],
            ),

            const SizedBox(height: 8),

            // Row 3: date + badge + chevron
            Row(
              children: [
                Expanded(
                  child: Text(
                    detectedOn,
                    style: TextStyle(
                      fontFamily: 'Inter',
                      fontSize: 11,
                      color: textMuted,
                    ),
                  ),
                ),
                PriorityBadge(priority: priority),
                const SizedBox(width: 8),
                Icon(
                  Icons.chevron_right_rounded,
                  size: 16,
                  color: textMuted,
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  IconData _detailIcon(String label) =>
      label.toLowerCase().contains('order') ? Icons.receipt_outlined : Icons.local_offer_outlined;
}

class _MarketplaceLogo extends StatelessWidget {
  const _MarketplaceLogo({required this.color, required this.name});
  final Color color;
  final String name;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 32,
      height: 32,
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Center(
        child: Text(
          name.isNotEmpty ? name[0].toUpperCase() : '?',
          style: TextStyle(
            fontFamily: 'Inter',
            fontSize: 13,
            fontWeight: FontWeight.w700,
            color: color,
          ),
        ),
      ),
    );
  }
}
