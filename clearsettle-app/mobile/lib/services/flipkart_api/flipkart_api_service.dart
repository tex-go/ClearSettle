import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import 'package:uuid/uuid.dart';

import '../../parsers/parser_result.dart';
import 'flipkart_api_client.dart';
import 'flipkart_api_models.dart';

final flipkartApiServiceProvider = Provider<FlipkartApiService>((ref) {
  return FlipkartApiService(client: ref.read(flipkartApiClientProvider));
});

class FlipkartSyncResult {
  const FlipkartSyncResult({
    required this.parseResult,
    required this.ordersCount,
    required this.dateFrom,
    required this.dateTo,
  });

  final ParseResult parseResult;
  final int ordersCount;
  final DateTime dateFrom;
  final DateTime dateTo;
}

/// Fetches seller data from the Flipkart Seller API and converts it to the
/// internal [ParseResult] format so it can flow through the existing
/// ReconciliationEngine → Hive pipeline unchanged.
class FlipkartApiService {
  const FlipkartApiService({required this.client});

  final FlipkartApiClient client;
  static const _uuid = Uuid();
  static const _parserVersion = 'flipkart_api_1.0';

  static final _dateFmt = DateFormat('yyyy-MM-dd');

  /// Fetches all orders in the given date range (auto-paginates) and
  /// returns a [FlipkartSyncResult] ready to hand off to [ReconciliationEngine].
  Future<FlipkartSyncResult> fetchSellerData({
    required DateTime from,
    required DateTime to,
  }) async {
    final orders = await _fetchAllOrders(from: from, to: to);
    final parseResult = _toParseResult(orders, from, to);
    return FlipkartSyncResult(
      parseResult: parseResult,
      ordersCount: orders.length,
      dateFrom: from,
      dateTo: to,
    );
  }

  // ── Internal ──────────────────────────────────────────────────────────────

  Future<List<FlipkartApiOrder>> _fetchAllOrders({
    required DateTime from,
    required DateTime to,
  }) async {
    final all = <FlipkartApiOrder>[];
    String? pageToken;

    do {
      final params = <String, dynamic>{
        'orderState': 'APPROVED,PACKING_IN_PROGRESS,SHIPPED,DELIVERED,RETURN_REQUESTED,RETURNED',
        'orderDate.from': _dateFmt.format(from),
        'orderDate.to': _dateFmt.format(to),
        'pageSize': '100',
        if (pageToken != null) 'pageToken': pageToken,
      };

      final json = await client.get('/orders/list', queryParameters: params);
      final page = FlipkartOrdersPage.fromJson(json);
      all.addAll(page.orders);
      pageToken = page.hasMore ? page.nextPageToken : null;
    } while (pageToken != null);

    return all;
  }

  ParseResult _toParseResult(
    List<FlipkartApiOrder> apiOrders,
    DateTime from,
    DateTime to,
  ) {
    final parsedOrders = apiOrders.map(_toParsedOrder).toList();
    final summary = ParsedSummary.fromOrders(parsedOrders);

    final label =
        '${_dateFmt.format(from)}_to_${_dateFmt.format(to)}';

    return ParseResult(
      marketplace: 'flipkart',
      parserVersion: _parserVersion,
      fileHash: _uuid.v4(),
      fileName: 'flipkart_api_sync_$label.json',
      parsedAt: DateTime.now(),
      orders: parsedOrders,
      summary: summary,
      errors: [],
      warnings: [],
      sheetsFound: ['api_orders'],
    );
  }

  ParsedOrder _toParsedOrder(FlipkartApiOrder o) {
    final c = o.charges;
    final t = o.taxes;
    final s = o.settlement;

    // GST on fees = totalTax - TCS - TDS (the platform service tax)
    final gstOnFees = (t.totalTax - t.tcsAmount - t.tdsAmount).clamp(0.0, double.infinity);

    return ParsedOrder(
      orderId: o.orderId,
      settlementId: s?.settlementId,
      orderDate: o.orderDate,
      sku: o.sku ?? o.fsn,
      productTitle: o.productTitle,
      category: o.category,
      quantity: o.quantity,
      grossAmount: o.sellingPrice * o.quantity,
      commission: c.commission,
      collectionFee: c.collectionFee,
      shippingFee: c.shippingCharges,
      reverseShippingFee: c.reverseShipping,
      fixedFee: c.fixedFee,
      pickPackFee: c.pickPack,
      gstOnFees: gstOnFees,
      tcs: t.tcsAmount,
      tds: t.tdsAmount,
      netSettlement: s?.paymentAmount ?? 0.0,
      status: o.orderState,
      fulfilmentType: o.fulfilmentType,
      settlementDate: s?.paymentDate,
    );
  }
}
