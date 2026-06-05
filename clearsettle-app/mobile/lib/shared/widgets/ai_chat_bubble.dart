import 'package:flutter/material.dart';

import '../../core/theme/app_colors.dart';

/// AI chat bubbles for the Copilot screen.
///
/// Bot bubble  — left-aligned, asymmetric radius (TL=4, TR=16, BR=16, BL=16)
/// User bubble — right-aligned, asymmetric radius (TL=16, TR=4, BR=16, BL=16)
///             — always white text on teal, even in light mode
class AiChatBubble extends StatelessWidget {
  const AiChatBubble({
    super.key,
    required this.message,
    required this.isUser,
    this.embeddedCtaLabel,
    this.onCtaTap,
    this.timestamp,
  });

  final String message;
  final bool isUser;
  final String? embeddedCtaLabel;
  final VoidCallback? onCtaTap;
  final String? timestamp;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    if (isUser) {
      return _UserBubble(message: message, timestamp: timestamp);
    }
    return _BotBubble(
      message: message,
      isDark: isDark,
      embeddedCtaLabel: embeddedCtaLabel,
      onCtaTap: onCtaTap,
      timestamp: timestamp,
    );
  }
}

class _UserBubble extends StatelessWidget {
  const _UserBubble({required this.message, this.timestamp});
  final String message;
  final String? timestamp;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.end,
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          if (timestamp != null) ...[
            Text(
              timestamp!,
              style: const TextStyle(
                fontFamily: 'Inter',
                fontSize: 10,
                color: AppColors.textMuted,
              ),
            ),
            const SizedBox(width: 6),
          ],
          ConstrainedBox(
            constraints: BoxConstraints(
              maxWidth: MediaQuery.of(context).size.width * 0.75,
            ),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
              decoration: const BoxDecoration(
                color: AppColors.teal500,
                borderRadius: BorderRadius.only(
                  topLeft: Radius.circular(16),
                  topRight: Radius.circular(4),
                  bottomRight: Radius.circular(16),
                  bottomLeft: Radius.circular(16),
                ),
              ),
              child: Text(
                message,
                style: const TextStyle(
                  fontFamily: 'Inter',
                  fontSize: 14,
                  color: Colors.white,
                  height: 1.45,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _BotBubble extends StatelessWidget {
  const _BotBubble({
    required this.message,
    required this.isDark,
    this.embeddedCtaLabel,
    this.onCtaTap,
    this.timestamp,
  });

  final String message;
  final bool isDark;
  final String? embeddedCtaLabel;
  final VoidCallback? onCtaTap;
  final String? timestamp;

  @override
  Widget build(BuildContext context) {
    final bgColor = isDark ? AppColors.surfaceDark : AppColors.surfaceVariant;
    final textColor = isDark ? AppColors.textPrimaryDark : AppColors.textPrimary;
    final borderColor = isDark ? AppColors.borderDark : AppColors.border;

    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.start,
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          ConstrainedBox(
            constraints: BoxConstraints(
              maxWidth: MediaQuery.of(context).size.width * 0.75,
            ),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
              decoration: BoxDecoration(
                color: bgColor,
                borderRadius: const BorderRadius.only(
                  topLeft: Radius.circular(4),
                  topRight: Radius.circular(16),
                  bottomRight: Radius.circular(16),
                  bottomLeft: Radius.circular(16),
                ),
                border: Border.all(color: borderColor),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    message,
                    style: TextStyle(
                      fontFamily: 'Inter',
                      fontSize: 14,
                      color: textColor,
                      height: 1.5,
                    ),
                  ),
                  if (embeddedCtaLabel != null) ...[
                    const SizedBox(height: 10),
                    _EmbeddedCta(
                      label: embeddedCtaLabel!,
                      onTap: onCtaTap,
                      isDark: isDark,
                    ),
                  ],
                ],
              ),
            ),
          ),
          if (timestamp != null) ...[
            const SizedBox(width: 6),
            Text(
              timestamp!,
              style: const TextStyle(
                fontFamily: 'Inter',
                fontSize: 10,
                color: AppColors.textMuted,
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _EmbeddedCta extends StatelessWidget {
  const _EmbeddedCta({
    required this.label,
    required this.isDark,
    this.onTap,
  });

  final String label;
  final bool isDark;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: AppColors.teal500),
        ),
        child: Text(
          label,
          style: const TextStyle(
            fontFamily: 'Inter',
            fontSize: 13,
            fontWeight: FontWeight.w600,
            color: AppColors.teal500,
          ),
        ),
      ),
    );
  }
}
