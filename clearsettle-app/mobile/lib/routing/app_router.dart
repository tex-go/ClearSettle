import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../core/constants/route_constants.dart';
import '../features/alerts/presentation/screens/alerts_screen.dart';
import '../features/analytics/presentation/screens/analytics_screen.dart';
import '../features/auth/presentation/providers/auth_provider.dart';
import '../features/auth/presentation/screens/forgot_password_screen.dart';
import '../features/auth/presentation/screens/login_screen.dart';
import '../features/auth/presentation/screens/register_screen.dart';
import '../features/auth/presentation/screens/social_onboarding_screen.dart';
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
import '../shared/screens/coming_soon_screen.dart';
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

      final isPublic = loc == RouteConstants.splash ||
          loc == RouteConstants.login ||
          loc == RouteConstants.register ||
          loc == RouteConstants.forgotPassword ||
          loc == RouteConstants.socialOnboarding;

      if (!isAuthenticated && !isPublic) return RouteConstants.login;
      if (isAuthenticated && loc == RouteConstants.login) {
        return RouteConstants.dashboard;
      }
      return null;
    },
    routes: [
      // ── Splash ───────────────────────────────────────────────────────────
      GoRoute(
        path: RouteConstants.splash,
        builder: (_, __) => const SplashScreen(),
      ),

      // ── Auth ─────────────────────────────────────────────────────────────
      GoRoute(
        path: RouteConstants.login,
        builder: (_, __) => const LoginScreen(),
      ),
      GoRoute(
        path: RouteConstants.register,
        builder: (_, __) => const RegisterScreen(),
      ),
      GoRoute(
        path: RouteConstants.forgotPassword,
        builder: (_, __) => const ForgotPasswordScreen(),
      ),
      GoRoute(
        path: RouteConstants.socialOnboarding,
        builder: (_, __) => const SocialOnboardingScreen(),
      ),

      // ── Full-screen modals (no bottom nav / shell) ────────────────────────
      GoRoute(
        path: RouteConstants.search,
        builder: (_, __) => const SearchScreen(),
      ),

      // ── Finance (drawer — no bottom nav, standalone routes) ───────────────
      GoRoute(
        path: RouteConstants.bankReconciliation,
        builder: (_, __) => const ComingSoonScreen(
          title: 'Bank Reconciliation',
          icon: Icons.account_balance_outlined,
          description:
              'Automatically match your bank statements with marketplace settlements to find missing credits and unmatched transactions.',
          features: [
            'Automated statement matching',
            'Unmatched credit detection',
            'Settlement variance reports',
            'Missing payment alerts',
            'Over-deduction recovery',
          ],
        ),
      ),
      GoRoute(
        path: RouteConstants.returns,
        builder: (_, __) => const ComingSoonScreen(
          title: 'Returns',
          icon: Icons.assignment_return_outlined,
          description:
              'Track and analyse return rates, RTO orders, and refund transactions across all marketplaces.',
          features: [
            'Return rate by SKU and category',
            'RTO order tracking',
            'Refund reconciliation',
            'Fake return detection',
            'Return trend analytics',
          ],
        ),
      ),
      GoRoute(
        path: RouteConstants.commissionAudit,
        builder: (_, __) => const ComingSoonScreen(
          title: 'Commission Audit',
          icon: Icons.percent_outlined,
          description:
              'Audit marketplace commission charges and automatically detect overcharges that are recoverable.',
          features: [
            'Commission rate verification',
            'Overcharge detection',
            'Recoverable amount calculation',
            'Category-wise fee breakdown',
            'Dispute auto-generation',
          ],
        ),
      ),
      GoRoute(
        path: RouteConstants.cashFlow,
        builder: (_, __) => const ComingSoonScreen(
          title: 'Cash Flow Forecast',
          icon: Icons.waterfall_chart_outlined,
          description:
              'Predict upcoming settlements and plan your cash flow with AI-powered forecasts.',
          features: [
            '30/60/90-day settlement forecast',
            'Cash gap detection',
            'Payout delay prediction',
            'Platform-wise payout timeline',
          ],
        ),
      ),

      // ── Operations ────────────────────────────────────────────────────────
      GoRoute(
        path: RouteConstants.connectors,
        builder: (_, __) => const ConnectedPlatformsScreen(),
      ),
      GoRoute(
        path: RouteConstants.inventorySync,
        builder: (_, __) => const ComingSoonScreen(
          title: 'Inventory Sync',
          icon: Icons.inventory_2_outlined,
          description:
              'Sync your inventory levels across all connected marketplaces from a single dashboard.',
          features: [
            'Real-time inventory levels',
            'Low stock alerts',
            'Cross-platform sync',
            'Dead stock identification',
          ],
        ),
      ),
      GoRoute(
        path: RouteConstants.profitability,
        builder: (_, __) => const ComingSoonScreen(
          title: 'Profitability',
          icon: Icons.trending_up_outlined,
          description:
              'Analyse profitability at SKU, category, and platform level after all fees and returns.',
          features: [
            'Per-SKU profit & loss',
            'Category-wise margin analysis',
            'Platform contribution view',
            'Loss-making SKU alerts',
          ],
        ),
      ),

      // ── GST / Compliance ──────────────────────────────────────────────────
      GoRoute(
        path: RouteConstants.gst,
        builder: (_, __) => const ComingSoonScreen(
          title: 'GST Filing',
          icon: Icons.receipt_outlined,
          description:
              'Prepare and file your GSTR-1, GSTR-3B, and reconcile input tax credits automatically.',
          features: [
            'GSTR-1 auto-population',
            'GSTR-3B preparation',
            'ITC reconciliation',
            'GST liability summary',
            'TCS / TDS computation',
          ],
        ),
      ),
      GoRoute(
        path: RouteConstants.gstr1,
        builder: (_, __) => const ComingSoonScreen(
          title: 'GSTR-1',
          icon: Icons.article_outlined,
          description:
              'Auto-populate your GSTR-1 return with outward supply data from all connected marketplaces.',
          features: [
            'B2B and B2C invoice split',
            'HSN-wise summary',
            'Export invoice tagging',
            'JSON / Excel export for portal upload',
          ],
        ),
      ),
      GoRoute(
        path: RouteConstants.gstr3b,
        builder: (_, __) => const ComingSoonScreen(
          title: 'GSTR-3B',
          icon: Icons.article_outlined,
          description:
              'Calculate your GSTR-3B liability with input tax credit set-off automatically.',
          features: [
            'Tax liability computation',
            'ITC claim optimisation',
            'Late fee calculator',
            'Interest on delayed payment',
          ],
        ),
      ),
      GoRoute(
        path: RouteConstants.gstReconciliation,
        builder: (_, __) => const ComingSoonScreen(
          title: 'GST Reconciliation',
          icon: Icons.compare_arrows_outlined,
          description:
              'Reconcile your books with GSTR-2A / 2B to ensure you claim the correct input tax credit.',
          features: [
            'GSTR-2A / 2B matching',
            'Missing invoice detection',
            'ITC mismatch alerts',
            'Vendor-wise reconciliation',
          ],
        ),
      ),
      GoRoute(
        path: RouteConstants.gstSummary,
        builder: (_, __) => const ComingSoonScreen(
          title: 'GST Summary',
          icon: Icons.summarize_outlined,
          description:
              'Monthly GST summary across all marketplaces including TCS collected and TDS deducted.',
          features: [
            'Monthly tax summary',
            'Platform-wise TCS / TDS',
            'Net GST payable',
            'Year-to-date liability',
          ],
        ),
      ),

      // ── Intelligence ──────────────────────────────────────────────────────
      GoRoute(
        path: RouteConstants.disputeRules,
        builder: (_, __) => const ComingSoonScreen(
          title: 'Dispute Rule Engine',
          icon: Icons.rule_outlined,
          description:
              'Create automated rules that detect overcharges and raise disputes without manual intervention.',
          features: [
            'Custom rule builder',
            'Auto-dispute creation',
            'Priority scoring',
            'Success rate tracking',
          ],
        ),
      ),
      GoRoute(
        path: RouteConstants.anomalyDetection,
        builder: (_, __) => const ComingSoonScreen(
          title: 'Anomaly Detection',
          icon: Icons.analytics_outlined,
          description:
              'AI-powered detection of unusual patterns in your settlements, fees, and returns.',
          features: [
            'Settlement anomaly alerts',
            'Fee spike detection',
            'Return rate anomalies',
            'Commission rate changes',
          ],
        ),
      ),
      GoRoute(
        path: RouteConstants.aiInsights,
        builder: (_, __) => const ComingSoonScreen(
          title: 'AI Insights',
          icon: Icons.auto_awesome_outlined,
          description:
              'Personalised AI recommendations to grow revenue and recover lost money faster.',
          features: [
            'Recovery opportunity ranking',
            'Platform expansion suggestions',
            'Pricing optimisation hints',
            'Seasonal trend predictions',
          ],
        ),
      ),

      // ── Help ─────────────────────────────────────────────────────────────
      GoRoute(
        path: RouteConstants.helpCenter,
        builder: (_, __) => const ComingSoonScreen(
          title: 'Help Center',
          icon: Icons.help_outline,
          description:
              'Documentation, video tutorials, and live support to help you get the most from ClearSettle.',
          features: [
            'Step-by-step guides',
            'Video walkthroughs',
            'Live chat support',
            'FAQ library',
          ],
        ),
      ),

      // ── Shell (bottom-nav tabs) ───────────────────────────────────────────
      ShellRoute(
        builder: (context, state, child) => AppShell(child: child),
        routes: [
          GoRoute(
            path: RouteConstants.dashboard,
            builder: (_, __) => const DashboardScreen(),
          ),
          GoRoute(
            path: RouteConstants.settlements,
            builder: (_, __) => const SettlementsScreen(),
          ),
          GoRoute(
            path: RouteConstants.alerts,
            builder: (_, __) => const AlertsScreen(),
          ),
          GoRoute(
            path: RouteConstants.disputes,
            builder: (_, __) => const DisputesScreen(),
          ),
          GoRoute(
            path: RouteConstants.settings,
            builder: (_, __) => const SettingsScreen(),
            routes: [
              GoRoute(
                path: 'connected-platforms',
                builder: (_, __) => const ConnectedPlatformsScreen(),
              ),
              GoRoute(
                path: 'analytics',
                builder: (_, __) => const AnalyticsScreen(),
              ),
            ],
          ),
          GoRoute(
            path: RouteConstants.reports,
            builder: (_, __) => const ReportsScreen(),
            routes: [
              GoRoute(
                path: ':reportId',
                builder: (_, state) => ReportDetailScreen(
                  reportId: state.pathParameters['reportId']!,
                ),
                routes: [
                  GoRoute(
                    path: 'settlement',
                    builder: (_, state) => SettlementDetailScreen(
                      reportId: state.pathParameters['reportId']!,
                    ),
                  ),
                  GoRoute(
                    path: 'reconciliation',
                    builder: (_, state) => ReconciliationSummaryScreen(
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
    errorBuilder: (_, __) => const LoginScreen(),
  );
});
