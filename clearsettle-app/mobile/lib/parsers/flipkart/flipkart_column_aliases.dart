/// Column alias lists for every canonical Flipkart field.
/// Matching is case-insensitive substring — see FlipkartParser._findColumn().
abstract final class FlipkartColumnAliases {
  // ── Primary identifiers ────────────────────────────────────────────────────

  static const List<String> orderId = [
    'order id', 'order_id', 'order no', 'order no.', 'order number',
    'orderid', 'sub order no', 'sub order id', 'order ref', 'order reference',
  ];

  static const List<String> settlementId = [
    'settlement id', 'settlement_id', 'neft id', 'neft_id', 'neft reference',
    'neft ref', 'remittance id', 'payment id', 'payment ref',
  ];

  static const List<String> orderDate = [
    'order date', 'order_date', 'placed date', 'order placed date',
    'purchase date', 'created date', 'invoice date', 'date',
  ];

  static const List<String> settlementDate = [
    'settlement date', 'payment date', 'remittance date', 'paid date',
    'transferred date', 'payout date',
  ];

  // ── Product info ───────────────────────────────────────────────────────────

  static const List<String> sku = [
    'seller sku', 'seller sku id', 'sku id', 'sku_id', 'sku', 'fsn',
    'product id', 'product_id', 'listing id', 'item id', 'product code',
  ];

  static const List<String> productTitle = [
    'product title', 'title', 'product name', 'product', 'item name',
    'item title', 'description', 'listing title', 'product description',
  ];

  static const List<String> category = [
    'category', 'product category', 'item category', 'cat', 'vertical',
    'product sub category',
  ];

  static const List<String> quantity = [
    'quantity', 'qty', 'units', 'order qty', 'order quantity', 'quantity ordered',
  ];

  static const List<String> orderStatus = [
    'status', 'order status', 'fulfilment status', 'fulfillment status',
    'shipment status', 'item return status', 'return type',
  ];

  static const List<String> fulfilmentType = [
    'fulfilment type', 'fulfillment type', 'fulfillment_type',
    'shipping type', 'dispatch type',
  ];

  // ── Revenue ────────────────────────────────────────────────────────────────

  static const List<String> grossAmount = [
    'gross amount', 'gross order value', 'sale amount (rs.)', 'sale amount',
    'sale_amount', 'gross revenue', 'gross', 'total amount', 'order value',
    'order amount', 'gross sales', 'my share (rs.)', 'my share',
    'total gross sales', 'gross mrp sales',
  ];

  // ── Fees (stored as negatives in some formats, abs-handled in parser) ──────

  static const List<String> commission = [
    'commission (rs.)', 'commission', 'platform commission', 'platform fee',
    'marketplace fee (rs.)', 'marketplace fee', 'referral fee',
    'commission amount', 'flipkart commission', 'selling fee',
    'seller commission',
  ];

  static const List<String> collectionFee = [
    'collection fee (rs.)', 'collection fee', 'collection charges',
    'payment collection fee', 'payment gateway fee',
  ];

  static const List<String> shippingFee = [
    'shipping fee (rs.)', 'shipping fee', 'shipping charges', 'shipping',
    'forward shipping', 'logistics charges', 'logistics fee',
    'delivery charges', 'forward logistics', 'shipping cost',
    'forward shipping charges',
  ];

  static const List<String> reverseShippingFee = [
    'reverse shipping fee (rs.)', 'reverse shipping fee', 'reverse shipping',
    'return shipping', 'reverse logistics', 'return freight',
    'reverse shipping charges', 'return logistics charges',
  ];

  static const List<String> fixedFee = [
    'fixed fee  (rs.)', 'fixed fee (rs.)', 'fixed fee', 'tech fee',
    'category fee',
  ];

  static const List<String> pickPackFee = [
    'pick and pack fee (rs.)', 'pick and pack fee', 'pick & pack fee',
    'pick & pack',
  ];

  static const List<String> nosCostEmiFee = [
    'no cost emi fee reimbursement(rs.)', 'no cost emi fee reimbursement',
    'no cost emi fee', 'no cost emi',
  ];

  // ── Taxes ──────────────────────────────────────────────────────────────────

