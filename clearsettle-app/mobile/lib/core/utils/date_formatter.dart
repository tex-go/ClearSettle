import 'package:intl/intl.dart';

abstract final class DateFormatter {
  static final DateFormat _date = DateFormat('dd MMM yyyy');
  static final DateFormat _dateTime = DateFormat('dd MMM yyyy, hh:mm a');
  static final DateFormat _time = DateFormat('hh:mm a');
  static final DateFormat _relative = DateFormat('dd MMM');
  static final DateFormat _short = DateFormat('d MMM');

  static String formatDate(DateTime date) => _date.format(date);

  /// Day + short month, no year. e.g. "5 Jan"
  static String formatShort(DateTime date) => _short.format(date);

  /// Parse an ISO date string then format short. Returns the raw string on failure.
  static String formatShortString(String? dateStr) {
    if (dateStr == null || dateStr.isEmpty) return '—';
    final dt = DateTime.tryParse(dateStr);
    return dt != null ? _short.format(dt) : dateStr;
  }

  static String formatDateTime(DateTime date) => _dateTime.format(date);

  static String formatTime(DateTime date) => _time.format(date);

  static String formatRelative(DateTime date) {
    final now = DateTime.now();
    final diff = now.difference(date);

    if (diff.inMinutes < 1) return 'just now';
    if (diff.inMinutes < 60) return '${diff.inMinutes}m ago';
    if (diff.inHours < 24) return '${diff.inHours}h ago';
    if (diff.inDays == 1) return 'yesterday';
    if (diff.inDays < 7) return '${diff.inDays}d ago';
    return _relative.format(date);
  }

  static String formatLastSync(DateTime? date) {
    if (date == null) return 'Never synced';
    return 'Last synced ${formatRelative(date)}';
  }
}
