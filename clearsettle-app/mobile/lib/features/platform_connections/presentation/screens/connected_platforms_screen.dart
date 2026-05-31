import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_text_styles.dart';
import '../../../../services/oauth/flipkart_oauth_service.dart';
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
        error: (e, _) => _ErrorView(message: e.toString()),
        data: (connections) => _Body(connections: connections),
      ),
    );
  }
}

class _Body extends ConsumerWidget {
  const _Body({required this.connections});

  final List<PlatformConnection> connections;

  PlatformConnection? _find(String platform) =>
      connections.where((c) => c.platform == platform).firstOrNull;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final notifier = ref.read(platformConnectionProvider.notifier);
    final isLoading = ref.watch(platformConnectionProvider).isLoading;

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
              connection: _find('flipkart'),
              onConnect: () => _connect(context, notifier.connectFlipkart),
              onDisconnect: () =>
                  _confirmDisconnect(context, 'Flipkart', notifier, 'flipkart'),
            ),
            const SizedBox(height: 12),

            // ── Amazon ───────────────────────────────────────────────────
            PlatformTile(
              platform: 'amazon',
              displayName: 'Amazon',
              logoColor: AppColors.amazon,
              logoIcon: Icons.store_outlined,
              connection: null,
              comingSoon: true,
            ),
            const SizedBox(height: 12),

            // ── Meesho ───────────────────────────────────────────────────
            PlatformTile(
              platform: 'meesho',
              displayName: 'Meesho',
              logoColor: AppColors.meesho,
              logoIcon: Icons.local_mall_outlined,
              connection: null,
              comingSoon: true,
            ),
            const SizedBox(height: 12),

            // ── Myntra ───────────────────────────────────────────────────
            PlatformTile(
              platform: 'myntra',
              displayName: 'Myntra',
              logoColor: AppColors.myntra,
              logoIcon: Icons.checkroom_outlined,
              connection: null,
              comingSoon: true,
            ),
          ],
        ),

        // Loading overlay during OAuth flow
        if (isLoading)
          Container(
            color: Colors.black.withValues(alpha: 0.3),
            child: const Center(child: CircularProgressIndicator()),
          ),
      ],
    );
  }

  Future<void> _connect(
    BuildContext context,
    Future<void> Function() action,
  ) async {
    try {
      await action();
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Flipkart account connected successfully!'),
            backgroundColor: AppColors.success,
          ),
        );
      }
    } on FlipkartOAuthException catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(e.message),
            backgroundColor: AppColors.error,
          ),
        );
      }
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Connection failed: $e'),
            backgroundColor: AppColors.error,
          ),
        );
      }
    }
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
            child: Text(
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

class _ErrorView extends StatelessWidget {
  const _ErrorView({required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.error_outline, color: AppColors.error, size: 48),
            const SizedBox(height: 12),
            Text(message,
                textAlign: TextAlign.center,
                style: AppTextStyles.bodyMedium
                    .copyWith(color: AppColors.textSecondary)),
          ],
        ),
      ),
    );
  }
}
