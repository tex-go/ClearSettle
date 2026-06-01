import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../core/constants/route_constants.dart';
import '../features/alerts/presentation/screens/alerts_screen.dart';
import '../features/analytics/presentation/screens/analytics_screen.dart';
import '../features/auth/presentation/providers/auth_provider.dart';
import '../features/auth/presentation/screens/forgot_password_screen.dart';
import '../features/auth/presentation/screens/login_screen.dart';
import '../features/auth/presentation/screens/splash_screen.dart';
import '../features/dashboard/presentation/screens/dashboard_screen.dart';
import '../features/disputes/presentation/screens/disputes_screen.dart';
import '../features/platform_connections/presentation/screens/connected_platforms_screen.dart';
import '../features/reports/presentation/screens/reconciliation_summary_screen.dart';
import '../features/reports/presentation/screens/report_detail_screen.dart';
import '../features/reports/presentation/screens/reports_screen.dart';
import '../features/reports/presentation/screens/settlement_detail_screen.dart';
import '../features/search/presentation/screens/search_screen.dart';
import '../features/settlements/presentation/screens/settlements_screen.dart';
import '../features/settings/presentation/screens/settings_screen.dart';
import 'app_shell.dart';
import 'router_notifier.dart';

final routerProvider = Provider<GoRouter>((ref) {
  final notifier = ref.read(routerNotifierProvider);

  return GoRouter(
    debugLogDiagnostics: false,
    initialLocation: RouteConstants.splash,
    refreshListenable: notifier,
    redirect: (context, state) {
      final authAsync = ref.read(authProvider);
      if (authAsync.isLoading) return null;

      final isAuthenticated =
          authAsync.valueOrNull?.isAuthenticated ?? false;
      final loc = state.matchedLocation;

      // Always allow splash, login, forgot-password
      final isPublic = loc == RouteConstants.splash ||
          loc == RouteConstants.login ||
          loc == RouteConstants.forgotPassword;

      if (!isAuthenticated && !isPublic) return RouteConstants.login;
      if (isAuthenticated && loc == RouteConstants.login) {
        return RouteConstants.dashboard;
      }
      return null;
    },
    routes: [
      // ── Splash ─────────────────────────────────────────────────────────
      GoRoute(
        path: RouteConstants.splash,
        builder: (context, state) => const SplashScreen(),
      ),

      // ── Auth ───────────────────────────────────────────────────────────
      GoRoute(
        path: RouteConstants.login,
        builder: (context, state) => const LoginScreen(),
      ),
      GoRoute(
        path: RouteConstants.forgotPassword,
        builder: (context, state) => const ForgotPasswordScreen(),
      ),

      // ── Full-screen modals (no bottom nav) ─────────────────────────────
      GoRoute(
        path: RouteConstants.search,
        builder: (context, state) => const SearchScreen(),
      ),

      // ── Shell (bottom-nav tabs) ────────────────────────────────────────
      ShellRoute(
        builder: (context, state, child) => AppShell(child: child),
        routes: [
          // Dashboard
          GoRoute(
            path: RouteConstants.dashboard,
            builder: (context, state) => const DashboardScreen(),
          ),

          // Settlements
          GoRoute(
            path: RouteConstants.settlements,
            builder: (context, state) => const SettlementsScreen(),
          ),

          // Alerts
          GoRoute(
            path: RouteConstants.alerts,
            builder: (context, state) => const AlertsScreen(),
          ),

          // Disputes
          GoRoute(
            path: RouteConstants.disputes,
            builder: (context, state) => const DisputesScreen(),
          ),

          // Settings + nested
          GoRoute(
            path: RouteConstants.settings,
            builder: (context, state) => const SettingsScreen(),
            routes: [
              GoRoute(
                path: 'connected-platforms',
                builder: (context, state) =>
                    const ConnectedPlatformsScreen(),
              ),
              // Analytics accessible from Settings → nested
              GoRoute(
                path: 'analytics',
                builder: (context, state) => const AnalyticsScreen(),
              ),
            ],
          ),

          // Reports (legacy — accessible from Settings or deep links)
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
                    builder: (context, state) =>
                        ReconciliationSummaryScreen(
                      reportId: state.pathParameters['reportId']!,
                    ),
                  ),
                ],
              ),
            ],
          ),
        ],
      ),
    ],
    errorBuilder: (context, state) => const LoginScreen(),
  );
});
