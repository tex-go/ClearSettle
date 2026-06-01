import 'package:flutter/material.dart';

import 'app_colors.dart';

/// Typography sourced from ClearSettle web app (index.css).
/// Web font: 'Plus Jakarta Sans' — mobile uses system sans-serif as fallback
/// since google_fonts is not in the dependency tree.
/// Weights: 500 (body), 600 (semibold), 700 (bold), 800 (extrabold)
abstract final class AppTextStyles {
  // Web uses 'Plus Jakarta Sans' — closest system match is sans-serif
  static const String _font = 'sans-serif';

  // ── Display (web: 2xl = clamp(20,3vw,28)) ────────────────────────────────

  static const TextStyle displayLarge = TextStyle(
    fontFamily: _font, fontSize: 28,
    fontWeight: FontWeight.w700, color: AppColors.textPrimary, letterSpacing: -0.5,
    height: 1.2,
  );

  static const TextStyle displayMedium = TextStyle(
    fontFamily: _font, fontSize: 22,
    fontWeight: FontWeight.w700, color: AppColors.textPrimary, letterSpacing: -0.3,
    height: 1.25,
  );

  // ── Headline (web: xl = clamp(18,2.5vw,22)) ──────────────────────────────

  static const TextStyle headlineLarge = TextStyle(
    fontFamily: _font, fontSize: 20,
    fontWeight: FontWeight.w800, color: AppColors.textPrimary,
    letterSpacing: -0.3, height: 1.3,
  );

  static const TextStyle headlineMedium = TextStyle(
    fontFamily: _font, fontSize: 18,
    fontWeight: FontWeight.w700, color: AppColors.textPrimary,
    letterSpacing: -0.2, height: 1.3,
  );

  // ── Title (web: lg = clamp(15,2vw,18)) ───────────────────────────────────

  static const TextStyle titleLarge = TextStyle(
    fontFamily: _font, fontSize: 17,
    fontWeight: FontWeight.w600, color: AppColors.textPrimary,
    height: 1.35,
  );

  static const TextStyle titleMedium = TextStyle(
    fontFamily: _font, fontSize: 15,
    fontWeight: FontWeight.w600, color: AppColors.textPrimary,
    height: 1.35,
  );

  // ── Body (web: base = 14, md = 15) ───────────────────────────────────────

  static const TextStyle bodyLarge = TextStyle(
    fontFamily: _font, fontSize: 15,
    fontWeight: FontWeight.w500, color: AppColors.textPrimary,
    height: 1.5,
  );

  static const TextStyle bodyMedium = TextStyle(
    fontFamily: _font, fontSize: 14,
    fontWeight: FontWeight.w500, color: AppColors.textPrimary,
    height: 1.5,
  );

  static const TextStyle bodySmall = TextStyle(
    fontFamily: _font, fontSize: 12,
    fontWeight: FontWeight.w500, color: AppColors.textSecondary,
    height: 1.45,
  );

  // ── Label (web: sm = 12, xs = 11) ────────────────────────────────────────

  static const TextStyle labelLarge = TextStyle(
    fontFamily: _font, fontSize: 13,
    fontWeight: FontWeight.w600, color: AppColors.textSecondary,
    letterSpacing: 0.1,
  );

  static const TextStyle labelMedium = TextStyle(
    fontFamily: _font, fontSize: 12,
    fontWeight: FontWeight.w600, color: AppColors.textSecondary,
    letterSpacing: 0.3,
  );

  static const TextStyle labelSmall = TextStyle(
    fontFamily: _font, fontSize: 11,
    fontWeight: FontWeight.w600, color: AppColors.textMuted,
    letterSpacing: 0.5,
  );

  // ── Financial amounts ─────────────────────────────────────────────────────

  static const TextStyle amountLarge = TextStyle(
    fontFamily: _font, fontSize: 28,
    fontWeight: FontWeight.w700, color: AppColors.positive,
    letterSpacing: -0.5,
  );

  static const TextStyle amountMedium = TextStyle(
    fontFamily: _font, fontSize: 20,
    fontWeight: FontWeight.w700, color: AppColors.positive,
  );

  static const TextStyle amountSmall = TextStyle(
    fontFamily: _font, fontSize: 15,
    fontWeight: FontWeight.w700, color: AppColors.textPrimary,
  );

  // ── Monospace (for IDs, reference numbers) ───────────────────────────────
  static const TextStyle mono = TextStyle(
    fontFamily: 'monospace', fontSize: 12,
    fontWeight: FontWeight.w500, color: AppColors.textSecondary,
    letterSpacing: 0.3,
  );
}

/// Spacing tokens (web: --s1=4 → --s8=32)
abstract final class AppSpacing {
  static const double s1 = 4;
  static const double s2 = 8;
  static const double s3 = 12;
  static const double s4 = 16;
  static const double s5 = 20;
  static const double s6 = 24;
  static const double s7 = 28;
  static const double s8 = 32;
}

/// Border radius tokens (web: --r1=6 → --r6=24)
abstract final class AppRadius {
  static const double r1 = 6;   // chips, tags
  static const double r2 = 9;   // inputs
  static const double r3 = 12;  // cards (small)
  static const double r4 = 14;  // cards (default)
  static const double r5 = 18;  // modals
  static const double r6 = 24;  // large surfaces, bottom sheets

  static BorderRadius get card     => BorderRadius.circular(r4);
  static BorderRadius get input    => BorderRadius.circular(r2);
  static BorderRadius get chip     => BorderRadius.circular(r1);
  static BorderRadius get modal    => BorderRadius.circular(r5);
}

/// Shadow tokens (web: --sh1 → --sh4)
abstract final class AppShadows {
  // 0 1px 3px rgba(13,31,53,.06)
  static const BoxShadow sh1 = BoxShadow(
    color: Color(0x0F0D1F35), blurRadius: 3, offset: Offset(0, 1),
  );
  // 0 4px 16px rgba(13,31,53,.08)
  static const BoxShadow sh2 = BoxShadow(
    color: Color(0x140D1F35), blurRadius: 16, offset: Offset(0, 4),
  );
  // 0 8px 32px rgba(13,31,53,.12)
  static const BoxShadow sh3 = BoxShadow(
    color: Color(0x1E0D1F35), blurRadius: 32, offset: Offset(0, 8),
  );

  static const List<BoxShadow> card  = [sh1];
  static const List<BoxShadow> hover = [sh2];
  static const List<BoxShadow> modal = [sh3];

  // Teal CTA button glow (web: btn-p box-shadow)
  static const List<BoxShadow> ctaButton = [
    BoxShadow(color: Color(0x400ABFCA), blurRadius: 8, offset: Offset(0, 2)),
  ];
}
