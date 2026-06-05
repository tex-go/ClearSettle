import 'package:flutter/material.dart';

import '../../../../core/theme/app_colors.dart';

/// Supported social login providers.
enum SocialProvider {
  google,
  instagram,
  microsoft,    // future
  apple,        // future
  linkedin,     // future
}

extension SocialProviderX on SocialProvider {
  String get label {
    switch (this) {
      case SocialProvider.google:    return 'Continue with Google';
      case SocialProvider.instagram: return 'Continue with Instagram';
      case SocialProvider.microsoft: return 'Continue with Microsoft';
      case SocialProvider.apple:     return 'Continue with Apple';
      case SocialProvider.linkedin:  return 'Continue with LinkedIn';
    }
  }

  Color get brandColor {
    switch (this) {
      case SocialProvider.google:    return const Color(0xFF4285F4);
      case SocialProvider.instagram: return const Color(0xFFE1306C);
      case SocialProvider.microsoft: return const Color(0xFF00A4EF);
      case SocialProvider.apple:     return Colors.white;
      case SocialProvider.linkedin:  return const Color(0xFF0077B5);
    }
  }

  Color get backgroundColor {
    switch (this) {
      case SocialProvider.google:    return const Color(0xFF1A2F4A);
      case SocialProvider.instagram: return const Color(0xFF1A2030);
      case SocialProvider.microsoft: return const Color(0xFF1A2B3A);
      case SocialProvider.apple:     return const Color(0xFF1A1A1A);
      case SocialProvider.linkedin:  return const Color(0xFF0E2C40);
    }
  }

  Widget get icon {
    switch (this) {
      case SocialProvider.google:
        return _GoogleIcon();
      case SocialProvider.instagram:
        return _InstagramIcon();
      case SocialProvider.microsoft:
        return Icon(Icons.window_rounded, color: brandColor, size: 20);
      case SocialProvider.apple:
        return Icon(Icons.apple_rounded, color: Colors.white, size: 22);
      case SocialProvider.linkedin:
        return Icon(Icons.work_rounded, color: brandColor, size: 20);
    }
  }
}

/// A production-grade social login button.
///
/// Usage:
/// ```dart
/// SocialLoginButton(
///   provider: SocialProvider.google,
///   onPressed: () => _handleGoogleLogin(),
///   isLoading: state.isGoogleLoading,
/// )
/// ```
///
/// Adding a new provider:
///   1. Add an enum value to [SocialProvider]
///   2. Fill in the extension fields (label, color, icon)
///   3. Pass the provider to this widget — no other changes needed
class SocialLoginButton extends StatelessWidget {
  const SocialLoginButton({
    super.key,
    required this.provider,
    required this.onPressed,
    this.isLoading = false,
    this.isDisabled = false,
  });

  final SocialProvider provider;
  final VoidCallback? onPressed;
  final bool isLoading;
  final bool isDisabled;

  @override
  Widget build(BuildContext context) {
    final bool active = !isLoading && !isDisabled && onPressed != null;

    return AnimatedOpacity(
      duration: const Duration(milliseconds: 200),
      opacity: active ? 1.0 : 0.55,
      child: GestureDetector(
        onTap: active ? onPressed : null,
        child: Container(
          height: 52,
          decoration: BoxDecoration(
            color: provider.backgroundColor,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: provider.brandColor.withValues(alpha: 0.25),
              width: 1,
            ),
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              if (isLoading)
                SizedBox(
                  width: 20,
                  height: 20,
                  child: CircularProgressIndicator(
                    strokeWidth: 2,
                    color: provider.brandColor,
                  ),
                )
              else
                provider.icon,
              const SizedBox(width: 12),
              Text(
                provider.label,
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 14,
                  fontWeight: FontWeight.w600,
                  letterSpacing: 0.2,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Divider between email/password form and social buttons.
class SocialDivider extends StatelessWidget {
  const SocialDivider({super.key, this.text = 'or continue with'});
  final String text;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Expanded(child: Divider(color: AppColors.border, thickness: 1)),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: Text(
            text,
            style: TextStyle(
              color: AppColors.textMuted,
              fontSize: 12,
              fontWeight: FontWeight.w500,
              letterSpacing: 0.3,
            ),
          ),
        ),
        Expanded(child: Divider(color: AppColors.border, thickness: 1)),
      ],
    );
  }
}

// ── SVG-free brand icons (inline paths) ──────────────────────────────────────

class _GoogleIcon extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return CustomPaint(
      size: const Size(20, 20),
      painter: _GooglePainter(),
    );
  }
}

