import 'package:flutter/material.dart';

import '../../core/theme/app_colors.dart';
import '../../core/theme/app_text_styles.dart';

/// Card with scale(0.98) on press.
///
/// Press down: 80ms, release: 200ms — matches spec animation tokens.
/// Use instead of bare Container + GestureDetector wherever cards are tappable.
class PressableCard extends StatefulWidget {
  const PressableCard({
    super.key,
    required this.child,
    this.onTap,
    this.onLongPress,
    this.padding,
    this.margin,
    this.borderRadius,
    this.color,
    this.border,
    this.boxShadow,
    this.semanticLabel,
  });

  final Widget child;
  final VoidCallback? onTap;
  final VoidCallback? onLongPress;
  final EdgeInsetsGeometry? padding;
  final EdgeInsetsGeometry? margin;
  final BorderRadius? borderRadius;
  final Color? color;
  final BoxBorder? border;
  final List<BoxShadow>? boxShadow;
  final String? semanticLabel;

  @override
  State<PressableCard> createState() => _PressableCardState();
}

class _PressableCardState extends State<PressableCard>
    with SingleTickerProviderStateMixin {
  late final AnimationController _ctrl = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 80),
    reverseDuration: const Duration(milliseconds: 200),
    value: 1.0,
  );

  late final Animation<double> _scale = Tween<double>(
    begin: 0.98,
    end: 1.0,
  ).animate(CurvedAnimation(parent: _ctrl, curve: Curves.easeOut));

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  void _onTapDown(TapDownDetails _) {
    if (widget.onTap == null) return;
    _ctrl.reverse(from: 1.0);
  }

  void _onTapUp(TapUpDetails _) {
    _ctrl.forward();
    widget.onTap?.call();
  }

  void _onTapCancel() => _ctrl.forward();

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final defaultColor = isDark ? AppColors.surfaceDark : AppColors.surface;
    final defaultBorder = Border.all(
      color: isDark ? AppColors.borderDark : AppColors.border,
    );
    final defaultRadius = BorderRadius.circular(AppRadius.r4);

    return Semantics(
      label: widget.semanticLabel,
      button: widget.onTap != null,
      child: GestureDetector(
        onTapDown: _onTapDown,
        onTapUp: _onTapUp,
        onTapCancel: _onTapCancel,
        onLongPress: widget.onLongPress,
        child: AnimatedBuilder(
          animation: _scale,
          builder: (context, child) => Transform.scale(
            scale: _scale.value,
            child: child,
          ),
          child: Container(
            margin: widget.margin,
            padding: widget.padding ??
                const EdgeInsets.all(AppSpacing.cardPadding),
            decoration: BoxDecoration(
              color: widget.color ?? defaultColor,
              borderRadius: widget.borderRadius ?? defaultRadius,
              border: widget.border ?? defaultBorder,
              boxShadow: widget.boxShadow ?? AppShadows.card,
            ),
            child: widget.child,
          ),
        ),
      ),
    );
  }
}
