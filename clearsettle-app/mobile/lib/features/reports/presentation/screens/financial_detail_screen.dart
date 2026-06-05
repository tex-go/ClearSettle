import 'package:flutter/material.dart';

import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_text_styles.dart';
import '../../../../core/utils/currency_formatter.dart';
import '../../../../core/utils/date_formatter.dart';
import '../../../../parsers/parser_result.dart';

// ── Detail type ────────────────────────────────────────────────────────────────

enum FinancialDetailType {
  grossRevenue,
  returns,
  cancellations,
  netSales,
  netSettlement,
}

extension _TypeLabel on FinancialDetailType {
  String get title {
    switch (this) {
      case FinancialDetailType.grossRevenue:   return 'Gross Revenue';
      case FinancialDetailType.returns:        return 'Returns';
      case FinancialDetailType.cancellations:  return 'Cancellations';
      case FinancialDetailType.netSales:       return 'Net Sales';
      case FinancialDetailType.netSettlement:  return 'Net Settlement';
    }
  }

  String get emptyMessage {
    switch (this) {
      case FinancialDetailType.grossRevenue:   return 'No sale orders found in this report.';
      case FinancialDetailType.returns:        return 'No returned items found in this report.';
      case FinancialDetailType.cancellations:  return 'No cancelled orders found in this report.';
      case FinancialDetailType.netSales:       return 'No sales orders found in this report.';
      case FinancialDetailType.netSettlement:  return 'No settlement records found in this report.';
    }
  }
}

// ── Screen ─────────────────────────────────────────────────────────────────────

class FinancialDetailScreen extends StatefulWidget {
  const FinancialDetailScreen({
    super.key,
    required this.type,
    required this.allOrders,
    required this.totalAmount,
    required this.reportName,
  });

  final FinancialDetailType type;
  final List<ParsedOrder> allOrders;
  final double totalAmount;
  final String reportName;

  @override
  State<FinancialDetailScreen> createState() => _FinancialDetailScreenState();
}

class _FinancialDetailScreenState extends State<FinancialDetailScreen> {
  String _query = '';
  _SortBy _sortBy = _SortBy.date;
  bool _ascending = false;

  // ── Filter based on type ─────────────────────────────────────────────────────

  List<ParsedOrder> get _baseOrders {
    switch (widget.type) {
      case FinancialDetailType.grossRevenue:
        return widget.allOrders.where((o) => o.grossAmount > 0).toList();
      case FinancialDetailType.returns:
        return widget.allOrders.where((o) =>
            o.grossAmount < 0 ||
            (o.status?.toLowerCase().contains('return') ?? false) ||
            (o.status?.toLowerCase().contains('rto') ?? false)).toList();
      case FinancialDetailType.cancellations:
        return widget.allOrders.where((o) =>
            (o.status?.toLowerCase().contains('cancel') ?? false)).toList();
      case FinancialDetailType.netSales:
        return widget.allOrders;
      case FinancialDetailType.netSettlement:
        return widget.allOrders.where((o) => o.netSettlement != 0).toList();
    }
  }

  List<ParsedOrder> get _visibleOrders {
    var list = _baseOrders;

    if (_query.isNotEmpty) {
      final q = _query.toLowerCase();
      list = list.where((o) =>
          (o.orderId?.toLowerCase().contains(q) ?? false) ||
          (o.productTitle?.toLowerCase().contains(q) ?? false) ||
          (o.sku?.toLowerCase().contains(q) ?? false)).toList();
    }

    list.sort((a, b) {
      int cmp;
      switch (_sortBy) {
        case _SortBy.amount:
          cmp = _amount(a).compareTo(_amount(b));
        case _SortBy.date:
          cmp = (a.orderDate ?? '').compareTo(b.orderDate ?? '');
        case _SortBy.product:
          cmp = (a.productTitle ?? '').compareTo(b.productTitle ?? '');
      }
      return _ascending ? cmp : -cmp;
    });

    return list;
  }

