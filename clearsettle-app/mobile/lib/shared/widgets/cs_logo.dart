import 'package:flutter/material.dart';

// ── Brand palette (self-contained — no theme dependency) ─────────────────────
const _teal = Color(0xFF0ABFCA);
const _navy = Color(0xFF0A1628);

const String _logoAsset = 'assets/images/clear_settle_logo_fintech_v4.png';

// ── White-to-transparent color matrix ────────────────────────────────────────
// Applied formula (normalized [0,1] per channel):
//   Alpha_out = 3 − R − G − B
//
//   • Pure white  (1, 1, 1) → A = 3−3   = 0   → fully transparent ✅
//   • Pure black  (0, 0, 0) → A = 3−0   = 3→1 → fully opaque      ✅
//   • Teal        (~0,.75,.79) → A ≈ 1.46→1  → fully opaque      ✅
//   • Mid-gray    (0.5,0.5,0.5) → A = 1.5→1 → fully opaque      ✅
//
// RGB channels are passed through unchanged — logo colors are preserved.
const _kWhiteRemove = ColorFilter.matrix([
  1,  0,  0, 0, 0,
  0,  1,  0, 0, 0,
  0,  0,  1, 0, 0,
  -1, -1, -1, 0, 3,
]);

// ─────────────────────────────────────────────────────────────────────────────
// CsLogoBadge — primary logo widget for headers and nav bars
// ─────────────────────────────────────────────────────────────────────────────

/// Premium ClearSettle logo badge — no white box, native dark-UI look.
///
/// Features:
///   • White PNG background removed via color-matrix filter (colors preserved)
///   • Subtle radial teal gradient (5–8% opacity) replaces the white square
///   • Soft outer teal glow shadow matching the brand color
///   • Circle clip with anti-aliased edges
///   • Scales to any [size] — default 44 for header use
class CsLogoBadge extends StatelessWidget {
  const CsLogoBadge({
    super.key,
    this.size = 44.0,
    this.glow  = true,
  });

  final double size;

  /// Set to false in dense lists or when many badges appear together.
  final bool glow;

  @override
  Widget build(BuildContext context) {
    return Container(
      width:  size,
      height: size,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        // 5–8% teal radial gradient — replaces the white square
        gradient: RadialGradient(
          center: Alignment.center,
          radius: 0.9,
          colors: [
            _teal.withValues(alpha: 0.08),
            _navy.withValues(alpha: 0.04),
            Colors.transparent,
          ],
          stops: const [0.0, 0.55, 1.0],
        ),
        boxShadow: glow
            ? [
                // Tight inner glow
                BoxShadow(
                  color: _teal.withValues(alpha: 0.18),
                  blurRadius: size * 0.36,
                  spreadRadius: 0,
                ),
              ]
            : null,
      ),
      child: Padding(
        // Small inset so gradient ring is visible around the mark
        padding: EdgeInsets.all(size * 0.06),
        child: ColorFiltered(
          colorFilter: _kWhiteRemove,
          child: Image.asset(
            _logoAsset,
            fit: BoxFit.contain,
            errorBuilder: (_, __, ___) => Icon(
              Icons.account_balance_outlined,
              color: _teal,
              size: size * 0.58,
            ),
          ),
        ),
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// CsLogoSplash — large version for splash / onboarding screens
// ─────────────────────────────────────────────────────────────────────────────

/// Large logo for the splash screen with two-layer glow (inner + diffuse outer).
class CsLogoSplash extends StatelessWidget {
  const CsLogoSplash({super.key, this.size = 120.0});
  final double size;

  @override
  Widget build(BuildContext context) {
    return Container(
      width:  size,
      height: size,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        gradient: RadialGradient(
          center: Alignment.center,
          radius: 1.0,
          colors: [
            _teal.withValues(alpha: 0.11),
            _teal.withValues(alpha: 0.04),
            Colors.transparent,
          ],
          stops: const [0.0, 0.52, 1.0],
        ),
        boxShadow: [
          // Inner crisp glow
          BoxShadow(
            color: _teal.withValues(alpha: 0.22),
            blurRadius: size * 0.28,
            spreadRadius: 0,
          ),
          // Outer diffuse atmosphere
          BoxShadow(
            color: _teal.withValues(alpha: 0.08),
            blurRadius: size * 0.75,
            spreadRadius: size * 0.08,
          ),
        ],
      ),
      child: Padding(
        padding: EdgeInsets.all(size * 0.09),
        child: ColorFiltered(
          colorFilter: _kWhiteRemove,
          child: Image.asset(
            _logoAsset,
            fit: BoxFit.contain,
            errorBuilder: (_, __, ___) => Icon(
              Icons.account_balance_outlined,
              color: _teal,
              size: size * 0.58,
            ),
          ),
        ),
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// CsWordmark — logo badge + "ClearSettle" gradient text in one row
// ─────────────────────────────────────────────────────────────────────────────

/// Horizontally aligned logo + wordmark, vertically centred on the same axis.
/// Drop-in replacement for the manual Row + ShaderMask pattern in every screen.
class CsWordmark extends StatelessWidget {
  const CsWordmark({
    super.key,
    this.logoSize  = 44.0,
    this.fontSize  = 22.0,
    this.spacing   = 12.0,
  });

  final double logoSize;
  final double fontSize;
  final double spacing;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.center,
      children: [
        CsLogoBadge(size: logoSize),
        SizedBox(width: spacing),
        ShaderMask(
          shaderCallback: (bounds) => const LinearGradient(
            colors: [_teal, Color(0xFF7FE4EC)],
            begin: Alignment.centerLeft,
            end: Alignment.centerRight,
          ).createShader(bounds),
          child: Text(
            'ClearSettle',
            style: TextStyle(
              fontSize: fontSize,
              fontWeight: FontWeight.w800,
              color: Colors.white,    // masked by ShaderMask
              letterSpacing: -0.5,
              height: 1.0,
            ),
          ),
        ),
      ],
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// CsLogo — backward-compat shim
// ─────────────────────────────────────────────────────────────────────────────

/// Legacy widget — delegates to [CsLogoBadge].
/// New screens should use [CsLogoBadge] or [CsWordmark] directly.
class CsLogo extends StatelessWidget {
  const CsLogo({
    super.key,
    this.size = 44,
    this.borderRadius = 0,
    this.backgroundColor,
    this.padding = EdgeInsets.zero,
  });

  final double size;
  final double borderRadius;
  final Color? backgroundColor;
  final EdgeInsets padding;

  @override
  Widget build(BuildContext context) => CsLogoBadge(size: size);
}
