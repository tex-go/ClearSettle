import 'package:intl/intl.dart';

abstract final class DateFormatter {
  static final DateFormat _date = DateFormat('dd MMM yyyy');
  static final DateFormat _dateTime = DateFormat('dd MMM yyyy, hh:mm a');
  static final DateFormat _time = DateFormat('hh:mm a');
  static final DateFormat _relative = DateFormat('dd MMM');

  static String formatDate(DateTime date) => _date.format(date);

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
