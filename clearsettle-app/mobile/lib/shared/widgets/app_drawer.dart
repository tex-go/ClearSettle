import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/config/app_config.dart';
import '../../core/constants/route_constants.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_text_styles.dart';
import '../../features/auth/domain/entities/auth_entity.dart';
import '../../features/auth/presentation/providers/auth_provider.dart';
import 'cs_logo.dart';

/// Navigation drawer — mirrors the ClearSettle web sidebar exactly.
///
/// Sections: Overview | Finance | Operations | Coming Soon
/// Colors: #061B3A background, #00C2D1 active highlight.
class AppDrawer extends ConsumerWidget {
  const AppDrawer({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final auth = ref.watch(authProvider).valueOrNull;
    final sellerName =
        auth is AuthAuthenticated ? auth.sellerName : 'Seller';
    final location = GoRouterState.of(context).matchedLocation;

    return Drawer(
      backgroundColor: AppColors.darkNavy,
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
                  const _NavGroup(label: 'Overview'),
                  _NavItem(
                    icon: Icons.dashboard_outlined,
                    label: 'Dashboard',
                    route: RouteConstants.dashboard,
                    location: location,
                    context: context,
                  ),
                  _NavItem(
                    icon: Icons.electrical_services_outlined,
                    label: 'Connected Platforms',
                    route: RouteConstants.connectedPlatforms,
                    location: location,
                    context: context,
                  ),

                  const _NavDivider(),

                  // ── Operations ────────────────────────────────────────────
                  const _NavGroup(label: 'Operations'),
                  _NavItem(
                    icon: Icons.upload_file_outlined,
                    label: 'Upload Center',
                    route: RouteConstants.uploadCenter,
                    location: location,
                    context: context,
                  ),
                  _NavItem(
                    icon: Icons.compare_arrows_outlined,
                    label: 'Reconciliation',
                    route: RouteConstants.reports,
                    location: location,
                    context: context,
                  ),
                  _NavItem(
                    icon: Icons.receipt_long_outlined,
                    label: 'Settlements',
                    route: RouteConstants.settlements,
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
                    icon: Icons.notifications_outlined,
                    label: 'Alerts',
                    route: RouteConstants.alerts,
                    location: location,
                    context: context,
                  ),
                  _NavItem(
                    icon: Icons.description_outlined,
                    label: 'Reports',
                    route: RouteConstants.reports,
                    location: location,
                    context: context,
                  ),

                  const _NavDivider(),

                  // ── Coming Soon ───────────────────────────────────────────
                  const _NavGroup(label: 'Coming Soon'),
                  _NavItemComingSoon(
                    icon: Icons.receipt_outlined,
                    label: 'GST Filing',
                    context: context,
                    route: RouteConstants.gst,
                  ),
                  _NavItemComingSoon(
                    icon: Icons.inventory_2_outlined,
                    label: 'Inventory',
                    context: context,
                    route: RouteConstants.inventorySync,
                  ),

                  const _NavDivider(),

                  // ── Account ───────────────────────────────────────────────
                  const _NavGroup(label: 'Account'),
                  _NavItem(
                    icon: Icons.settings_outlined,
                    label: 'Settings',
                    route: RouteConstants.settings,
                    location: location,
                    context: context,
                  ),
                  _NavLogout(ref: ref, context: context),
                ],
              ),
            ),

            Padding(
              padding: const EdgeInsets.fromLTRB(20, 0, 20, 12),
              child: Text(
                'ClearSettle v${AppConfig.appVersion}',
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
      decoration: const BoxDecoration(
        color: AppColors.accentNavy,
        border: Border(
          bottom: BorderSide(color: AppColors.dividerDark),
        ),
      ),
      child: Row(
        children: [
          const CsLogo(
            size: 42,
            borderRadius: 10,
            backgroundColor: Color(0x1A00C2D1),
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
                    fontWeight: FontWeight.w700,
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
            ? AppColors.primary.withValues(alpha: 0.14)
            : Colors.transparent,
        borderRadius: BorderRadius.circular(8),
        child: InkWell(
          borderRadius: BorderRadius.circular(8),
          splashColor: AppColors.primary.withValues(alpha: 0.1),
          highlightColor: AppColors.primary.withValues(alpha: 0.06),
          onTap: () {
            Navigator.of(context).pop();
            context.go(route);
          },
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
            child: Row(
              children: [
                Icon(
                  icon,
                  size: 18,
                  color: _isActive
                      ? AppColors.primary
                      : AppColors.textSecondaryDark,
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Text(
                    label,
                    style: AppTextStyles.bodySmall.copyWith(
                      color: _isActive
                          ? AppColors.primary
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
                      color: AppColors.primary,
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

// ── Coming soon nav item ───────────────────────────────────────────────────────

class _NavItemComingSoon extends StatelessWidget {
  const _NavItemComingSoon({
    required this.icon,
    required this.label,
    required this.context,
    required this.route,
  });

  final IconData icon;
  final String label;
  final BuildContext context;
  final String route;

  @override
  Widget build(BuildContext _) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 1),
      child: Material(
        color: Colors.transparent,
        borderRadius: BorderRadius.circular(8),
        child: InkWell(
          borderRadius: BorderRadius.circular(8),
          splashColor: AppColors.primary.withValues(alpha: 0.06),
          onTap: () {
            Navigator.of(context).pop();
            context.go(route);
          },
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
            child: Row(
              children: [
                Icon(icon, size: 18, color: AppColors.textMutedDark),
                const SizedBox(width: 12),
                Expanded(
                  child: Text(
                    label,
                    style: AppTextStyles.bodySmall.copyWith(
                      color: AppColors.textMutedDark,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                  decoration: BoxDecoration(
                    color: AppColors.warning.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(4),
                    border: Border.all(
                      color: AppColors.warning.withValues(alpha: 0.3),
                    ),
                  ),
                  child: const Text(
                    'Soon',
                    style: TextStyle(
                      fontSize: 9,
                      fontWeight: FontWeight.w700,
                      color: AppColors.warning,
                      letterSpacing: 0.3,
                    ),
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
    return const Divider(
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
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
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
