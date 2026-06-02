// Raw DTOs that mirror the Flipkart Seller API JSON structure.
// These are only used inside FlipkartApiService — the rest of the
// app works with ParsedOrder / ParsedSummary.

class FlipkartApiCharges {
  const FlipkartApiCharges({
    this.commission = 0.0,
    this.shippingCharges = 0.0,
    this.reverseShipping = 0.0,
    this.fixedFee = 0.0,
    this.collectionFee = 0.0,
    this.pickPack = 0.0,
  });

  final double commission;
  final double shippingCharges;
  final double reverseShipping;
  final double fixedFee;
  final double collectionFee;
  final double pickPack;

  factory FlipkartApiCharges.fromJson(Map<String, dynamic> j) =>
      FlipkartApiCharges(
        commission: _d(j['commission']),
        shippingCharges: _d(j['shipping_charges'] ?? j['shipping_charge']),
        reverseShipping: _d(j['reverse_shipping'] ?? j['reverse_shipping_charge']),
        fixedFee: _d(j['fixed_fee']),
        collectionFee: _d(j['collection_fee']),
        pickPack: _d(j['pick_pack'] ?? j['pick_and_pack_fee']),
      );
}

class FlipkartApiTaxes {
  const FlipkartApiTaxes({
    this.totalTax = 0.0,
    this.tcsAmount = 0.0,
    this.tdsAmount = 0.0,
  });

  final double totalTax;
  final double tcsAmount;
  final double tdsAmount;

  factory FlipkartApiTaxes.fromJson(Map<String, dynamic> j) =>
      FlipkartApiTaxes(
        totalTax: _d(j['total_tax']),
        tcsAmount: _d(j['tcs_amount']),
        tdsAmount: _d(j['tds_amount']),
      );
}

class FlipkartApiSettlement {
  const FlipkartApiSettlement({
    this.settlementId,
    this.paymentDate,
    this.paymentAmount = 0.0,
  });

  final String? settlementId;
  final String? paymentDate;
  final double paymentAmount;

  factory FlipkartApiSettlement.fromJson(Map<String, dynamic> j) =>
      FlipkartApiSettlement(
        settlementId: j['settlement_id'] as String?,
        paymentDate: j['payment_date'] as String?,
        paymentAmount: _d(j['payment_amount'] ?? j['settlement_amount']),
      );
}

class FlipkartApiOrder {
  const FlipkartApiOrder({
    required this.orderId,
    this.orderItemId,
    this.orderDate,
    this.sku,
    this.fsn,
    this.productTitle,
    this.category,
    this.quantity = 1,
    this.sellingPrice = 0.0,
    this.orderState,
    this.fulfilmentType,
    this.charges = const FlipkartApiCharges(),
    this.taxes = const FlipkartApiTaxes(),
    this.settlement,
  });

  final String orderId;
  final String? orderItemId;
  final String? orderDate;
  final String? sku;
  final String? fsn;
  final String? productTitle;
  final String? category;
  final int quantity;
  final double sellingPrice;
  final String? orderState;
  final String? fulfilmentType;
  final FlipkartApiCharges charges;
  final FlipkartApiTaxes taxes;
  final FlipkartApiSettlement? settlement;

  factory FlipkartApiOrder.fromJson(Map<String, dynamic> j) {
    final chargesJson =
        (j['charges'] as Map<String, dynamic>?) ?? {};
    final taxesJson =
        (j['taxes'] as Map<String, dynamic>?) ?? {};
    final settlementJson =
        j['settlement'] as Map<String, dynamic>?;
    final itemDetails =
        (j['item_details'] as Map<String, dynamic>?) ?? {};

    return FlipkartApiOrder(
      orderId: (j['order_id'] ?? j['orderId'] ?? '') as String,
      orderItemId: j['order_item_id'] as String?,
      orderDate: j['order_date'] as String?,
      sku: (j['sku'] ?? j['seller_sku_id']) as String?,
      fsn: (j['fsn'] ?? j['product_id']) as String?,
      productTitle: (j['product_title'] ?? j['title']) as String?,
      category: j['category'] as String?,
      quantity: (j['quantity'] as int?) ?? 1,
      sellingPrice: _d(j['selling_price'] ?? itemDetails['selling_price']),
      orderState: (j['order_state'] ?? j['status']) as String?,
      fulfilmentType: (j['fulfilment_type'] ?? j['fulfillment_type']) as String?,
      charges: FlipkartApiCharges.fromJson(chargesJson),
      taxes: FlipkartApiTaxes.fromJson(taxesJson),
      settlement: settlementJson != null
          ? FlipkartApiSettlement.fromJson(settlementJson)
          : null,
    );
  }
}

class FlipkartOrdersPage {
  const FlipkartOrdersPage({
    required this.orders,
    this.hasMore = false,
    this.nextPageToken,
  });

  final List<FlipkartApiOrder> orders;
  final bool hasMore;
  final String? nextPageToken;

  factory FlipkartOrdersPage.fromJson(Map<String, dynamic> j) {
    final raw = (j['orderItems'] ?? j['order_items'] ?? j['orders']) as List?;
    return FlipkartOrdersPage(
      orders: (raw ?? [])
          .map((e) => FlipkartApiOrder.fromJson(e as Map<String, dynamic>))
          .toList(),
      hasMore: j['hasMore'] as bool? ?? false,
      nextPageToken: j['nextPageToken'] as String?,
    );
  }
}

// ── Helpers ───────────────────────────────────────────────────────────────────

double _d(dynamic v) => (v as num?)?.toDouble() ?? 0.0;
