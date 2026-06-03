import 'package:flutter/material.dart';
import 'package:shimmer/shimmer.dart';

import '../../core/theme/app_colors.dart';
import '../../core/theme/app_text_styles.dart';

/// Base shimmer wrapper. All skeleton widgets use this.
class _Shimmer extends StatelessWidget {
  const _Shimmer({required this.child});
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Shimmer.fromColors(
      baseColor: AppColors.borderLight,
      highlightColor: AppColors.surface,
      period: const Duration(milliseconds: 1400),
      child: child,
    );
  }
}

/// Rounded rectangle placeholder — the building block for all skeletons.
class SkeletonBox extends StatelessWidget {
  const SkeletonBox({
    super.key,
    required this.width,
    required this.height,
    this.radius = 8,
  });

  final double? width;
  final double height;
  final double radius;

  @override
  Widget build(BuildContext context) {
    return _Shimmer(
      child: Container(
        width: width,
        height: height,
        decoration: BoxDecoration(
          color: AppColors.borderLight,
          borderRadius: BorderRadius.circular(radius),
        ),
      ),
    );
  }
}

/// Skeleton for a metric KPI card (label + big number + trend line).
class SkeletonMetricCard extends StatelessWidget {
  const SkeletonMetricCard({super.key});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(AppSpacing.s6),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: AppRadius.card,
        border: Border.all(color: AppColors.border),
      ),
      child: _Shimmer(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Label
            Container(
              width: 80,
              height: 10,
              decoration: BoxDecoration(
                color: AppColors.borderLight,
                borderRadius: BorderRadius.circular(4),
              ),
            ),
            const SizedBox(height: 12),
            // Hero number
            Container(
              width: 140,
              height: 32,
              decoration: BoxDecoration(
                color: AppColors.borderLight,
                borderRadius: BorderRadius.circular(6),
              ),
            ),
            const SizedBox(height: 8),
            // Trend
            Container(
              width: 100,
              height: 10,
              decoration: BoxDecoration(
                color: AppColors.borderLight,
                borderRadius: BorderRadius.circular(4),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Skeleton for a list row (icon + two lines of text + trailing amount).
class SkeletonListRow extends StatelessWidget {
  const SkeletonListRow({super.key});

  @override
  Widget build(BuildContext context) {
    return _Shimmer(
      child: Padding(
        padding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.s4,
          vertical: AppSpacing.s3,
        ),
        child: Row(
          children: [
            Container(
              width: 40,
              height: 40,
              decoration: BoxDecoration(
                color: AppColors.borderLight,
                borderRadius: BorderRadius.circular(10),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    height: 13,
                    decoration: BoxDecoration(
                      color: AppColors.borderLight,
                      borderRadius: BorderRadius.circular(4),
                    ),
                  ),
                  const SizedBox(height: 6),
                  Container(
                    width: 100,
                    height: 11,
                    decoration: BoxDecoration(
                      color: AppColors.borderLight,
                      borderRadius: BorderRadius.circular(4),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 12),
            Container(
              width: 64,
              height: 16,
              decoration: BoxDecoration(
                color: AppColors.borderLight,
                borderRadius: BorderRadius.circular(4),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Full dashboard skeleton — shown while first report loads.
class SkeletonDashboard extends StatelessWidget {
  const SkeletonDashboard({super.key});

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(AppSpacing.s4),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SizedBox(height: AppSpacing.s4),
          // Health score card
          const SkeletonBox(width: double.infinity, height: 80, radius: 16),
          const SizedBox(height: AppSpacing.s4),
          // 2×2 metric grid
          Row(
            children: const [
              Expanded(child: SkeletonMetricCard()),
              SizedBox(width: AppSpacing.s3),
              Expanded(child: SkeletonMetricCard()),
            ],
          ),
          const SizedBox(height: AppSpacing.s3),
          Row(
            children: const [
              Expanded(child: SkeletonMetricCard()),
              SizedBox(width: AppSpacing.s3),
              Expanded(child: SkeletonMetricCard()),
            ],
          ),
          const SizedBox(height: AppSpacing.s4),
          // Recoverable banner
          const SkeletonBox(width: double.infinity, height: 64, radius: 12),
          const SizedBox(height: AppSpacing.s4),
          // Recent activity
          for (int i = 0; i < 4; i++) ...[
            const SkeletonListRow(),
            const Divider(height: 1),
          ],
        ],
      ),
    );
  }
}
