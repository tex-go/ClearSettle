import 'dart:developer' as dev;

import 'package:flutter/foundation.dart';

/// Structured logger for ClearSettle mobile.
///
/// Debug builds: full [INFO]/[WARNING]/[ERROR] output via developer.log + debugPrint.
/// Release builds: only [ERROR] and [WARNING] (no PII in prod logs).
abstract final class CsLogger {
  static const _tag = 'ClearSettle';

  static void info(String stage, String message, {Map<String, dynamic>? data}) {
    if (!kDebugMode) return;
    final line = _format('INFO', stage, message, data);
    dev.log(line, name: _tag, level: 800);
  }

  static void warning(String stage, String message, {Map<String, dynamic>? data}) {
    final line = _format('WARNING', stage, message, data);
    if (kDebugMode) {
      dev.log(line, name: _tag, level: 900);
    } else {
      debugPrint(line);
    }
  }

  static void error(String stage, String message, {Object? error, StackTrace? stack}) {
    final line = _format('ERROR', stage, message, error != null ? {'error': '$error'} : null);
    dev.log(line, name: _tag, level: 1000, error: error, stackTrace: stack);
    debugPrint(line);
  }

  static String _format(String level, String stage, String message, Map<String, dynamic>? data) {
    final buf = StringBuffer()
      ..write('[$level] $stage | $message');
    if (data != null && data.isNotEmpty) {
      buf.write(' | ');
      buf.write(data.entries.map((e) => '${e.key}=${e.value}').join(' '));
    }
    return buf.toString();
  }
}
