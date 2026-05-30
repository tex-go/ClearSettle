import 'dart:typed_data';

import 'package:excel/excel.dart';

import '../../parsers/parser_result.dart';
import '../../reconciliation/reconciliation_result.dart';

abstract final class ExcelExporter {
  static Uint8List exportReport({
    required String reportName,
    required ParsedSummary summary,
    required List<ParsedOrder> orders,
    required List<Discrepancy> discrepancies,
  }) {
    final excel = Excel.createExcel();

    _writeSummarySheet(excel, reportName, summary);
    _writeOrdersSheet(excel, orders);
    _writeDiscrepanciesSheet(excel, discrepancies);

    // Remove the default empty sheet
    if (excel.tables.containsKey('Sheet1')) excel.delete('Sheet1');

    return Uint8List.fromList(excel.encode()!);
  }

  static void _writeSummarySheet(
    Excel excel,
    String reportName,
    ParsedSummary summary,
  ) {
    final sheet = excel['Summary'];

    void row(String label, double value) {
      sheet.appendRow([TextCellValue(label), DoubleCellValue(value)]);
    }

    sheet.appendRow([TextCellValue('ClearSettle — Settlement Report')]);
    sheet.appendRow([TextCellValue('Report:'), TextCellValue(reportName)]);
    sheet.appendRow([TextCellValue('')]);
    sheet.appendRow([TextCellValue('Metric'), TextCellValue('Amount (₹)')]);
    row('Gross Sales', summary.grossSales);
    row('Returns', -summary.returnsValue);
    row('Cancellations', -summary.cancellationsValue);
    row('Net Sales', summary.netSales);
    sheet.appendRow([TextCellValue('')]);
    row('Commission', -summary.totalCommission);
    row('Shipping', -summary.totalShipping);
    row('Reverse Shipping', -summary.totalReverseShipping);
    row('Collection Fees', -summary.totalCollectionFees);
    row('Fixed Fees', -summary.totalFixedFees);
    row('GST on Fees', -summary.totalGstOnFees);
    row('TCS', -summary.totalTcs);
    row('TDS', -summary.totalTds);
    sheet.appendRow([TextCellValue('')]);
    row('Net Settlement', summary.netEarnings);
    if (summary.amountSettled > 0) row('Amount Settled', summary.amountSettled);
    if (summary.amountPending > 0) row('Amount Pending', summary.amountPending);
    sheet.appendRow([TextCellValue('')]);
    sheet.appendRow([TextCellValue('Total Orders'), IntCellValue(summary.totalOrders)]);
  }

  static void _writeOrdersSheet(Excel excel, List<ParsedOrder> orders) {
    final sheet = excel['Orders'];
    sheet.appendRow([
      TextCellValue('Order ID'),
      TextCellValue('Settlement ID'),
      TextCellValue('Order Date'),
      TextCellValue('SKU'),
      TextCellValue('Product Title'),
      TextCellValue('Qty'),
      TextCellValue('Gross Amount'),
      TextCellValue('Commission'),
      TextCellValue('Collection Fee'),
      TextCellValue('Shipping Fee'),
      TextCellValue('Reverse Shipping'),
      TextCellValue('GST on Fees'),
      TextCellValue('TCS'),
      TextCellValue('TDS'),
      TextCellValue('Net Settlement'),
      TextCellValue('Total Fees'),
      TextCellValue('Settlement Variance'),
      TextCellValue('Status'),
    ]);

    for (final o in orders) {
      sheet.appendRow([
        TextCellValue(o.orderId ?? ''),
        TextCellValue(o.settlementId ?? ''),
        TextCellValue(o.orderDate ?? ''),
        TextCellValue(o.sku ?? ''),
        TextCellValue(o.productTitle ?? ''),
        IntCellValue(o.quantity),
        DoubleCellValue(o.grossAmount),
        DoubleCellValue(o.commission),
        DoubleCellValue(o.collectionFee),
        DoubleCellValue(o.shippingFee),
        DoubleCellValue(o.reverseShippingFee),
        DoubleCellValue(o.gstOnFees),
        DoubleCellValue(o.tcs),
        DoubleCellValue(o.tds),
        DoubleCellValue(o.netSettlement),
        DoubleCellValue(o.totalFees),
        DoubleCellValue(o.settlementVariance),
        TextCellValue(o.status ?? ''),
      ]);
    }
  }

  static void _writeDiscrepanciesSheet(
    Excel excel,
    List<Discrepancy> discrepancies,
  ) {
    final sheet = excel['Discrepancies'];
    sheet.appendRow([
      TextCellValue('Type'),
      TextCellValue('Severity'),
      TextCellValue('Order ID'),
      TextCellValue('Description'),
      TextCellValue('Expected (₹)'),
      TextCellValue('Actual (₹)'),
      TextCellValue('Variance (₹)'),
      TextCellValue('Rule'),
    ]);

    for (final d in discrepancies) {
      sheet.appendRow([
        TextCellValue(d.typeLabel),
        TextCellValue(d.severity.name),
        TextCellValue(d.orderId ?? ''),
        TextCellValue(d.description),
        DoubleCellValue(d.expectedAmount),
        DoubleCellValue(d.actualAmount),
        DoubleCellValue(d.variance),
        TextCellValue(d.ruleName ?? ''),
      ]);
    }
  }
}
