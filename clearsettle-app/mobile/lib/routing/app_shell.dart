import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../core/constants/route_constants.dart';
import '../features/alerts/presentation/providers/alerts_provider.dart';
import '../shared/widgets/app_bottom_nav.dart';

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

  int _currentIndex(BuildContext context) {
    final location = GoRouterState.of(context).matchedLocation;
    final index = _routes.indexWhere((r) => location.startsWith(r));
    return index == -1 ? 0 : index;
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final unread = ref.watch(unreadAlertCountProvider);

    return Scaffold(
      body: child,
      bottomNavigationBar: AppBottomNav(
        currentIndex: _currentIndex(context),
        alertBadgeCount: unread,
        onTap: (index) => context.go(_routes[index]),
      ),
    );
  }
}
