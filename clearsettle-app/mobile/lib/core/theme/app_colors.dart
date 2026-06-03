import 'package:flutter/material.dart';

/// ClearSettle design tokens — premium fintech palette.
///
/// Primary:   #0F172A  (dark navy — replaces heavy cyan)
/// Accent:    #14B8A6  (teal — used sparingly for highlights)
/// Background:#F8FAFC  (off-white, not stark white)
abstract final class AppColors {
  // ── Brand ─────────────────────────────────────────────────────────────────
  /// Primary — dark navy. Used for text, active nav, prominent UI.
  static const Color primary      = Color(0xFF0F172A);
  static const Color primaryDark  = Color(0xFF1E293B);
  static const Color primaryLight = Color(0xFF334155);

  /// Accent — teal. Used sparingly: CTAs, badges, highlights.
  static const Color accent      = Color(0xFF14B8A6);
  static const Color accentDark  = Color(0xFF0D9488);
  static const Color accentLight = Color(0xFF5EEAD4);

  /// Hero gradient — dark navy → teal
  static const LinearGradient heroGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [Color(0xFF0F172A), Color(0xFF134E4A)],
    stops: [0.0, 1.0],
  );

  /// Accent gradient — teal variant for cards
  static const LinearGradient accentGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [Color(0xFF134E4A), Color(0xFF14B8A6)],
  );

  // ── Semantic ──────────────────────────────────────────────────────────────
  static const Color success = Color(0xFF10B981);
  static const Color warning = Color(0xFFF59E0B);
  static const Color error   = Color(0xFFEF4444);
  static const Color info    = Color(0xFF3B82F6);
  static const Color purple  = Color(0xFF8B5CF6);

  // ── Financial helpers ─────────────────────────────────────────────────────
  static const Color positive = success;
  static const Color negative = error;
  static const Color neutral  = Color(0xFF94A3B8);

  // ── Light-mode surfaces ───────────────────────────────────────────────────
  static const Color background       = Color(0xFFF8FAFC);
  static const Color backgroundLight  = Color(0xFFF8FAFC);
  static const Color surface          = Color(0xFFFFFFFF);
  static const Color surfaceVariant   = Color(0xFFF1F5F9);
  static const Color surfaceVariant2  = Color(0xFFE2E8F0);

  // ── Dark-mode surfaces ────────────────────────────────────────────────────
  static const Color backgroundDark     = Color(0xFF0F172A);
  static const Color surfaceDark        = Color(0xFF1E293B);
  static const Color surfaceVariantDark = Color(0xFF334155);

  // ── Dark-navy alias (hero card, top bar) ──────────────────────────────────
  static const Color darkNavy  = primary;
  static const Color darkNavy2 = primaryDark;
  static const Color accentNavy = primaryLight;

  // ── Borders / Dividers ────────────────────────────────────────────────────
  static const Color divider     = Color(0xFFE2E8F0);
  static const Color dividerDark = Color(0x1AFFFFFF);

  // ── Light-mode text ───────────────────────────────────────────────────────
  static const Color textPrimary   = Color(0xFF0F172A);
  static const Color textSecondary = Color(0xFF64748B);
  static const Color textMuted     = Color(0xFF94A3B8);
  static const Color textDisabled  = Color(0xFFCBD5E1);
  static const Color textInverse   = Color(0xFFFFFFFF);

  // ── Dark-mode text ────────────────────────────────────────────────────────
  static const Color textPrimaryDark   = Color(0xFFF1F5F9);
  static const Color textSecondaryDark = Color(0xFF94A3B8);
  static const Color textMutedDark     = Color(0xFF64748B);

  // ── Backward-compat aliases ───────────────────────────────────────────────
  /// Legacy teal alias — maps to new accent color.
  static const Color teal     = accent;
  static const Color tealDark = accentDark;
  static const Color primary2 = primaryDark;  // secondary in design spec

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
