import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../../../core/constants/route_constants.dart';
import '../../../../core/errors/oauth_error_mapper.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_text_styles.dart';
import '../../domain/entities/platform_connection.dart';
import '../providers/platform_connection_provider.dart';
import '../widgets/platform_tile.dart';

class ConnectedPlatformsScreen extends ConsumerWidget {
  const ConnectedPlatformsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final connectionsAsync = ref.watch(platformConnectionProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Connected Platforms')),
      body: connectionsAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        // Initial load failures (Hive unavailable etc.) show friendly error + retry.
        error: (e, _) => _ErrorView(
          message: OAuthErrorMapper.toUserMessage(e),
          onRetry: () => ref.invalidate(platformConnectionProvider),
        ),
        data: (connections) => _Body(connections: connections),
      ),
    );
  }
}

// ── Body ──────────────────────────────────────────────────────────────────────

class _Body extends ConsumerStatefulWidget {
  const _Body({required this.connections});

  final List<PlatformConnection> connections;

  @override
  ConsumerState<_Body> createState() => _BodyState();
}

class _BodyState extends ConsumerState<_Body> {
  PlatformConnection? _find(String platform) =>
      widget.connections.where((c) => c.platform == platform).firstOrNull;

  @override
  Widget build(BuildContext context) {
    final notifier = ref.read(platformConnectionProvider.notifier);
    final isLoading = ref.watch(platformConnectionProvider).isLoading;
    final flipkart = _find('flipkart');

    return Stack(
      children: [
        ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Padding(
              padding: const EdgeInsets.only(left: 4, bottom: 16),
              child: Text(
                'Connect your seller accounts to automatically import orders, '
                'settlements, and financial data into ClearSettle.',
                style: AppTextStyles.bodySmall
                    .copyWith(color: AppColors.textSecondary),
              ),
            ),

            // ── Flipkart ─────────────────────────────────────────────────
            PlatformTile(
              platform: 'flipkart',
              displayName: 'Flipkart',
              logoColor: AppColors.flipkart,
              logoIcon: Icons.shopping_bag_outlined,
              connection: flipkart,
              onConnect: () =>
                  _connectFlipkart(context, notifier),
              onDisconnect: () =>
                  _confirmDisconnect(context, 'Flipkart', notifier, 'flipkart'),
            ),

            // Upload row — shown when Flipkart is connected (manual upload mode)
            if (flipkart?.isConnected == true) ...[
              const SizedBox(height: 8),
              _SyncRow(
                lastSyncAt: flipkart?.lastSyncAt,
                syncing: false,
                actionLabel: 'Upload Report',
                onSync: () => context.go(RouteConstants.reports),
              ),
            ],

            const SizedBox(height: 12),

            // ── Amazon ───────────────────────────────────────────────────
            PlatformTile(
              platform: 'amazon',
              displayName: 'Amazon',
              logoColor: AppColors.amazon,
              logoIcon: Icons.store_outlined,
              connection: _find('amazon'),
              onConnect: () => _runOAuth(
                context: context,
                platformName: 'Amazon',
                action: notifier.connectAmazon,
              ),
              onDisconnect: () =>
                  _confirmDisconnect(context, 'Amazon', notifier, 'amazon'),
            ),
            const SizedBox(height: 12),

            // ── Meesho ───────────────────────────────────────────────────
            const PlatformTile(
              platform: 'meesho',
              displayName: 'Meesho',
              logoColor: AppColors.meesho,
              logoIcon: Icons.local_mall_outlined,
              connection: null,
              comingSoon: true,
            ),
            const SizedBox(height: 12),

            // ── Myntra ───────────────────────────────────────────────────
            const PlatformTile(
              platform: 'myntra',
              displayName: 'Myntra',
              logoColor: AppColors.myntra,
              logoIcon: Icons.checkroom_outlined,
              connection: null,
              comingSoon: true,
            ),
          ],
        ),

        // Full-screen overlay during OAuth (prevents double-taps)
        if (isLoading)
          Container(
            color: Colors.black.withValues(alpha: 0.3),
            child: const Center(child: CircularProgressIndicator()),
          ),
      ],
    );
  }

  /// Shows an explanation dialog before enabling Flipkart manual-upload mode.
  /// Flipkart has no public OAuth API — connecting simply activates the
  /// upload feature so the user can import settlement Excel files.
  Future<void> _connectFlipkart(
    BuildContext context,
    PlatformConnectionNotifier notifier,
  ) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        icon: const Icon(
          Icons.upload_file_outlined,
          color: AppColors.flipkart,
          size: 36,
        ),
        title: const Text(
          'Connect Flipkart',
          textAlign: TextAlign.center,
        ),
        content: const Text(
          'Flipkart uses manual report uploads — no account login required.\n\n'
          'After connecting, go to the Reports tab and upload your '
          'Flipkart settlement Excel file to see your financial data.',
          textAlign: TextAlign.center,
        ),
        actionsAlignment: MainAxisAlignment.spaceBetween,
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: const Text('Cancel'),
          ),
          FilledButton.icon(
            style: FilledButton.styleFrom(
              backgroundColor: AppColors.flipkart,
            ),
            onPressed: () => Navigator.of(ctx).pop(true),
            icon: const Icon(Icons.link_outlined, size: 16),
            label: const Text('Enable Upload'),
          ),
        ],
      ),
    );
    if (confirmed == true && context.mounted) {
      await _runOAuth(
        context: context,
        platformName: 'Flipkart',
        action: notifier.connectFlipkart,
      );
    }
  }

  /// Unified OAuth launcher for all platforms.
  ///
  /// On success: shows a brief success snackbar.
  /// On failure: shows an error dialog with Retry and Cancel buttons.
  ///   - The error message is always sanitized through [OAuthErrorMapper].
  ///   - No raw exception text, status codes, or credentials are ever shown.
  Future<void> _runOAuth({
    required BuildContext context,
    required String platformName,
    required Future<void> Function() action,
  }) async {
    try {
      await action();
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('$platformName connected successfully!'),
            backgroundColor: AppColors.success,
          ),
        );
      }
    } catch (e) {
      await _showOAuthError(
        context: context,
        platformName: platformName,
        error: e,
        // Retry runs the same flow again from scratch.
        onRetry: () => _runOAuth(
          context: context,
          platformName: platformName,
          action: action,
        ),
      );
    }
  }

  /// Shows a modal dialog with a user-friendly error message, a Retry button,
  /// and a Cancel button.  Never surfaces raw exception text.
  ///
  /// Non-async: returns the showDialog Future directly to avoid BuildContext
  /// usage across an async gap.
  Future<void> _showOAuthError({
    required BuildContext context,
    required String platformName,
    required Object error,
    required VoidCallback onRetry,
  }) {
    if (!context.mounted) return Future.value();

    final friendlyMessage = OAuthErrorMapper.toUserMessage(error);

    return showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => AlertDialog(
        icon: const Icon(
          Icons.cloud_off_outlined,
          color: AppColors.error,
          size: 36,
        ),
        title: Text(
          'Unable to Connect $platformName',
          textAlign: TextAlign.center,
          style: AppTextStyles.titleMedium,
        ),
        content: Text(
          friendlyMessage,
          textAlign: TextAlign.center,
          style: AppTextStyles.bodySmall
              .copyWith(color: AppColors.textSecondary),
        ),
        actionsAlignment: MainAxisAlignment.spaceBetween,
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: const Text('Cancel'),
          ),
          FilledButton.icon(
            onPressed: () {
              Navigator.of(ctx).pop();
              onRetry();
            },
            icon: const Icon(Icons.refresh, size: 16),
            label: const Text('Retry'),
          ),
        ],
      ),
    );
  }

  Future<void> _confirmDisconnect(
    BuildContext context,
    String platformName,
    PlatformConnectionNotifier notifier,
    String platformKey,
  ) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text('Disconnect $platformName?'),
        content: Text(
          'This will remove your $platformName seller account from ClearSettle. '
          'Previously imported data will be retained.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(true),
            child: const Text(
              'Disconnect',
              style: TextStyle(color: AppColors.error),
            ),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      await notifier.disconnect(platformKey);
    }
  }
}

