import 'package:flutter/material.dart';

import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_text_styles.dart';
import '../../../../shared/widgets/empty_state_widget.dart';

class AnalyticsScreen extends StatelessWidget {
  const AnalyticsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.backgroundLight,
      appBar: AppBar(title: const Text('Analytics')),
      body: Column(
        children: [
          _buildFilterBar(),
          Expanded(
            child: EmptyStateWidget(
              icon: Icons.bar_chart_outlined,
              title: 'Analytics coming soon',
              subtitle:
                  'SKU-level profitability, fee analysis, and refund trends will appear here.',
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildFilterBar() {
    return Container(
      color: AppColors.surface,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
      child: Row(
        children: [
          _ChipFilter(label: 'Last 30 days', selected: true),
          const SizedBox(width: 8),
          _ChipFilter(label: 'Flipkart', selected: false),
          const SizedBox(width: 8),
          _ChipFilter(label: 'All SKUs', selected: false),
        ],
      ),
    );
  }
}

class _ChipFilter extends StatelessWidget {
  const _ChipFilter({required this.label, required this.selected});

  final String label;
  final bool selected;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: selected
            ? AppColors.primary.withOpacity(0.1)
            : AppColors.surfaceVariant,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(
          color: selected ? AppColors.primary : AppColors.divider,
        ),
      ),
      child: Text(
        label,
        style: AppTextStyles.labelMedium.copyWith(
          color: selected ? AppColors.primary : AppColors.textSecondary,
        ),
      ),
    );
  }
}