  double _amount(ParsedOrder o) {
    switch (widget.type) {
      case FinancialDetailType.grossRevenue: return o.grossAmount;
      case FinancialDetailType.returns:      return o.grossAmount.abs();
      case FinancialDetailType.cancellations:return o.grossAmount.abs();
      case FinancialDetailType.netSales:     return o.grossAmount;
      case FinancialDetailType.netSettlement:return o.netSettlement;
    }
  }

  // ── Build ────────────────────────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    final orders  = _visibleOrders;
    final isEmpty  = widget.allOrders.isEmpty;
    final noOrders = _baseOrders.isEmpty;

    return Scaffold(
      appBar: AppBar(
        title: Text(widget.type.title),
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(56),
          child: Padding(
            padding: const EdgeInsets.fromLTRB(12, 0, 12, 8),
            child: TextField(
              onChanged: (v) => setState(() => _query = v),
              style: const TextStyle(color: AppColors.textInverse, fontSize: 14),
              decoration: InputDecoration(
                hintText: 'Search product, SKU, order ID…',
                hintStyle: const TextStyle(color: Colors.white54, fontSize: 13),
                prefixIcon: const Icon(Icons.search, color: Colors.white54, size: 18),
                filled: true,
                fillColor: Colors.white12,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(10),
                  borderSide: BorderSide.none,
                ),
                contentPadding: const EdgeInsets.symmetric(vertical: 8),
              ),
            ),
          ),
        ),
      ),
      body: Column(
        children: [
          // ── Summary header ──────────────────────────────────────────────────
          _SummaryHeader(
            type: widget.type,
            total: widget.totalAmount,
            count: _baseOrders.length,
          ),

          // ── Sort bar ────────────────────────────────────────────────────────
          if (!isEmpty && !noOrders)
            _SortBar(
              sortBy: _sortBy,
              ascending: _ascending,
              onSort: (s) => setState(() {
                if (_sortBy == s) {
                  _ascending = !_ascending;
                } else {
                  _sortBy = s;
                  _ascending = false;
                }
              }),
            ),

          // ── Empty states ────────────────────────────────────────────────────
          if (isEmpty)
            Expanded(child: _EmptyState(
              icon: Icons.table_chart_outlined,
              message: 'Order-level data is not available for backend-processed reports.\n\n'
                  'Re-upload the report in debug mode or view the full breakdown on the web app.',
            ))
          else if (noOrders)
            Expanded(child: _EmptyState(
              icon: Icons.inbox_outlined,
              message: widget.type.emptyMessage,
            ))
          else if (orders.isEmpty)
            Expanded(child: _EmptyState(
              icon: Icons.search_off_outlined,
              message: 'No results for "$_query".',
            ))
          else
            // ── Order list ────────────────────────────────────────────────────
            Expanded(
              child: ListView.separated(
                padding: const EdgeInsets.fromLTRB(12, 8, 12, 24),
                itemCount: orders.length,
                separatorBuilder: (_, __) => const SizedBox(height: 8),
                itemBuilder: (_, i) => _OrderCard(
                  order: orders[i],
                  type: widget.type,
                ),
              ),
            ),
        ],
      ),
    );
  }
}

// ── Summary header ─────────────────────────────────────────────────────────────

class _SummaryHeader extends StatelessWidget {
  const _SummaryHeader({
    required this.type,
    required this.total,
    required this.count,
  });

