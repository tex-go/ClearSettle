import 'dart:ui';

import 'package:flutter/material.dart';

import '../../core/theme/app_colors.dart';
import '../../core/theme/app_text_styles.dart';

// ─────────────────────────────────────────────────────────────────────────────
// AppCard — premium surface card with optional tap / gradient
// ─────────────────────────────────────────────────────────────────────────────

class AppCard extends StatelessWidget {
  const AppCard({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(16),
    this.margin = EdgeInsets.zero,
    this.radius = AppRadius.r4,
    this.gradient,
    this.color,
    this.borderColor,
    this.shadows = AppShadows.card,
    this.onTap,
  });

  final Widget child;
  final EdgeInsets padding;
  final EdgeInsets margin;
  final double radius;
  final Gradient? gradient;
  final Color? color;
  final Color? borderColor;
  final List<BoxShadow> shadows;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final bg = color ?? (isDark ? AppColors.surfaceDark : AppColors.surface);
    final border = borderColor ?? (isDark ? AppColors.dividerDark : AppColors.divider);

    Widget content = Container(
      padding: padding,
      decoration: BoxDecoration(
        color: gradient == null ? bg : null,
        gradient: gradient,
        borderRadius: BorderRadius.circular(radius),
        border: Border.all(color: border, width: gradient != null ? 0 : 1),
        boxShadow: shadows,
      ),
      child: child,
    );

    if (onTap != null) {
      content = Material(
        color: Colors.transparent,
        borderRadius: BorderRadius.circular(radius),
        child: InkWell(
          borderRadius: BorderRadius.circular(radius),
          splashColor: AppColors.accent.withValues(alpha: 0.06),
          highlightColor: AppColors.accent.withValues(alpha: 0.03),
          onTap: onTap,
          child: content,
        ),
      );
    }

    return Padding(padding: margin, child: content);
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// MetricCard — analytics KPI tile with label, value, optional trend
// ─────────────────────────────────────────────────────────────────────────────

class MetricCard extends StatelessWidget {
  const MetricCard({
    super.key,
    required this.label,
    required this.value,
    this.trend,          // e.g. '+12%' or '-3%'
    this.trendPositive,  // true=green, false=red, null=neutral
    this.icon,
    this.iconColor,
    this.valueColor,
    this.subtitle,
    this.onTap,
    this.margin = EdgeInsets.zero,
  });

  final String label;
  final String value;
  final String? trend;
  final bool? trendPositive;
  final IconData? icon;
  final Color? iconColor;
  final Color? valueColor;
  final String? subtitle;
  final VoidCallback? onTap;
  final EdgeInsets margin;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final icolor = iconColor ?? AppColors.accent;
    final vcolor = valueColor ??
        (isDark ? AppColors.textPrimaryDark : AppColors.textPrimary);
    final labelColor = isDark ? AppColors.textSecondaryDark : AppColors.textSecondary;

    return AppCard(
      margin: margin,
      onTap: onTap,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            children: [
              if (icon != null) ...[
                Container(
                  width: 28,
                  height: 28,
                  decoration: BoxDecoration(
                    color: icolor.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Icon(icon, size: 14, color: icolor),
                ),
                const SizedBox(width: 8),
              ],
              Expanded(
                child: Text(
                  label,
                  style: AppTextStyles.labelMedium.copyWith(color: labelColor),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              if (trend != null) _TrendBadge(trend: trend!, positive: trendPositive),
            ],
          ),
          const SizedBox(height: 10),
          Text(
            value,
            style: AppTextStyles.metricMedium.copyWith(color: vcolor),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
          if (subtitle != null) ...[
            const SizedBox(height: 3),
            Text(
              subtitle!,
              style: AppTextStyles.labelSmall,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          ],
        ],
      ),
    );
  }
}

class _TrendBadge extends StatelessWidget {
  const _TrendBadge({required this.trend, required this.positive});

  final String trend;
  final bool? positive;

  @override
  Widget build(BuildContext context) {
    final isPos = positive ?? true;
    final color = positive == null
        ? AppColors.textMuted
        : isPos
            ? AppColors.success
            : AppColors.error;

    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(
          positive == null
              ? Icons.remove
              : isPos
                  ? Icons.trending_up_rounded
                  : Icons.trending_down_rounded,
          size: 12,
          color: color,
        ),
        const SizedBox(width: 2),
        Text(
          trend,
          style: TextStyle(
            fontSize: 11,
            fontWeight: FontWeight.w600,
            color: color,
          ),
        ),
      ],
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// PrimaryButton — accent teal CTA with optional glow
// ─────────────────────────────────────────────────────────────────────────────

class PrimaryButton extends StatelessWidget {
  const PrimaryButton({
    super.key,
    required this.label,
    required this.onPressed,
    this.icon,
    this.isLoading = false,
    this.expanded = true,
    this.small = false,
  });

  final String label;
  final VoidCallback? onPressed;
  final IconData? icon;
  final bool isLoading;
  final bool expanded;
  final bool small;

