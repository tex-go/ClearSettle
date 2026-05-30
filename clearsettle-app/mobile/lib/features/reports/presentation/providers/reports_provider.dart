import 'dart:typed_data';

import 'package:file_picker/file_picker.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../reconciliation/reconciliation_engine.dart';
import '../../../../services/file_storage/file_storage_service.dart';
import '../../data/datasources/report_local_datasource.dart';
import '../../data/repositories/report_repository_impl.dart';
import '../../domain/entities/report_entities.dart';
import '../../domain/repositories/report_repository.dart';
import '../../domain/usecases/delete_report_usecase.dart';
import '../../domain/usecases/get_reports_usecase.dart';
import '../../domain/usecases/parse_report_usecase.dart';
import '../../domain/usecases/upload_report_usecase.dart';

// — DI —

final _reconciliationEngineProvider = Provider<ReconciliationEngine>(
  (_) => ReconciliationEngine(),
);

final _reportLocalDataSourceProvider = Provider<ReportLocalDataSource>((ref) {
  return ReportLocalDataSource(
    fileStorage: ref.read(fileStorageServiceProvider),
    reconciliationEngine: ref.read(_reconciliationEngineProvider),
  );
});

final reportRepositoryProvider = Provider<ReportRepository>((ref) {
  return ReportRepositoryImpl(
    localDataSource: ref.read(_reportLocalDataSourceProvider),
  );
});

// — Notifier —

class ReportsState {
  const ReportsState({
    this.reports = const [],
    this.isUploading = false,
    this.uploadingFileName,
    this.parsingReportId,
    this.errorMessage,
  });

  final List<ReportListItem> reports;
  final bool isUploading;
  final String? uploadingFileName;
  final String? parsingReportId;
  final String? errorMessage;

  bool get isBusy => isUploading || parsingReportId != null;

  ReportsState copyWith({
    List<ReportListItem>? reports,
    bool? isUploading,
    String? uploadingFileName,
    String? parsingReportId,
    String? errorMessage,
    bool clearParsingId = false,
    bool clearError = false,
    bool clearUploadingName = false,
  }) {
    return ReportsState(
      reports: reports ?? this.reports,
      isUploading: isUploading ?? this.isUploading,
      uploadingFileName:
          clearUploadingName ? null : (uploadingFileName ?? this.uploadingFileName),
      parsingReportId:
          clearParsingId ? null : (parsingReportId ?? this.parsingReportId),
      errorMessage: clearError ? null : (errorMessage ?? this.errorMessage),
    );
  }
}

class ReportsNotifier extends Notifier<ReportsState> {
  late final GetReportsUseCase _getReports;
  late final UploadReportUseCase _upload;
  late final ParseReportUseCase _parse;
  late final DeleteReportUseCase _delete;

  @override
  ReportsState build() {
    final repo = ref.read(reportRepositoryProvider);
    _getReports = GetReportsUseCase(repo);
    _upload = UploadReportUseCase(repo);
    _parse = ParseReportUseCase(repo);
    _delete = DeleteReportUseCase(repo);

    return ReportsState(reports: _getReports());
  }

  Future<bool> pickAndUpload({
    String marketplace = 'flipkart',
    String reportType = 'payment_ledger',
  }) async {
    state = state.copyWith(isUploading: true, clearError: true);

    try {
      final result = await FilePicker.platform.pickFiles(
        type: FileType.custom,
        allowedExtensions: ['xlsx', 'xls'],
        withData: true,
      );

      if (result == null || result.files.isEmpty) {
        state = state.copyWith(isUploading: false, clearUploadingName: true);
        return false;
      }

      final file = result.files.first;
      final bytes = file.bytes;
      if (bytes == null) {
        state = state.copyWith(
          isUploading: false,
          errorMessage: 'Could not read file bytes.',
        );
        return false;
      }

      state = state.copyWith(uploadingFileName: file.name);

      final reportId = await _upload(
        marketplace: marketplace,
        reportType: reportType,
        fileName: file.name,
        bytes: Uint8List.fromList(bytes),
      );

      // Refresh list
      state = state.copyWith(
        reports: _getReports(),
        isUploading: false,
        parsingReportId: reportId,
        clearUploadingName: true,
      );

      // Parse immediately
      await _parseReport(reportId);
      return true;
    } catch (e) {
      state = state.copyWith(
        isUploading: false,
        errorMessage: 'Upload failed: $e',
        clearUploadingName: true,
      );
      return false;
    }
  }

  Future<ReportDetail?> _parseReport(String reportId) async {
    state = state.copyWith(parsingReportId: reportId);
    try {
      final detail = await _parse(reportId);
      state = state.copyWith(
        reports: _getReports(),
        clearParsingId: true,
      );
      return detail;
    } catch (e) {
      state = state.copyWith(
        reports: _getReports(),
        clearParsingId: true,
        errorMessage: 'Parse failed: $e',
      );
      return null;
    }
  }

  Future<void> retryParse(String reportId) async {
    await _parseReport(reportId);
  }

  Future<void> deleteReport(String reportId) async {
    await _delete(reportId);
    state = state.copyWith(reports: _getReports());
  }

  void refresh() {
    state = state.copyWith(reports: _getReports(), clearError: true);
  }

  void clearError() {
    state = state.copyWith(clearError: true);
  }
}

final reportsProvider = NotifierProvider<ReportsNotifier, ReportsState>(
  ReportsNotifier.new,
);
