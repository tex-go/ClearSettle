import 'dart:typed_data';

import 'package:pdf/pdf.dart';
import 'package:pdf/widgets.dart' as pw;

import '../../core/utils/currency_formatter.dart';
import '../../parsers/parser_result.dart';
import '../../reconciliation/reconciliation_result.dart';

abstract final class PdfGenerator {
  static Future<Uint8List> generateReport({
    required String reportName,
    required ParsedSummary summary,
    required List<ParsedOrder> orders,
    required List<Discrepancy> discrepancies,
    required DateTime generatedAt,
  }) async {
    final doc = pw.Document(
      theme: pw.ThemeData.withFont(
        base: pw.Font.helvetica(),
        bold: pw.Font.helveticaBold(),
      ),
    );

    doc.addPage(
      pw.MultiPage(
        pageFormat: PdfPageFormat.a4,
        margin: const pw.EdgeInsets.all(32),
        header: (ctx) => _header(reportName, generatedAt),
        footer: (ctx) => _footer(ctx),
        build: (ctx) => [
          _summarySection(summary),
          pw.SizedBox(height: 20),
          if (discrepancies.isNotEmpty) ...[
            _discrepanciesSection(discrepancies),
            pw.SizedBox(height: 20),
          ],
          _ordersSection(orders),
        ],
      ),
    );

    return doc.save();
  }

  static pw.Widget _header(String reportName, DateTime date) {
    return pw.Container(
      padding: const pw.EdgeInsets.only(bottom: 12),
      decoration: const pw.BoxDecoration(
        border: pw.Border(
          bottom: pw.BorderSide(color: PdfColors.blueGrey300),
        ),
      ),
      child: pw.Row(
        mainAxisAlignment: pw.MainAxisAlignment.spaceBetween,
        children: [
          pw.Text(
            'ClearSettle',
            style: pw.TextStyle(
              fontSize: 18,
              fontWeight: pw.FontWeight.bold,
              color: PdfColor.fromHex('1A3A5C'),
            ),
          ),
          pw.Column(
            crossAxisAlignment: pw.CrossAxisAlignment.end,
            children: [
              pw.Text(
                reportName,
                style: const pw.TextStyle(
                    fontSize: 9, color: PdfColors.blueGrey700),
              ),
              pw.Text(
                'Generated: ${_fmtDate(date)}',
                style: const pw.TextStyle(
                    fontSize: 8, color: PdfColors.blueGrey400),
              ),
            ],
          ),
        ],
      ),
    );
  }

  static pw.Widget _footer(pw.Context ctx) {
    return pw.Row(
      mainAxisAlignment: pw.MainAxisAlignment.spaceBetween,
      children: [
        pw.Text(
          'ClearSettle — Confidential',
          style: const pw.TextStyle(fontSize: 8, color: PdfColors.blueGrey400),
        ),
        pw.Text(
          'Page ${ctx.pageNumber} of ${ctx.pagesCount}',
          style: const pw.TextStyle(fontSize: 8, color: PdfColors.blueGrey400),
        ),
      ],
    );
  }

  static pw.Widget _summarySection(ParsedSummary summary) {
    return pw.Column(
      crossAxisAlignment: pw.CrossAxisAlignment.start,
      children: [
        _sectionTitle('Financial Summary'),
        pw.SizedBox(height: 8),
        pw.Table(
          border: pw.TableBorder.all(color: PdfColors.blueGrey200, width: 0.5),
          children: [
            _tableHeader(['Metric', 'Amount (₹)']),
            _tableRow('Gross Sales', CurrencyFormatter.format(summary.grossSales)),
            _tableRow('Returns', '- ${CurrencyFormatter.format(summary.returnsValue)}'),
            _tableRow('Net Sales', CurrencyFormatter.format(summary.netSales),
                bold: true),
            _tableRow('Commission',
                '- ${CurrencyFormatter.format(summary.totalCommission)}'),
            _tableRow('Shipping',
                '- ${CurrencyFormatter.format(summary.totalShipping)}'),
            _tableRow('Reverse Shipping',
                '- ${CurrencyFormatter.format(summary.totalReverseShipping)}'),
            _tableRow('GST on Fees',
                '- ${CurrencyFormatter.format(summary.totalGstOnFees)}'),
            _tableRow('TCS', '- ${CurrencyFormatter.format(summary.totalTcs)}'),
            _tableRow('TDS', '- ${CurrencyFormatter.format(summary.totalTds)}'),
            _tableRow('Net Settlement',
                CurrencyFormatter.format(summary.netEarnings),
                bold: true, highlight: true),
          ],
        ),
        pw.SizedBox(height: 8),
        pw.Text(
          'Total Orders: ${summary.totalOrders}',
          style: const pw.TextStyle(fontSize: 9, color: PdfColors.blueGrey700),
        ),
      ],
    );
  }

