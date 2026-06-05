import 'package:flutter/material.dart';

import '../../core/theme/app_colors.dart';

/// Spec-aligned bottom navigation bar.
///
/// Tabs: Home | Issues | Reconcile | Analytics | More
/// Height: 64dp (spec token AppSpacing.bottomNavHeight)
/// Active: teal icon + teal label, no pill background
/// Badge: red circle on Issues tab
class AppBottomNav extends StatelessWidget {
  const AppBottomNav({
    super.key,
    required this.currentIndex,
    required this.onTap,
    this.issueBadgeCount = 0,
  });

  final int currentIndex;
  final ValueChanged<int> onTap;
  final int issueBadgeCount;

  static const _items = [
    _NavItem(icon: Icons.home_outlined,         activeIcon: Icons.home_rounded,              label: 'Home'),
    _NavItem(icon: Icons.warning_amber_outlined, activeIcon: Icons.warning_amber_rounded,     label: 'Issues'),
    _NavItem(icon: Icons.sync_outlined,          activeIcon: Icons.sync_rounded,              label: 'Reconcile'),
    _NavItem(icon: Icons.bar_chart_outlined,     activeIcon: Icons.bar_chart_rounded,         label: 'Analytics'),
    _NavItem(icon: Icons.grid_view_outlined,     activeIcon: Icons.grid_view_rounded,         label: 'More'),
  ];

  @override
  Widget build(BuildContext context) {
    final isDark    = Theme.of(context).brightness == Brightness.dark;
    final bgColor   = isDark ? AppColors.surfaceDark : AppColors.surface;
    final topBorder = isDark ? AppColors.borderDark  : AppColors.border;

    return Container(
      height: 64 + MediaQuery.of(context).padding.bottom,
      decoration: BoxDecoration(
        color: bgColor,
        border: Border(top: BorderSide(color: topBorder)),
      ),
      child: SafeArea(
        top: false,
        child: SizedBox(
          height: 64,
          child: Row(
            children: List.generate(_items.length, (i) {
              final item      = _items[i];
              final isActive  = i == currentIndex;
              final showBadge = i == 1 && issueBadgeCount > 0; // Issues tab

              return Expanded(
                child: Semantics(
                  label: i == 1 && issueBadgeCount > 0
                      ? '${item.label}, $issueBadgeCount unresolved'
                      : item.label,
                  selected: isActive,
                  child: GestureDetector(
                    onTap: () => onTap(i),
                    behavior: HitTestBehavior.opaque,
                    child: AnimatedContainer(
                      duration: const Duration(milliseconds: 200),
                      curve: Curves.easeInOut,
                      padding: const EdgeInsets.symmetric(vertical: 8),
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Stack(
                            clipBehavior: Clip.none,
                            children: [
                              AnimatedSwitcher(
                                duration: const Duration(milliseconds: 200),
                                child: Icon(
                                  isActive ? item.activeIcon : item.icon,
                                  key: ValueKey(isActive),
                                  size: 22,
                                  color: isActive
                                      ? AppColors.teal500
                                      : isDark
                                          ? AppColors.textMutedDark
                                          : AppColors.textMuted,
                                ),
                              ),
                              if (showBadge)
                                Positioned(
                                  top: -5,
                                  right: -10,
                                  child: _Badge(count: issueBadgeCount),
                                ),
                            ],
                          ),
                          const SizedBox(height: 3),
                          AnimatedDefaultTextStyle(
                            duration: const Duration(milliseconds: 200),
                            style: TextStyle(
                              fontFamily: 'Inter',
                              fontSize: 10,
                              fontWeight: isActive
                                  ? FontWeight.w600
                                  : FontWeight.w400,
                              color: isActive
                                  ? AppColors.teal500
                                  : isDark
                                      ? AppColors.textMutedDark
                                      : AppColors.textMuted,
                            ),
                            child: Text(item.label, maxLines: 1),
                          ),
                        ],
                      ),
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
}

class _NavItem {
  const _NavItem({
    required this.icon,
    required this.activeIcon,
    required this.label,
  });
  final IconData icon, activeIcon;
  final String label;
}

class _Badge extends StatelessWidget {
  const _Badge({required this.count});
  final int count;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 1),
      constraints: const BoxConstraints(minWidth: 16, minHeight: 16),
      decoration: BoxDecoration(
        color: AppColors.danger,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Text(
        count > 99 ? '99+' : '$count',
        style: const TextStyle(
          color: Colors.white,
          fontSize: 9,
          fontWeight: FontWeight.w700,
          fontFamily: 'Inter',
        ),
        textAlign: TextAlign.center,
      ),
    );
  }
}