  static const List<String> gstOnFees = [
    'gst on mp fees (rs.)', 'gst on mp fees', 'gst on fees',
    'gst on marketplace fees', 'gst', 'igst', 'gst charges',
    'tax on services', 'service tax', 'taxes (rs.)', 'taxes',
  ];

  static const List<String> tcs = [
    'tcs (rs.)', 'tcs', 'tax collected at source', 'tcs deduction', 'tcs amount',
  ];

  static const List<String> tds = [
    'tds (rs.)', 'tds', 'tax deducted at source', 'tds deduction', 'tds amount',
    'income tax credits',
  ];

  // ── Net settlement ─────────────────────────────────────────────────────────

  static const List<String> netSettlement = [
    'net earnings', 'net payout', 'net payment', 'total payout', 'net proceeds',
    'total earnings', 'seller earnings', 'payout amount', 'net amount', 'net',
    'earnings', 'bank settlement value', 'bank settlement (rs.)',
  ];

  static const List<String> commissionRate = [
    'commission rate (%)', 'commission rate', 'commission_rate',
  ];

  // ── Summary sheet row-label aliases ───────────────────────────────────────

  static const List<String> summaryGrossSales = [
    'gross sales', 'gross revenue', 'total sales', 'total revenue',
    'gross mrp sales', 'total gross sales', 'total gmv',
  ];

  static const List<String> summaryNetSales = [
    'net sales', 'net revenue', 'net amount', 'effective sales',
    'adjusted revenue', 'total net sales', 'net gmv',
  ];

  static const List<String> summaryCommission = [
    'platform commission', 'commission', 'marketplace fee', 'selling fee',
    'referral fee', 'total commission', 'flipkart commission',
  ];

  static const List<String> summaryShipping = [
    'shipping charges', 'shipping fee', 'forward shipping charges',
    'logistics charges', 'total shipping', 'logistics fees', 'forward shipping',
  ];

  static const List<String> summaryReverseShipping = [
    'reverse shipping', 'return shipping', 'reverse logistics charges',
    'reverse shipping charges', 'return logistics',
  ];

  static const List<String> summaryCollectionFees = [
    'collection fees', 'collection fee', 'payment collection fee', 'collection charges',
  ];

  static const List<String> summaryFixedFees = [
    'fixed fees', 'fixed fee', 'category fee', 'tech fee', 'platform fee',
  ];

  static const List<String> summaryGstOnFees = [
    'gst on fees', 'gst on services', 'gst', 'service tax', 'tax on services',
    'igst on fees', 'gst charges',
  ];

  static const List<String> summaryTcs = [
    'tcs', 'tax collected at source', 'tcs deduction', 'tcs amount',
  ];

  static const List<String> summaryTds = [
    'tds', 'tax deducted at source', 'tds deduction', 'tds amount',
  ];

  static const List<String> summaryNetEarnings = [
    'net earnings', 'net payout', 'net payment', 'total payout',
    'net proceeds', 'total earnings', 'seller earnings',
  ];

  static const List<String> summaryAmountSettled = [
    'amount settled', 'amount received', 'settlement received',
    'total settled', 'total received', 'settled amount', 'total remittance',
  ];

  static const List<String> summaryAmountPending = [
    'amount pending', 'pending settlement', 'unsettled amount',
    'pending payout', 'outstanding amount', 'total pending',
  ];

  static const List<String> summaryTotalOrders = [
    'total orders', 'orders', 'no. of orders', 'total order count',
    'number of orders', 'total shipped orders',
  ];

  static const List<String> summaryReturns = [
    'total returns', 'returns', 'return value', 'return deduction',
    'return amount', 'total return value', 'returns amount',
  ];

  static const List<String> summaryCancellations = [
    'total cancellations', 'cancellations', 'cancellation deduction',
    'cancellation value', 'cancelled amount', 'cancellation amount',
  ];

  // ── Validation sets ────────────────────────────────────────────────────────

  static const Set<String> knownFeeTypes = {
    'fixed fee', 'commission', 'reverse shipping fee', 'shipping fee',
    'collection fee', 'sdd fee', 'pick and pack fee', 'tech visit fee',
    'installation fee', 'product cancellation fee', 'shopsy marketing fee',
    'franchise fee', 'no cost emi fee reimbursement',
    'customer add-ons amount recovery',
  };

  static const Set<String> suspectFeeTypes = {
    'wallet redeem',
  };
}
