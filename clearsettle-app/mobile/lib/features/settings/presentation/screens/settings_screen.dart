import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:go_router/go_router.dart';

import '../../../../core/config/app_config.dart';
import '../../../../core/constants/route_constants.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_text_styles.dart';
import '../../../auth/domain/entities/auth_entity.dart';
import '../../../auth/presentation/providers/auth_provider.dart';
import '../providers/settings_provider.dart';

class SettingsScreen extends ConsumerStatefulWidget {
  const SettingsScreen({super.key});

  @override
  ConsumerState<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends ConsumerState<SettingsScreen> {
  @override
  void initState() {
    super.initState();
    // Compute storage on open
    Future.microtask(
      () => ref.read(settingsProvider.notifier).calculateStorageUsed(),
    );
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authProvider).valueOrNull;
    final user = authState is AuthAuthenticated ? authState : null;
    final settings = ref.watch(settingsProvider);
    final notifier = ref.read(settingsProvider.notifier);

    return Scaffold(
      appBar: AppBar(
        leading: Builder(
          builder: (ctx) => IconButton(
            icon: const Icon(Icons.menu_rounded, size: 20),
            tooltip: 'Menu',
            onPressed: () => Scaffold.of(ctx).openDrawer(),
          ),
        ),
        title: const Text('Settings'),
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          if (user != null) _ProfileCard(user: user),
          const SizedBox(height: 16),

          // ── Account ──────────────────────────────────────────────────────
          _Section(
            title: 'Account',
            children: [
              _InfoTile(
                icon: Icons.business_outlined,
                label: 'Organization',
                value: user?.organization ?? '—',
              ),
              _InfoTile(
                icon: Icons.alternate_email,
                label: 'Email',
                value: user?.email ?? '—',
              ),
              _InfoTile(
                icon: Icons.badge_outlined,
                label: 'Role',
                value: user?.role ?? '—',
              ),
            ],
          ),
          const SizedBox(height: 16),

          // ── Connected Platforms ─────────────────────────────────────────
          _Section(
            title: 'Connected Platforms',
            children: [
              _ActionTile(
                icon: Icons.shopping_bag_outlined,
                label: 'Manage Connections',
                onTap: () => context.push(RouteConstants.connectedPlatforms),
              ),
            ],
          ),
          const SizedBox(height: 16),

          // ── Reports ─────────────────────────────────────────────────────
          _Section(
            title: 'Reports & Analytics',
            children: [
              _ActionTile(
                icon: Icons.description_outlined,
                label: 'Settlement Reports',
                onTap: () => context.push(RouteConstants.reports),
              ),
              _ActionTile(
                icon: Icons.bar_chart_outlined,
                label: 'Analytics',
                onTap: () => context.push('/settings/analytics'),
              ),
            ],
          ),
          const SizedBox(height: 16),

          // ── Preferences ────────────────────────────────────────────────
          _Section(
            title: 'Preferences',
            children: [
              _SwitchTile(
                icon: Icons.dark_mode_outlined,
                label: 'Dark Mode',
                value: settings.isDarkMode,
                onChanged: (v) => notifier.setDarkMode(v),
              ),
              _SwitchTile(
                icon: Icons.sync_outlined,
                label: 'Auto Sync',
                subtitle: 'Sync data when connected',
                value: settings.autoSyncEnabled,
                onChanged: (v) => notifier.setAutoSync(v),
              ),
              _SwitchTile(
                icon: Icons.notifications_outlined,
                label: 'Notifications',
                value: settings.notificationsEnabled,
                onChanged: (v) => notifier.setNotifications(v),
              ),
            ],
          ),
          const SizedBox(height: 16),

          // ── Storage ────────────────────────────────────────────────────
          _Section(
            title: 'Storage',
            children: [
              _InfoTile(
                icon: Icons.folder_outlined,
                label: 'Used',
                value: settings.storageUsedLabel,
              ),
              _ActionTile(
                icon: Icons.delete_sweep_outlined,
                label: 'Clear All Data',
                labelColor: AppColors.error,
                iconColor: AppColors.error,
                onTap: () => _confirmClearData(context, notifier),
              ),
            ],
          ),
          const SizedBox(height: 16),

          // ── App Info ───────────────────────────────────────────────────
          _Section(
            title: 'App',
            children: [
              const _InfoTile(
                icon: Icons.info_outline,
                label: 'Version',
                value: AppConfig.appVersion,
              ),
              _InfoTile(
                icon: Icons.build_outlined,
                label: 'Environment',
                value: AppConfig.apiBaseUrl.contains('localhost')
                    ? 'Development'
                    : 'Production',
              ),
            ],
          ),
          const SizedBox(height: 24),

          // ── Sign Out ───────────────────────────────────────────────────
          _SignOutButton(
            onTap: () => _confirmLogout(context, ref),
          ),
          const SizedBox(height: 32),
        ],
      ),
    );
  }

  Future<void> _confirmClearData(
    BuildContext context,
    SettingsNotifier notifier,
  ) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Clear All Data'),
        content: const Text(
          'This will delete all locally-stored reports, parsed data, and settings. '
          'This action cannot be undone.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(true),
            child: const Text('Clear', style: TextStyle(color: AppColors.error)),
          ),
        ],
      ),
    );
    if (confirmed == true && context.mounted) {
      await notifier.clearAllData();
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('All local data cleared.')),
        );
      }
    }
  }

  Future<void> _confirmLogout(BuildContext context, WidgetRef ref) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Sign Out'),
        content: const Text('Are you sure you want to sign out?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(true),
            child: const Text('Sign Out',
                style: TextStyle(color: AppColors.error)),
          ),
        ],
      ),
    );
    if (confirmed == true) {
      await ref.read(authProvider.notifier).logout();
    }
  }
}

