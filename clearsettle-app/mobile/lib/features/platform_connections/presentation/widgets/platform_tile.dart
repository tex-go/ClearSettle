import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_text_styles.dart';
import '../../domain/entities/platform_connection.dart';

class PlatformTile extends StatelessWidget {
  const PlatformTile({
    super.key,
    required this.platform,
    required this.displayName,
    required this.logoColor,
    required this.logoIcon,
    required this.connection,
    this.onConnect,
    this.onDisconnect,
    this.comingSoon = false,
  });

  final String platform;
  final String displayName;
  final Color logoColor;
  final IconData logoIcon;
  final PlatformConnection? connection;
  final VoidCallback? onConnect;
  final VoidCallback? onDisconnect;
  final bool comingSoon;

  bool get _isConnected =>
      connection != null && connection!.status == ConnectionStatus.connected;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Container(
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: _isConnected
              ? AppColors.success.withValues(alpha: 0.4)
              : isDark
                  ? AppColors.dividerDark
                  : AppColors.divider,
        ),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            Container(
              width: 44,
              height: 44,
              decoration: BoxDecoration(
                color: logoColor.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Icon(logoIcon, color: logoColor, size: 22),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(displayName, style: AppTextStyles.titleMedium),
                  const SizedBox(height: 3),
                  _StatusLabel(connection: connection, comingSoon: comingSoon),
                ],
              ),
            ),
            const SizedBox(width: 8),
            if (comingSoon)
              _ComingSoonBadge()
            else if (_isConnected)
              _DisconnectButton(onTap: onDisconnect)
            else
              _ConnectButton(onTap: onConnect),
          ],
        ),
      ),
    );
  }
}

class _StatusLabel extends StatelessWidget {
  const _StatusLabel({required this.connection, required this.comingSoon});

  final PlatformConnection? connection;
  final bool comingSoon;

  @override
  Widget build(BuildContext context) {
    if (comingSoon) {
      return Text(
        'Coming soon',
        style:
            AppTextStyles.labelSmall.copyWith(color: AppColors.textSecondary),
      );
    }

    if (connection == null ||
        connection!.status == ConnectionStatus.disconnected) {
      return Text(
        'Not connected',
        style:
            AppTextStyles.labelSmall.copyWith(color: AppColors.textSecondary),
      );
    }

    if (connection!.status == ConnectionStatus.expired) {
      return Text(
        'Token expired — reconnect',
        style: AppTextStyles.labelSmall.copyWith(color: AppColors.warning),
      );
    }

    final connectedAt = connection!.connectedAt;
    final dateStr = connectedAt != null
        ? DateFormat('d MMM yyyy').format(connectedAt)
        : '';

    return Row(
      children: [
        Container(
          width: 7,
          height: 7,
          decoration: const BoxDecoration(
            color: AppColors.success,
            shape: BoxShape.circle,
          ),
        ),
        const SizedBox(width: 5),
        Text(
          'Connected${dateStr.isNotEmpty ? ' · $dateStr' : ''}',
          style: AppTextStyles.labelSmall.copyWith(color: AppColors.success),
        ),
      ],
    );
  }
}

class _ConnectButton extends StatelessWidget {
  const _ConnectButton({required this.onTap});

  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return FilledButton(
      onPressed: onTap,
      style: FilledButton.styleFrom(
        backgroundColor: AppColors.primary,
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
        minimumSize: Size.zero,
        tapTargetSize: MaterialTapTargetSize.shrinkWrap,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
      ),
      child: const Text('Connect', style: TextStyle(fontSize: 13)),
    );
  }
}

class _DisconnectButton extends StatelessWidget {
  const _DisconnectButton({required this.onTap});

  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return OutlinedButton(
      onPressed: onTap,
      style: OutlinedButton.styleFrom(
        foregroundColor: AppColors.error,
        side: const BorderSide(color: AppColors.error),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
        minimumSize: Size.zero,
        tapTargetSize: MaterialTapTargetSize.shrinkWrap,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
      ),
      child: const Text('Disconnect', style: TextStyle(fontSize: 13)),
    );
  }
}

class _ComingSoonBadge extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: AppColors.textSecondary.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(6),
      ),
      child: Text(
        'Soon',
        style: AppTextStyles.labelSmall.copyWith(
          color: AppColors.textSecondary,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }
}
