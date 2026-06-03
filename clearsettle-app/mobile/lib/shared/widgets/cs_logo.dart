import 'package:flutter/material.dart';

import '../../core/theme/app_colors.dart';

/// ClearSettle logo widget — consistent across all screens.
///
/// Always uses BoxFit.contain and never stretches.
/// Falls back to a bank icon if the asset is missing.
class CsLogo extends StatelessWidget {
  const CsLogo({
    super.key,
    this.size = 44,
    this.borderRadius = 10,
    this.backgroundColor,
    this.padding = EdgeInsets.zero,
  });

  /// Square dimension (width = height = size).
  final double size;
  final double borderRadius;

  /// Wraps the logo in a container with this background.
  /// Pass null to render the image without a container.
  final Color? backgroundColor;
  final EdgeInsets padding;

  @override
  Widget build(BuildContext context) {
    final img = Image.asset(
      'assets/images/clear_settle_logo.png',
      width: size,
      height: size,
      fit: BoxFit.contain,
      errorBuilder: (_, __, ___) => Icon(
        Icons.account_balance_outlined,
        color: AppColors.primary,
        size: size * 0.55,
      ),
    );

    if (backgroundColor == null && padding == EdgeInsets.zero) return img;

    return Container(
      width: size,
      height: size,
      padding: padding,
      decoration: backgroundColor != null
          ? BoxDecoration(
              color: backgroundColor,
              borderRadius: BorderRadius.circular(borderRadius),
            )
          : null,
      child: ClipRRect(
        borderRadius: BorderRadius.circular(borderRadius),
        child: img,
      ),
    );
  }
}
