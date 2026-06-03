import 'package:flutter/material.dart';

import '../../core/theme/app_colors.dart';

/// ClearSettle brand logo — v3 teal C + red S symbol.
///
/// Always renders on a white rounded container so the logo looks crisp
/// on any background color (dark or light). Falls back to a bank icon
/// if the asset is missing.
class CsLogo extends StatelessWidget {
  const CsLogo({
    super.key,
    this.size = 44,
    this.borderRadius = 10,
    this.backgroundColor,
    this.padding = EdgeInsets.zero,
  });

  final double size;
  final double borderRadius;

  /// Background behind the logo. Defaults to white so the logo
  /// looks clean on both dark and light surfaces.
  final Color? backgroundColor;
  final EdgeInsets padding;

  static const String _asset = 'assets/images/cs_logo_v3.jpeg';

  @override
  Widget build(BuildContext context) {
    final bg = backgroundColor ?? Colors.white;
    final effectivePadding = padding == EdgeInsets.zero
        ? EdgeInsets.all(size * 0.08)
        : padding;

    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(borderRadius),
      ),
      padding: effectivePadding,
      child: ClipRRect(
        borderRadius: BorderRadius.circular(
            (borderRadius - 2).clamp(0.0, borderRadius)),
        child: Image.asset(
          _asset,
          fit: BoxFit.contain,
          errorBuilder: (_, __, ___) => Icon(
            Icons.account_balance_outlined,
            color: AppColors.teal500,
            size: size * 0.55,
          ),
        ),
      ),
    );
  }
}
