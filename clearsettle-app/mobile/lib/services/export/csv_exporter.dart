import '../../parsers/parser_result.dart';
import '../../reconciliation/reconciliation_result.dart';

abstract final class CsvExporter {
  static String exportOrders(List<ParsedOrder> orders) {
    final buffer = StringBuffer();
    buffer.writeln(
      'Order ID,Settlement ID,Order Date,SKU,Product Title,'
      'Gross Amount,Commission,Collection Fee,Shipping Fee,'
      'Reverse Shipping,GST on Fees,TCS,TDS,Net Settlement,'
      'Total Fees,Settlement Variance,Status,Fulfilment Type',
    );
    for (final o in orders) {
      buffer.writeln([
        _esc(o.orderId),
        _esc(o.settlementId),
        _esc(o.orderDate),
        _esc(o.sku),
        _esc(o.productTitle),
        o.grossAmount.toStringAsFixed(2),
        o.commission.toStringAsFixed(2),
        o.collectionFee.toStringAsFixed(2),
        o.shippingFee.toStringAsFixed(2),
        o.reverseShippingFee.toStringAsFixed(2),
        o.gstOnFees.toStringAsFixed(2),
        o.tcs.toStringAsFixed(2),
        o.tds.toStringAsFixed(2),
        o.netSettlement.toStringAsFixed(2),
        o.totalFees.toStringAsFixed(2),
        o.settlementVariance.toStringAsFixed(2),
        _esc(o.status),
        _esc(o.fulfilmentType),
      ].join(','));
    }
    return buffer.toString();
  }

  static String exportDiscrepancies(List<Discrepancy> discrepancies) {
    final buffer = StringBuffer();
    buffer.writeln(
      'Type,Severity,Order ID,Description,'
      'Expected Amount,Actual Amount,Variance,Rule',
    );
    for (final d in discrepancies) {
      buffer.writeln([
        _esc(d.typeLabel),
        _esc(d.severity.name),
        _esc(d.orderId),
        _esc(d.description),
        d.expectedAmount.toStringAsFixed(2),
        d.actualAmount.toStringAsFixed(2),
        d.variance.toStringAsFixed(2),
        _esc(d.ruleName),
      ].join(','));
    }
    return buffer.toString();
  }

  // Escape a CSV value: wrap in quotes if it contains comma, quote, or newline
  static String _esc(String? value) {
    if (value == null || value.isEmpty) return '';
    if (value.contains(',') || value.contains('"') || value.contains('\n')) {
      return '"${value.replaceAll('"', '""')}"';
    }
    return value;
  }
}