// ── Sub-widgets ────────────────────────────────────────────────────────────────

class _ProfileCard extends StatelessWidget {
  const _ProfileCard({required this.user});

  final AuthAuthenticated user;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.primary,
        borderRadius: BorderRadius.circular(14),
      ),
      child: Row(
        children: [
          Container(
            width: 52,
            height: 52,
            decoration: BoxDecoration(
              color: AppColors.textInverse.withValues(alpha: 0.15),
              shape: BoxShape.circle,
            ),
            child: Center(
              child: Text(
                user.sellerName.isNotEmpty
                    ? user.sellerName[0].toUpperCase()
                    : 'S',
                style: AppTextStyles.headlineMedium.copyWith(
                  color: AppColors.textInverse,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  user.sellerName,
                  style: AppTextStyles.titleLarge.copyWith(
                    color: AppColors.textInverse,
                  ),
                ),
                const SizedBox(height: 3),
                Text(
                  user.email,
                  style: AppTextStyles.bodySmall.copyWith(
                    color: AppColors.textInverse.withValues(alpha: 0.75),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _Section extends StatelessWidget {
  const _Section({required this.title, required this.children});

  final String title;
  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(left: 4, bottom: 8),
          child: Text(
            title.toUpperCase(),
            style: AppTextStyles.labelSmall.copyWith(letterSpacing: 1.2),
          ),
        ),
        Container(
          decoration: BoxDecoration(
            color: Theme.of(context).colorScheme.surface,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: Theme.of(context).brightness == Brightness.dark
                  ? AppColors.dividerDark
                  : AppColors.divider,
            ),
          ),
          child: Column(children: children),
        ),
      ],
    );
  }
}

class _InfoTile extends StatelessWidget {
  const _InfoTile({
    required this.icon,
    required this.label,
    required this.value,
  });

  final IconData icon;
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 13),
      child: Row(
        children: [
          Icon(icon, color: AppColors.primary, size: 20),
          const SizedBox(width: 12),
          Expanded(child: Text(label, style: AppTextStyles.bodyMedium)),
          Text(value, style: AppTextStyles.bodySmall),
        ],
      ),
    );
  }
}

class _SwitchTile extends StatelessWidget {
  const _SwitchTile({
    required this.icon,
    required this.label,
    required this.value,
    required this.onChanged,
    this.subtitle,
  });

  final IconData icon;
  final String label;
  final bool value;
  final ValueChanged<bool> onChanged;
  final String? subtitle;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
      child: Row(
        children: [
          Icon(icon, color: AppColors.primary, size: 20),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(label, style: AppTextStyles.bodyMedium),
                if (subtitle != null)
                  Text(subtitle!,
                      style: AppTextStyles.labelSmall
                          .copyWith(color: AppColors.textSecondary)),
              ],
            ),
          ),
          Switch(
            value: value,
            activeThumbColor: AppColors.textInverse,
            activeTrackColor: AppColors.primary,
            onChanged: onChanged,
          ),
        ],
      ),
    );
  }
}

class _ActionTile extends StatelessWidget {
  const _ActionTile({
    required this.icon,
    required this.label,
    required this.onTap,
    this.labelColor,
    this.iconColor,
  });

  final IconData icon;
  final String label;
  final VoidCallback onTap;
  final Color? labelColor;
  final Color? iconColor;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(12),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 13),
        child: Row(
          children: [
            Icon(icon, color: iconColor ?? AppColors.primary, size: 20),
            const SizedBox(width: 12),
            Expanded(
              child: Text(
                label,
                style: AppTextStyles.bodyMedium
                    .copyWith(color: labelColor ?? AppColors.textPrimary),
              ),
            ),
            const Icon(Icons.chevron_right,
                color: AppColors.textDisabled, size: 18),
          ],
        ),
      ),
    );
  }
}

class _SignOutButton extends StatelessWidget {
  const _SignOutButton({required this.onTap});

  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: double.infinity,
      height: 50,
      child: OutlinedButton.icon(
        onPressed: onTap,
        icon: const Icon(Icons.logout, color: AppColors.error),
        label: const Text('Sign Out',
            style: TextStyle(color: AppColors.error)),
        style: OutlinedButton.styleFrom(
          side: const BorderSide(color: AppColors.error),
          shape:
              RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
        ),
      ),
    );
  }
}