  @override
  Widget build(BuildContext context) {
    final height = small ? 40.0 : 50.0;
    final fontSize = small ? 13.0 : 15.0;

    final Widget button = Container(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(AppRadius.r2),
        boxShadow: onPressed != null ? AppShadows.ctaButton : null,
      ),
      child: ElevatedButton(
        onPressed: isLoading ? null : onPressed,
        style: ElevatedButton.styleFrom(
          minimumSize: Size(expanded ? double.infinity : 0, height),
          padding: EdgeInsets.symmetric(
              horizontal: small ? 16 : 24, vertical: 0),
        ),
        child: isLoading
            ? SizedBox(
                width: 20,
                height: 20,
                child: CircularProgressIndicator(
                  strokeWidth: 2,
                  color: AppColors.textInverse.withValues(alpha: 0.8),
                ),
              )
            : Row(
                mainAxisSize: expanded ? MainAxisSize.max : MainAxisSize.min,
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  if (icon != null) ...[
                    Icon(icon, size: small ? 16 : 18),
                    const SizedBox(width: 8),
                  ],
                  Text(
                    label,
                    style: TextStyle(
                      fontSize: fontSize,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ),
      ),
    );

    return button;
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// SectionHeader — title row with optional action link
// ─────────────────────────────────────────────────────────────────────────────

class SectionHeader extends StatelessWidget {
  const SectionHeader({
    super.key,
    required this.title,
    this.actionLabel,
    this.onAction,
    this.margin = const EdgeInsets.fromLTRB(0, 20, 0, 10),
  });

  final String title;
  final String? actionLabel;
  final VoidCallback? onAction;
  final EdgeInsets margin;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Padding(
      padding: margin,
      child: Row(
        children: [
          Expanded(
            child: Text(
              title,
              style: AppTextStyles.titleSmall.copyWith(
                color: isDark ? AppColors.textPrimaryDark : AppColors.textPrimary,
                letterSpacing: 0.1,
              ),
            ),
          ),
          if (actionLabel != null && onAction != null)
            GestureDetector(
              onTap: onAction,
              child: Text(
                actionLabel!,
                style: AppTextStyles.labelMedium.copyWith(
                  color: AppColors.accent,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
        ],
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// StatusBadge — colored pill chip
// ─────────────────────────────────────────────────────────────────────────────

class StatusBadge extends StatelessWidget {
  const StatusBadge({
    super.key,
    required this.label,
    this.color = AppColors.accent,
    this.small = false,
  });

  final String label;
  final Color color;
  final bool small;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: EdgeInsets.symmetric(
        horizontal: small ? 6 : 8,
        vertical: small ? 2 : 3,
      ),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.10),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: color.withValues(alpha: 0.25)),
      ),
      child: Text(
        label,
        style: TextStyle(
          fontSize: small ? 9 : 11,
          fontWeight: FontWeight.w600,
          color: color,
          letterSpacing: 0.2,
        ),
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// GlassCard — legacy compatibility alias → delegates to AppCard
// ─────────────────────────────────────────────────────────────────────────────

class GlassCard extends StatelessWidget {
  const GlassCard({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(16),
    this.margin = EdgeInsets.zero,
    this.borderRadius = AppRadius.r4,
    this.blur = 0,
    this.borderColor,
    this.backgroundColor,
    this.gradient,
    this.onTap,
  });

  final Widget child;
  final EdgeInsets padding;
  final EdgeInsets margin;
  final double borderRadius;
  final double blur;
  final Color? borderColor;
  final Color? backgroundColor;
  final Gradient? gradient;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    // Only apply backdrop blur in dark mode when explicitly requested
    if (isDark && blur > 0) {
      final bg = backgroundColor ?? AppColors.surfaceDark.withValues(alpha: 0.6);
      return Padding(
        padding: margin,
        child: ClipRRect(
          borderRadius: BorderRadius.circular(borderRadius),
          child: BackdropFilter(
            filter: ImageFilter.blur(sigmaX: blur, sigmaY: blur),
            child: AppCard(
              padding: padding,
              radius: borderRadius,
              gradient: gradient,
              color: bg,
              borderColor: borderColor,
              onTap: onTap,
              child: child,
            ),
          ),
        ),
      );
    }

    return AppCard(
      padding: padding,
      margin: margin,
      radius: borderRadius,
      gradient: gradient,
      color: backgroundColor,
      borderColor: borderColor,
      onTap: onTap,
      child: child,
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// KpiCard — legacy alias (used by screens that import glass_card.dart)
// ─────────────────────────────────────────────────────────────────────────────

class KpiCard extends StatelessWidget {
  const KpiCard({
    super.key,
    required this.label,
    required this.value,
    this.subtitle,
    this.valueColor,
    this.icon,
    this.iconColor,
    this.margin = EdgeInsets.zero,
  });

  final String label;
  final String value;
  final String? subtitle;
  final Color? valueColor;
  final IconData? icon;
  final Color? iconColor;
  final EdgeInsets margin;

  @override
  Widget build(BuildContext context) {
    return MetricCard(
      label: label,
      value: value,
      subtitle: subtitle,
      valueColor: valueColor,
      icon: icon,
      iconColor: iconColor,
      margin: margin,
    );
  }
}
