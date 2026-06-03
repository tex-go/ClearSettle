import 'package:flutter/material.dart';

import 'app_colors.dart';

/// ClearSettle typography — premium fintech scale.
///
/// Font: Inter (system fallback). Weights: 400/500/600/700.
/// Scale mirrors Stripe/Linear density: tight leading, negative tracking on
/// large sizes, generous tracking on labels.
abstract final class AppTextStyles {
  static const String _font = 'sans-serif'; // system sans; swap with Google Fonts later

  // ── Display — hero numbers, big metric values ────────────────────────────

  static const TextStyle displayLarge = TextStyle(
    fontFamily: _font,
    fontSize: 32,
    fontWeight: FontWeight.w700,
    color: AppColors.textPrimary,
    letterSpacing: -0.8,
    height: 1.15,
  );

  static const TextStyle displayMedium = TextStyle(
    fontFamily: _font,
    fontSize: 28,
    fontWeight: FontWeight.w700,
    color: AppColors.textPrimary,
    letterSpacing: -0.6,
    height: 1.2,
  );

  static const TextStyle displaySmall = TextStyle(
    fontFamily: _font,
    fontSize: 24,
    fontWeight: FontWeight.w700,
    color: AppColors.textPrimary,
    letterSpacing: -0.4,
    height: 1.25,
  );

  // ── Headline ─────────────────────────────────────────────────────────────

  static const TextStyle headlineLarge = TextStyle(
    fontFamily: _font,
    fontSize: 22,
    fontWeight: FontWeight.w700,
    color: AppColors.textPrimary,
    letterSpacing: -0.3,
    height: 1.3,
  );

  static const TextStyle headlineMedium = TextStyle(
    fontFamily: _font,
    fontSize: 18,
    fontWeight: FontWeight.w700,
    color: AppColors.textPrimary,
    letterSpacing: -0.2,
    height: 1.3,
  );

  static const TextStyle headlineSmall = TextStyle(
    fontFamily: _font,
    fontSize: 16,
    fontWeight: FontWeight.w600,
    color: AppColors.textPrimary,
    letterSpacing: -0.1,
    height: 1.35,
  );

  // ── Title ────────────────────────────────────────────────────────────────

  static const TextStyle titleLarge = TextStyle(
    fontFamily: _font,
    fontSize: 17,
    fontWeight: FontWeight.w600,
    color: AppColors.textPrimary,
    height: 1.35,
  );

  static const TextStyle titleMedium = TextStyle(
    fontFamily: _font,
    fontSize: 15,
    fontWeight: FontWeight.w600,
    color: AppColors.textPrimary,
    height: 1.4,
  );

  static const TextStyle titleSmall = TextStyle(
    fontFamily: _font,
    fontSize: 13,
    fontWeight: FontWeight.w600,
    color: AppColors.textPrimary,
    height: 1.4,
  );

  // ── Body ─────────────────────────────────────────────────────────────────

  static const TextStyle bodyLarge = TextStyle(
    fontFamily: _font,
    fontSize: 15,
    fontWeight: FontWeight.w400,
    color: AppColors.textPrimary,
    height: 1.5,
  );

  static const TextStyle bodyMedium = TextStyle(
    fontFamily: _font,
    fontSize: 14,
    fontWeight: FontWeight.w400,
    color: AppColors.textPrimary,
    height: 1.5,
  );

  static const TextStyle bodySmall = TextStyle(
    fontFamily: _font,
    fontSize: 12,
    fontWeight: FontWeight.w400,
    color: AppColors.textSecondary,
    height: 1.45,
  );

  // ── Label ────────────────────────────────────────────────────────────────

  static const TextStyle labelLarge = TextStyle(
    fontFamily: _font,
    fontSize: 13,
    fontWeight: FontWeight.w600,
    color: AppColors.textSecondary,
    letterSpacing: 0.1,
  );

  static const TextStyle labelMedium = TextStyle(
    fontFamily: _font,
    fontSize: 12,
    fontWeight: FontWeight.w500,
    color: AppColors.textSecondary,
    letterSpacing: 0.2,
  );

