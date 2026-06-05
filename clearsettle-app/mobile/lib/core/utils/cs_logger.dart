import 'dart:developer' as dev;

import 'package:firebase_crashlytics/firebase_crashlytics.dart';
import 'package:flutter/foundation.dart';

/// Structured logger for ClearSettle — outputs to:
///   1. VS Code Debug Console  (dart:developer)
///   2. ADB logcat             (debugPrint)
///   3. Firebase Crashlytics   (errors + non-fatal warnings in production)
///
/// HOW TO SEE LOGS:
///   USB connected  : adb logcat -s flutter ClearSettle
///   VS Code        : F5 → View → Output → "Flutter"
///   GCP / Firebase : Firebase Console → Crashlytics → Non-fatals
///
/// LOG LEVELS:
///   section()  — pipeline boundary marker (e.g. "Upload started")
///   info()     — every step of upload/parse/poll flow  (debug builds)
///   warning()  — non-fatal issues  (all builds + Crashlytics)
///   error()    — failures with stack trace (all builds + Crashlytics crash log)
abstract final class CsLogger {
  static const _tag = 'ClearSettle';
  static bool _crashlyticsAvailable = false;

  /// Call once at startup after Firebase.initializeApp().
  static void init() {
    try {
      if (!kDebugMode) {
        FirebaseCrashlytics.instance.setCrashlyticsCollectionEnabled(true);
      }
      _crashlyticsAvailable = true;
    } catch (_) {
      _crashlyticsAvailable = false;
    }
  }

  // ── Public API ──────────────────────────────────────────────────────────────

  static void section(String title) {
    const sep = '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━';
    _print('$sep\n>> $title\n$sep');
    dev.log('>> $title', name: _tag, level: 800);
    _crashlyticsLog('SECTION: $title');
  }

  static void info(String stage, String message, {Map<String, dynamic>? data}) {
    if (!kDebugMode) return;
    final line = _format('INFO ', stage, message, data);
    dev.log(line, name: _tag, level: 800);
    _print(line);
  }

  static void warning(String stage, String message, {Map<String, dynamic>? data}) {
    final line = _format('WARN ', stage, message, data);
    dev.log(line, name: _tag, level: 900);
    _print(line);
    _crashlyticsLog('WARN [$stage] $message ${_dataStr(data)}');
  }

  static void error(
    String stage,
    String message, {
    Object? error,
    StackTrace? stack,
    Map<String, dynamic>? data,
  }) {
    final merged = <String, dynamic>{
      if (data != null) ...data,
      if (error != null) 'error': '$error',
    };
    final line = _format('ERROR', stage, message, merged.isEmpty ? null : merged);
    dev.log(line, name: _tag, level: 1000, error: error, stackTrace: stack);
    _print(line);
    if (stack != null && kDebugMode) {
      _print('STACK:\n$stack');
    }
    // Send to Crashlytics as non-fatal
    if (_crashlyticsAvailable) {
      try {
        FirebaseCrashlytics.instance.recordError(
          error ?? Exception('[$stage] $message'),
          stack,
          reason: '[$stage] $message',
          information: merged.entries.map((e) => '${e.key}=${e.value}').toList(),
          fatal: false,
        );
      } catch (_) {}
    }
  }

  /// Log a key-value breadcrumb (shown in Crashlytics before a crash).
  static void breadcrumb(String key, String value) {
    if (_crashlyticsAvailable) {
      try {
        FirebaseCrashlytics.instance.setCustomKey(key, value);
      } catch (_) {}
    }
    if (kDebugMode) {
      _print('[CRUMB] $key = $value');
    }
  }

  // ── Upload flow specific helpers ────────────────────────────────────────────

  /// Log the start of a file upload with all relevant metadata.
  static void uploadStarted({
    required String fileName,
    required int fileSizeBytes,
    required String marketplace,
  }) {
    section('UPLOAD STARTED: $fileName');
    info('Upload', 'File selected', data: {
      'file_name':    fileName,
      'file_size_kb': (fileSizeBytes / 1024).toStringAsFixed(1),
      'marketplace':  marketplace,
    });
    breadcrumb('last_upload_file', fileName);
    breadcrumb('last_upload_size_kb', (fileSizeBytes / 1024).toStringAsFixed(1));
  }

