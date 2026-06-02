import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'app_colors.dart';
import 'app_text_styles.dart';

/// Theme system that exactly mirrors the ClearSettle web application.
///
/// Light theme: white surfaces, #F1F5F9 backgrounds, #0D1F35 primary navy.
/// Dark theme: #0D1F35 background (web sidebar palette), #162B48 surfaces.
abstract final class AppTheme {
  static ThemeData get light => _build(Brightness.light);
  static ThemeData get dark  => _build(Brightness.dark);

  static ThemeData _build(Brightness brightness) {
    final isDark = brightness == Brightness.dark;

    final colorScheme = isDark ? _darkScheme : _lightScheme;
    final bgColor     = isDark ? AppColors.backgroundDark  : AppColors.backgroundLight;
    final surfColor   = isDark ? AppColors.surfaceDark      : AppColors.surface;
    final divColor    = isDark ? AppColors.dividerDark      : AppColors.divider;
    final txtPrimary  = isDark ? AppColors.textPrimaryDark  : AppColors.textPrimary;
    final txtSecond   = isDark ? AppColors.textSecondaryDark: AppColors.textSecondary;

    return ThemeData(
      useMaterial3: true,
      brightness: brightness,
      colorScheme: colorScheme,
      scaffoldBackgroundColor: bgColor,

      // ── AppBar ──────────────────────────────────────────────────────────
      appBarTheme: AppBarTheme(
        backgroundColor: isDark ? AppColors.primaryLight : AppColors.primary,
        foregroundColor: AppColors.textInverse,
        elevation: 0,
        centerTitle: false,
        systemOverlayStyle: SystemUiOverlayStyle(
          statusBarColor: Colors.transparent,
          statusBarIconBrightness: Brightness.light,
          statusBarBrightness: Brightness.dark,
          systemNavigationBarColor:
              isDark ? AppColors.backgroundDark : AppColors.surface,
          systemNavigationBarIconBrightness:
              isDark ? Brightness.light : Brightness.dark,
        ),
        titleTextStyle: const TextStyle(
          color: AppColors.textInverse,
          fontSize: 17,
          fontWeight: FontWeight.w600,
        ),
        iconTheme: const IconThemeData(color: AppColors.textInverse),
      ),

      // ── Bottom navigation ────────────────────────────────────────────────
      bottomNavigationBarTheme: BottomNavigationBarThemeData(
        backgroundColor: surfColor,
        selectedItemColor: AppColors.teal,
        unselectedItemColor: isDark
            ? AppColors.textSecondaryDark
            : AppColors.textSecondary,
        type: BottomNavigationBarType.fixed,
        elevation: 0,
        selectedLabelStyle: const TextStyle(
            fontSize: 11, fontWeight: FontWeight.w600),
        unselectedLabelStyle: const TextStyle(
            fontSize: 11, fontWeight: FontWeight.w500),
        showSelectedLabels: true,
        showUnselectedLabels: true,
      ),

      // ── Cards ────────────────────────────────────────────────────────────
      cardTheme: CardThemeData(
        color: surfColor,
        elevation: 0,
        margin: EdgeInsets.zero,
        shape: RoundedRectangleBorder(
          borderRadius: AppRadius.card,
          side: BorderSide(color: divColor),
        ),
      ),

      // ── Inputs ───────────────────────────────────────────────────────────
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: isDark
            ? AppColors.surfaceVariantDark
            : AppColors.surfaceVariant,
        contentPadding: const EdgeInsets.symmetric(
            horizontal: AppSpacing.s4, vertical: AppSpacing.s3),
        border: OutlineInputBorder(
          borderRadius: AppRadius.input,
          borderSide: BorderSide(color: divColor),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: AppRadius.input,
          borderSide: BorderSide(color: divColor),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: AppRadius.input,
          borderSide:
              const BorderSide(color: AppColors.teal, width: 1.5),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: AppRadius.input,
          borderSide: const BorderSide(color: AppColors.error),
        ),
        focusedErrorBorder: OutlineInputBorder(
          borderRadius: AppRadius.input,
          borderSide:
              const BorderSide(color: AppColors.error, width: 1.5),
        ),
        hintStyle: TextStyle(
            color: isDark
                ? AppColors.textSecondaryDark
                : AppColors.textMuted,
            fontSize: 14,
            fontWeight: FontWeight.w500),
        labelStyle: TextStyle(
            color: isDark
                ? AppColors.textSecondaryDark
                : AppColors.textSecondary,
            fontSize: 12,
            fontWeight: FontWeight.w600),
        errorStyle: const TextStyle(
            color: AppColors.error, fontSize: 11),
      ),

      // ── Elevated buttons (teal CTA, matches .btn-p) ───────────────────────
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ButtonStyle(
          backgroundColor: WidgetStateProperty.resolveWith((states) {
            if (states.contains(WidgetState.disabled)) {
              return AppColors.teal.withValues(alpha: 0.4);
            }
            return AppColors.teal;
          }),
          foregroundColor:
              WidgetStateProperty.all(AppColors.textInverse),
          elevation: WidgetStateProperty.all(0),
          shadowColor: WidgetStateProperty.all(
              AppColors.teal.withValues(alpha: 0.25)),
          minimumSize: WidgetStateProperty.all(
              const Size(double.infinity, 48)),
          shape: WidgetStateProperty.all(
            RoundedRectangleBorder(borderRadius: AppRadius.input),
          ),
          textStyle: WidgetStateProperty.all(
            const TextStyle(fontSize: 15, fontWeight: FontWeight.w700),
          ),
        ),
      ),