// ── Sync row widget ───────────────────────────────────────────────────────────

class _SyncRow extends StatelessWidget {
  const _SyncRow({
    required this.lastSyncAt,
    required this.syncing,
    required this.onSync,
    this.actionLabel = 'Sync Now',
  });

  final DateTime? lastSyncAt;
  final bool syncing;
  final VoidCallback onSync;
  final String actionLabel;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final lastSyncLabel = lastSyncAt != null
        ? 'Last synced ${DateFormat('d MMM · h:mm a').format(lastSyncAt!)}'
        : 'Never synced';

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: AppColors.flipkart.withValues(alpha: 0.06),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(
          color: isDark ? AppColors.dividerDark : AppColors.divider,
        ),
      ),
      child: Row(
        children: [
          const Icon(Icons.sync, color: AppColors.flipkart, size: 17),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              lastSyncLabel,
              style: AppTextStyles.labelSmall
                  .copyWith(color: AppColors.textSecondary),
            ),
          ),
          TextButton(
            onPressed: syncing ? null : onSync,
            style: TextButton.styleFrom(
              foregroundColor: AppColors.flipkart,
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
              minimumSize: Size.zero,
              tapTargetSize: MaterialTapTargetSize.shrinkWrap,
            ),
            child: Text(
              syncing ? 'Syncing…' : actionLabel,
              style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600),
            ),
          ),
        ],
      ),
    );
  }
}

// ── Error view (initial load failures) ───────────────────────────────────────

class _ErrorView extends StatelessWidget {
  const _ErrorView({required this.message, this.onRetry});

  final String message;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(
              Icons.cloud_off_outlined,
              color: AppColors.error,
              size: 52,
            ),
            const SizedBox(height: 16),
            Text(
              message,
              textAlign: TextAlign.center,
              style: AppTextStyles.bodyMedium
                  .copyWith(color: AppColors.textSecondary),
            ),
            if (onRetry != null) ...[
              const SizedBox(height: 24),
              FilledButton.icon(
                onPressed: onRetry,
                icon: const Icon(Icons.refresh, size: 16),
                label: const Text('Retry'),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
