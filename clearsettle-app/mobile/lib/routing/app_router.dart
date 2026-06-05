import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../core/constants/route_constants.dart';
import '../core/theme/app_colors.dart';
import '../core/theme/app_text_styles.dart';
import '../features/alerts/presentation/screens/alerts_screen.dart';
import '../features/analytics/presentation/screens/analytics_screen.dart';
import '../features/auth/presentation/providers/auth_provider.dart';
import '../features/auth/presentation/screens/forgot_password_screen.dart';
import '../features/auth/presentation/screens/login_screen.dart';
import '../features/auth/presentation/screens/register_screen.dart';
import '../features/auth/presentation/screens/social_onboarding_screen.dart';
import '../features/auth/presentation/screens/splash_screen.dart';
import '../features/copilot/presentation/screens/copilot_screen.dart';
import '../features/dashboard/presentation/screens/dashboard_screen.dart';
import '../features/disputes/presentation/screens/disputes_screen.dart';
import '../features/issues/presentation/screens/issues_screen.dart';
import '../features/notifications/presentation/screens/notifications_screen.dart';
import '../features/payouts/presentation/screens/payouts_screen.dart';
import '../features/platform_connections/presentation/screens/connected_platforms_screen.dart';
import '../features/reconciliation_center/presentation/screens/reconciliation_center_screen.dart';
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

// ── Custom slide+fade page transition (300ms) ─────────────────────────────────

Page<T> _slideFadePage<T>({
  required LocalKey key,
  required Widget child,
}) {
  return CustomTransitionPage<T>(
    key: key,
    child: child,
    transitionDuration: const Duration(milliseconds: 300),
    reverseTransitionDuration: const Duration(milliseconds: 250),
    transitionsBuilder: (context, animation, secondaryAnimation, child) {
      final slideIn = Tween<Offset>(
        begin: const Offset(0.04, 0),
        end: Offset.zero,
      ).animate(CurvedAnimation(parent: animation, curve: Curves.easeOutCubic));

      final fadeIn = Tween<double>(begin: 0.0, end: 1.0).animate(
        CurvedAnimation(parent: animation, curve: const Interval(0, 0.6)),
      );

      final slideOut = Tween<Offset>(
        begin: Offset.zero,
        end: const Offset(-0.03, 0),
      ).animate(CurvedAnimation(
          parent: secondaryAnimation, curve: Curves.easeInCubic));

      return SlideTransition(
        position: slideOut,
        child: SlideTransition(
          position: slideIn,
          child: FadeTransition(opacity: fadeIn, child: child),
        ),
      );
    },
  );
}

