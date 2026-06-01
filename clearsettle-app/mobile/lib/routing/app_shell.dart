import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../core/constants/route_constants.dart';
import '../features/alerts/presentation/providers/alerts_provider.dart';
import '../shared/widgets/app_bottom_nav.dart';
import '../shared/widgets/app_drawer.dart';

/// Global key used by child screens (e.g. DashboardScreen) to
/// programmatically open the navigation drawer without needing a BuildContext
/// that reaches the AppShell Scaffold.
final _shellScaffoldKey = GlobalKey<ScaffoldState>();

class AppShell extends ConsumerWidget {
  const AppShell({super.key, required this.child});

  final Widget child;

  static const _routes = [
    RouteConstants.dashboard,
    RouteConstants.settlements,
    RouteConstants.alerts,
    RouteConstants.disputes,
    RouteConstants.settings,
  ];

  /// Open the side drawer from any screen within the shell.
  static void openDrawer() => _shellScaffoldKey.currentState?.openDrawer();

  int _currentIndex(BuildContext context) {
    final location = GoRouterState.of(context).matchedLocation;
    final index = _routes.indexWhere((r) => location.startsWith(r));
    return index == -1 ? 0 : index;
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final unread = ref.watch(unreadAlertCountProvider);

    return Scaffold(
      key: _shellScaffoldKey,
      drawer: const AppDrawer(),
      body: child,
      bottomNavigationBar: AppBottomNav(
        currentIndex: _currentIndex(context),
        alertBadgeCount: unread,
        onTap: (index) => context.go(_routes[index]),
      ),
    );
  }
}
