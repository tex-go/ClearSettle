import 'package:flutter/material.dart';

import 'app_colors.dart';

/// ClearSettle typography — enterprise FinTech scale v2.0
///
/// Font     : Inter (Google Fonts) — standard for financial products (Stripe, Brex, Mercury).
/// Mono     : JetBrains Mono — order IDs, transaction codes, amount columns.
/// Figures  : tabularFigures on all metric styles so currency columns align.
/// Tracking : Negative on large display, positive on labels (Bloomberg convention).
abstract final class AppTextStyles {
  static const String _font  = 'Inter';
  static const String _mono  = 'JetBrains Mono';

  // ── Financial Metrics — the most important scale ───────────────────────────
  // ₹1,24,892 must dominate. Sellers scan numbers before reading anything else.

  /// Hero metric — dashboard KPI, full-width card. e.g. ₹1,24,892
  static const TextStyle metricHero = TextStyle(
    fontFamily: _font,
    fontSize: 36,
    fontWeight: FontWeight.w700,
    color: AppColors.textPrimary,
    letterSpacing: -1.2,
    height: 1.0,
    fontFeatures: [FontFeature.tabularFigures()],
  );

  /// Large metric — standard KPI card. e.g. ₹24,500
  static const TextStyle metricLarge = TextStyle(
    fontFamily: _font,
    fontSize: 28,
    fontWeight: FontWeight.w700,
    color: AppColors.textPrimary,
    letterSpacing: -0.8,
    height: 1.1,
    fontFeatures: [FontFeature.tabularFigures()],
  );

  /// Medium metric — compact card, list rows. e.g. ₹8,421
  static const TextStyle metricMedium = TextStyle(
    fontFamily: _font,
    fontSize: 22,
    fontWeight: FontWeight.w600,
    color: AppColors.textPrimary,
    letterSpacing: -0.4,
    height: 1.1,
    fontFeatures: [FontFeature.tabularFigures()],
  );

  /// Small metric — inline amounts, table cells.
  static const TextStyle metricSmall = TextStyle(
    fontFamily: _font,
    fontSize: 16,
    fontWeight: FontWeight.w600,
    color: AppColors.textPrimary,
    letterSpacing: -0.2,
    height: 1.2,
    fontFeatures: [FontFeature.tabularFigures()],
  );

  /// Inline amount — body text rows, subtle financial figures.
  static const TextStyle metricInline = TextStyle(
    fontFamily: _font,
    fontSize: 14,
    fontWeight: FontWeight.w600,
    color: AppColors.textPrimary,
    letterSpacing: 0.0,
    fontFeatures: [FontFeature.tabularFigures()],
  );

  // ── Display ────────────────────────────────────────────────────────────────

  static const TextStyle displayLarge = TextStyle(
    fontFamily: _font,
    fontSize: 40,
    fontWeight: FontWeight.w700,
    color: AppColors.textPrimary,
    letterSpacing: -1.5,
    height: 1.1,
  );

  static const TextStyle displayMedium = TextStyle(
    fontFamily: _font,
    fontSize: 32,
    fontWeight: FontWeight.w700,
    color: AppColors.textPrimary,
    letterSpacing: -0.8,
    height: 1.15,
  );

  static const TextStyle displaySmall = TextStyle(
    fontFamily: _font,
    fontSize: 24,
    fontWeight: FontWeight.w700,
    color: AppColors.textPrimary,
    letterSpacing: -0.4,
    height: 1.25,
  );

  // ── Headline ───────────────────────────────────────────────────────────────

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

  // ── Title ──────────────────────────────────────────────────────────────────

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

  // ── Body ───────────────────────────────────────────────────────────────────

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

  // ── Label ──────────────────────────────────────────────────────────────────

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

  // ── Overline / Eyebrow ─────────────────────────────────────────────────────
  // Used for metric card labels: "NET SETTLEMENT", "PENDING PAYOUT"
  // ALL CAPS in usage — letterSpacing 0.8 creates premium Bloomberg feel.

  static const TextStyle overline = TextStyle(
    fontFamily: _font,
    fontSize: 10,
    fontWeight: FontWeight.w600,
    color: AppColors.textMuted,
    letterSpacing: 0.8,
  );

  // ── Monospace — order IDs, transaction codes, table amounts ───────────────

