import 'package:intl/intl.dart';

abstract final class CurrencyFormatter {
  static final NumberFormat _inr = NumberFormat.currency(
    locale: 'en_IN',
    symbol: '₹',
    decimalDigits: 2,
  );

  static final NumberFormat _inrCompact = NumberFormat.compactCurrency(
    locale: 'en_IN',
    symbol: '₹',
    decimalDigits: 1,
  );

  static String format(double amount) => _inr.format(amount);

  static String formatCompact(double amount) => _inrCompact.format(amount);

  static String formatSigned(double amount) {
    final formatted = _inr.format(amount.abs());
    return amount >= 0 ? '+$formatted' : '-$formatted';
  }
}
