enum SheetType { summary, orders, sku, ignore, unknown }

abstract final class FlipkartSheetDetector {
  static SheetType detect(String sheetName, List<String> headers) {
    final name = sheetName.toLowerCase().trim();

    if (_isIgnored(name)) return SheetType.ignore;
    if (_isSummary(name, headers)) return SheetType.summary;
    if (_isOrders(name, headers)) return SheetType.orders;
    if (_isSku(name, headers)) return SheetType.sku;
    return _inferFromHeaders(headers);
  }

  static bool _isIgnored(String name) => const [
        'help', 'read me', 'readme', 'guide', 'instruction', 'about', 'index',
      ].any(name.contains);

  static bool _isSummary(String name, List<String> headers) {
    if (const ['overall summary', 'p&l summary', 'summary', 'overall']
        .any(name.contains)) return true;
    // Key-value layout: ≤3 meaningful columns, no order_id header
    return headers.length <= 3 &&
        !headers.any((h) => h.contains('order id')) &&
        headers.any((h) => h.contains('amount') || h.contains('value'));
  }

  static bool _isOrders(String name, List<String> headers) {
    if (const [
      'order',
      'transaction',
      'order p&l',
      'order details',
      'orders p&l',
      'payment',
      'ledger',
    ].any(name.contains)) return true;
    return headers.any((h) => h.contains('order id'));
  }

  static bool _isSku(String name, List<String> headers) {
    if (const ['sku', 'product summary', 'product p&l', 'listing', 'item-level']
        .any(name.contains)) return true;
    return headers.any((h) => h == 'sku' || h == 'sku id' || h == 'fsn');
  }

  static SheetType _inferFromHeaders(List<String> headers) {
    if (headers.any((h) => h.contains('order id'))) return SheetType.orders;
    if (headers.any((h) => h.contains('sku'))) return SheetType.sku;
    return SheetType.unknown;
  }
}
