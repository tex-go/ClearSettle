import 'dart:developer' as dev;

import 'package:flutter/foundation.dart';

/// Structured logger — output visible in VS Code Debug Console.
///
/// HOW TO SEE LOGS IN VS CODE:
///   1. Press F5  →  select "📱 ClearSettle — Android Phone (10.83.8.137)"
///   2. View → Output → select "Flutter" from the dropdown  ← logs here
///      OR  View → Debug Console                            ← also here
///
/// LOG LEVELS:
///   [INFO]    — every upload/parse/poll step  (debug builds only)
///   [WARN]    — non-fatal issues (both builds)
///   [ERROR]   — failures with stack trace (both builds)
abstract final class CsLogger {
  static const _tag = 'ClearSettle';

  static void info(String stage, String message, {Map<String, dynamic>? data}) {
    if (!kDebugMode) return;
    final line = _format('INFO ', stage, message, data);
    dev.log(line, name: _tag, level: 800);
    debugPrint('[$_tag] $line');
  }

  static void warning(String stage, String message, {Map<String, dynamic>? data}) {
    final line = _format('WARN ', stage, message, data);
    dev.log(line, name: _tag, level: 900);
    debugPrint('[$_tag] $line');
  }

  static void error(
    String stage,
    String message, {
    Object? error,
    StackTrace? stack,
  }) {
    final line = _format('ERROR', stage, message,
        error != null ? {'error': '$error'} : null);
    dev.log(line, name: _tag, level: 1000, error: error, stackTrace: stack);
    debugPrint('[$_tag] $line');
    if (stack != null && kDebugMode) {
      debugPrint('[$_tag] STACK\n$stack');
    }
  }

  /// Prints a divider line — marks the start of a new upload in the log stream.
  static void section(String title) {
    if (!kDebugMode) return;
    const sep = '────────────────────────────────────────────────────';
    debugPrint('[$_tag] $sep');
    debugPrint('[$_tag] >> $title');
    debugPrint('[$_tag] $sep');
    dev.log('>> $title', name: _tag, level: 800);
  }

  static String _format(
    String level,
    String stage,
    String message,
    Map<String, dynamic>? data,
  ) {
    // HH:mm:ss.mmm — compact but enough to correlate with backend logs
    final ts = DateTime.now().toIso8601String().substring(11, 23);
    final buf = StringBuffer()
      ..write('[$level] $ts  $stage  $message');
    if (data != null && data.isNotEmpty) {
      buf.write('  ');
      buf.write(data.entries.map((e) => '${e.key}=${e.value}').join('  '));
    }
    return buf.toString();
  }
}
