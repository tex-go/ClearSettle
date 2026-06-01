import 'package:flutter/material.dart';

/// Design tokens sourced directly from ClearSettle web app (index.css).
/// CSS variable → Dart constant mapping documented per property.
abstract final class AppColors {
  // ── Brand (web: --nv, --nv2, --tl, --tl2) ────────────────────────────────
  static const Color primary      = Color(0xFF0D1F35); // --nv  #0D1F35
  static const Color primaryDark  = Color(0xFF0A1628); // darker shade (login bg)
  static const Color primaryLight = Color(0xFF162B48); // --nv2 #162B48
  static const Color teal         = Color(0xFF0ABFCA); // --tl  #0ABFCA (CTA / accent)
  static const Color tealDark     = Color(0xFF088F99); // --tl2 #088F99

  // ── Status (web: --gn, --am, --rd, --bl) ─────────────────────────────────
  static const Color success  = Color(0xFF0DB07A); // --gn #0DB07A
  static const Color warning  = Color(0xFFE9930D); // --am #E9930D
  static const Color error    = Color(0xFFE8344A); // --rd #E8344A
  static const Color info     = Color(0xFF2563EB); // --bl #2563EB
  static const Color purple   = Color(0xFF7B52E8); // --pu #7B52E8

  // ── Financial helpers ─────────────────────────────────────────────────────
  static const Color positive = Color(0xFF0DB07A); // same as success
  static const Color negative = Color(0xFFE8344A); // same as error
  static const Color neutral  = Color(0xFF8FA5BD); // --tx3

  // ── Light-mode surfaces (web: --sf, --sf2, --sf3) ────────────────────────
  static const Color backgroundLight  = Color(0xFFF1F5F9); // --sf2
  static const Color surface          = Color(0xFFFFFFFF); // --sf  white
  static const Color surfaceVariant   = Color(0xFFF1F5F9); // --sf2 (inputs, table headers)
  static const Color surfaceVariant2  = Color(0xFFE8F0F8); // --sf3

  // ── Dark-mode surfaces (web sidebar palette) ──────────────────────────────
  static const Color backgroundDark   = Color(0xFF061020); // login bg darkest
  static const Color surfaceDark      = Color(0xFF162B48); // --nv2 (cards in dark)
  static const Color surfaceVariantDark = Color(0xFF1E3A5F); // slightly lighter

  // ── Borders / Dividers ────────────────────────────────────────────────────
  static const Color divider     = Color(0xFFE2EBF3); // --br #E2EBF3
  static const Color dividerDark = Color(0x14FFFFFF); // rgba(255,255,255,0.08)

  // ── Light-mode text (web: --tx, --tx2, --tx3) ────────────────────────────
  static const Color textPrimary   = Color(0xFF0D1F35); // --tx  #0D1F35
  static const Color textSecondary = Color(0xFF4B6080); // --tx2 #4B6080
  static const Color textMuted     = Color(0xFF8FA5BD); // --tx3 #8FA5BD
  static const Color textDisabled  = Color(0xFFB8CADA); // lighter tx3
  static const Color textInverse   = Color(0xFFFFFFFF); // white on dark

  // ── Dark-mode text (web sidebar text) ────────────────────────────────────
  static const Color textPrimaryDark   = Color(0xFFE2EBF3); // sidebar title
  static const Color textSecondaryDark = Color(0xFF8FA5BD); // sidebar nav text
  static const Color textMutedDark     = Color(0xFF4B6080); // sidebar group label

  // ── Marketplace brand colors (web chart palette) ──────────────────────────
  static const Color flipkart  = Color(0xFF2874F0);
  static const Color amazon    = Color(0xFFFF9900);
  static const Color meesho    = Color(0xFF9B1FE8);
  static const Color myntra    = Color(0xFFFF3E6C);
  static const Color shopify   = Color(0xFF96BF48);

  // ── Accent (primary interactive) ─────────────────────────────────────────
  /// Use teal as the accent — matches all web CTA buttons and focus states
  static const Color accent     = teal;
  static const Color accentDark = tealDark;
}
