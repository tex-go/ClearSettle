import 'package:flutter/material.dart';

import '../../core/theme/app_colors.dart';

/// ClearSettle brand logo — v4 fintech PNG with transparent background.
///
/// Renders the logo directly on any surface — dark, light, colored.
/// No white container. The PNG transparency blends naturally.
class CsLogo extends StatelessWidget {
  const CsLogo({
    super.key,
    this.size = 44,
    this.borderRadius = 0,
    this.backgroundColor,
    this.padding = EdgeInsets.zero,
  });

  final double size;

  /// Ignored unless explicitly set — logo is transparent by default.
  final double borderRadius;

  /// Optional tinted background. Pass null (default) for fully transparent.
  final Color? backgroundColor;
  final EdgeInsets padding;

  static const String _asset = 'assets/images/clear_settle_logo_fintech_v4.png';

  @override
  Widget build(BuildContext context) {
    Widget img = Image.asset(
      _asset,
      width: size,
      height: size,
      fit: BoxFit.contain,
      errorBuilder: (_, __, ___) => Icon(
        Icons.account_balance_outlined,
        color: AppColors.teal500,
        size: size * 0.6,
      ),
    );

    if (backgroundColor != null || padding != EdgeInsets.zero) {
      img = Container(
        width: size,
        height: size,
        padding: padding,
        decoration: backgroundColor != null
            ? BoxDecoration(
                color: backgroundColor,
                borderRadius: BorderRadius.circular(borderRadius),
              )
            : null,
        child: img,
      );
    }

    return img;
  }
}