  final FinancialDetailType type;
  final double total;
  final int count;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.fromLTRB(16, 14, 16, 14),
      color: isDark ? AppColors.accentNavy : AppColors.primary.withValues(alpha: 0.06),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  type.title,
                  style: AppTextStyles.labelSmall.copyWith(
                    color: isDark ? AppColors.textSecondaryDark : AppColors.textSecondary,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  CurrencyFormatter.format(total.abs()),
                  style: AppTextStyles.headlineMedium.copyWith(
                    color: AppColors.primary,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ],
            ),
          ),
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(
                '$count',
                style: AppTextStyles.titleLarge.copyWith(
                  color: AppColors.primary,
                  fontWeight: FontWeight.w700,
                ),
              ),
              Text(
                count == 1 ? 'order' : 'orders',
                style: AppTextStyles.labelSmall.copyWith(
                  color: isDark ? AppColors.textSecondaryDark : AppColors.textSecondary,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

// ── Sort bar ───────────────────────────────────────────────────────────────────

enum _SortBy { amount, date, product }

class _SortBar extends StatelessWidget {
  const _SortBar({
    required this.sortBy,
    required this.ascending,
    required this.onSort,
  });

  final _SortBy sortBy;
  final bool ascending;
  final void Function(_SortBy) onSort;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      child: Row(
        children: [
          Text('Sort:', style: AppTextStyles.labelSmall),
          const SizedBox(width: 8),
          ..._SortBy.values.map((s) => _Chip(
                label: s == _SortBy.amount
                    ? 'Amount'
                    : s == _SortBy.date
                        ? 'Date'
                        : 'Product',
                selected: sortBy == s,
                ascending: ascending,
                showArrow: sortBy == s,
                onTap: () => onSort(s),
              )),
        ],
      ),
    );
  }
}

class _Chip extends StatelessWidget {
  const _Chip({
    required this.label,
    required this.selected,
    required this.ascending,
    required this.showArrow,
    required this.onTap,
  });

