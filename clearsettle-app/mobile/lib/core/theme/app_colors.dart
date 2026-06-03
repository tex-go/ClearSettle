import 'package:flutter/material.dart';

/// Design tokens — ClearSettle brand palette.
///
/// Web-app specification (latest):
///   Primary (CTA/teal):  #00C2D1
///   Dark Navy (bg):      #061B3A
///   Accent navy:         #0D2A52
///   Success:             #00C27A
///   Warning:             #F59E0B
///   Error:               #EF4444
abstract final class AppColors {
  // ── Brand ─────────────────────────────────────────────────────────────────
  /// Primary CTA — teal/cyan — buttons, active nav, highlights.
  static const Color primary      = Color(0xFF00C2D1);
  static const Color primaryDark  = Color(0xFF009BAA); // darker teal for pressed
  static const Color primaryLight = Color(0xFF33CDD9); // lighter teal for hover

  /// Dark navy — page backgrounds in dark mode, sidebar.
  static const Color darkNavy     = Color(0xFF061B3A);
  static const Color darkNavy2    = Color(0xFF0A2347); // slightly lighter
  static const Color accentNavy   = Color(0xFF0D2A52); // card surfaces dark mode

  // ── Semantic ──────────────────────────────────────────────────────────────
  static const Color success = Color(0xFF00C27A);
  static const Color warning = Color(0xFFF59E0B);
  static const Color error   = Color(0xFFEF4444);
  static const Color info    = Color(0xFF3B82F6);
  static const Color purple  = Color(0xFF7B52E8);

  // ── Financial helpers ─────────────────────────────────────────────────────
  static const Color positive = success;
  static const Color negative = error;
  static const Color neutral  = Color(0xFF8FA5BD);

  // ── Light-mode surfaces ───────────────────────────────────────────────────
  static const Color backgroundLight  = Color(0xFFF1F5F9);
  static const Color surface          = Color(0xFFFFFFFF);
  static const Color surfaceVariant   = Color(0xFFF1F5F9);
  static const Color surfaceVariant2  = Color(0xFFE8F0F8);

  // ── Dark-mode surfaces ────────────────────────────────────────────────────
  static const Color backgroundDark      = darkNavy;      // #061B3A
  static const Color surfaceDark         = accentNavy;    // #0D2A52
  static const Color surfaceVariantDark  = Color(0xFF133264); // slightly lighter

  // ── Borders / Dividers ────────────────────────────────────────────────────
  static const Color divider     = Color(0xFFE2EBF3);
  static const Color dividerDark = Color(0x14FFFFFF);

  // ── Light-mode text ───────────────────────────────────────────────────────
  static const Color textPrimary   = Color(0xFF061B3A); // darkNavy
  static const Color textSecondary = Color(0xFF4B6080);
  static const Color textMuted     = Color(0xFF8FA5BD);
  static const Color textDisabled  = Color(0xFFB8CADA);
  static const Color textInverse   = Color(0xFFFFFFFF);

  // ── Dark-mode text ────────────────────────────────────────────────────────
  static const Color textPrimaryDark   = Color(0xFFE2EBF3);
  static const Color textSecondaryDark = Color(0xFF8FA5BD);
  static const Color textMutedDark     = Color(0xFF4B6080);

  // ── Backward-compat aliases ───────────────────────────────────────────────
  /// Use [primary] for teal CTA colour throughout the app.
  static const Color teal     = primary;
  static const Color tealDark = primaryDark;
  static const Color accent   = primary;
  static const Color accentDark = primaryDark;

  // ── Marketplace brand colours ──────────────────────────────────────────────
  static const Color flipkart  = Color(0xFF2874F0);
  static const Color amazon    = Color(0xFFFF9900);
  static const Color meesho    = Color(0xFF9B1FE8);
  static const Color myntra    = Color(0xFFFF3E6C);
  static const Color shopify   = Color(0xFF96BF48);
  static const Color nykaa     = Color(0xFFFC2779);
  static const Color ajio      = Color(0xFFE03018);
  static const Color snapdeal  = Color(0xFFE40046);
  static const Color jiomart   = Color(0xFF0071F6);
}
