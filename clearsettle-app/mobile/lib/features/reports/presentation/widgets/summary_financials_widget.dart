import 'package:flutter/material.dart';

import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_text_styles.dart';
import '../../../../core/utils/currency_formatter.dart';
import '../../../../parsers/parser_result.dart';

class SummaryFinancialsWidget extends StatelessWidget {
  const SummaryFinancialsWidget({super.key, required this.summary});

  final ParsedSummary summary;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.divider),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Financial Summary', style: AppTextStyles.titleLarge),
          const SizedBox(height: 14),
          _Row(label: 'Gross Revenue', value: summary.grossSales, isPositive: true),
          _Row(label: 'Returns', value: -summary.returnsValue),
          _Row(label: 'Cancellations', value: -summary.cancellationsValue),
          const Divider(height: 20),
          _Row(label: 'Net Sales', value: summary.netSales, isPositive: true),
          const SizedBox(height: 8),
          _SubRow(label: 'Commission', value: summary.totalCommission),
          _SubRow(label: 'Shipping', value: summary.totalShipping),
          _SubRow(label: 'Reverse Shipping', value: summary.totalReverseShipping),
          _SubRow(label: 'Collection Fees', value: summary.totalCollectionFees),
          _SubRow(label: 'Fixed Fees', value: summary.totalFixedFees),
          _SubRow(label: 'GST on Fees', value: summary.totalGstOnFees),
          _SubRow(label: 'TCS', value: summary.totalTcs),
          _SubRow(label: 'TDS', value: summary.totalTds),
          const Divider(height: 20),
          _Row(
            label: 'Net Settlement',
            value: summary.netEarnings,
            isPositive: summary.netEarnings >= 0,
            bold: true,
          ),
          if (summary.amountSettled > 0) ...[
            const SizedBox(height: 4),
            _Row(label: 'Amount Settled', value: summary.amountSettled, isPositive: true),
          ],
          if (summary.amountPending > 0)
            _Row(label: 'Pending', value: summary.amountPending,
                valueColor: AppColors.warning),
        ],
      ),
    );
  }
}

class _Row extends StatelessWidget {
  const _Row({
    required this.label,
    required this.value,
    this.isPositive,
    this.bold = false,
    this.valueColor,
  });

  final String label;
  final double value;
  final bool? isPositive;
  final bool bold;
  final Color? valueColor;

  @override
  Widget build(BuildContext context) {
    final color = valueColor ??
        (isPositive == null
            ? AppColors.textPrimary
            : (isPositive! ? AppColors.positive : AppColors.negative));
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Row(
        children: [
          Expanded(
            child: Text(
              label,
              style: bold
                  ? AppTextStyles.titleMedium
                  : AppTextStyles.bodyMedium,
            ),
          ),
          Text(
            CurrencyFormatter.format(value.abs()),
            style: (bold ? AppTextStyles.titleMedium : AppTextStyles.bodyMedium)
                .copyWith(color: color, fontWeight: bold ? FontWeight.w700 : null),
          ),
        ],
      ),
    );
  }
}

class _SubRow extends StatelessWidget {
  const _SubRow({required this.label, required this.value});

  final String label;
  final double value;

  @override
  Widget build(BuildContext context) {
    if (value == 0) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.only(left: 12, bottom: 2),
      child: Row(
        children: [
          const Text('· ', style: TextStyle(color: AppColors.textSecondary)),
          Expanded(
            child: Text(label, style: AppTextStyles.bodySmall),
          ),
          Text(
            CurrencyFormatter.format(value),
            style: AppTextStyles.bodySmall
                .copyWith(color: AppColors.negative),
          ),
        ],
      ),
    );
  }
}
