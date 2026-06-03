import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../core/theme/app_colors.dart';
import '../../core/theme/app_text_styles.dart';

/// Animates a currency amount from 0 to [amount] on first build.
///
/// Uses easeOut curve — starts fast, lands precisely on the final value.
/// Never use bouncy/elastic curves on financial numbers.
class AnimatedAmount extends StatefulWidget {
  const AnimatedAmount({
    super.key,
    required this.amount,
    this.style,
    this.color,
    this.prefix = '₹',
    this.duration = AppDurations.countUp,
    this.showSign = false,
  });

  final double amount;
  final TextStyle? style;
  final Color? color;
  final String prefix;
  final Duration duration;

  /// When true, positive values show a + prefix (for delta indicators).
  final bool showSign;

  @override
  State<AnimatedAmount> createState() => _AnimatedAmountState();
}

class _AnimatedAmountState extends State<AnimatedAmount>
    with SingleTickerProviderStateMixin {
  late final AnimationController _ctrl;
  late final Animation<double> _anim;
  final _fmt = NumberFormat('#,##,###', 'en_IN');

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(vsync: this, duration: widget.duration);
    _anim = Tween<double>(begin: 0, end: widget.amount.abs())
        .animate(CurvedAnimation(parent: _ctrl, curve: AppCurves.dataReveal));
    _ctrl.forward();
  }

  @override
  void didUpdateWidget(AnimatedAmount old) {
    super.didUpdateWidget(old);
    if (old.amount != widget.amount) {
      _anim = Tween<double>(begin: _anim.value, end: widget.amount.abs())
          .animate(CurvedAnimation(parent: _ctrl, curve: AppCurves.dataReveal));
      _ctrl
        ..reset()
        ..forward();
    }
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final isNegative = widget.amount < 0;
    final effectiveColor = widget.color ??
        (isNegative ? AppColors.debit : null);

    return AnimatedBuilder(
      animation: _anim,
      builder: (_, __) {
        final value = _anim.value;
        final formatted = _fmt.format(value.round());
        final sign = isNegative
            ? '-'
            : (widget.showSign && widget.amount > 0 ? '+' : '');

        return Text(
          '$sign${widget.prefix}$formatted',
          style: (widget.style ?? AppTextStyles.metricLarge)
              .copyWith(color: effectiveColor),
        );
      },
    );
  }
}

/// Compact delta indicator — shows change vs previous period.
/// e.g. "↑ +₹12,400" in success green or "↓ -₹3,200" in danger red.
class AmountDelta extends StatelessWidget {
  const AmountDelta({super.key, required this.delta, this.style});

  final double delta;
  final TextStyle? style;

  @override
  Widget build(BuildContext context) {
    final isPositive = delta >= 0;
    final color  = isPositive ? AppColors.credit : AppColors.debit;
    final arrow  = isPositive ? '↑' : '↓';
    final sign   = isPositive ? '+' : '';
    final fmt    = NumberFormat('#,##,###', 'en_IN');
    final label  = '$arrow $sign₹${fmt.format(delta.abs().round())}';

    return Text(
      label,
      style: (style ?? AppTextStyles.bodySmall).copyWith(color: color),
    );
  }
}
