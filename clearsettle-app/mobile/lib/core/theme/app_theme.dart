import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'app_colors.dart';
import 'app_text_styles.dart';

/// Premium fintech theme — Material 3, dark-navy primary, teal accent.
abstract final class AppTheme {
  static ThemeData get light => _build(Brightness.light);
  static ThemeData get dark  => _build(Brightness.dark);

  static ThemeData _build(Brightness brightness) {
    final isDark = brightness == Brightness.dark;

    final colorScheme = isDark ? _darkScheme : _lightScheme;
    final bgColor    = isDark ? AppColors.backgroundDark  : AppColors.background;
    final surfColor  = isDark ? AppColors.surfaceDark     : AppColors.surface;
    final divColor   = isDark ? AppColors.dividerDark     : AppColors.divider;
    final txtPrimary = isDark ? AppColors.textPrimaryDark : AppColors.textPrimary;
    final txtSecond  = isDark ? AppColors.textSecondaryDark: AppColors.textSecondary;

    return ThemeData(
      useMaterial3: true,
      brightness: brightness,
      colorScheme: colorScheme,
      scaffoldBackgroundColor: bgColor,

      // ── AppBar ────────────────────────────────────────────────────────────
      // Clean white/surface app bar — no heavy colored bar
      appBarTheme: AppBarTheme(
        backgroundColor: surfColor,
        foregroundColor: isDark ? AppColors.textPrimaryDark : AppColors.textPrimary,
        elevation: 0,
        scrolledUnderElevation: 0.5,
        centerTitle: false,
        shadowColor: AppColors.divider,
        surfaceTintColor: Colors.transparent,
        systemOverlayStyle: SystemUiOverlayStyle(
          statusBarColor: Colors.transparent,
          statusBarIconBrightness: isDark ? Brightness.light : Brightness.dark,
          statusBarBrightness: isDark ? Brightness.dark : Brightness.light,
          systemNavigationBarColor: bgColor,
          systemNavigationBarIconBrightness: isDark ? Brightness.light : Brightness.dark,
        ),
        titleTextStyle: TextStyle(
          fontFamily: 'sans-serif',
          color: isDark ? AppColors.textPrimaryDark : AppColors.textPrimary,
          fontSize: 17,
          fontWeight: FontWeight.w600,
          letterSpacing: -0.1,
        ),
        iconTheme: IconThemeData(
          color: isDark ? AppColors.textSecondaryDark : AppColors.textSecondary,
          size: 22,
        ),
      ),

      // ── Bottom nav (raw theme — overridden by custom widget) ─────────────
      bottomNavigationBarTheme: BottomNavigationBarThemeData(
        backgroundColor: surfColor,
        selectedItemColor: AppColors.accent,
        unselectedItemColor: isDark ? AppColors.textSecondaryDark : AppColors.textSecondary,
        type: BottomNavigationBarType.fixed,
        elevation: 0,
        selectedLabelStyle: const TextStyle(fontSize: 11, fontWeight: FontWeight.w600),
        unselectedLabelStyle: const TextStyle(fontSize: 11, fontWeight: FontWeight.w400),
        showSelectedLabels: true,
        showUnselectedLabels: true,
      ),

      // ── NavigationBar (M3 bottom nav) ─────────────────────────────────────
      navigationBarTheme: NavigationBarThemeData(
        backgroundColor: surfColor,
        indicatorColor: AppColors.accent.withValues(alpha: 0.15),
        iconTheme: WidgetStateProperty.resolveWith((states) {
          return IconThemeData(
            color: states.contains(WidgetState.selected)
                ? AppColors.accent
                : isDark ? AppColors.textSecondaryDark : AppColors.textSecondary,
            size: 22,
          );
        }),
        labelTextStyle: WidgetStateProperty.resolveWith((states) {
          return TextStyle(
            fontSize: 11,
            fontWeight: states.contains(WidgetState.selected)
                ? FontWeight.w600
                : FontWeight.w400,
            color: states.contains(WidgetState.selected)
                ? AppColors.accent
                : isDark ? AppColors.textSecondaryDark : AppColors.textSecondary,
          );
        }),
        height: 64,
        elevation: 0,
        surfaceTintColor: Colors.transparent,
      ),

      // ── Cards ─────────────────────────────────────────────────────────────
      cardTheme: CardThemeData(
        color: surfColor,
        elevation: 0,
        margin: EdgeInsets.zero,
        shadowColor: const Color(0x100F172A),
        shape: RoundedRectangleBorder(
          borderRadius: AppRadius.card,
          side: BorderSide(color: divColor),
        ),
      ),

      // ── Inputs ────────────────────────────────────────────────────────────
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: isDark ? AppColors.surfaceVariantDark : AppColors.surfaceVariant,
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
          borderSide: const BorderSide(color: AppColors.accent, width: 1.5),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: AppRadius.input,
          borderSide: const BorderSide(color: AppColors.error),
        ),
        focusedErrorBorder: OutlineInputBorder(
          borderRadius: AppRadius.input,
          borderSide: const BorderSide(color: AppColors.error, width: 1.5),
        ),
        hintStyle: TextStyle(
            color: isDark ? AppColors.textSecondaryDark : AppColors.textMuted,
            fontSize: 14,
            fontWeight: FontWeight.w400),
        labelStyle: TextStyle(
            color: isDark ? AppColors.textSecondaryDark : AppColors.textSecondary,
            fontSize: 12,
            fontWeight: FontWeight.w500),
        errorStyle: const TextStyle(color: AppColors.error, fontSize: 11),
      ),