      // ── Outlined buttons (.btn-g) ─────────────────────────────────────────
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: isDark ? AppColors.textPrimaryDark : AppColors.textPrimary,
          side: BorderSide(color: divColor),
          shape: RoundedRectangleBorder(borderRadius: AppRadius.input),
          minimumSize: const Size(double.infinity, 48),
          textStyle: const TextStyle(
              fontSize: 14, fontWeight: FontWeight.w600),
        ),
      ),

      // ── Text buttons ──────────────────────────────────────────────────────
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          foregroundColor: AppColors.teal,
          textStyle: const TextStyle(
              fontSize: 14, fontWeight: FontWeight.w600),
        ),
      ),

      // ── Divider ───────────────────────────────────────────────────────────
      dividerTheme: DividerThemeData(
        color: divColor, thickness: 1, space: 0),

      // ── Chip ─────────────────────────────────────────────────────────────
      chipTheme: ChipThemeData(
        backgroundColor: isDark
            ? AppColors.surfaceVariantDark
            : AppColors.surfaceVariant,
        labelStyle: TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.w600,
            color: txtSecond),
        side: BorderSide(color: divColor),
        shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppRadius.r1)),
        padding: const EdgeInsets.symmetric(
            horizontal: AppSpacing.s2, vertical: 2),
      ),

      // ── Switch ────────────────────────────────────────────────────────────
      switchTheme: SwitchThemeData(
        thumbColor: WidgetStateProperty.resolveWith((states) =>
            states.contains(WidgetState.selected)
                ? AppColors.textInverse
                : null),
        trackColor: WidgetStateProperty.resolveWith((states) =>
            states.contains(WidgetState.selected)
                ? AppColors.teal
                : null),
      ),

      // ── Progress indicator ────────────────────────────────────────────────
      progressIndicatorTheme: const ProgressIndicatorThemeData(
        color: AppColors.teal,
      ),

      // ── RefreshIndicator ─────────────────────────────────────────────────
      // (handled per-widget via RefreshIndicator.color)

      // ── Text theme ───────────────────────────────────────────────────────
      textTheme: TextTheme(
        displayLarge:  AppTextStyles.displayLarge.copyWith(color: txtPrimary),
        displayMedium: AppTextStyles.displayMedium.copyWith(color: txtPrimary),
        headlineLarge: AppTextStyles.headlineLarge.copyWith(color: txtPrimary),
        headlineMedium:AppTextStyles.headlineMedium.copyWith(color: txtPrimary),
        titleLarge:    AppTextStyles.titleLarge.copyWith(color: txtPrimary),
        titleMedium:   AppTextStyles.titleMedium.copyWith(color: txtPrimary),
        bodyLarge:     AppTextStyles.bodyLarge.copyWith(color: txtPrimary),
        bodyMedium:    AppTextStyles.bodyMedium.copyWith(color: txtPrimary),
        bodySmall:     AppTextStyles.bodySmall.copyWith(color: txtSecond),
        labelLarge:    AppTextStyles.labelLarge.copyWith(color: txtSecond),
        labelMedium:   AppTextStyles.labelMedium.copyWith(color: txtSecond),
        labelSmall:    AppTextStyles.labelSmall,
      ),
    );
  }

  static const ColorScheme _lightScheme = ColorScheme.light(
    primary:    AppColors.primary,
    onPrimary:  AppColors.textInverse,
    secondary:  AppColors.teal,
    onSecondary:AppColors.textInverse,
    error:      AppColors.error,
    onError:    AppColors.textInverse,
    surface:    AppColors.surface,
    onSurface:  AppColors.textPrimary,
    outline:    AppColors.divider,
  );

  static const ColorScheme _darkScheme = ColorScheme.dark(
    primary:    AppColors.teal,
    onPrimary:  AppColors.textInverse,
    secondary:  AppColors.teal,
    onSecondary:AppColors.textInverse,
    error:      AppColors.error,
    onError:    AppColors.textInverse,
    surface:    AppColors.surfaceDark,
    onSurface:  AppColors.textPrimaryDark,
    outline:    AppColors.dividerDark,
  );
}
