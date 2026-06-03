import 'package:flutter/material.dart';

import '../../core/theme/app_colors.dart';
import '../widgets/glass_card.dart';

/// Generic "Coming Soon" screen used throughout the app for unreleased features.
///
/// The router supplies explicit [title], [icon], [description], and [features].
/// The drawer can also push this with a [feature] key (looked up from [_meta]).
class ComingSoonScreen extends StatelessWidget {
  /// Direct construction — used by the router for every coming-soon route.
  const ComingSoonScreen({
    super.key,
    required this.title,
    required this.icon,
    required this.description,
    this.features = const [],
    this.expectedRelease,
  }) : _featureKey = null;

  /// Feature-key construction — used when pushing /coming-soon/:feature.
  const ComingSoonScreen.fromKey({
    super.key,
    required String feature,
  })  : _featureKey = feature,
        title = '',
        icon = Icons.construction_outlined,
        description = '',
        features = const [],
        expectedRelease = null;

  final String? _featureKey;
  final String title;
  final IconData icon;
  final String description;
  final List<String> features;
  final String? expectedRelease;

  static const _meta = <String, _Meta>{
    'gst-filing': _Meta(
      title: 'GST Filing',
      icon: Icons.receipt_outlined,
      description:
          'File GSTR-1, GSTR-3B, and reconcile ITC directly from ClearSettle. '
          'Auto-populate from your reconciled sales data.',
      expectedRelease: 'Q3 2026',
      features: ['GSTR-1 auto-population', 'GSTR-3B preparation', 'ITC reconciliation'],
    ),
    'inventory': _Meta(
      title: 'Inventory Sync',
      icon: Icons.inventory_2_outlined,
      description:
          'Real-time inventory tracking across all marketplace warehouses. '
          'Low-stock alerts, reorder suggestions, and damage report automation.',
      expectedRelease: 'Q4 2026',
      features: ['Real-time inventory levels', 'Low stock alerts', 'Cross-platform sync'],
    ),
  };

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    final _Meta? resolved = _featureKey != null ? _meta[_featureKey] : null;
    final effectiveTitle   = resolved?.title       ?? title;
    final effectiveIcon    = resolved?.icon        ?? icon;
    final effectiveDesc    = resolved?.description ?? description;
    final effectiveRelease = resolved?.expectedRelease ?? expectedRelease;
    final effectiveFeatures = resolved?.features   ?? features;

    return Scaffold(
      appBar: AppBar(
        title: Text(effectiveTitle),
        leading: const BackButton(),
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              const Spacer(),

              Container(
                width: 80,
                height: 80,
                decoration: BoxDecoration(
                  color: AppColors.primary.withValues(alpha: 0.12),
                  shape: BoxShape.circle,
                ),
                child: Icon(effectiveIcon, size: 40, color: AppColors.primary),
              ),
              const SizedBox(height: 24),

              Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                decoration: BoxDecoration(
                  color: AppColors.warning.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(
                    color: AppColors.warning.withValues(alpha: 0.4),
                  ),
                ),
                child: const Text(
                  'COMING SOON',
                  style: TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.w800,
                    color: AppColors.warning,
                    letterSpacing: 1.2,
                  ),
                ),
              ),
              const SizedBox(height: 16),

              Text(
                effectiveTitle,
                style: TextStyle(
                  fontSize: 24,
                  fontWeight: FontWeight.w800,
                  color: isDark
                      ? AppColors.textPrimaryDark
                      : AppColors.textPrimary,
                  letterSpacing: -0.5,
                ),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 12),

              Text(
                effectiveDesc,
                style: TextStyle(
                  fontSize: 14,
                  height: 1.6,
                  color: isDark
                      ? AppColors.textSecondaryDark
                      : AppColors.textSecondary,
                ),
                textAlign: TextAlign.center,
              ),

              if (effectiveFeatures.isNotEmpty) ...[
                const SizedBox(height: 20),
                GlassCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      for (final f in effectiveFeatures)
                        Padding(
                          padding: const EdgeInsets.symmetric(vertical: 4),
                          child: Row(
                            children: [
                              const Icon(Icons.check_circle_outline,
                                  size: 14, color: AppColors.primary),
                              const SizedBox(width: 8),
                              Expanded(
                                child: Text(
                                  f,
                                  style: TextStyle(
                                    fontSize: 13,
                                    color: isDark
                                        ? AppColors.textPrimaryDark
                                        : AppColors.textPrimary,
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ),
                    ],
                  ),
                ),
              ],

              if (effectiveRelease != null) ...[
                const SizedBox(height: 16),
                GlassCard(
                  child: Row(
                    children: [
                      const Icon(Icons.calendar_today_outlined,
                          size: 16, color: AppColors.primary),
                      const SizedBox(width: 10),
                      Text(
                        'Expected: $effectiveRelease',
                        style: TextStyle(
                          fontSize: 13,
                          fontWeight: FontWeight.w600,
                          color: isDark
                              ? AppColors.textPrimaryDark
                              : AppColors.textPrimary,
                        ),
                      ),
                    ],
                  ),
                ),
              ],

              const Spacer(),

              SizedBox(
                width: double.infinity,
                child: ElevatedButton.icon(
                  onPressed: () => Navigator.of(context).pop(),
                  icon: const Icon(Icons.arrow_back, size: 18),
                  label: const Text('Go Back'),
                ),
              ),
              const SizedBox(height: 8),
            ],
          ),
        ),
      ),
    );
  }
}

class _Meta {
  const _Meta({
    required this.title,
    required this.icon,
    required this.description,
    required this.expectedRelease,
    required this.features,
  });

  final String title;
  final IconData icon;
  final String description;
  final String expectedRelease;
  final List<String> features;
}
