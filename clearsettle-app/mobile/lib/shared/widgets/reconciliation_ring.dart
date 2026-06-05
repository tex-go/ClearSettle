import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../../core/theme/app_colors.dart';
import '../../core/theme/app_text_styles.dart';

/// Animated donut ring showing reconciliation percentage.
///
/// - Ring width: 16dp, diameter: 160dp
/// - Track: surface-03 background
/// - Progress: teal (#00C896), round cap
/// - Center: percentage (Display Medium) + label + check icon
/// - Animation: sweepAngle 0→target over 1200ms, count-up in sync
class ReconciliationRing extends StatefulWidget {
  const ReconciliationRing({
    super.key,
    required this.percent,
    this.size = 160,
    this.strokeWidth = 16,
    this.animate = true,
  });

  final double percent;   // 0.0–100.0
  final double size;
  final double strokeWidth;
  final bool animate;

  @override
  State<ReconciliationRing> createState() => _ReconciliationRingState();
}

class _ReconciliationRingState extends State<ReconciliationRing>
    with SingleTickerProviderStateMixin {
  late final AnimationController _ctrl;
  late final Animation<double> _anim;

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(
      vsync: this,
      duration: AppDurations.countUp,
    );
    _anim = CurvedAnimation(parent: _ctrl, curve: AppCurves.dataReveal);
    if (widget.animate) {
      _ctrl.forward();
    } else {
      _ctrl.value = 1.0;
    }
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final trackColor = isDark ? AppColors.surfaceElevatedDark : AppColors.surfaceVariant2;

    return Semantics(
      label: '${widget.percent.round()} percent reconciled',
      child: SizedBox(
        width: widget.size,
        height: widget.size,
        child: AnimatedBuilder(
          animation: _anim,
          builder: (context, _) {
            final progress = _anim.value * (widget.percent / 100);
            final displayPct = (_anim.value * widget.percent).round();
            return CustomPaint(
              painter: _RingPainter(
                progress: progress,
                trackColor: trackColor,
                progressColor: AppColors.teal500,
                strokeWidth: widget.strokeWidth,
              ),
              child: Center(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      '$displayPct%',
                      style: AppTextStyles.displaySmall.copyWith(
                        color: isDark
                            ? AppColors.textPrimaryDark
                            : AppColors.textPrimary,
                        fontFeatures: const [FontFeature.tabularFigures()],
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      'Reconciled',
                      style: TextStyle(
                        fontFamily: 'Inter',
                        fontSize: 11,
                        color: isDark ? AppColors.textMutedDark : AppColors.textMuted,
                      ),
                    ),
                    const SizedBox(height: 4),
                    const Icon(
                      Icons.check_circle_rounded,
                      size: 18,
                      color: AppColors.teal500,
                    ),
                  ],
                ),
              ),
            );
          },
        ),
      ),
    );
  }
}

class _RingPainter extends CustomPainter {
  const _RingPainter({
    required this.progress,
    required this.trackColor,
    required this.progressColor,
    required this.strokeWidth,
  });

  final double progress;       // 0.0–1.0
  final Color trackColor;
  final Color progressColor;
  final double strokeWidth;

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = (size.width - strokeWidth) / 2;
    const startAngle = -math.pi / 2; // 12 o'clock

    final trackPaint = Paint()
      ..color = trackColor
      ..style = PaintingStyle.stroke
      ..strokeWidth = strokeWidth
      ..strokeCap = StrokeCap.round;

    final progressPaint = Paint()
      ..color = progressColor
      ..style = PaintingStyle.stroke
      ..strokeWidth = strokeWidth
      ..strokeCap = StrokeCap.round;

    // Track (full circle)
    canvas.drawCircle(center, radius, trackPaint);

    // Progress arc
    if (progress > 0) {
      canvas.drawArc(
        Rect.fromCircle(center: center, radius: radius),
        startAngle,
        2 * math.pi * progress,
        false,
        progressPaint,
      );
    }
  }

  @override
  bool shouldRepaint(_RingPainter old) =>
      old.progress != progress || old.progressColor != progressColor;
}