  static const TextStyle monoMedium = TextStyle(
    fontFamily: _mono,
    fontSize: 12,
    fontWeight: FontWeight.w500,
    color: AppColors.textSecondary,
    letterSpacing: 0.2,
    height: 1.4,
  );

  static const TextStyle monoSmall = TextStyle(
    fontFamily: _mono,
    fontSize: 11,
    fontWeight: FontWeight.w400,
    color: AppColors.textMuted,
    letterSpacing: 0.1,
    height: 1.4,
  );

  // ── Legacy compat aliases ──────────────────────────────────────────────────
  static TextStyle get amountLarge  => metricLarge;
  static TextStyle get amountMedium => metricMedium;
  static TextStyle get amountSmall  => metricSmall;
  static const TextStyle mono = monoMedium;
}

/// 8-point spacing grid.
abstract final class AppSpacing {
  static const double s1 =  4;
  static const double s2 =  8;
  static const double s3 = 12;
  static const double s4 = 16;  // Default page padding
  static const double s5 = 20;
  static const double s6 = 24;  // Card padding
  static const double s7 = 32;  // Section spacing
  static const double s8 = 40;  // Page top padding
  static const double s9 = 48;  // Hero spacing

  static const double pageHorizontal = 16;
  static const double cardPadding    = 20;
  static const double sectionGap     = 24;
}

/// Border-radius tokens.
abstract final class AppRadius {
  static const double r1 = 6;   // chips, tags
  static const double r2 = 8;   // inputs, small buttons
  static const double r3 = 12;  // buttons (default)
  static const double r4 = 16;  // cards (default)
  static const double r5 = 20;  // modals
  static const double r6 = 24;  // hero card, bottom sheets

  static BorderRadius get card   => BorderRadius.circular(r4);
  static BorderRadius get button => BorderRadius.circular(r3);
  static BorderRadius get input  => BorderRadius.circular(r2);
  static BorderRadius get chip   => BorderRadius.circular(r1);
  static BorderRadius get modal  => BorderRadius.circular(r5);
  static BorderRadius get hero   => BorderRadius.circular(r6);
}

/// Shadow tokens — premium, institutional depth.
abstract final class AppShadows {
  static const BoxShadow sh1 = BoxShadow(
    color: Color(0x08081B2E),
    blurRadius: 4,
    offset: Offset(0, 1),
  );

  static const BoxShadow sh2 = BoxShadow(
    color: Color(0x10081B2E),
    blurRadius: 16,
    offset: Offset(0, 4),
    spreadRadius: -2,
  );

  static const BoxShadow sh3 = BoxShadow(
    color: Color(0x18081B2E),
    blurRadius: 32,
    offset: Offset(0, 8),
    spreadRadius: -4,
  );

  static const List<BoxShadow> card     = [sh1, sh2];
  static const List<BoxShadow> hover    = [sh2, sh3];
  static const List<BoxShadow> modal    = [sh3];

  // Teal glow on primary CTA
  static const List<BoxShadow> ctaButton = [
    BoxShadow(
      color: Color(0x400DB7A3),
      blurRadius: 12,
      offset: Offset(0, 4),
    ),
  ];

  static const List<BoxShadow> heroCard = [
    BoxShadow(
      color: Color(0x30081B2E),
      blurRadius: 24,
      offset: Offset(0, 8),
      spreadRadius: -4,
    ),
  ];
}

/// Motion tokens — stable, predictable, trustworthy.
/// No elastic, no bounce, no spring physics. This is a financial product.
abstract final class AppDurations {
  static const micro    = Duration(milliseconds: 100); // State feedback (tap)
  static const fast     = Duration(milliseconds: 180); // List items, chips
  static const standard = Duration(milliseconds: 250); // Cards, panels
  static const moderate = Duration(milliseconds: 350); // Page transitions
  static const slow     = Duration(milliseconds: 500); // Modal sheets, overlays
  static const countUp  = Duration(milliseconds: 1200); // Number count-up
  static const parse    = Duration(milliseconds: 800);  // Parse step reveal
}

abstract final class AppCurves {
  static const enter      = Curves.easeOut;
  static const exit       = Curves.easeIn;
  static const move       = Curves.easeInOut;
  static const dataReveal = Curves.decelerate;
  static const pageEnter  = Curves.easeOutCubic;
  static const pageExit   = Curves.easeInCubic;
}
