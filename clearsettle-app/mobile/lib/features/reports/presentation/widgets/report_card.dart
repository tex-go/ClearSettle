import 'package:flutter/material.dart';

import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_text_styles.dart';
import '../../../../core/utils/currency_formatter.dart';
import '../../../../core/utils/date_formatter.dart';
import '../../domain/entities/report_entities.dart';

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
    // Allow opening parsed, failed, and backend_processing reports (detail shows processing state)
    final canOpen = report.isParsed || report.isFailed || report.isBackendProcessing;

    return GestureDetector(
      onTap: canOpen ? onTap : null,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 150),
        decoration: BoxDecoration(
          color: AppColors.surface,
          borderRadius: BorderRadius.circular(AppRadius.r4),
          border: Border.all(color: _borderColor, width: 1),
          boxShadow: AppShadows.card,
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // ── Header ───────────────────────────────────────────────
            Padding(
              padding: const EdgeInsets.fromLTRB(14, 14, 14, 12),
              child: Row(
                children: [
                  _LeadingIcon(report: report),
                  const SizedBox(width: 12),
                  Expanded(child: _HeaderText(report: report)),
                  const SizedBox(width: 8),
                  _StatusPill(report: report),
                  if (onDelete != null) ...[
                    const SizedBox(width: 4),
                    _DeleteButton(onDelete: onDelete!),
                  ],
                ],
              ),
            ),

            // ── Parsing progress bar ─────────────────────────────────
            if (isParsing) ...[
              Padding(
                padding: const EdgeInsets.fromLTRB(14, 0, 14, 4),
                child: Row(
                  children: [
                    const Icon(Icons.hourglass_top_rounded,
                        size: 12, color: AppColors.accent),
                    const SizedBox(width: 6),
                    const Text('Analyzing report…',
                        style: AppTextStyles.labelSmall),
                  ],
                ),
              ),
              ClipRRect(
                borderRadius: const BorderRadius.vertical(
                    bottom: Radius.circular(AppRadius.r4)),
                child: const LinearProgressIndicator(
                  color: AppColors.accent,
                  backgroundColor: AppColors.surfaceVariant,
                  minHeight: 3,
                ),
              ),
            ],

            // ── Financial stats ──────────────────────────────────────
            if (report.isParsed && !isParsing) ...[
              Container(
                height: 1,
                margin: const EdgeInsets.symmetric(horizontal: 14),
                color: AppColors.divider,
              ),
              Padding(
                padding: const EdgeInsets.fromLTRB(14, 10, 14, 12),
                child: _FinancialRow(report: report),
              ),
            ],

            // ── Error row ────────────────────────────────────────────
            if (report.isFailed)
              _ErrorRow(
                message: report.errorMessage,
                onRetry: onRetry,
              ),
          ],
        ),
      ),
    );
  }

  Color get _borderColor {
    if (report.isFailed) return AppColors.error.withValues(alpha: 0.25);
    if (report.isParsed && report.discrepancyCount > 0) {
      return AppColors.warning.withValues(alpha: 0.35);
    }
    return AppColors.divider;
  }
}

// ── Leading icon ────────────────────────────────────────────────────────────

class _LeadingIcon extends StatelessWidget {
  const _LeadingIcon({required this.report});
  final ReportListItem report;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 40,
      height: 40,
      decoration: BoxDecoration(
        color: _bg,
        borderRadius: BorderRadius.circular(10),
      ),
      child: Icon(_icon, color: _color, size: 19),
    );
  }

  Color get _bg {
    if (report.isFailed) return AppColors.error.withValues(alpha: 0.08);
    if (report.isParsed) return AppColors.success.withValues(alpha: 0.08);
    if (report.isApiSync) return AppColors.flipkart.withValues(alpha: 0.08);
    return AppColors.accent.withValues(alpha: 0.08);
  }

  Color get _color {
    if (report.isFailed) return AppColors.error;
    if (report.isParsed) return AppColors.success;
    if (report.isApiSync) return AppColors.flipkart;
    return AppColors.accent;
  }

  IconData get _icon {
    if (report.isFailed) return Icons.error_outline_rounded;
    if (report.isParsed) return Icons.check_circle_outline_rounded;
    if (report.isApiSync) return Icons.cloud_done_outlined;
    return Icons.pending_outlined;
  }
}

// ── Header text ─────────────────────────────────────────────────────────────

class _HeaderText extends StatelessWidget {
  const _HeaderText({required this.report});
  final ReportListItem report;

  @override
  Widget build(BuildContext context) {
    final subtitle = report.isApiSync
        ? 'API Sync • ${report.totalOrders} orders • ${DateFormatter.formatDate(report.uploadedAt)}'
        : '${report.marketplace.toUpperCase()} • ${report.fileSizeLabel} • ${DateFormatter.formatDate(report.uploadedAt)}';

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          report.isApiSync ? 'Flipkart API Sync' : report.fileName,
          style: AppTextStyles.titleSmall,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
        ),
        const SizedBox(height: 2),
        Text(subtitle, style: AppTextStyles.labelSmall),
      ],
    );
  }
}