  static pw.Widget _discrepanciesSection(List<Discrepancy> discrepancies) {
    return pw.Column(
      crossAxisAlignment: pw.CrossAxisAlignment.start,
      children: [
        _sectionTitle('Discrepancies (${discrepancies.length})'),
        pw.SizedBox(height: 8),
        pw.Table(
          border: pw.TableBorder.all(color: PdfColors.blueGrey200, width: 0.5),
          columnWidths: {
            0: const pw.FlexColumnWidth(2),
            1: const pw.FlexColumnWidth(1),
            2: const pw.FlexColumnWidth(2),
            3: const pw.FlexColumnWidth(3),
            4: const pw.FlexColumnWidth(1.5),
          },
          children: [
            _tableHeader(['Type', 'Severity', 'Order ID', 'Description', 'Variance']),
            ...discrepancies.take(50).map(
                  (d) => _tableRow5(
                    d.typeLabel,
                    d.severity.name.toUpperCase(),
                    d.orderId ?? '—',
                    d.description.length > 80
                        ? '${d.description.substring(0, 77)}...'
                        : d.description,
                    CurrencyFormatter.format(d.variance),
                  ),
                ),
          ],
        ),
        if (discrepancies.length > 50)
          pw.Padding(
            padding: const pw.EdgeInsets.only(top: 4),
            child: pw.Text(
              '... and ${discrepancies.length - 50} more. Export Excel for full list.',
              style: const pw.TextStyle(fontSize: 8, color: PdfColors.blueGrey400),
            ),
          ),
      ],
    );
  }

  static pw.Widget _ordersSection(List<ParsedOrder> orders) {
    if (orders.isEmpty) return pw.SizedBox.shrink();
    return pw.Column(
      crossAxisAlignment: pw.CrossAxisAlignment.start,
      children: [
        _sectionTitle('Settlement Rows (${orders.length} orders)'),
        pw.SizedBox(height: 8),
        pw.Table(
          border: pw.TableBorder.all(color: PdfColors.blueGrey200, width: 0.5),
          columnWidths: {
            0: const pw.FlexColumnWidth(2.5),
            1: const pw.FlexColumnWidth(2),
            2: const pw.FlexColumnWidth(1.5),
            3: const pw.FlexColumnWidth(1.5),
            4: const pw.FlexColumnWidth(1.5),
          },
          children: [
            _tableHeader(['Order ID', 'Product', 'Gross', 'Fees', 'Net']),
            ...orders.take(100).map(
                  (o) => _tableRow5(
                    o.orderId ?? '—',
                    (o.productTitle ?? '—').length > 20
                        ? '${(o.productTitle!).substring(0, 17)}...'
                        : (o.productTitle ?? '—'),
                    CurrencyFormatter.format(o.grossAmount),
                    CurrencyFormatter.format(o.totalFees),
                    CurrencyFormatter.format(o.netSettlement),
                  ),
                ),
          ],
        ),
        if (orders.length > 100)
          pw.Padding(
            padding: const pw.EdgeInsets.only(top: 4),
            child: pw.Text(
              '... and ${orders.length - 100} more rows. Export Excel/CSV for full data.',
              style: const pw.TextStyle(fontSize: 8, color: PdfColors.blueGrey400),
            ),
          ),
      ],
    );
  }

  // ── Table helpers ──────────────────────────────────────────────────────────

  static pw.TableRow _tableHeader(List<String> cols) {
    return pw.TableRow(
      decoration: const pw.BoxDecoration(color: PdfColor.fromInt(0xFF1A3A5C)),
      children: cols
          .map(
            (c) => pw.Padding(
              padding: const pw.EdgeInsets.all(4),
              child: pw.Text(
                c,
                style: pw.TextStyle(
                  color: PdfColors.white,
                  fontSize: 8,
                  fontWeight: pw.FontWeight.bold,
                ),
              ),
            ),
          )
          .toList(),
    );
  }

  static pw.TableRow _tableRow(
    String label,
    String value, {
    bool bold = false,
    bool highlight = false,
  }) {
    final bg = highlight
        ? const PdfColor.fromInt(0xFFE8F5E9)
        : PdfColors.white;
    return pw.TableRow(
      decoration: pw.BoxDecoration(color: bg),
      children: [label, value].map((cell) {
        return pw.Padding(
          padding: const pw.EdgeInsets.all(4),
          child: pw.Text(
            cell,
            style: pw.TextStyle(
              fontSize: 8,
              fontWeight: bold ? pw.FontWeight.bold : pw.FontWeight.normal,
            ),
          ),
        );
      }).toList(),
    );
  }

  static pw.TableRow _tableRow5(
    String c1,
    String c2,
    String c3,
    String c4,
    String c5,
  ) {
    return pw.TableRow(
      children: [c1, c2, c3, c4, c5]
          .map(
            (cell) => pw.Padding(
              padding: const pw.EdgeInsets.all(3),
              child: pw.Text(cell, style: const pw.TextStyle(fontSize: 7)),
            ),
          )
          .toList(),
    );
  }

  static pw.Widget _sectionTitle(String title) {
    return pw.Text(
      title,
      style: pw.TextStyle(
        fontSize: 12,
        fontWeight: pw.FontWeight.bold,
        color: PdfColor.fromHex('1A3A5C'),
      ),
    );
  }

  static String _fmtDate(DateTime d) =>
      '${d.day.toString().padLeft(2, '0')}/${d.month.toString().padLeft(2, '0')}/${d.year}';
}
