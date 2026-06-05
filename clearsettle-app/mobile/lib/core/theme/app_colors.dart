import 'package:flutter/material.dart';

/// ClearSettle design tokens — enterprise FinTech palette v3.0
///
/// Primary Navy : #081B2E  — institutional authority
/// Accent Teal  : #00C896  — financial clarity (spec-aligned)
/// Dark BG      : #0C1020  — dark-first surface
/// Background   : #F7F9FC  — light mode clinical precision
abstract final class AppColors {
  // ── Brand Core ─────────────────────────────────────────────────────────────
  static const Color navy900 = Color(0xFF081B2E);
  static const Color navy800 = Color(0xFF0D2540);
  static const Color navy700 = Color(0xFF123052);
  static const Color navy600 = Color(0xFF1A3F6A);
  static const Color navy500 = Color(0xFF234F82);

  // Spec-aligned teal — #00C896 (vibrant emerald-teal)
  static const Color teal500 = Color(0xFF00C896);
  static const Color teal400 = Color(0xFF00D9A8);
  static const Color teal300 = Color(0xFF33DFB8);
  static const Color teal200 = Color(0xFF80EDD4);
  static const Color teal100 = Color(0xFFCCF8EE);
  static const Color teal50  = Color(0xFFEAFDF8);

  // Teal hover/active
  static const Color tealHover  = Color(0xFF00B588);
  static const Color tealActive = Color(0xFF00A07A);

  // ── Semantic ───────────────────────────────────────────────────────────────
  static const Color success    = Color(0xFF00C896); // unified with teal
  static const Color success100 = Color(0xFFCCF8EE);
  static const Color warning    = Color(0xFFF59E0B);
  static const Color warning100 = Color(0xFFFEF3DC);
  static const Color danger     = Color(0xFFEF4444);
  static const Color danger100  = Color(0xFFFFE4E4);
  static const Color info       = Color(0xFF3B82F6);
  static const Color info100    = Color(0xFFE6F1FE);
  static const Color purple     = Color(0xFF8B5CF6);

  // ── Financial Semantic ─────────────────────────────────────────────────────
  static const Color credit      = Color(0xFF00C896);
  static const Color debit       = Color(0xFFEF4444);
  static const Color pending     = Color(0xFFF59E0B);
  static const Color recoverable = Color(0xFF00C896);
  static const Color neutral     = Color(0xFF64748B);

  // ── Light Mode Surfaces ────────────────────────────────────────────────────
  static const Color background      = Color(0xFFF7F9FC);
  static const Color surface         = Color(0xFFFFFFFF);
  static const Color surfaceAlt      = Color(0xFFF0F4F8);
  static const Color surfaceVariant  = Color(0xFFF1F5F9);
  static const Color surfaceVariant2 = Color(0xFFE2E8F0);

  // ── Dark Mode Surfaces (spec-aligned: deep navy, not pure black) ───────────
  static const Color bgBaseDark          = Color(0xFF080B14); // darkest layer
  static const Color backgroundDark     = Color(0xFF0C1020); // scaffold bg
  static const Color surfaceDark        = Color(0xFF161D2F); // card surface
  static const Color surfaceElevatedDark = Color(0xFF1C2438); // elevated card
  static const Color surfaceHoverDark    = Color(0xFF1F2940);
  static const Color surfaceVariantDark  = Color(0xFF123052); // input fills

  // ── Borders ────────────────────────────────────────────────────────────────
  static const Color border      = Color(0xFFE2E8F0);
  static const Color borderLight = Color(0xFFF1F5F9);
  static const Color divider     = Color(0xFFE2E8F0);
  // Dark borders
  static const Color borderDark        = Color(0xFF2A3555);
  static const Color borderSecondaryDark = Color(0xFF1E2840);
  static const Color borderSubtleDark  = Color(0xFF141B2D);
  static const Color dividerDark       = Color(0x1AFFFFFF); // 10% white

  // ── Text — light mode ──────────────────────────────────────────────────────
  static const Color textPrimary   = Color(0xFF0F172A);
  static const Color textSecondary = Color(0xFF475569);
  static const Color textMuted     = Color(0xFF94A3B8);
  static const Color textDisabled  = Color(0xFFCBD5E1);
  static const Color textInverse   = Color(0xFFFFFFFF);

  // ── Text — dark mode ───────────────────────────────────────────────────────
  static const Color textPrimaryDark   = Color(0xFFF1F5F9);
  static const Color textSecondaryDark = Color(0xFF94A3B8);
  static const Color textMutedDark     = Color(0xFF64748B);
  static const Color textLinkDark      = Color(0xFF00C896);
  static const Color textLinkLight     = Color(0xFF00A87A); // slightly darker for light bg

  // ── Priority / Issue Status ────────────────────────────────────────────────
  static const Color priorityHigh   = Color(0xFFEF4444);
  static const Color priorityMedium = Color(0xFFF59E0B);
  static const Color priorityLow    = Color(0xFF64748B);

  // ── Notification dot colors ────────────────────────────────────────────────
  static const Color dotMissing    = Color(0xFFEF4444); // red
  static const Color dotExcessFee  = Color(0xFFF59E0B); // amber
  static const Color dotSettlement = Color(0xFF00C896); // teal
  static const Color dotUpload     = Color(0xFF3B82F6); // blue
  static const Color dotRecovery   = Color(0xFF00C896); // teal

  // ── Gradients ──────────────────────────────────────────────────────────────
  static const LinearGradient heroGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [Color(0xFF081B2E), Color(0xFF0D2540), Color(0xFF0A3040)],
    stops: [0.0, 0.6, 1.0],
  );

  static const LinearGradient accentGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [Color(0xFF00C896), Color(0xFF00D9A8)],
  );

  static const LinearGradient tealTextGradient = LinearGradient(
    colors: [Color(0xFF00C896), Color(0xFF33DFB8)],
  );

  // ── Chart palette (8-color) ────────────────────────────────────────────────
  static const List<Color> chartPalette = [
    Color(0xFF00C896), // teal (primary)
    Color(0xFF234F82), // navy
    Color(0xFF3B82F6), // blue
    Color(0xFFF59E0B), // amber
    Color(0xFFEF4444), // red
    Color(0xFF8B5CF6), // purple
    Color(0xFF0EA5E9), // sky
    Color(0xFFEC4899), // pink
  ];

  // ── Marketplace brand colours ──────────────────────────────────────────────
  static const Color flipkart = Color(0xFF2874F0);
  static const Color amazon   = Color(0xFFFF9900);
  static const Color meesho   = Color(0xFFE91E8C);
  static const Color myntra   = Color(0xFFFF3E6C);
  static const Color shopify  = Color(0xFF96BF48);
  static const Color nykaa    = Color(0xFFFC2779);
  static const Color ajio     = Color(0xFFE03018);
  static const Color snapdeal = Color(0xFFE40046);
  static const Color jiomart  = Color(0xFF0071F6);

  // ── Backward-compat aliases ────────────────────────────────────────────────
  static const Color primary       = navy900;
  static const Color primaryDark   = navy800;
  static const Color primaryLight  = navy600;
  static const Color accent        = teal500;
  static const Color accentDark    = tealHover;
  static const Color accentLight   = teal300;
  static const Color teal          = teal500;
  static const Color tealDark      = tealHover;
  static const Color error         = danger;
  static const Color positive      = success;
  static const Color negative      = danger;
  static const Color darkNavy      = navy900;
  static const Color darkNavy2     = navy800;
  static const Color accentNavy    = navy600;
  static const Color primary2      = navy800;
  static const Color backgroundLight = background;
}
