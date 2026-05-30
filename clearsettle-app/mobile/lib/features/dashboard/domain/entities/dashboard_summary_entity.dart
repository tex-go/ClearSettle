class DashboardSummary {
  const DashboardSummary({
    required this.sellerName,
    required this.organization,
    required this.totalReports,
    required this.totalOrders,
    required this.netSettlement,
    required this.connectedMarketplaces,
    this.lastSync,
    this.isFromCache = false,
  });

  final String sellerName;
  final String organization;
  final int totalReports;
  final int totalOrders;
  final double netSettlement;
  final List<String> connectedMarketplaces;
  final DateTime? lastSync;
  final bool isFromCache;

  DashboardSummary copyWith({
    String? sellerName,
    String? organization,
    int? totalReports,
    int? totalOrders,
    double? netSettlement,
    List<String>? connectedMarketplaces,
    DateTime? lastSync,
    bool? isFromCache,
  }) {
    return DashboardSummary(
      sellerName: sellerName ?? this.sellerName,
      organization: organization ?? this.organization,
      totalReports: totalReports ?? this.totalReports,
      totalOrders: totalOrders ?? this.totalOrders,
      netSettlement: netSettlement ?? this.netSettlement,
      connectedMarketplaces: connectedMarketplaces ?? this.connectedMarketplaces,
      lastSync: lastSync ?? this.lastSync,
      isFromCache: isFromCache ?? this.isFromCache,
    );
  }
}
