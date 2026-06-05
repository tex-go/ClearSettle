import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../core/constants/route_constants.dart';
import '../core/theme/app_colors.dart';
import '../features/issues/presentation/providers/issues_provider.dart';
import '../shared/widgets/app_bottom_nav.dart';
import '../shared/widgets/app_drawer.dart';

final _shellScaffoldKey = GlobalKey<ScaffoldState>();

/// Breakpoint at which sidebar becomes persistent and bottom nav is hidden.
const _tabletBreakpoint = 768.0;

class AppShell extends ConsumerWidget {
  const AppShell({super.key, required this.child});

  final Widget child;

  /// Spec-aligned shell tabs — matches AppBottomNav order exactly.
  static const _routes = [
    RouteConstants.dashboard,
    RouteConstants.issues,
    RouteConstants.reconcile,
    RouteConstants.analytics,
    RouteConstants.more,
  ];

  static void openDrawer() =>
      _shellScaffoldKey.currentState?.openDrawer();

  int _currentIndex(BuildContext context) {
    final location = GoRouterState.of(context).matchedLocation;
    final index = _routes.indexWhere((r) => location.startsWith(r));
    return index == -1 ? 0 : index;
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final issueCount  = ref.watch(issueCountProvider);
    final screenWidth = MediaQuery.of(context).size.width;
    final isTablet    = screenWidth >= _tabletBreakpoint;

    if (isTablet) {
      return _TabletShell(
        currentIndex: _currentIndex(context),
        issueCount: issueCount,
        onNavTap: (i) => context.go(_routes[i]),
        child: child,
      );
    }

    return Scaffold(
      key: _shellScaffoldKey,
      drawer: const AppDrawer(),
      body: child,
      bottomNavigationBar: AppBottomNav(
        currentIndex: _currentIndex(context),
        issueBadgeCount: issueCount,
        onTap: (i) => context.go(_routes[i]),
      ),
    );
  }
}

// ── Tablet layout — persistent sidebar + no bottom nav ────────────────────────

class _TabletShell extends StatelessWidget {
  const _TabletShell({
    required this.child,
    required this.currentIndex,
    required this.issueCount,
    required this.onNavTap,
  });

  final Widget child;
  final int currentIndex;
  final int issueCount;
  final ValueChanged<int> onNavTap;

  @override
  Widget build(BuildContext context) {
    final isDark    = Theme.of(context).brightness == Brightness.dark;
    final sidebarBg = isDark ? AppColors.surfaceDark : AppColors.surface;
    final borderColor = isDark ? AppColors.borderDark : AppColors.border;

    return Scaffold(
      body: Row(
        children: [
          // Persistent sidebar (280dp spec width)
          SizedBox(
            width: 280,
            child: Container(
              decoration: BoxDecoration(
                color: sidebarBg,
                border: Border(right: BorderSide(color: borderColor)),
              ),
              child: const AppDrawer(embedded: true),
            ),
          ),
          // Main content
          Expanded(child: child),
        ],
      ),
    );
  }
}
