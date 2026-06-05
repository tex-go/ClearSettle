import 'package:flutter/material.dart';

import '../../core/theme/app_colors.dart';

enum IssuePriority { high, medium, low }

/// Pill-shaped priority badge: HIGH / MEDIUM / LOW.
///
/// Colors per spec:
///   HIGH   — red   (#EF4444)
///   MEDIUM — amber (#F59E0B)
///   LOW    — gray  (#64748B)
class PriorityBadge extends StatelessWidget {
  const PriorityBadge({
    super.key,
    required this.priority,
  });

  final IssuePriority priority;

  @override
  Widget build(BuildContext context) {
    final color = _color(priority);
    final label = _label(priority);

    return Semantics(
      label: '${label.toLowerCase()} priority issue',
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.15),
          borderRadius: BorderRadius.circular(100),
          border: Border.all(color: color.withValues(alpha: 0.30)),
        ),
        child: Text(
          label,
          style: TextStyle(
            fontFamily: 'Inter',
            fontSize: 11,
            fontWeight: FontWeight.w600,
            color: color,
            letterSpacing: 0.2,
          ),
        ),
      ),
    );
  }

  static Color _color(IssuePriority p) => switch (p) {
        IssuePriority.high   => AppColors.priorityHigh,
        IssuePriority.medium => AppColors.priorityMedium,
        IssuePriority.low    => AppColors.priorityLow,
      };

  static String _label(IssuePriority p) => switch (p) {
        IssuePriority.high   => 'HIGH',
        IssuePriority.medium => 'MEDIUM',
        IssuePriority.low    => 'LOW',
      };

  static IssuePriority fromString(String s) => switch (s.toLowerCase()) {
        'high'   => IssuePriority.high,
        'medium' => IssuePriority.medium,
        _        => IssuePriority.low,
      };
}
