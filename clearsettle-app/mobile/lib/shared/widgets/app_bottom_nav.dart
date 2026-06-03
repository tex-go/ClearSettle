import 'package:flutter/material.dart';

import '../../core/theme/app_colors.dart';
import '../../core/theme/app_text_styles.dart';

/// Premium floating pill bottom navigation.
///
/// Selected tab: accent-filled pill background + white icon/label.
/// Unselected: transparent background, muted icon/label.
class AppBottomNav extends StatelessWidget {
  const AppBottomNav({
    super.key,
    required this.currentIndex,
    required this.onTap,
    this.alertBadgeCount = 0,
  });

  final int currentIndex;
  final ValueChanged<int> onTap;
  final int alertBadgeCount;

  static const _items = [
    _NavItem(icon: Icons.grid_view_rounded, label: 'Dashboard'),
    _NavItem(icon: Icons.receipt_long_outlined, label: 'Settlements'),
    _NavItem(icon: Icons.notifications_outlined, label: 'Alerts'),
    _NavItem(icon: Icons.gavel_outlined, label: 'Disputes'),
    _NavItem(icon: Icons.settings_outlined, label: 'Settings'),
  ];

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final bgColor = isDark ? AppColors.surfaceDark : AppColors.surface;

    return Container(
      decoration: BoxDecoration(
        color: bgColor,
        border: Border(
          top: BorderSide(color: AppColors.divider.withValues(alpha: isDark ? 0.15 : 1.0)),
        ),
        boxShadow: [
          BoxShadow(
            color: AppColors.primary.withValues(alpha: isDark ? 0.2 : 0.06),
            blurRadius: 16,
            offset: const Offset(0, -4),
          ),
        ],
      ),
      child: SafeArea(
        top: false,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
          child: Row(
            children: List.generate(_items.length, (index) {
              final item = _items[index];
              final isSelected = index == currentIndex;
              final showBadge = index == 2 && alertBadgeCount > 0;

              return Expanded(
                child: GestureDetector(
                  onTap: () => onTap(index),
                  behavior: HitTestBehavior.opaque,
                  child: AnimatedContainer(
                    duration: const Duration(milliseconds: 200),
                    curve: Curves.easeInOut,
                    padding: EdgeInsets.symmetric(
                      horizontal: isSelected ? 12 : 0,
                      vertical: 8,
                    ),
                    decoration: BoxDecoration(
                      color: isSelected
                          ? AppColors.accent.withValues(alpha: 0.12)
                          : Colors.transparent,
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Stack(
                          clipBehavior: Clip.none,
                          children: [
                            Icon(
                              isSelected
                                  ? _activeIcon(item.icon)
                                  : item.icon,
                              size: 22,
                              color: isSelected
                                  ? AppColors.accent
                                  : isDark
                                      ? AppColors.textSecondaryDark
                                      : AppColors.textSecondary,
                            ),
                            if (showBadge)
                              Positioned(
                                top: -4,
                                right: -8,
                                child: _Badge(count: alertBadgeCount),
                              ),
                          ],
                        ),
                        const SizedBox(height: 3),
                        AnimatedDefaultTextStyle(
                          duration: const Duration(milliseconds: 200),
                          style: AppTextStyles.labelSmall.copyWith(
                            fontSize: 10,
                            fontWeight: isSelected
                                ? FontWeight.w600
                                : FontWeight.w400,
                            color: isSelected
                                ? AppColors.accent
                                : isDark
                                    ? AppColors.textSecondaryDark
                                    : AppColors.textSecondary,
                          ),
                          child: Text(item.label, maxLines: 1),
                        ),
                      ],
                    ),
                  ),
                ),
              );
            }),
          ),
        ),
      ),
    );
  }

  IconData _activeIcon(IconData base) {
    // IconData overrides == so cannot be a const-map key
    final map = <IconData, IconData>{
      Icons.grid_view_rounded:      Icons.grid_view_rounded,
      Icons.receipt_long_outlined:  Icons.receipt_long,
      Icons.notifications_outlined: Icons.notifications,
      Icons.gavel_outlined:         Icons.gavel,
      Icons.settings_outlined:      Icons.settings,
    };
    return map[base] ?? base;
  }
}

class _NavItem {
  const _NavItem({required this.icon, required this.label});
  final IconData icon;
  final String label;
}

class _Badge extends StatelessWidget {
  const _Badge({required this.count});
  final int count;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 1),
      decoration: BoxDecoration(
        color: AppColors.error,
        borderRadius: BorderRadius.circular(8),
      ),
      constraints: const BoxConstraints(minWidth: 16),
      child: Text(
        count > 99 ? '99+' : '$count',
        style: const TextStyle(
          color: Colors.white,
          fontSize: 9,
          fontWeight: FontWeight.w700,
        ),
        textAlign: TextAlign.center,
      ),
    );
  }
}