  static const TextStyle labelSmall = TextStyle(
    fontFamily: _font,
    fontSize: 11,
    fontWeight: FontWeight.w500,
    color: AppColors.textMuted,
    letterSpacing: 0.3,
  );

  // ── Overline / Eyebrow ────────────────────────────────────────────────────

  static const TextStyle overline = TextStyle(
    fontFamily: _font,
    fontSize: 10,
    fontWeight: FontWeight.w600,
    color: AppColors.textMuted,
    letterSpacing: 0.8,
  );

  // ── Financial amounts ─────────────────────────────────────────────────────

  /// Large metric value on hero card or KPI card.
  static const TextStyle metricLarge = TextStyle(
    fontFamily: _font,
    fontSize: 28,
    fontWeight: FontWeight.w700,
    color: AppColors.textInverse,
    letterSpacing: -0.5,
    height: 1.15,
  );

  /// Standard metric value on analytics card.
  static const TextStyle metricMedium = TextStyle(
    fontFamily: _font,
    fontSize: 22,
    fontWeight: FontWeight.w700,
    color: AppColors.textPrimary,
    letterSpacing: -0.3,
    height: 1.2,
  );

  /// Compact metric for list rows.
  static const TextStyle metricSmall = TextStyle(
    fontFamily: _font,
    fontSize: 16,
    fontWeight: FontWeight.w700,
    color: AppColors.textPrimary,
    letterSpacing: -0.1,
  );

  // Legacy compat aliases
  static const TextStyle amountLarge  = metricLarge;
  static const TextStyle amountMedium = metricMedium;
  static const TextStyle amountSmall  = metricSmall;

  // ── Monospace ─────────────────────────────────────────────────────────────
  static const TextStyle mono = TextStyle(
    fontFamily: 'monospace',
    fontSize: 12,
    fontWeight: FontWeight.w500,
    color: AppColors.textSecondary,
    letterSpacing: 0.3,
  );
}

/// 8-point spacing grid.
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

/// Border-radius tokens.
abstract final class AppRadius {
  static const double r1 = 6;   // chips, tags
  static const double r2 = 8;   // inputs, small buttons
  static const double r3 = 12;  // cards (small)
  static const double r4 = 16;  // cards (default)
  static const double r5 = 20;  // modals
  static const double r6 = 24;  // hero card, bottom sheets

  static BorderRadius get card  => BorderRadius.circular(r4);
  static BorderRadius get input => BorderRadius.circular(r2);
  static BorderRadius get chip  => BorderRadius.circular(r1);
  static BorderRadius get modal => BorderRadius.circular(r5);
  static BorderRadius get hero  => BorderRadius.circular(r6);
}

/// Shadow tokens — premium, subtle depth.
abstract final class AppShadows {
  // Subtle card shadow
  static const BoxShadow sh1 = BoxShadow(
    color: Color(0x080F172A),
    blurRadius: 4,
    offset: Offset(0, 1),
  );
  // Default card shadow
  static const BoxShadow sh2 = BoxShadow(
    color: Color(0x100F172A),
    blurRadius: 16,
    offset: Offset(0, 4),
    spreadRadius: -2,
  );
  // Elevated modal / popover shadow
  static const BoxShadow sh3 = BoxShadow(
    color: Color(0x180F172A),
    blurRadius: 32,
    offset: Offset(0, 8),
    spreadRadius: -4,
  );

  static const List<BoxShadow> card  = [sh1, sh2];
  static const List<BoxShadow> hover = [sh2, sh3];
  static const List<BoxShadow> modal = [sh3];

  // Accent teal glow — used on primary CTA buttons
  static const List<BoxShadow> ctaButton = [
    BoxShadow(
      color: Color(0x4014B8A6),
      blurRadius: 12,
      offset: Offset(0, 4),
    ),
  ];

  // Hero card shadow
  static const List<BoxShadow> heroCard = [
    BoxShadow(
      color: Color(0x300F172A),
      blurRadius: 24,
      offset: Offset(0, 8),
      spreadRadius: -4,
    ),
  ];
}
