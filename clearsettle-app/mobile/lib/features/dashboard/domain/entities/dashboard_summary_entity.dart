class DashboardSummary {
  const DashboardSummary({
    required this.sellerName,
    required this.organization,
    required this.totalReports,
    required this.totalOrders,
    required this.netSettlement,
    required this.connectedMarketplaces,
    this.grossRevenue = 0.0,
    this.totalFees = 0.0,
    this.payoutsTransferred = 0.0,
    this.payoutsPending = 0.0,
    this.reconUnresolved = 0,
    this.totalVariance = 0.0,
    this.lastSync,
    this.isFromCache = false,
  });

  final String sellerName;
  final String organization;
  final int totalReports;
  final int totalOrders;
  final double netSettlement;
  final double grossRevenue;
  final double totalFees;
  final double payoutsTransferred; // payouts.transferred from backend
  final double payoutsPending;     // payouts.pending from backend
  final int reconUnresolved;       // reconciliation.unresolved_discrepancies
  final double totalVariance;      // reconciliation.total_variance
  final List<String> connectedMarketplaces;
  final DateTime? lastSync;
  final bool isFromCache;

  DashboardSummary copyWith({
    String? sellerName,
    String? organization,
    int? totalReports,
    int? totalOrders,
    double? netSettlement,
    double? grossRevenue,
    double? totalFees,
    double? payoutsTransferred,
    double? payoutsPending,
    int? reconUnresolved,
    double? totalVariance,
    List<String>? connectedMarketplaces,
    DateTime? lastSync,
    bool? isFromCache,
  }) {
    return DashboardSummary(
      sellerName:           sellerName   ?? this.sellerName,
      organization:         organization ?? this.organization,
      totalReports:         totalReports ?? this.totalReports,
      totalOrders:          totalOrders  ?? this.totalOrders,
      netSettlement:        netSettlement ?? this.netSettlement,
      grossRevenue:         grossRevenue  ?? this.grossRevenue,
      totalFees:            totalFees     ?? this.totalFees,
      payoutsTransferred:   payoutsTransferred ?? this.payoutsTransferred,
      payoutsPending:       payoutsPending     ?? this.payoutsPending,
      reconUnresolved:      reconUnresolved    ?? this.reconUnresolved,
      totalVariance:        totalVariance      ?? this.totalVariance,
      connectedMarketplaces: connectedMarketplaces ?? this.connectedMarketplaces,
      lastSync:    lastSync    ?? this.lastSync,
      isFromCache: isFromCache ?? this.isFromCache,
    );
  }
}
