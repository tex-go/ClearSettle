import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/constants/route_constants.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_text_styles.dart';
import '../../features/auth/domain/entities/auth_entity.dart';
import '../../features/auth/presentation/providers/auth_provider.dart';

/// Full-width navigation drawer that mirrors the ClearSettle web sidebar.
///
/// Background: navy (#0D1F35) — exact web sidebar colour.
/// Active item: teal highlight — exact web nav-active style.
/// Group labels: muted text — exact web sidebar section labels.
class AppDrawer extends ConsumerWidget {
  const AppDrawer({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final auth = ref.watch(authProvider).valueOrNull;
    final sellerName =
        auth is AuthAuthenticated ? auth.sellerName : 'Seller';
    final location = GoRouterState.of(context).matchedLocation;

    return Drawer(
      backgroundColor: AppColors.primary,
      surfaceTintColor: Colors.transparent,
      width: 288,
      child: SafeArea(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            _DrawerHeader(sellerName: sellerName),
            Expanded(
              child: ListView(
                padding: const EdgeInsets.only(top: 4, bottom: 16),
                children: [
                  // ── Overview ──────────────────────────────────────────────
                  _NavGroup(label: 'Overview'),
                  _NavItem(
                    icon: Icons.dashboard_outlined,
                    label: 'Dashboard',
                    route: RouteConstants.dashboard,
                    location: location,
                    context: context,
                  ),

                  _NavDivider(),

                  // ── Finance ───────────────────────────────────────────────
                  _NavGroup(label: 'Finance'),
                  _NavItem(
                    icon: Icons.receipt_long_outlined,
                    label: 'Settlements',
                    route: RouteConstants.settlements,
                    location: location,
                    context: context,
                  ),
                  _NavItem(
                    icon: Icons.account_balance_outlined,
                    label: 'Bank Reconciliation',
                    route: RouteConstants.bankReconciliation,
                    location: location,
                    context: context,
                  ),
                  _NavItem(
                    icon: Icons.gavel_outlined,
                    label: 'Disputes',
                    route: RouteConstants.disputes,
                    location: location,
                    context: context,
                  ),
                  _NavItem(
                    icon: Icons.assignment_return_outlined,
                    label: 'Returns',
                    route: RouteConstants.returns,
                    location: location,
                    context: context,
                  ),
                  _NavItem(
                    icon: Icons.percent_outlined,
                    label: 'Commission Audit',
                    route: RouteConstants.commissionAudit,
                    location: location,
                    context: context,
                  ),
                  _NavItem(
                    icon: Icons.calculate_outlined,
                    label: 'GST / TCS',
                    route: RouteConstants.gst,
                    location: location,
                    context: context,
                  ),

                  _NavDivider(),

                  // ── Operations ────────────────────────────────────────────
                  _NavGroup(label: 'Operations'),
                  _NavItem(
                    icon: Icons.electrical_services_outlined,
                    label: 'Connectors',
                    route: RouteConstants.connectors,
                    location: location,
                    context: context,
                  ),
                  _NavItem(
                    icon: Icons.inventory_2_outlined,
                    label: 'Inventory Sync',
                    route: RouteConstants.inventorySync,
                    location: location,
                    context: context,
                  ),
                  _NavItem(
                    icon: Icons.waterfall_chart_outlined,
                    label: 'Cash Flow Forecast',
                    route: RouteConstants.cashFlow,
                    location: location,
                    context: context,
                  ),
                  _NavItem(
                    icon: Icons.trending_up_outlined,
                    label: 'Profitability',
                    route: RouteConstants.profitability,
                    location: location,
                    context: context,
                  ),

                  _NavDivider(),

                  // ── Compliance ────────────────────────────────────────────
                  _NavGroup(label: 'Compliance'),
                  _NavItem(
                    icon: Icons.receipt_outlined,
                    label: 'GSTR-1',
                    route: RouteConstants.gstr1,
                    location: location,
                    context: context,
                  ),
                  _NavItem(
                    icon: Icons.receipt_outlined,
                    label: 'GSTR-3B',
                    route: RouteConstants.gstr3b,
                    location: location,
                    context: context,
                  ),
                  _NavItem(
                    icon: Icons.compare_arrows_outlined,
                    label: 'GST Reconciliation',
                    route: RouteConstants.gstReconciliation,
                    location: location,
                    context: context,
                  ),
                  _NavItem(
                    icon: Icons.summarize_outlined,
                    label: 'GST Summary',
                    route: RouteConstants.gstSummary,
                    location: location,
                    context: context,
                  ),

                  _NavDivider(),

                  // ── Intelligence ──────────────────────────────────────────
                  _NavGroup(label: 'Intelligence'),
                  _NavItem(
                    icon: Icons.rule_outlined,
                    label: 'Dispute Rule Engine',
                    route: RouteConstants.disputeRules,
                    location: location,
                    context: context,
                  ),
                  _NavItem(
                    icon: Icons.analytics_outlined,
                    label: 'Anomaly Detection',
                    route: RouteConstants.anomalyDetection,
                    location: location,
                    context: context,
                  ),
                  _NavItem(
                    icon: Icons.auto_awesome_outlined,
                    label: 'AI Insights',
                    route: RouteConstants.aiInsights,
                    location: location,
                    context: context,
                  ),

                  _NavDivider(),

                  // ── Administration ────────────────────────────────────────
                  _NavGroup(label: 'Administration'),
                  _NavItem(
                    icon: Icons.power_outlined,
                    label: 'Marketplace Connections',
                    route: RouteConstants.connectedPlatforms,
                    location: location,
                    context: context,
                  ),
                  _NavItem(
                    icon: Icons.upload_file_outlined,
                    label: 'Uploaded Reports',
                    route: RouteConstants.reports,
                    location: location,
                    context: context,
                  ),
                  _NavItem(
                    icon: Icons.person_outline,
                    label: 'User Settings',
                    route: RouteConstants.settings,
                    location: location,
                    context: context,
                  ),
                  _NavItem(
                    icon: Icons.notifications_outlined,
                    label: 'Notifications',
                    route: RouteConstants.alerts,
                    location: location,
                    context: context,
                  ),
                  _NavItem(
                    icon: Icons.help_outline,
                    label: 'Help Center',
                    route: RouteConstants.helpCenter,
                    location: location,
                    context: context,
                  ),

                  _NavDivider(),

                  // ── Logout ────────────────────────────────────────────────
                  _NavLogout(ref: ref, context: context),
                ],
              ),
            ),

            // Version footer
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 0, 20, 12),
              child: Text(
                'ClearSettle v1.0',
                style: AppTextStyles.labelSmall.copyWith(
                  color: AppColors.textMutedDark,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ── Header ────────────────────────────────────────────────────────────────────

class _DrawerHeader extends StatelessWidget {
  const _DrawerHeader({required this.sellerName});

  final String sellerName;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(20, 20, 20, 20),
      decoration: BoxDecoration(
        color: AppColors.primaryLight,
        border: Border(
          bottom: BorderSide(color: AppColors.dividerDark),
        ),
      ),
      child: Row(
        children: [
          Container(
            width: 42,
            height: 42,
            decoration: BoxDecoration(
              color: AppColors.teal.withValues(alpha: 0.2),
              borderRadius: BorderRadius.circular(10),
            ),
            child: const Icon(Icons.store_outlined,
                color: AppColors.teal, size: 22),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  'ClearSettle',
                  style: AppTextStyles.titleMedium.copyWith(
                    color: AppColors.textInverse,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  sellerName,
                  style: AppTextStyles.labelSmall.copyWith(
                    color: AppColors.textSecondaryDark,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

// ── Nav item ──────────────────────────────────────────────────────────────────

class _NavItem extends StatelessWidget {
  const _NavItem({
    required this.icon,
    required this.label,
    required this.route,
    required this.location,
    required this.context,
  });

  final IconData icon;
  final String label;
  final String route;
  final String location;
  final BuildContext context;

  bool get _isActive => location == route || location.startsWith('$route/');

  @override
  Widget build(BuildContext _) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 1),
      child: Material(
        color: _isActive
            ? AppColors.teal.withValues(alpha: 0.14)
            : Colors.transparent,
        borderRadius: BorderRadius.circular(8),
        child: InkWell(
          borderRadius: BorderRadius.circular(8),
          splashColor: AppColors.teal.withValues(alpha: 0.1),
          highlightColor: AppColors.teal.withValues(alpha: 0.06),
          onTap: () {
            Navigator.of(context).pop(); // close drawer
            context.go(route);
          },
          child: Padding(
            padding:
                const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
            child: Row(
              children: [
                Icon(
                  icon,
                  size: 18,
                  color: _isActive
                      ? AppColors.teal
                      : AppColors.textSecondaryDark,
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Text(
                    label,
                    style: AppTextStyles.bodySmall.copyWith(
                      color: _isActive
                          ? AppColors.teal
                          : AppColors.textSecondaryDark,
                      fontWeight:
                          _isActive ? FontWeight.w600 : FontWeight.w500,
                    ),
                  ),
                ),
                if (_isActive)
                  Container(
                    width: 4,
                    height: 4,
                    decoration: const BoxDecoration(
                      color: AppColors.teal,
                      shape: BoxShape.circle,
                    ),
                  ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

// ── Nav group label ───────────────────────────────────────────────────────────

class _NavGroup extends StatelessWidget {
  const _NavGroup({required this.label});
  final String label;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(22, 12, 22, 4),
      child: Text(
        label.toUpperCase(),
        style: AppTextStyles.labelSmall.copyWith(
          color: AppColors.textMutedDark,
          letterSpacing: 0.8,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }
}

// ── Divider ───────────────────────────────────────────────────────────────────

class _NavDivider extends StatelessWidget {
  const _NavDivider();

  @override
  Widget build(BuildContext context) {
    return Divider(
      color: AppColors.dividerDark,
      thickness: 1,
      height: 20,
      indent: 20,
      endIndent: 20,
    );
  }
}

// ── Logout ────────────────────────────────────────────────────────────────────

class _NavLogout extends StatelessWidget {
  const _NavLogout({required this.ref, required this.context});
  final WidgetRef ref;
  final BuildContext context;

  @override
  Widget build(BuildContext _) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 2),
      child: Material(
        color: Colors.transparent,
        borderRadius: BorderRadius.circular(8),
        child: InkWell(
          borderRadius: BorderRadius.circular(8),
          splashColor: AppColors.error.withValues(alpha: 0.1),
          onTap: () async {
            Navigator.of(context).pop();
            await ref.read(authProvider.notifier).logout();
            if (context.mounted) context.go('/login');
          },
          child: Padding(
            padding:
                const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
            child: Row(
              children: [
                const Icon(Icons.logout_outlined,
                    size: 18, color: AppColors.error),
                const SizedBox(width: 12),
                Text(
                  'Logout',
                  style: AppTextStyles.bodySmall.copyWith(
                    color: AppColors.error,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
