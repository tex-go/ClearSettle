import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_text_styles.dart';
import '../../../../core/utils/currency_formatter.dart';
import '../../../../core/utils/date_formatter.dart';
import '../../../../parsers/parser_result.dart';
import '../../../../shared/widgets/app_error_widget.dart';
import '../../../../shared/widgets/empty_state_widget.dart';
import '../../../../shared/widgets/loading_indicator.dart';
import '../providers/report_detail_provider.dart';

class SettlementDetailScreen extends ConsumerWidget {
  const SettlementDetailScreen({super.key, required this.reportId});

  final String reportId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final detailAsync = ref.watch(reportDetailProvider(reportId));

    return Scaffold(
      backgroundColor: AppColors.backgroundLight,
      appBar: AppBar(title: const Text('Settlements')),
      body: detailAsync.when(
        loading: () => const LoadingIndicator(message: 'Loading settlements…'),
        error: (e, _) => AppErrorWidget(message: e.toString()),
        data: (detail) {
          final orders = detail.orders;
          if (orders.isEmpty) {
            return const EmptyStateWidget(
              icon: Icons.receipt_long_outlined,
              title: 'No settlement rows',
              subtitle: 'No order-level data was extracted from this report.',
            );
          }

          final totalGross = orders.fold(0.0, (s, o) => s + o.grossAmount);
          final totalNet = orders.fold(0.0, (s, o) => s + o.netSettlement);

          return Column(
            children: [
              _SummaryStrip(
                totalOrders: orders.length,
                totalGross: totalGross,
                totalNet: totalNet,
              ),
              Expanded(
                child: ListView.separated(
                  padding: const EdgeInsets.all(12),
                  itemCount: orders.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 8),
                  itemBuilder: (context, index) =>
                      _OrderRow(order: orders[index]),
                ),
              ),
            ],
          );
        },
      ),
    );
  }
}

class _SummaryStrip extends StatelessWidget {
  const _SummaryStrip({
    required this.totalOrders,
    required this.totalGross,
    required this.totalNet,
  });

  final int totalOrders;
  final double totalGross;
  final double totalNet;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      color: AppColors.surface,
      child: Row(
        children: [
          _Strip(label: 'Orders', value: totalOrders.toString()),
          const _Divider(),
          _Strip(
            label: 'Gross',
            value: CurrencyFormatter.formatCompact(totalGross),
          ),
          const _Divider(),
          _Strip(
            label: 'Net Settlement',
            value: CurrencyFormatter.formatCompact(totalNet),
            valueColor: AppColors.positive,
          ),
        ],
      ),
    );
  }
}

class _Strip extends StatelessWidget {
  const _Strip({required this.label, required this.value, this.valueColor});

  final String label;
  final String value;
  final Color? valueColor;

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Column(
        children: [
          Text(
            value,
            style: AppTextStyles.titleMedium.copyWith(
              color: valueColor ?? AppColors.textPrimary,
              fontWeight: FontWeight.w700,
            ),
          ),
          Text(label, style: AppTextStyles.labelSmall),
        ],
      ),
    );
  }
}

class _Divider extends StatelessWidget {
  const _Divider();

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 1,
      height: 32,
      color: AppColors.divider,
      margin: const EdgeInsets.symmetric(horizontal: 8),
    );
  }
}

class _OrderRow extends StatelessWidget {
  const _OrderRow({required this.order});

  final ParsedOrder order;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: AppColors.divider),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  order.orderId ?? '—',
                  style: AppTextStyles.titleMedium,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              _StatusPill(status: order.status),
            ],
          ),
          if (order.productTitle != null) ...[
            const SizedBox(height: 2),
            Text(
              order.productTitle!,
              style: AppTextStyles.bodySmall,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          ],
          if (order.orderDate != null) ...[
            const SizedBox(height: 2),
            Text(
              DateFormatter.formatDate(
                DateTime.tryParse(order.orderDate!) ?? DateTime.now(),
              ),
              style: AppTextStyles.labelSmall,
            ),
          ],
          const SizedBox(height: 8),
          Row(
            children: [
              _Amount(label: 'Gross', amount: order.grossAmount),
              _Amount(label: 'Fees', amount: -order.totalFees),
              _Amount(
                label: 'Net',
                amount: order.netSettlement,
                color: order.netSettlement >= 0
                    ? AppColors.positive
                    : AppColors.negative,
              ),
            ],
          ),
          if (order.settlementVariance > 1.0) ...[
            const SizedBox(height: 6),
            Row(
              children: [
                const Icon(Icons.warning_amber_rounded,
                    size: 13, color: AppColors.warning),
                const SizedBox(width: 4),
                Text(
                  'Variance: ${CurrencyFormatter.format(order.settlementVariance)}',
                  style: AppTextStyles.labelSmall
                      .copyWith(color: AppColors.warning),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }
}

class _StatusPill extends StatelessWidget {
  const _StatusPill({required this.status});

  final String? status;

  @override
  Widget build(BuildContext context) {
    if (status == null) return const SizedBox.shrink();
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
      decoration: BoxDecoration(
        color: AppColors.primary.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(4),
      ),
      child: Text(
        status!,
        style: AppTextStyles.labelSmall.copyWith(color: AppColors.primary),
      ),
    );
  }
}

class _Amount extends StatelessWidget {
  const _Amount({required this.label, required this.amount, this.color});

  final String label;
  final double amount;
  final Color? color;

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: AppTextStyles.labelSmall),
          Text(
            CurrencyFormatter.format(amount.abs()),
            style: AppTextStyles.bodySmall.copyWith(
              color: color ?? AppColors.textPrimary,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }
}