  final String label;
  final bool selected;
  final bool ascending;
  final bool showArrow;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(right: 6),
      child: GestureDetector(
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
          decoration: BoxDecoration(
            color: selected
                ? AppColors.primary.withValues(alpha: 0.12)
                : Colors.transparent,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(
              color: selected ? AppColors.primary : AppColors.divider,
            ),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                label,
                style: AppTextStyles.labelSmall.copyWith(
                  color: selected ? AppColors.primary : AppColors.textSecondary,
                  fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
                ),
              ),
              if (showArrow) ...[
                const SizedBox(width: 2),
                Icon(
                  ascending ? Icons.arrow_upward : Icons.arrow_downward,
                  size: 10,
                  color: AppColors.primary,
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

// ── Order card ─────────────────────────────────────────────────────────────────

class _OrderCard extends StatelessWidget {
  const _OrderCard({required this.order, required this.type});

  final ParsedOrder order;
  final FinancialDetailType type;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final surfColor = isDark ? AppColors.surfaceDark : AppColors.surface;
    final divColor  = isDark ? AppColors.dividerDark : AppColors.divider;

    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: surfColor,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: divColor),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Product title + amount
          Row(
            children: [
              Expanded(
                child: Text(
                  order.productTitle ?? order.sku ?? 'Unknown Product',
                  style: AppTextStyles.bodyMedium.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              const SizedBox(width: 8),
              Text(
                _primaryAmountLabel(),
                style: AppTextStyles.bodyMedium.copyWith(
                  color: _amountColor(),
                  fontWeight: FontWeight.w700,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          // Detail rows
          ..._buildDetails(),
        ],
      ),
    );
  }

  String _primaryAmountLabel() {
    double amt;
    switch (type) {
      case FinancialDetailType.grossRevenue:   amt = order.grossAmount;
      case FinancialDetailType.returns:        amt = order.grossAmount.abs();
      case FinancialDetailType.cancellations:  amt = order.grossAmount.abs();
      case FinancialDetailType.netSales:       amt = order.grossAmount;
      case FinancialDetailType.netSettlement:  amt = order.netSettlement;
    }
    return CurrencyFormatter.format(amt.abs());
  }

  Color _amountColor() {
    switch (type) {
      case FinancialDetailType.returns:
      case FinancialDetailType.cancellations:
        return AppColors.negative;
      case FinancialDetailType.netSettlement:
        return order.netSettlement >= 0 ? AppColors.positive : AppColors.negative;
      default:
        return AppColors.positive;
    }
  }

  List<Widget> _buildDetails() {
    final rows = <_DetailRow>[];

    if (order.orderId != null) {
      rows.add(_DetailRow('Order ID', order.orderId!));
    }
    if (order.sku != null) {
      rows.add(_DetailRow('SKU', order.sku!));
    }

    switch (type) {
      case FinancialDetailType.grossRevenue:
        rows.addAll([
          if (order.quantity > 0)
            _DetailRow('Qty', '${order.quantity}'),
          if (order.rawCommissionRate != null)
            _DetailRow('Commission Rate', '${order.rawCommissionRate!.toStringAsFixed(1)}%'),
          if (order.totalFees > 0)
            _DetailRow('Marketplace Fees', CurrencyFormatter.format(order.totalFees)),
          _DetailRow('Order Date', DateFormatter.formatShortString(order.orderDate)),
        ]);

      case FinancialDetailType.returns:
        rows.addAll([
          if (order.quantity > 0)
            _DetailRow('Qty Returned', '${order.quantity}'),
          if (order.reverseShippingFee != 0)
            _DetailRow('Reverse Shipping', CurrencyFormatter.format(order.reverseShippingFee.abs())),
          _DetailRow('Return Date', DateFormatter.formatShortString(order.orderDate)),
          if (order.status != null)
            _DetailRow('Status', order.status!),
        ]);

      case FinancialDetailType.cancellations:
        rows.addAll([
          _DetailRow('Date', DateFormatter.formatShortString(order.orderDate)),
          if (order.status != null)
            _DetailRow('Reason', order.status!),
        ]);

      case FinancialDetailType.netSales:
        rows.addAll([
          _DetailRow('Sale Amount', CurrencyFormatter.format(order.grossAmount)),
          if (order.totalFees > 0)
            _DetailRow('Total Fees', '− ${CurrencyFormatter.format(order.totalFees)}'),
          _DetailRow('Net', CurrencyFormatter.format(order.grossAmount - order.totalFees),
              highlight: true),
          _DetailRow('Date', DateFormatter.formatShortString(order.orderDate)),
        ]);

      case FinancialDetailType.netSettlement:
        rows.addAll([
          if (order.settlementId != null)
            _DetailRow('Settlement ID', order.settlementId!),
          _DetailRow('Settlement Date', DateFormatter.formatShortString(order.settlementDate)),
          if (order.grossAmount != 0)
            _DetailRow('Sale Amount', CurrencyFormatter.format(order.grossAmount)),
          if (order.totalFees > 0)
            _DetailRow('Fees Deducted', '− ${CurrencyFormatter.format(order.totalFees)}'),
          if (order.status != null)
            _DetailRow('Payment Status', order.status!),
        ]);
    }

    return rows.map((r) => _DetailTile(row: r)).toList();
  }
}

class _DetailRow {
  const _DetailRow(this.label, this.value, {this.highlight = false});
  final String label;
  final String value;
  final bool highlight;
}

class _DetailTile extends StatelessWidget {
  const _DetailTile({required this.row});
  final _DetailRow row;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(top: 4),
      child: Row(
        children: [
          Expanded(
            child: Text(
              row.label,
              style: AppTextStyles.bodySmall.copyWith(color: AppColors.textSecondary),
            ),
          ),
          Flexible(
            child: Text(
              row.value,
              style: AppTextStyles.bodySmall.copyWith(
                fontWeight: row.highlight ? FontWeight.w700 : FontWeight.w500,
                color: row.highlight ? AppColors.primary : null,
              ),
              overflow: TextOverflow.ellipsis,
              textAlign: TextAlign.end,
            ),
          ),
        ],
      ),
    );
  }
}

// ── Empty state ────────────────────────────────────────────────────────────────

class _EmptyState extends StatelessWidget {
  const _EmptyState({required this.icon, required this.message});
  final IconData icon;
  final String message;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 48, color: AppColors.textMuted),
            const SizedBox(height: 16),
            Text(
              message,
              style: AppTextStyles.bodyMedium.copyWith(color: AppColors.textSecondary),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }
}
