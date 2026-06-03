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

  static bool _isIgnored(String name) {
    // Exact/prefix known-ignore terms
    if (const ['help', 'read me', 'readme', 'guide', 'instruction', 'about', 'index']
        .any(name.contains)) return true;

    // Flipkart non-order adjustment sheets — must be checked BEFORE _isOrders
    // because their names contain the substring "order" and would otherwise
    // be misclassified as order-level sheets.
    if (const [
      'non_order_spf', 'non_order', 'non-order',  // Non-Order SPF adjustments
      'spf_non',                                    // alternative naming
      'neft_summary', 'neft summary',               // payment-level, not order-level
      'ads', 'advertisement', 'campaign',            // ad-spend sheets
      'tcs_recovery', 'tds_recovery',               // tax recovery sheets
      'pickup_charge', 'pickup charge',              // logistics sheets
    ].any(name.contains)) return true;

    return false;
  }

  static bool _isSummary(String name, List<String> headers) {
    if (const ['overall summary', 'p&l summary', 'summary', 'overall']
        .any(name.contains)) return true;
    // Key-value layout: ≤3 meaningful columns, no order_id header
    return headers.length <= 3 &&
        !headers.any((h) => h.contains('order id')) &&
        headers.any((h) => h.contains('amount') || h.contains('value'));
  }

  static bool _isOrders(String name, List<String> headers) {
    // Use exact-match for standalone keywords to avoid false positives like
    // "non_order_spf" matching "order". Multi-word phrases use contains() safely.
    const exactOrders = ['order', 'orders', 'payment', 'ledger', 'transaction', 'transactions'];
    const phraseOrders = ['order p&l', 'order details', 'orders p&l', 'order level', 'order_level'];

    for (final kw in exactOrders) {
      if (name == kw || name.startsWith('${kw}_') || name.startsWith('$kw ') ||
          name.endsWith('_$kw') || name.endsWith(' $kw')) {
        return true;
      }
    }
    if (phraseOrders.any(name.contains)) return true;
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