// ── Status pill ─────────────────────────────────────────────────────────────

class _StatusPill extends StatelessWidget {
  const _StatusPill({required this.report});
  final ReportListItem report;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: _color.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: _color.withValues(alpha: 0.2)),
      ),
      child: Text(
        _label,
        style: TextStyle(
          fontSize: 10,
          fontWeight: FontWeight.w600,
          color: _color,
        ),
      ),
    );
  }

  String get _label => switch (report.status) {
        'parsed'  => 'Parsed',
        'parsing' => 'Parsing',
        'failed'  => 'Failed',
        _         => 'Pending',
      };

  Color get _color => switch (report.status) {
        'parsed'  => AppColors.success,
        'failed'  => AppColors.error,
        'parsing' => AppColors.warning,
        _         => AppColors.textSecondary,
      };
}

// ── Delete button ────────────────────────────────────────────────────────────

class _DeleteButton extends StatelessWidget {
  const _DeleteButton({required this.onDelete});
  final VoidCallback onDelete;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onDelete,
      child: Container(
        width: 28,
        height: 28,
        decoration: BoxDecoration(
          color: AppColors.error.withValues(alpha: 0.06),
          borderRadius: BorderRadius.circular(7),
        ),
        child: const Icon(Icons.delete_outline_rounded,
            size: 14, color: AppColors.error),
      ),
    );
  }
}

// ── Financial row ────────────────────────────────────────────────────────────

class _FinancialRow extends StatelessWidget {
  const _FinancialRow({required this.report});
  final ReportListItem report;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        _Stat(
          label: 'Orders',
          value: report.totalOrders.toString(),
          icon: Icons.shopping_bag_outlined,
          iconColor: AppColors.info,
        ),
        const _StatDivider(),
        _Stat(
          label: 'Gross Revenue',
          value: CurrencyFormatter.formatCompact(report.grossRevenue),
          icon: Icons.trending_up_rounded,
          iconColor: AppColors.accent,
        ),
        const _StatDivider(),
        _Stat(
          label: 'Net Settlement',
          value: CurrencyFormatter.formatCompact(report.netSettlement),
          icon: Icons.account_balance_outlined,
          iconColor: AppColors.success,
          valueColor: AppColors.success,
        ),
        if (report.discrepancyCount > 0) ...[
          const _StatDivider(),
          _DiscrepancyPill(count: report.discrepancyCount),
        ],
      ],
    );
  }
}

class _Stat extends StatelessWidget {
  const _Stat({
    required this.label,
    required this.value,
    required this.icon,
    required this.iconColor,
    this.valueColor,
  });

  final String label;
  final String value;
  final IconData icon;
  final Color iconColor;
  final Color? valueColor;

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, size: 10, color: iconColor),
              const SizedBox(width: 3),
              Text(label, style: AppTextStyles.labelSmall),
            ],
          ),
          const SizedBox(height: 3),
          Text(
            value,
            style: AppTextStyles.metricSmall.copyWith(
              fontSize: 14,
              color: valueColor ?? AppColors.textPrimary,
            ),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
        ],
      ),
    );
  }
}

class _StatDivider extends StatelessWidget {
  const _StatDivider();
  @override
  Widget build(BuildContext context) {
    return Container(
      width: 1,
      height: 28,
      margin: const EdgeInsets.symmetric(horizontal: 10),
      color: AppColors.divider,
    );
  }
}

class _DiscrepancyPill extends StatelessWidget {
  const _DiscrepancyPill({required this.count});
  final int count;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 4),
      decoration: BoxDecoration(
        color: AppColors.warning.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: AppColors.warning.withValues(alpha: 0.2)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.warning_amber_rounded,
              color: AppColors.warning, size: 11),
          const SizedBox(width: 3),
          Text(
            '$count',
            style: const TextStyle(
              fontSize: 11,
              fontWeight: FontWeight.w700,
              color: AppColors.warning,
            ),
          ),
        ],
      ),
    );
  }
}

// ── Error row ────────────────────────────────────────────────────────────────

class _ErrorRow extends StatelessWidget {
  const _ErrorRow({this.message, this.onRetry});
  final String? message;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(14, 8, 14, 12),
      decoration: const BoxDecoration(
        color: Color(0x06EF4444),
        borderRadius: BorderRadius.vertical(
            bottom: Radius.circular(AppRadius.r4)),
      ),
      child: Row(
        children: [
          const Icon(Icons.info_outline, color: AppColors.error, size: 13),
          const SizedBox(width: 6),
          Expanded(
            child: Text(
              message ?? 'Parse failed.',
              style: AppTextStyles.labelSmall
                  .copyWith(color: AppColors.error),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          ),
          if (onRetry != null) ...[
            const SizedBox(width: 8),
            GestureDetector(
              onTap: onRetry,
              child: Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: AppColors.error.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(6),
                ),
                child: const Text('Retry',
                    style: TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.w600,
                        color: AppColors.error)),
              ),
            ),
          ],
        ],
      ),
    );
  }
}
