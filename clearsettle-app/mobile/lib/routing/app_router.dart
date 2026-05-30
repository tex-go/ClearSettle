import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../core/constants/route_constants.dart';
import '../features/analytics/presentation/screens/analytics_screen.dart';
import '../features/auth/domain/entities/auth_entity.dart';
import '../features/auth/presentation/providers/auth_provider.dart';
import '../features/auth/presentation/screens/login_screen.dart';
import '../features/dashboard/presentation/screens/dashboard_screen.dart';
import '../features/reports/presentation/screens/reconciliation_summary_screen.dart';
import '../features/reports/presentation/screens/report_detail_screen.dart';
import '../features/reports/presentation/screens/reports_screen.dart';
import '../features/reports/presentation/screens/settlement_detail_screen.dart';
import '../features/settings/presentation/screens/settings_screen.dart';
import 'app_shell.dart';
import 'router_notifier.dart';

final routerProvider = Provider<GoRouter>((ref) {
  final notifier = ref.read(routerNotifierProvider);

  return GoRouter(
    debugLogDiagnostics: false,
    initialLocation: RouteConstants.dashboard,
    refreshListenable: notifier,
    redirect: (context, state) {
      final authAsync = ref.read(authProvider);

      if (authAsync.isLoading) return null;

      final isAuthenticated =
          authAsync.valueOrNull?.isAuthenticated ?? false;
      final isLoginRoute = state.matchedLocation == RouteConstants.login;

      if (!isAuthenticated && !isLoginRoute) return RouteConstants.login;
      if (isAuthenticated && isLoginRoute) return RouteConstants.dashboard;
      return null;
    },
    routes: [
      GoRoute(
        path: RouteConstants.login,
        builder: (context, state) => const LoginScreen(),
      ),
      ShellRoute(
        builder: (context, state, child) => AppShell(child: child),
        routes: [
          GoRoute(
            path: RouteConstants.dashboard,
            builder: (context, state) => const DashboardScreen(),
          ),
          GoRoute(
            path: RouteConstants.reports,
            builder: (context, state) => const ReportsScreen(),
            routes: [
              GoRoute(
                path: ':reportId',
                builder: (context, state) => ReportDetailScreen(
                  reportId: state.pathParameters['reportId']!,
                ),
                routes: [
                  GoRoute(
                    path: 'settlement',
                    builder: (context, state) => SettlementDetailScreen(
                      reportId: state.pathParameters['reportId']!,
                    ),
                  ),
                  GoRoute(
                    path: 'reconciliation',
                    builder: (context, state) => ReconciliationSummaryScreen(
                      reportId: state.pathParameters['reportId']!,
                    ),
                  ),
                ],
              ),
            ],
          ),
          GoRoute(
            path: RouteConstants.analytics,
            builder: (context, state) => const AnalyticsScreen(),
          ),
          GoRoute(
            path: RouteConstants.settings,
            builder: (context, state) => const SettingsScreen(),
          ),
        ],
      ),
    ],
    errorBuilder: (context, state) => const LoginScreen(),
  );
});