// ── Router provider ───────────────────────────────────────────────────────────

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
      // ── Splash ────────────────────────────────────────────────────────────
      GoRoute(
        path: RouteConstants.splash,
        builder: (_, __) => const SplashScreen(),
      ),

      // ── Auth ──────────────────────────────────────────────────────────────
      GoRoute(path: RouteConstants.login,
          builder: (_, __) => const LoginScreen()),
      GoRoute(path: RouteConstants.register,
          builder: (_, __) => const RegisterScreen()),
      GoRoute(path: RouteConstants.forgotPassword,
          builder: (_, __) => const ForgotPasswordScreen()),
      GoRoute(path: RouteConstants.socialOnboarding,
          builder: (_, __) => const SocialOnboardingScreen()),

      // ── Full-screen overlays (no shell) ────────────────────────────────────
      GoRoute(
        path: RouteConstants.search,
        pageBuilder: (_, state) =>
            _slideFadePage(key: state.pageKey, child: const SearchScreen()),
      ),
      GoRoute(
        path: RouteConstants.copilot,
        pageBuilder: (_, state) =>
            _slideFadePage(key: state.pageKey, child: const CopilotScreen()),
      ),
      GoRoute(
        path: RouteConstants.payouts,
        pageBuilder: (_, state) =>
            _slideFadePage(key: state.pageKey, child: const PayoutsScreen()),
      ),
      GoRoute(
        path: RouteConstants.notifications,
        pageBuilder: (_, state) => _slideFadePage(
            key: state.pageKey, child: const NotificationsScreen()),
      ),

      // ── Finance (coming soon) ──────────────────────────────────────────────
      GoRoute(path: RouteConstants.bankReconciliation,
          builder: (_, __) => const ComingSoonScreen(
            title: 'Bank Reconciliation', icon: Icons.account_balance_outlined,
            description: 'Match bank statements with marketplace settlements.',
            features: ['Automated matching', 'Unmatched credit detection',
              'Settlement variance reports', 'Missing payment alerts'],
          )),
      GoRoute(path: RouteConstants.returns,
          builder: (_, __) => const ComingSoonScreen(
            title: 'Returns', icon: Icons.assignment_return_outlined,
            description: 'Track return rates and refund transactions.',
            features: ['Return rate by SKU', 'RTO tracking',
              'Refund reconciliation', 'Fake return detection'],
          )),
      GoRoute(path: RouteConstants.commissionAudit,
          builder: (_, __) => const ComingSoonScreen(
            title: 'Commission Audit', icon: Icons.percent_outlined,
            description: 'Audit commission charges and detect overcharges.',
            features: ['Rate verification', 'Overcharge detection',
              'Dispute auto-generation'],
          )),
      GoRoute(path: RouteConstants.cashFlow,
          builder: (_, __) => const ComingSoonScreen(
            title: 'Cash Flow Forecast', icon: Icons.waterfall_chart_outlined,
            description: 'Predict upcoming settlements.',
            features: ['30/60/90-day forecast', 'Cash gap detection'],
          )),

      // ── Operations ────────────────────────────────────────────────────────
      GoRoute(path: RouteConstants.connectors,
          builder: (_, __) => const ConnectedPlatformsScreen()),
      GoRoute(path: RouteConstants.inventorySync,
          builder: (_, __) => const ComingSoonScreen(
            title: 'Inventory Sync', icon: Icons.inventory_2_outlined,
            description: 'Sync inventory across all marketplaces.',
            features: ['Real-time levels', 'Low stock alerts', 'Cross-platform sync'],
          )),
      GoRoute(path: RouteConstants.profitability,
          builder: (_, __) => const ComingSoonScreen(
            title: 'Profitability', icon: Icons.trending_up_outlined,
            description: 'Analyse profitability at SKU level.',
            features: ['Per-SKU P&L', 'Category margins', 'Loss-making SKU alerts'],
          )),

      // ── GST ───────────────────────────────────────────────────────────────
      GoRoute(path: RouteConstants.gst,
          builder: (_, __) => const ComingSoonScreen(
            title: 'GST Filing', icon: Icons.receipt_outlined,
            description: 'Prepare GSTR-1, GSTR-3B, reconcile ITC.',
            features: ['GSTR-1 auto-population', 'GSTR-3B preparation',
              'ITC reconciliation', 'TCS / TDS computation'],
          )),
      GoRoute(path: RouteConstants.gstr1,
          builder: (_, __) => const ComingSoonScreen(
            title: 'GSTR-1', icon: Icons.article_outlined,
            description: 'Auto-populate GSTR-1 from marketplace data.',
            features: ['B2B/B2C split', 'HSN summary', 'JSON export'],
          )),
      GoRoute(path: RouteConstants.gstr3b,
          builder: (_, __) => const ComingSoonScreen(
            title: 'GSTR-3B', icon: Icons.article_outlined,
            description: 'Calculate GSTR-3B liability.',
            features: ['Tax liability computation', 'ITC optimisation'],
          )),
      GoRoute(path: RouteConstants.gstReconciliation,
          builder: (_, __) => const ComingSoonScreen(
            title: 'GST Reconciliation', icon: Icons.compare_arrows_outlined,
            description: 'Reconcile with GSTR-2A / 2B.',
            features: ['GSTR-2A/2B matching', 'ITC mismatch alerts'],
          )),
      GoRoute(path: RouteConstants.gstSummary,
          builder: (_, __) => const ComingSoonScreen(
            title: 'GST Summary', icon: Icons.summarize_outlined,
            description: 'Monthly GST summary across all marketplaces.',
            features: ['Monthly tax summary', 'Platform-wise TCS/TDS'],
          )),

      // ── Intelligence ──────────────────────────────────────────────────────
      GoRoute(path: RouteConstants.disputeRules,
          builder: (_, __) => const ComingSoonScreen(
            title: 'Dispute Rule Engine', icon: Icons.rule_outlined,
            description: 'Automated rules to detect and raise disputes.',
            features: ['Custom rule builder', 'Auto-dispute creation'],
          )),
      GoRoute(path: RouteConstants.anomalyDetection,
          builder: (_, __) => const ComingSoonScreen(
            title: 'Anomaly Detection', icon: Icons.analytics_outlined,
            description: 'AI detection of unusual settlement patterns.',
            features: ['Settlement anomaly alerts', 'Fee spike detection'],
          )),
      GoRoute(path: RouteConstants.aiInsights,
          builder: (_, __) => const ComingSoonScreen(
            title: 'AI Insights', icon: Icons.auto_awesome_outlined,
            description: 'AI recommendations to recover money faster.',
            features: ['Recovery opportunity ranking', 'Pricing hints'],
          )),

      // ── Help ──────────────────────────────────────────────────────────────
      GoRoute(path: RouteConstants.helpCenter,
          builder: (_, __) => const ComingSoonScreen(
            title: 'Help Center', icon: Icons.help_outline,
            description: 'Documentation and live support.',
            features: ['Step-by-step guides', 'Live chat', 'FAQ library'],
          )),

      // ── Shell (bottom-nav tabs) ────────────────────────────────────────────
      ShellRoute(
        builder: (context, state, child) => AppShell(child: child),
        routes: [
          // Tab 1 — Home / Dashboard
          GoRoute(
            path: RouteConstants.dashboard,
            pageBuilder: (_, state) =>
                _slideFadePage(key: state.pageKey, child: const DashboardScreen()),
          ),

          // Tab 2 — Issues (deep-linkable as /issues)
          GoRoute(
            path: RouteConstants.issues,
            pageBuilder: (_, state) =>
                _slideFadePage(key: state.pageKey, child: const IssuesScreen()),
          ),

          // Tab 3 — Reconcile
          GoRoute(
            path: RouteConstants.reconcile,
            pageBuilder: (_, state) => _slideFadePage(
                key: state.pageKey,
                child: const ReconciliationCenterScreen()),
          ),

          // Tab 4 — Analytics
          GoRoute(
            path: RouteConstants.analytics,
            pageBuilder: (_, state) =>
                _slideFadePage(key: state.pageKey, child: const AnalyticsScreen()),
          ),

          // Tab 5 — More hub
          GoRoute(
            path: RouteConstants.more,
            pageBuilder: (_, state) =>
                _slideFadePage(key: state.pageKey, child: const _MoreScreen()),
          ),

          // Legacy shell routes (kept for backward compat within drawers/links)
          GoRoute(path: RouteConstants.settlements,
              builder: (_, __) => const SettlementsScreen()),
          GoRoute(path: RouteConstants.alerts,
              builder: (_, __) => const AlertsScreen()),
          GoRoute(path: RouteConstants.disputes,
              builder: (_, __) => const DisputesScreen()),
          GoRoute(
            path: RouteConstants.settings,
            builder: (_, __) => const SettingsScreen(),
            routes: [
              GoRoute(path: 'connected-platforms',
                  builder: (_, __) => const ConnectedPlatformsScreen()),
              GoRoute(path: 'analytics',
                  builder: (_, __) => const AnalyticsScreen()),
            ],
          ),
          GoRoute(
            path: RouteConstants.reports,
            builder: (_, __) => const ReportsScreen(),
            routes: [
              GoRoute(
                path: ':reportId',
                builder: (_, state) => ReportDetailScreen(
                    reportId: state.pathParameters['reportId']!),
                routes: [
                  GoRoute(path: 'settlement',
                      builder: (_, state) => SettlementDetailScreen(
                          reportId: state.pathParameters['reportId']!)),
                  GoRoute(path: 'reconciliation',
                      builder: (_, state) => ReconciliationSummaryScreen(
                          reportId: state.pathParameters['reportId']!)),
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

// ── More hub screen ────────────────────────────────────────────────────────────

class _MoreScreen extends StatelessWidget {
  const _MoreScreen();

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final bgColor = isDark ? AppColors.backgroundDark : AppColors.background;
    final surfColor = isDark ? AppColors.surfaceDark : AppColors.surface;
    final textPrimary = isDark ? AppColors.textPrimaryDark : AppColors.textPrimary;
    final textMuted   = isDark ? AppColors.textMutedDark   : AppColors.textMuted;
    final borderColor = isDark ? AppColors.borderDark : AppColors.border;

    const items = [
      _MoreItem(Icons.smart_toy_outlined,          'AI Copilot',    'Ask anything about your settlements',  RouteConstants.copilot),
      _MoreItem(Icons.account_balance_outlined,    'Payouts',       'Upcoming and past payouts',            RouteConstants.payouts),
      _MoreItem(Icons.notifications_outlined,      'Notifications', 'Alerts and system updates',            RouteConstants.notifications),
      _MoreItem(Icons.description_outlined,        'Reports',       'Upload and manage settlement reports', RouteConstants.reports),
      _MoreItem(Icons.receipt_long_outlined,       'Settlements',   'Settlement history',                   RouteConstants.settlements),
      _MoreItem(Icons.gavel_outlined,              'Disputes',      'Track open disputes',                  RouteConstants.disputes),
      _MoreItem(Icons.electrical_services_outlined,'Platforms',     'Manage connected marketplaces',        RouteConstants.connectedPlatforms),
      _MoreItem(Icons.settings_outlined,           'Settings',      'Account and app preferences',          RouteConstants.settings),
    ];

    return Scaffold(
      backgroundColor: bgColor,
      appBar: AppBar(
        backgroundColor: surfColor,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        toolbarHeight: AppSpacing.appBarHeight,
        title: Text('More', style: TextStyle(
            fontFamily: 'Inter', fontSize: 18, fontWeight: FontWeight.w600,
            color: textPrimary)),
        centerTitle: false,
      ),
      body: ListView.separated(
        padding: const EdgeInsets.symmetric(
            horizontal: AppSpacing.pageHorizontal, vertical: 12),
        itemCount: items.length,
        separatorBuilder: (_, __) =>
            Divider(height: 1, color: borderColor, indent: 52),
        itemBuilder: (context, i) {
          final item = items[i];
          return ListTile(
            contentPadding: EdgeInsets.zero,
            minLeadingWidth: 40,
            leading: Container(
              width: 36, height: 36,
              decoration: BoxDecoration(
                color: AppColors.teal500.withValues(alpha: 0.10),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Icon(item.icon, color: AppColors.teal500, size: 18),
            ),
            title: Text(item.label,
                style: TextStyle(fontFamily: 'Inter', fontSize: 14,
                    fontWeight: FontWeight.w500, color: textPrimary)),
            subtitle: Text(item.subtitle,
                style: TextStyle(fontFamily: 'Inter', fontSize: 12,
                    color: textMuted)),
            trailing: Icon(Icons.chevron_right_rounded,
                color: textMuted, size: 20),
            onTap: () => context.push(item.route),
          );
        },
      ),
    );
  }
}

class _MoreItem {
  const _MoreItem(this.icon, this.label, this.subtitle, this.route);
  final IconData icon;
  final String label, subtitle, route;
}
