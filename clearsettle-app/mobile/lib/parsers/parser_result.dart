/// Severity levels for parse errors and warnings
enum ParseSeverity { critical, high, medium, low, info }

class ParseError {
  const ParseError({
    required this.code,
    required this.message,
    this.severity = ParseSeverity.high,
    this.rowIndex,
    this.columnName,
  });

  final String code;
  final String message;
  final ParseSeverity severity;
  final int? rowIndex;
  final String? columnName;

  @override
  String toString() => '[$severity] $code: $message';
}

class ParseWarning {
  const ParseWarning({
    required this.code,
    required this.message,
    this.rowIndex,
    this.columnName,
  });

  final String code;
  final String message;
  final int? rowIndex;
  final String? columnName;
}

/// Normalized order row extracted from any marketplace report
class ParsedOrder {
  const ParsedOrder({
    this.orderId,
    this.settlementId,
    this.orderDate,
    this.sku,
    this.productTitle,
    this.category,
    this.quantity = 1,
    this.grossAmount = 0.0,
    this.commission = 0.0,
    this.collectionFee = 0.0,
    this.shippingFee = 0.0,
    this.reverseShippingFee = 0.0,
    this.fixedFee = 0.0,
    this.pickPackFee = 0.0,
    this.gstOnFees = 0.0,
    this.tcs = 0.0,
    this.tds = 0.0,
    this.netSettlement = 0.0,
    this.status,
    this.fulfilmentType,
    this.settlementDate,
    this.rawCommissionRate,
  });

  final String? orderId;
  final String? settlementId;
  final String? orderDate;       // ISO-8601 date string
  final String? sku;
  final String? productTitle;
  final String? category;
  final int quantity;
  final double grossAmount;
  final double commission;
  final double collectionFee;
  final double shippingFee;
  final double reverseShippingFee;
  final double fixedFee;
  final double pickPackFee;
  final double gstOnFees;
  final double tcs;
  final double tds;
  final double netSettlement;
  final String? status;
  final String? fulfilmentType;
  final String? settlementDate;
  final double? rawCommissionRate;   // % if available in report

  double get totalFees =>
      commission.abs() +
      collectionFee.abs() +
      shippingFee.abs() +
      reverseShippingFee.abs() +
      fixedFee.abs() +
      pickPackFee.abs() +
      gstOnFees.abs() +
      tcs.abs() +
      tds.abs();

  double get expectedNet => grossAmount - totalFees;

  double get settlementVariance => (expectedNet - netSettlement).abs();

  Map<String, dynamic> toJson() => {
        'order_id': orderId,
        'settlement_id': settlementId,
        'order_date': orderDate,
        'sku': sku,
        'product_title': productTitle,
        'category': category,
        'quantity': quantity,
        'gross_amount': grossAmount,
        'commission': commission,
        'collection_fee': collectionFee,
        'shipping_fee': shippingFee,
        'reverse_shipping_fee': reverseShippingFee,
        'fixed_fee': fixedFee,
        'pick_pack_fee': pickPackFee,
        'gst_on_fees': gstOnFees,
        'tcs': tcs,
        'tds': tds,
        'net_settlement': netSettlement,
        'status': status,
        'fulfilment_type': fulfilmentType,
        'settlement_date': settlementDate,
        'raw_commission_rate': rawCommissionRate,
      };

  factory ParsedOrder.fromJson(Map<String, dynamic> j) => ParsedOrder(
        orderId: j['order_id'] as String?,
        settlementId: j['settlement_id'] as String?,
        orderDate: j['order_date'] as String?,
        sku: j['sku'] as String?,
        productTitle: j['product_title'] as String?,
        category: j['category'] as String?,
        quantity: (j['quantity'] as int?) ?? 1,
        grossAmount: (j['gross_amount'] as num?)?.toDouble() ?? 0.0,
        commission: (j['commission'] as num?)?.toDouble() ?? 0.0,
        collectionFee: (j['collection_fee'] as num?)?.toDouble() ?? 0.0,
        shippingFee: (j['shipping_fee'] as num?)?.toDouble() ?? 0.0,
        reverseShippingFee: (j['reverse_shipping_fee'] as num?)?.toDouble() ?? 0.0,
        fixedFee: (j['fixed_fee'] as num?)?.toDouble() ?? 0.0,
        pickPackFee: (j['pick_pack_fee'] as num?)?.toDouble() ?? 0.0,
        gstOnFees: (j['gst_on_fees'] as num?)?.toDouble() ?? 0.0,
        tcs: (j['tcs'] as num?)?.toDouble() ?? 0.0,
        tds: (j['tds'] as num?)?.toDouble() ?? 0.0,
        netSettlement: (j['net_settlement'] as num?)?.toDouble() ?? 0.0,
        status: j['status'] as String?,
        fulfilmentType: j['fulfilment_type'] as String?,
        settlementDate: j['settlement_date'] as String?,
        rawCommissionRate: (j['raw_commission_rate'] as num?)?.toDouble(),
      );
}

/// Aggregated financial summary for a report
class ParsedSummary {
  const ParsedSummary({
    this.grossSales = 0.0,
    this.returnsValue = 0.0,
    this.cancellationsValue = 0.0,
    this.netSales = 0.0,
    this.totalCommission = 0.0,
    this.totalShipping = 0.0,
    this.totalReverseShipping = 0.0,
    this.totalCollectionFees = 0.0,
    this.totalFixedFees = 0.0,
    this.totalGstOnFees = 0.0,
    this.totalTcs = 0.0,
    this.totalTds = 0.0,
    this.netEarnings = 0.0,
    this.amountSettled = 0.0,
    this.amountPending = 0.0,
    this.totalOrders = 0,
    this.totalReturned = 0,
    this.totalCancelled = 0,
  });

