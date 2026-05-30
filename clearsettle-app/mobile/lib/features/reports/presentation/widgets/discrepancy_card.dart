import 'package:flutter/material.dart';

import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_text_styles.dart';
import '../../../../core/utils/currency_formatter.dart';
import '../../../../reconciliation/reconciliation_result.dart';

class DiscrepancyCard extends StatelessWidget {
  const DiscrepancyCard({super.key, required this.discrepancy});

  final Discrepancy discrepancy;

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: _severityColor.withValues(alpha: 0.3)),
        boxShadow: [
          BoxShadow(
            color: _severityColor.withValues(alpha: 0.05),
            blurRadius: 6,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              _SeverityDot(color: _severityColor),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  discrepancy.typeLabel,
                  style: AppTextStyles.titleMedium.copyWith(
                    color: _severityColor,
                  ),
                ),
              ),
              _VariancePill(variance: discrepancy.variance),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            discrepancy.description,
            style: AppTextStyles.bodySmall,
          ),
          if (discrepancy.orderId != null) ...[
            const SizedBox(height: 6),
            _MetaRow(
              icon: Icons.receipt_long_outlined,
              label: 'Order',
              value: discrepancy.orderId!,
            ),
          ],
          const SizedBox(height: 8),
          Row(
            children: [
              Expanded(
                child: _AmountBox(
                  label: 'Expected',
                  amount: discrepancy.expectedAmount,
                  color: AppColors.success,
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: _AmountBox(
                  label: 'Actual',
                  amount: discrepancy.actualAmount,
                  color: AppColors.error,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Color get _severityColor {
    switch (discrepancy.severity) {
      case DiscrepancySeverity.critical:
        return AppColors.error;
      case DiscrepancySeverity.high:
        return const Color(0xFFE65100);
      case DiscrepancySeverity.medium:
        return AppColors.warning;
      case DiscrepancySeverity.low:
        return AppColors.textSecondary;
    }
  }
}

class _SeverityDot extends StatelessWidget {
  const _SeverityDot({required this.color});

  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 8,
      height: 8,
      decoration: BoxDecoration(color: color, shape: BoxShape.circle),
    );
  }
}

class _VariancePill extends StatelessWidget {
  const _VariancePill({required this.variance});

  final double variance;

  @override
  Widget build(BuildContext context) {
    if (variance <= 0) return const SizedBox.shrink();
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: AppColors.error.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(6),
      ),
      child: Text(
        '▲ ${CurrencyFormatter.format(variance)}',
        style: AppTextStyles.labelSmall.copyWith(color: AppColors.error),
      ),
    );
  }
}

class _MetaRow extends StatelessWidget {
  const _MetaRow({
    required this.icon,
    required this.label,
    required this.value,
  });

  final IconData icon;
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Icon(icon, size: 13, color: AppColors.textSecondary),
        const SizedBox(width: 4),
        Text('$label: ', style: AppTextStyles.labelSmall),
        Expanded(
          child: Text(
            value,
            style: AppTextStyles.labelSmall.copyWith(
              color: AppColors.textPrimary,
              fontWeight: FontWeight.w600,
            ),
            overflow: TextOverflow.ellipsis,
          ),
        ),
      ],
    );
  }
}

class _AmountBox extends StatelessWidget {
  const _AmountBox({
    required this.label,
    required this.amount,
    required this.color,
  });

  final String label;
  final double amount;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.06),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: AppTextStyles.labelSmall),
          const SizedBox(height: 2),
          Text(
            CurrencyFormatter.format(amount),
            style: AppTextStyles.titleMedium.copyWith(
              color: color,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
    );
  }
}
