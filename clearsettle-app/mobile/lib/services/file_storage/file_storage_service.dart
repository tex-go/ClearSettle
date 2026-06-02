import 'dart:io';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:path_provider/path_provider.dart';

final fileStorageServiceProvider = Provider<FileStorageService>(
  (_) => FileStorageService(),
);

/// Manages report files at:
///   <documents>/ClearSettle/reports/<marketplace>/<filename>
///
/// Also stores sidecar JSON files for parsed data:
///   <documents>/ClearSettle/reports/<marketplace>/<uuid>_parsed.json
class FileStorageService {
  static const String _rootDir = 'ClearSettle';
  static const String _reportsDir = 'reports';

  Future<Directory> _marketplaceDir(String marketplace) async {
    final docs = await getApplicationDocumentsDirectory();
    final dir = Directory(
      '${docs.path}/$_rootDir/$_reportsDir/${marketplace.toLowerCase()}',
    );
    if (!dir.existsSync()) await dir.create(recursive: true);
    return dir;
  }

  /// Saves [bytes] under [marketplace]/[fileName] and returns the full path.
  Future<String> saveReport({
    required String marketplace,
    required String fileName,
    required List<int> bytes,
  }) async {
    final dir = await _marketplaceDir(marketplace);
    final file = File('${dir.path}/$fileName');
    await file.writeAsBytes(bytes, flush: true);
    return file.path;
  }

  /// Reads report bytes from [filePath]. Returns null if file missing.
  Future<List<int>?> readReport(String filePath) async {
    final file = File(filePath);
    if (!file.existsSync()) return null;
    return file.readAsBytes();
  }

  /// Saves parsed JSON sidecar alongside the original report.
  Future<void> saveParsedJson({
    required String marketplace,
    required String reportId,
    required String json,
  }) async {
    final dir = await _marketplaceDir(marketplace);
    final file = File('${dir.path}/${reportId}_parsed.json');
    await file.writeAsString(json, flush: true);
  }

  /// Reads parsed JSON sidecar. Returns null if not found.
  Future<String?> readParsedJson({
    required String marketplace,
    required String reportId,
  }) async {
    final dir = await _marketplaceDir(marketplace);
    final file = File('${dir.path}/${reportId}_parsed.json');
    if (!file.existsSync()) return null;
    return file.readAsString();
  }

  /// Deletes report file and its sidecar JSON.
  Future<void> deleteReport({
    required String marketplace,
    required String reportId,
    required String filePath,
  }) async {
    final reportFile = File(filePath);
    if (reportFile.existsSync()) await reportFile.delete();

    final dir = await _marketplaceDir(marketplace);
    final sidecar = File('${dir.path}/${reportId}_parsed.json');
    if (sidecar.existsSync()) await sidecar.delete();
  }

  /// Returns the size of a file in bytes, or 0 if not found.
  int fileSize(String filePath) {
    final file = File(filePath);
    return file.existsSync() ? file.lengthSync() : 0;
  }

  /// Lists all report files for a marketplace.
  Future<List<FileSystemEntity>> listReports(String marketplace) async {
    final dir = await _marketplaceDir(marketplace);
    return dir
        .listSync()
        .where((f) =>
            f.path.endsWith('.xlsx') ||
            f.path.endsWith('.xls') ||
            f.path.endsWith('.csv'))
        .toList();
  }
}