      // ── Elevated buttons — accent teal CTA ────────────────────────────────
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ButtonStyle(
          backgroundColor: WidgetStateProperty.resolveWith((states) {
            if (states.contains(WidgetState.disabled)) {
              return AppColors.accent.withValues(alpha: 0.35);
            }
            return AppColors.accent;
          }),
          foregroundColor: WidgetStateProperty.all(AppColors.textInverse),
          overlayColor: WidgetStateProperty.all(
              AppColors.textInverse.withValues(alpha: 0.08)),
          elevation: WidgetStateProperty.all(0),
          shadowColor: WidgetStateProperty.all(Colors.transparent),
          minimumSize: WidgetStateProperty.all(const Size(double.infinity, 50)),
          shape: WidgetStateProperty.all(
            RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppRadius.r2)),
          ),
          textStyle: WidgetStateProperty.all(
            const TextStyle(fontSize: 15, fontWeight: FontWeight.w600, letterSpacing: 0.1),
          ),
        ),
      ),

      // ── Outlined buttons ──────────────────────────────────────────────────
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: isDark ? AppColors.textPrimaryDark : AppColors.textPrimary,
          side: BorderSide(color: divColor),
          shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(AppRadius.r2)),
          minimumSize: const Size(double.infinity, 50),
          textStyle: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600),
        ),
      ),

      // ── Text buttons ──────────────────────────────────────────────────────
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          foregroundColor: AppColors.accent,
          textStyle: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600),
        ),
      ),

      // ── Divider ───────────────────────────────────────────────────────────
      dividerTheme: DividerThemeData(color: divColor, thickness: 1, space: 0),

      // ── Chip ──────────────────────────────────────────────────────────────
      chipTheme: ChipThemeData(
        backgroundColor: isDark ? AppColors.surfaceVariantDark : AppColors.surfaceVariant,
        labelStyle: TextStyle(fontSize: 12, fontWeight: FontWeight.w500, color: txtSecond),
        side: BorderSide(color: divColor),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppRadius.r1)),
        padding: const EdgeInsets.symmetric(horizontal: AppSpacing.s2, vertical: 2),
      ),

      // ── Switch ────────────────────────────────────────────────────────────
      switchTheme: SwitchThemeData(
        thumbColor: WidgetStateProperty.resolveWith((states) =>
            states.contains(WidgetState.selected) ? AppColors.textInverse : null),
        trackColor: WidgetStateProperty.resolveWith((states) =>
            states.contains(WidgetState.selected) ? AppColors.accent : null),
      ),

      // ── Progress indicator ────────────────────────────────────────────────
      progressIndicatorTheme:
          const ProgressIndicatorThemeData(color: AppColors.accent),

      // ── Text theme ────────────────────────────────────────────────────────
      textTheme: TextTheme(
        displayLarge:   AppTextStyles.displayLarge.copyWith(color: txtPrimary),
        displayMedium:  AppTextStyles.displayMedium.copyWith(color: txtPrimary),
        displaySmall:   AppTextStyles.displaySmall.copyWith(color: txtPrimary),
        headlineLarge:  AppTextStyles.headlineLarge.copyWith(color: txtPrimary),
        headlineMedium: AppTextStyles.headlineMedium.copyWith(color: txtPrimary),
        headlineSmall:  AppTextStyles.headlineSmall.copyWith(color: txtPrimary),
        titleLarge:     AppTextStyles.titleLarge.copyWith(color: txtPrimary),
        titleMedium:    AppTextStyles.titleMedium.copyWith(color: txtPrimary),
        titleSmall:     AppTextStyles.titleSmall.copyWith(color: txtPrimary),
        bodyLarge:      AppTextStyles.bodyLarge.copyWith(color: txtPrimary),
        bodyMedium:     AppTextStyles.bodyMedium.copyWith(color: txtPrimary),
        bodySmall:      AppTextStyles.bodySmall.copyWith(color: txtSecond),
        labelLarge:     AppTextStyles.labelLarge.copyWith(color: txtSecond),
        labelMedium:    AppTextStyles.labelMedium.copyWith(color: txtSecond),
        labelSmall:     AppTextStyles.labelSmall,
      ),
    );
  }

  // ── Color schemes ─────────────────────────────────────────────────────────

  static const ColorScheme _lightScheme = ColorScheme.light(
    primary:     AppColors.primary,
    onPrimary:   AppColors.textInverse,
    secondary:   AppColors.accent,
    onSecondary: AppColors.textInverse,
    tertiary:    AppColors.primaryLight,
    onTertiary:  AppColors.textInverse,
    error:       AppColors.error,
    onError:     AppColors.textInverse,
    surface:     AppColors.surface,
    onSurface:   AppColors.textPrimary,
    outline:     AppColors.divider,
    outlineVariant: AppColors.surfaceVariant2,
  );

  static const ColorScheme _darkScheme = ColorScheme.dark(
    primary:     AppColors.accent,
    onPrimary:   AppColors.textInverse,
    secondary:   AppColors.accent,
    onSecondary: AppColors.textInverse,
    error:       AppColors.error,
    onError:     AppColors.textInverse,
    surface:     AppColors.surfaceDark,
    onSurface:   AppColors.textPrimaryDark,
    outline:     AppColors.dividerDark,
  );
}
