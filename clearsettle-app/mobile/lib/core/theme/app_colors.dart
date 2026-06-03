import 'package:flutter/material.dart';

/// ClearSettle design tokens — enterprise FinTech palette v2.0
///
/// Primary Navy : #081B2E  — institutional authority (Bloomberg, bank apps)
/// Primary Teal : #0DB7A3  — financial clarity, forward motion
/// Background   : #F7F9FC  — clinical precision (Bloomberg off-white)
abstract final class AppColors {
  // ── Brand Core ─────────────────────────────────────────────────────────────
  static const Color navy900 = Color(0xFF081B2E); // Primary Navy
  static const Color navy800 = Color(0xFF0D2540);
  static const Color navy700 = Color(0xFF123052);
  static const Color navy600 = Color(0xFF1A3F6A);
  static const Color navy500 = Color(0xFF234F82); // Interactive states

  static const Color teal500 = Color(0xFF0DB7A3); // Primary Accent
  static const Color teal400 = Color(0xFF1FCEBB);
  static const Color teal300 = Color(0xFF4DD9CB);
  static const Color teal200 = Color(0xFF8EEAE3);
  static const Color teal100 = Color(0xFFD1F5F2);
  static const Color teal50  = Color(0xFFEEFBFA);

  // ── Semantic ───────────────────────────────────────────────────────────────
  static const Color success    = Color(0xFF17C964);
  static const Color success100 = Color(0xFFE8FBF0);
  static const Color warning    = Color(0xFFF5A524);
  static const Color warning100 = Color(0xFFFEF3DC);
  static const Color danger     = Color(0xFFF31260);
  static const Color danger100  = Color(0xFFFFE4EE);
  static const Color info       = Color(0xFF006FEE);
  static const Color info100    = Color(0xFFE6F1FE);
  static const Color purple     = Color(0xFF8B5CF6);

  // ── Financial Semantic ─────────────────────────────────────────────────────
  /// Money received / positive settlement
  static const Color credit      = Color(0xFF17C964);
  /// Money owed / overcharge / loss
  static const Color debit       = Color(0xFFF31260);
  /// Awaiting settlement
  static const Color pending     = Color(0xFFF5A524);
  /// Overcharged / recoverable amount
  static const Color recoverable = Color(0xFF0DB7A3);
  /// Neutral / informational transactions
  static const Color neutral     = Color(0xFF64748B);

  // ── Surfaces ───────────────────────────────────────────────────────────────
  static const Color background      = Color(0xFFF7F9FC);
  static const Color surface         = Color(0xFFFFFFFF);
  static const Color surfaceAlt      = Color(0xFFF0F4F8);
  static const Color surfaceVariant  = Color(0xFFF1F5F9);
  static const Color surfaceVariant2 = Color(0xFFE2E8F0);

  // ── Dark surfaces ──────────────────────────────────────────────────────────
  static const Color backgroundDark     = Color(0xFF081B2E);
  static const Color surfaceDark        = Color(0xFF0D2540);
  static const Color surfaceVariantDark = Color(0xFF123052);

  // ── Borders ────────────────────────────────────────────────────────────────
  static const Color border      = Color(0xFFE2E8F0);
  static const Color borderLight = Color(0xFFF1F5F9);
  static const Color divider     = Color(0xFFE2E8F0);
  static const Color dividerDark = Color(0x1AFFFFFF);

  // ── Text — light mode ──────────────────────────────────────────────────────
  static const Color textPrimary   = Color(0xFF081B2E);
  static const Color textSecondary = Color(0xFF4A6180);
  static const Color textMuted     = Color(0xFF8BA3BE);
  static const Color textDisabled  = Color(0xFFB8CDD9);
  static const Color textInverse   = Color(0xFFFFFFFF);

  // ── Text — dark mode ───────────────────────────────────────────────────────
  static const Color textPrimaryDark   = Color(0xFFF1F5F9);
  static const Color textSecondaryDark = Color(0xFF94A3B8);
  static const Color textMutedDark     = Color(0xFF64748B);

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
    colors: [Color(0xFF0DB7A3), Color(0xFF1FCEBB)],
  );

  static const LinearGradient tealTextGradient = LinearGradient(
    colors: [Color(0xFF0DB7A3), Color(0xFF4DD9CB)],
  );

  // ── Data Visualisation (8-color scale) ────────────────────────────────────
  static const List<Color> chartPalette = [
    Color(0xFF0DB7A3), // teal      — primary series
    Color(0xFF234F82), // navy      — secondary series
    Color(0xFF17C964), // green     — positive
    Color(0xFFF5A524), // amber     — warning
    Color(0xFFF31260), // red       — negative
    Color(0xFF8B5CF6), // purple    — category 6
    Color(0xFF0EA5E9), // sky       — category 7
    Color(0xFFEC4899), // pink      — category 8
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
  static const Color primary      = navy900;
  static const Color primaryDark  = navy800;
  static const Color primaryLight = navy600;
  static const Color accent       = teal500;
  static const Color accentDark   = Color(0xFF0B9E8C);
  static const Color accentLight  = teal300;
  static const Color teal         = teal500;
  static const Color tealDark     = Color(0xFF0B9E8C);
  static const Color error        = danger;
  static const Color positive     = success;
  static const Color negative     = danger;
  static const Color darkNavy     = navy900;
  static const Color darkNavy2    = navy800;
  static const Color accentNavy   = navy600;
  static const Color primary2     = navy800;
  static const Color backgroundLight = background;
}
