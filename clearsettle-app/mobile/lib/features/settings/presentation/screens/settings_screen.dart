import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/config/app_config.dart';
import '../../../../core/constants/app_constants.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_text_styles.dart';
import '../../../auth/domain/entities/auth_entity.dart';
import '../../../auth/presentation/providers/auth_provider.dart';

class SettingsScreen extends ConsumerWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final authState = ref.watch(authProvider).valueOrNull;
    final user = authState is AuthAuthenticated ? authState : null;

    return Scaffold(
      backgroundColor: AppColors.backgroundLight,
      appBar: AppBar(title: const Text('Settings')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          if (user != null) _buildProfileCard(user),
          const SizedBox(height: 16),
          _buildSection(
            title: 'Account',
            children: [
              _SettingsTile(
                icon: Icons.business_outlined,
                label: 'Organization',
                value: user?.organization ?? '—',
              ),
              _SettingsTile(
                icon: Icons.alternate_email,
                label: 'Email',
                value: user?.email ?? '—',
              ),
              _SettingsTile(
                icon: Icons.badge_outlined,
                label: 'Role',
                value: user?.role ?? '—',
              ),
            ],
          ),
          const SizedBox(height: 16),
          _buildSection(
            title: 'Marketplaces',
            children: [
              _SettingsTile(
                icon: Icons.storefront_outlined,
                label: 'Connected',
                value: AppConstants.supportedMarketplaces
                    .map((m) => AppConstants.marketplaceDisplayNames[m] ?? m)
                    .join(', '),
              ),
            ],
          ),
          const SizedBox(height: 16),
          _buildSection(
            title: 'App',
            children: [
              _SettingsTile(
                icon: Icons.info_outline,
                label: 'Version',
                value: AppConfig.appVersion,
              ),
              _SettingsTile(
                icon: Icons.sync_outlined,
                label: 'Auto Sync',
                trailing: Switch(
                  value: true,
                  activeColor: AppColors.primary,
                  onChanged: (_) {},
                ),
              ),
            ],
          ),
          const SizedBox(height: 24),
          _buildLogoutButton(ref, context),
          const SizedBox(height: 32),
        ],
      ),
    );
  }

  Widget _buildProfileCard(AuthAuthenticated user) {
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
              color: AppColors.textInverse.withOpacity(0.15),
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
                    color: AppColors.textInverse.withOpacity(0.75),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSection({
    required String title,
    required List<Widget> children,
  }) {
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
            color: AppColors.surface,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: AppColors.divider),
          ),
          child: Column(children: children),
        ),
      ],
    );
  }

  Widget _buildLogoutButton(WidgetRef ref, BuildContext context) {
    return SizedBox(
      width: double.infinity,
      height: 50,
      child: OutlinedButton.icon(
        onPressed: () => _confirmLogout(ref, context),
        icon: const Icon(Icons.logout, color: AppColors.error),
        label: const Text(
          'Sign Out',
          style: TextStyle(color: AppColors.error),
        ),
        style: OutlinedButton.styleFrom(
          side: const BorderSide(color: AppColors.error),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(10),
          ),
        ),
      ),
    );
  }

  Future<void> _confirmLogout(WidgetRef ref, BuildContext context) async {
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
            child: const Text(
              'Sign Out',
              style: TextStyle(color: AppColors.error),
            ),
          ),
        ],
      ),
    );
    if (confirmed == true) {
      await ref.read(authProvider.notifier).logout();
    }
  }
}

class _SettingsTile extends StatelessWidget {
  const _SettingsTile({
    required this.icon,
    required this.label,
    this.value,
    this.trailing,
    this.onTap,
  });

  final IconData icon;
  final String label;
  final String? value;
  final Widget? trailing;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(12),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 13),
        child: Row(
          children: [
            Icon(icon, color: AppColors.primary, size: 20),
            const SizedBox(width: 12),
            Expanded(
              child: Text(label, style: AppTextStyles.bodyMedium),
            ),
            if (trailing != null) trailing!,
            if (value != null)
              Text(
                value!,
                style: AppTextStyles.bodySmall,
              ),
            if (onTap != null && trailing == null) ...[
              const SizedBox(width: 4),
              const Icon(
                Icons.chevron_right,
                color: AppColors.textDisabled,
                size: 18,
              ),
            ],
          ],
        ),
      ),
    );
  }
}