class _GooglePainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final double cx = size.width / 2;
    final double cy = size.height / 2;
    final double r  = size.width / 2;

    // White circle background
    canvas.drawCircle(
      Offset(cx, cy),
      r,
      Paint()..color = Colors.white,
    );

    // Google 'G' text (simplified as a colored arc)
    const double gStart  = 0.1;
    const double gSweep  = 1.55;

    // Blue arc
    canvas.drawArc(
      Rect.fromCircle(center: Offset(cx, cy), radius: r * 0.6),
      gStart,
      gSweep,
      false,
      Paint()
        ..color  = const Color(0xFF4285F4)
        ..style  = PaintingStyle.stroke
        ..strokeWidth = r * 0.3,
    );

    // Red arc
    canvas.drawArc(
      Rect.fromCircle(center: Offset(cx, cy), radius: r * 0.6),
      gStart + gSweep,
      1.1,
      false,
      Paint()
        ..color  = const Color(0xFFEA4335)
        ..style  = PaintingStyle.stroke
        ..strokeWidth = r * 0.3,
    );

    // Yellow arc
    canvas.drawArc(
      Rect.fromCircle(center: Offset(cx, cy), radius: r * 0.6),
      gStart + gSweep + 1.1,
      0.7,
      false,
      Paint()
        ..color  = const Color(0xFFFBBC05)
        ..style  = PaintingStyle.stroke
        ..strokeWidth = r * 0.3,
    );

    // Green arc
    canvas.drawArc(
      Rect.fromCircle(center: Offset(cx, cy), radius: r * 0.6),
      gStart + gSweep + 1.8,
      0.7,
      false,
      Paint()
        ..color  = const Color(0xFF34A853)
        ..style  = PaintingStyle.stroke
        ..strokeWidth = r * 0.3,
    );
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

class _InstagramIcon extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return CustomPaint(
      size: const Size(20, 20),
      painter: _InstagramPainter(),
    );
  }
}

class _InstagramPainter extends CustomPainter {
  static const _gradient = LinearGradient(
    begin: Alignment.bottomLeft,
    end: Alignment.topRight,
    colors: [
      Color(0xFFFFD600),
      Color(0xFFFF7A00),
      Color(0xFFFF0069),
      Color(0xFFD300C4),
      Color(0xFF7638FA),
    ],
  );

  @override
  void paint(Canvas canvas, Size size) {
    final rect = Offset.zero & size;
    final rrect = RRect.fromRectAndRadius(rect, Radius.circular(size.width * 0.24));

    // Gradient background
    final paint = Paint()
      ..shader = _gradient.createShader(rect);
    canvas.drawRRect(rrect, paint);

    // White camera outline
    final strokePaint = Paint()
      ..color = Colors.white
      ..style = PaintingStyle.stroke
      ..strokeWidth = size.width * 0.09;

    canvas.drawRRect(
      RRect.fromRectAndRadius(
        Rect.fromCenter(
          center: Offset(size.width / 2, size.height / 2),
          width:  size.width * 0.55,
          height: size.height * 0.55,
        ),
        Radius.circular(size.width * 0.12),
      ),
      strokePaint,
    );

    // White circle (lens)
    canvas.drawCircle(
      Offset(size.width / 2, size.height / 2),
      size.width * 0.16,
      strokePaint,
    );

    // White dot (flash)
    canvas.drawCircle(
      Offset(size.width * 0.72, size.height * 0.28),
      size.width * 0.05,
      Paint()..color = Colors.white,
    );
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