  final double grossSales;
  final double returnsValue;
  final double cancellationsValue;
  final double netSales;
  final double totalCommission;
  final double totalShipping;
  final double totalReverseShipping;
  final double totalCollectionFees;
  final double totalFixedFees;
  final double totalGstOnFees;
  final double totalTcs;
  final double totalTds;
  final double netEarnings;
  final double amountSettled;
  final double amountPending;
  final int totalOrders;
  final int totalReturned;
  final int totalCancelled;

  double get totalFees =>
      totalCommission.abs() +
      totalShipping.abs() +
      totalReverseShipping.abs() +
      totalCollectionFees.abs() +
      totalFixedFees.abs() +
      totalGstOnFees.abs() +
      totalTcs.abs() +
      totalTds.abs();

  Map<String, dynamic> toJson() => {
        'gross_sales': grossSales,
        'returns_value': returnsValue,
        'cancellations_value': cancellationsValue,
        'net_sales': netSales,
        'total_commission': totalCommission,
        'total_shipping': totalShipping,
        'total_reverse_shipping': totalReverseShipping,
        'total_collection_fees': totalCollectionFees,
        'total_fixed_fees': totalFixedFees,
        'total_gst_on_fees': totalGstOnFees,
        'total_tcs': totalTcs,
        'total_tds': totalTds,
        'net_earnings': netEarnings,
        'amount_settled': amountSettled,
        'amount_pending': amountPending,
        'total_orders': totalOrders,
        'total_returned': totalReturned,
        'total_cancelled': totalCancelled,
      };

  factory ParsedSummary.fromJson(Map<String, dynamic> j) => ParsedSummary(
        grossSales: (j['gross_sales'] as num?)?.toDouble() ?? 0.0,
        returnsValue: (j['returns_value'] as num?)?.toDouble() ?? 0.0,
        cancellationsValue: (j['cancellations_value'] as num?)?.toDouble() ?? 0.0,
        netSales: (j['net_sales'] as num?)?.toDouble() ?? 0.0,
        totalCommission: (j['total_commission'] as num?)?.toDouble() ?? 0.0,
        totalShipping: (j['total_shipping'] as num?)?.toDouble() ?? 0.0,
        totalReverseShipping: (j['total_reverse_shipping'] as num?)?.toDouble() ?? 0.0,
        totalCollectionFees: (j['total_collection_fees'] as num?)?.toDouble() ?? 0.0,
        totalFixedFees: (j['total_fixed_fees'] as num?)?.toDouble() ?? 0.0,
        totalGstOnFees: (j['total_gst_on_fees'] as num?)?.toDouble() ?? 0.0,
        totalTcs: (j['total_tcs'] as num?)?.toDouble() ?? 0.0,
        totalTds: (j['total_tds'] as num?)?.toDouble() ?? 0.0,
        netEarnings: (j['net_earnings'] as num?)?.toDouble() ?? 0.0,
        amountSettled: (j['amount_settled'] as num?)?.toDouble() ?? 0.0,
        amountPending: (j['amount_pending'] as num?)?.toDouble() ?? 0.0,
        totalOrders: (j['total_orders'] as int?) ?? 0,
        totalReturned: (j['total_returned'] as int?) ?? 0,
        totalCancelled: (j['total_cancelled'] as int?) ?? 0,
      );

  /// Build summary by aggregating parsed orders when no summary sheet found
  factory ParsedSummary.fromOrders(List<ParsedOrder> orders) {
    double grossSales = 0;
    double commission = 0;
    double shipping = 0;
    double reverseShipping = 0;
    double collectionFees = 0;
    double fixedFees = 0;
    double gstOnFees = 0;
    double tcs = 0;
    double tds = 0;
    double netEarnings = 0;

    for (final o in orders) {
      grossSales += o.grossAmount;
      commission += o.commission.abs();
      shipping += o.shippingFee.abs();
      reverseShipping += o.reverseShippingFee.abs();
      collectionFees += o.collectionFee.abs();
      fixedFees += o.fixedFee.abs();
      gstOnFees += o.gstOnFees.abs();
      tcs += o.tcs.abs();
      tds += o.tds.abs();
      netEarnings += o.netSettlement;
    }

    return ParsedSummary(
      grossSales: grossSales,
      netSales: grossSales,
      totalCommission: commission,
      totalShipping: shipping,
      totalReverseShipping: reverseShipping,
      totalCollectionFees: collectionFees,
      totalFixedFees: fixedFees,
      totalGstOnFees: gstOnFees,
      totalTcs: tcs,
      totalTds: tds,
      netEarnings: netEarnings,
      totalOrders: orders.length,
    );
  }
}

/// Complete result of parsing a marketplace report file
class ParseResult {
  const ParseResult({
    required this.marketplace,
    required this.parserVersion,
    required this.fileHash,
    required this.fileName,
    required this.parsedAt,
    required this.orders,
    required this.errors,
    required this.warnings,
    this.summary,
    this.sheetsFound = const [],
  });

  final String marketplace;
  final String parserVersion;
  final String fileHash;
  final String fileName;
  final DateTime parsedAt;
  final List<ParsedOrder> orders;
  final ParsedSummary? summary;
  final List<ParseError> errors;
  final List<ParseWarning> warnings;
  final List<String> sheetsFound;

  bool get hasErrors => errors.any(
        (e) =>
            e.severity == ParseSeverity.critical ||
            e.severity == ParseSeverity.high,
      );

  bool get hasCriticalErrors =>
      errors.any((e) => e.severity == ParseSeverity.critical);

  ParsedSummary get effectiveSummary =>
      summary ?? ParsedSummary.fromOrders(orders);

  int get totalRows => orders.length;
}
