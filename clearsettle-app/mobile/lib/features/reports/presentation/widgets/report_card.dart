import 'package:flutter/material.dart';

import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_text_styles.dart';
import '../../../../core/utils/currency_formatter.dart';
import '../../../../core/utils/date_formatter.dart';
import '../../domain/entities/report_entities.dart';

// Flipkart brand blue reused from AppColors
const _kFlipkartColor = AppColors.flipkart;

class ReportCard extends StatelessWidget {
  const ReportCard({
    super.key,
    required this.report,
    required this.onTap,
    this.onDelete,
    this.onRetry,
    this.isParsing = false,
  });

  final ReportListItem report;
  final VoidCallback onTap;
  final VoidCallback? onDelete;
  final VoidCallback? onRetry;
  final bool isParsing;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: report.isParsed ? onTap : null,
      child: Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: AppColors.surface,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: _borderColor),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                _buildIcon(),
                const SizedBox(width: 12),
                Expanded(child: _buildHeader()),
                _buildStatusBadge(),
              ],
            ),
            if (report.isParsed) ...[
              const SizedBox(height: 12),
              const Divider(height: 1),
              const SizedBox(height: 10),
              _buildFinancials(),
            ],
            if (report.isFailed) ...[
              const SizedBox(height: 8),
              _buildErrorRow(),
            ],
            if (isParsing) ...[
              const SizedBox(height: 10),
              const LinearProgressIndicator(
                backgroundColor: AppColors.surfaceVariant,
                color: AppColors.primary,
              ),
              const SizedBox(height: 4),
              const Text('Parsing report…', style: AppTextStyles.labelSmall),
            ],
          ],
        ),
      ),
    );
  }

  Color get _borderColor {
    if (report.isFailed) return AppColors.error.withValues(alpha: 0.3);
    if (report.isParsed && report.discrepancyCount > 0) {
      return AppColors.warning.withValues(alpha: 0.4);
    }
    return AppColors.divider;
  }

  Widget _buildIcon() {
    return Container(
      width: 40,
      height: 40,
      decoration: BoxDecoration(
        color: _iconBg,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Icon(_iconData, color: _iconColor, size: 20),
    );
  }

  Color get _iconBg {
    if (report.isApiSync) return _kFlipkartColor.withValues(alpha: 0.10);
    if (report.isFailed) return AppColors.error.withValues(alpha: 0.08);
    if (report.isParsed) return AppColors.success.withValues(alpha: 0.1);
    return AppColors.primary.withValues(alpha: 0.08);
  }

  Color get _iconColor {
    if (report.isApiSync) return _kFlipkartColor;
    if (report.isFailed) return AppColors.error;
    if (report.isParsed) return AppColors.success;
    return AppColors.primary;
  }

  IconData get _iconData {
    if (report.isApiSync) return Icons.cloud_done_outlined;
    if (report.isFailed) return Icons.error_outline;
    if (report.isParsed) return Icons.check_circle_outline;
    return Icons.pending_outlined;
  }

  Widget _buildHeader() {
    final subtitle = report.isApiSync
        ? 'API Sync • ${report.totalOrders} orders • '
            '${DateFormatter.formatDate(report.uploadedAt)}'
        : '${report.marketplace.toUpperCase()} • ${report.fileSizeLabel} • '
            '${DateFormatter.formatDate(report.uploadedAt)}';

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Expanded(
              child: Text(
                report.isApiSync ? 'Flipkart API Sync' : report.fileName,
                style: AppTextStyles.titleMedium,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
            ),
            if (report.isApiSync) ...[
              const SizedBox(width: 6),
              _ApiSourceBadge(),
            ],
          ],
        ),
        const SizedBox(height: 2),
        Text(subtitle, style: AppTextStyles.labelSmall),
      ],
    );
  }

  Widget _buildStatusBadge() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: _statusColor.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(6),
      ),
      child: Text(
        _statusLabel,
        style: AppTextStyles.labelSmall.copyWith(color: _statusColor),
      ),
    );
  }

  String get _statusLabel {
    switch (report.status) {
      case 'parsed':
        return 'Parsed';
      case 'parsing':
        return 'Parsing';
      case 'failed':
        return 'Failed';
      default:
        return 'Pending';
    }
  }

  Color get _statusColor {
    switch (report.status) {
      case 'parsed':
        return AppColors.success;
      case 'failed':
        return AppColors.error;
      case 'parsing':
        return AppColors.warning;
      default:
        return AppColors.textSecondary;
    }
  }

  Widget _buildFinancials() {
    return Row(
      children: [
        Expanded(
          child: _FinStat(
            label: 'Orders',
            value: report.totalOrders.toString(),
          ),
        ),
        Expanded(
          child: _FinStat(
            label: 'Gross Revenue',
            value: CurrencyFormatter.formatCompact(report.grossRevenue),
          ),
        ),
        Expanded(
          child: _FinStat(
            label: 'Net Settlement',
            value: CurrencyFormatter.formatCompact(report.netSettlement),
            valueColor: AppColors.positive,
          ),
        ),
        if (report.discrepancyCount > 0)
          _DiscrepancyPill(count: report.discrepancyCount),
      ],
    );
  }

  Widget _buildErrorRow() {
    return Row(
      children: [
        const Icon(Icons.info_outline, color: AppColors.error, size: 14),
        const SizedBox(width: 4),
        Expanded(
          child: Text(
            report.errorMessage ?? 'Parse failed.',
            style: AppTextStyles.labelSmall.copyWith(color: AppColors.error),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
        ),
        if (onRetry != null)
          TextButton(
            onPressed: onRetry,
            style: TextButton.styleFrom(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              minimumSize: Size.zero,
            ),
            child: const Text('Retry', style: TextStyle(fontSize: 12)),
          ),
      ],
    );
  }
}

class _FinStat extends StatelessWidget {
  const _FinStat({required this.label, required this.value, this.valueColor});

  final String label;
  final String value;
  final Color? valueColor;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(value,
            style: AppTextStyles.titleMedium.copyWith(
              color: valueColor ?? AppColors.textPrimary,
              fontWeight: FontWeight.w700,
            )),
        Text(label, style: AppTextStyles.labelSmall),
      ],
    );
  }
}

class _DiscrepancyPill extends StatelessWidget {
  const _DiscrepancyPill({required this.count});

  final int count;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: AppColors.warning.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.warning_amber_rounded,
              color: AppColors.warning, size: 13),
          const SizedBox(width: 3),
          Text(
            '$count',
            style: AppTextStyles.labelSmall.copyWith(
              color: AppColors.warning,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
    );
  }
}

class _ApiSourceBadge extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        color: _kFlipkartColor.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(4),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.cloud_outlined, color: _kFlipkartColor, size: 11),
          const SizedBox(width: 3),
          Text(
            'API',
            style: AppTextStyles.labelSmall.copyWith(
              color: _kFlipkartColor,
              fontWeight: FontWeight.w700,
              fontSize: 10,
            ),
          ),
        ],
      ),
    );
  }
}
