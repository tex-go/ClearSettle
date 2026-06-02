import 'dart:io';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:path_provider/path_provider.dart';
import 'package:printing/printing.dart';
import 'package:share_plus/share_plus.dart';

import '../../parsers/parser_result.dart';
import '../../reconciliation/reconciliation_result.dart';
import 'csv_exporter.dart';
import 'excel_exporter.dart';
import 'pdf_generator.dart';

final exportServiceProvider = Provider<ExportService>((_) => ExportService());

enum ExportFormat { pdf, excel, csv }

class ExportService {
  // ── PDF ────────────────────────────────────────────────────────────────────

  Future<void> exportPdf({
    required String reportName,
    required ParsedSummary summary,
    required List<ParsedOrder> orders,
    required List<Discrepancy> discrepancies,
  }) async {
    final bytes = await PdfGenerator.generateReport(
      reportName: reportName,
      summary: summary,
      orders: orders,
      discrepancies: discrepancies,
      generatedAt: DateTime.now(),
    );
    // Uses native PDF share/print UI — no temp file cleanup needed
    await Printing.sharePdf(
      bytes: bytes,
      filename: '${_sanitize(reportName)}.pdf',
    );
  }

  // ── Excel ──────────────────────────────────────────────────────────────────

  Future<void> exportExcel({
    required String reportName,
    required ParsedSummary summary,
    required List<ParsedOrder> orders,
    required List<Discrepancy> discrepancies,
  }) async {
    final bytes = ExcelExporter.exportReport(
      reportName: reportName,
      summary: summary,
      orders: orders,
      discrepancies: discrepancies,
    );
    final file = await _writeTempFile(
      bytes: bytes,
      filename: '${_sanitize(reportName)}.xlsx',
    );
    await _share(file, 'ClearSettle Export — $reportName');
    await _cleanupAfterDelay(file);
  }

  // ── CSV ────────────────────────────────────────────────────────────────────

  Future<void> exportOrdersCsv({
    required String reportName,
    required List<ParsedOrder> orders,
  }) async {
    final csv = CsvExporter.exportOrders(orders);
    final file = await _writeTempFile(
      bytes: csv.codeUnits,
      filename: '${_sanitize(reportName)}_orders.csv',
    );
    await _share(file, 'ClearSettle Orders CSV — $reportName');
    await _cleanupAfterDelay(file);
  }

  Future<void> exportDiscrepanciesCsv({
    required String reportName,
    required List<Discrepancy> discrepancies,
  }) async {
    final csv = CsvExporter.exportDiscrepancies(discrepancies);
    final file = await _writeTempFile(
      bytes: csv.codeUnits,
      filename: '${_sanitize(reportName)}_discrepancies.csv',
    );
    await _share(file, 'ClearSettle Discrepancies CSV — $reportName');
    await _cleanupAfterDelay(file);
  }

  // ── Helpers ────────────────────────────────────────────────────────────────

  Future<File> _writeTempFile({
    required List<int> bytes,
    required String filename,
  }) async {
    final tmp = await getTemporaryDirectory();
    final file = File('${tmp.path}/$filename');
    await file.writeAsBytes(bytes, flush: true);
    return file;
  }

  Future<void> _share(File file, String subject) async {
    await Share.shareXFiles(
      [XFile(file.path)],
      subject: subject,
    );
  }

  Future<void> _cleanupAfterDelay(File file) async {
    await Future.delayed(const Duration(seconds: 30));
    if (file.existsSync()) await file.delete();
  }

  String _sanitize(String name) =>
      name.replaceAll(RegExp(r'[^\w\-_.]'), '_').replaceAll('__', '_');
}