  static void uploadSent({required String fileName, required int bytes}) {
    info('Upload', 'Sending to backend API', data: {
      'file_name': fileName,
      'bytes':     bytes,
      'endpoint':  '/ingestion/upload',
    });
  }

  static void uploadAccepted({
    required String fileId,
    required String status,
    required bool isDuplicate,
    required String? platform,
    required double? confidence,
  }) {
    info('Upload', 'Backend accepted file', data: {
      'file_id':    fileId,
      'status':     status,
      'duplicate':  isDuplicate,
      'platform':   platform ?? 'unknown',
      'confidence': confidence?.toStringAsFixed(4) ?? 'n/a',
    });
    if (confidence != null && confidence < 0.5) {
      warning('Upload', 'LOW platform confidence — may use generic parser', data: {
        'file_id':    fileId,
        'platform':   platform ?? 'unknown',
        'confidence': confidence.toStringAsFixed(4),
        'fix':        'Upload with platform_hint=flipkart',
      });
    }
    breadcrumb('last_file_id', fileId);
    breadcrumb('last_platform', platform ?? 'unknown');
  }

  static void pollTick({
    required String fileId,
    required String status,
    required int elapsedSeconds,
  }) {
    info('Poll', 'Status check', data: {
      'file_id':         fileId,
      'status':          status,
      'elapsed_seconds': elapsedSeconds,
    });
  }

  static void pollDone({
    required String fileId,
    required String status,
    required int totalSeconds,
  }) {
    info('Poll', 'Processing complete', data: {
      'file_id':       fileId,
      'final_status':  status,
      'total_seconds': totalSeconds,
    });
    if (status == 'needs_review') {
      warning('Poll', 'Status is needs_review — platform detection was low confidence', data: {
        'file_id': fileId,
        'impact':  'Data may still be available via /summary',
      });
    }
  }

  static void summaryReceived({
    required String fileId,
    required int totalRecords,
    required int uniqueOrders,
    required double grossRevenue,
    required double payoutTotal,
  }) {
    final hasData = grossRevenue > 0 || uniqueOrders > 0;
    if (hasData) {
      info('Summary', 'Financial data received', data: {
        'file_id':       fileId,
        'total_records': totalRecords,
        'unique_orders': uniqueOrders,
        'gross_revenue': grossRevenue.toStringAsFixed(2),
        'payout_total':  payoutTotal.toStringAsFixed(2),
      });
    } else {
      warning('Summary', 'ALL VALUES ARE ZERO — data pipeline issue', data: {
        'file_id':       fileId,
        'total_records': totalRecords,
        'unique_orders': uniqueOrders,
        'gross_revenue': grossRevenue,
        'payout_total':  payoutTotal,
        'debug_hint':    'Check /ingestion/files/$fileId/ledger for raw rows',
        'common_cause':  'transaction_type mismatch or parser used generic fallback',
      });
    }
  }

  static void hiveUpdated({
    required String reportId,
    required String status,
    required int totalOrders,
    required double grossRevenue,
    required double netSettlement,
  }) {
    info('Hive', 'Local cache updated', data: {
      'report_id':     reportId,
      'status':        status,
      'total_orders':  totalOrders,
      'gross_revenue': grossRevenue.toStringAsFixed(2),
      'net_settlement': netSettlement.toStringAsFixed(2),
      'WARNING':       totalOrders == 0 && grossRevenue == 0
                         ? 'ZERO DATA STORED — dashboard will show 0'
                         : 'ok',
    });
  }

  // ── Internal helpers ────────────────────────────────────────────────────────

  static void _print(String line) => debugPrint('[$_tag] $line');

  static void _crashlyticsLog(String msg) {
    if (_crashlyticsAvailable) {
      try {
        FirebaseCrashlytics.instance.log(msg);
      } catch (_) {}
    }
  }

  static String _dataStr(Map<String, dynamic>? data) =>
      data == null || data.isEmpty
          ? ''
          : data.entries.map((e) => '${e.key}=${e.value}').join(' ');

  static String _format(
    String level,
    String stage,
    String message,
    Map<String, dynamic>? data,
  ) {
    final ts  = DateTime.now().toIso8601String().substring(11, 23);
    final buf = StringBuffer()..write('[$level] $ts  $stage  $message');
    if (data != null && data.isNotEmpty) {
      buf.write('  ');
      buf.write(data.entries.map((e) => '${e.key}=${e.value}').join('  '));
    }
    return buf.toString();
  }
}
