import '../../domain/entities/dashboard_summary_entity.dart';

/// Maps the backend /dashboard/summary response.
///
/// Backend payload structure (from audit):
/// {
///   "settlements": { total_gross, total_fees, total_net_paid, total_orders,
///                    total, open_count, closed_count, pending_amount },
///   "payouts":     { transferred, pending, failed },
///   "reconciliation": { clean, warning, critical, unresolved_discrepancies, total_variance },
///   "revenue_trend":  [{"date": "YYYY-MM-DD", "gross": float, "net": float}],
///   "platform_share": [{"platform": str, "share": float}]
/// }
class DashboardSummaryModel {
  const DashboardSummaryModel({
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
  });

  final String sellerName;
  final String organization;
  final int totalReports;
  final int totalOrders;
  final double netSettlement;
  final double grossRevenue;
  final double totalFees;
  final double payoutsTransferred;
  final double payoutsPending;
  final int reconUnresolved;
  final double totalVariance;
  final List<String> connectedMarketplaces;
  final String? lastSync;

  factory DashboardSummaryModel.fromJson(Map<String, dynamic> json) {
    // Support both old (flat) format from Hive cache and new nested backend format
    if (json.containsKey('settlements') && json['settlements'] is Map) {
      return _fromBackend(json);
    }
    return _fromCache(json);
  }

  /// Maps nested backend response
  static DashboardSummaryModel _fromBackend(Map<String, dynamic> json) {
    final s = json['settlements'] as Map<String, dynamic>? ?? {};
    final p = json['payouts']     as Map<String, dynamic>? ?? {};
    final r = json['reconciliation'] as Map<String, dynamic>? ?? {};

    // Extract platform names from platform_share list
    final shares = json['platform_share'] as List? ?? [];
    final platforms = shares
        .cast<Map<String, dynamic>>()
        .map((e) => _normalisePlatform(e['platform']?.toString() ?? ''))
        .where((name) => name.isNotEmpty)
        .toList();

    return DashboardSummaryModel(
      sellerName:         '',          // filled by auth state in provider
      organization:       '',          // filled by auth state in provider
      totalReports:       _i(s['total']),
      totalOrders:        _i(s['total_orders']),
      grossRevenue:       _d(s['total_gross']),
      totalFees:          _d(s['total_fees']),
      netSettlement:      _d(s['total_net_paid']),
      payoutsTransferred: _d(p['transferred']),
      payoutsPending:     _d(p['pending']),
      reconUnresolved:    _i(r['unresolved_discrepancies']),
      totalVariance:      _d(r['total_variance']),
      connectedMarketplaces: platforms,
      lastSync: DateTime.now().toIso8601String(),
    );
  }

  /// Maps old flat cache format
  static DashboardSummaryModel _fromCache(Map<String, dynamic> json) {
    return DashboardSummaryModel(
      sellerName:    (json['seller_name'] as String?) ?? '',
      organization:  (json['organization'] as String?) ??
                     (json['company_name'] as String?) ?? '',
      totalReports:  _i(json['total_reports']),
      totalOrders:   _i(json['total_orders']),
      netSettlement: _d(json['net_settlement']),
      grossRevenue:  _d(json['gross_revenue']),
      totalFees:     _d(json['total_fees']),
      connectedMarketplaces:
          List<String>.from(json['connected_marketplaces'] as List? ?? []),
      lastSync: json['last_sync'] as String?,
    );
  }

  Map<String, dynamic> toJson() => {
        'seller_name': sellerName,
        'organization': organization,
        'total_reports': totalReports,
        'total_orders': totalOrders,
        'net_settlement': netSettlement,
        'gross_revenue': grossRevenue,
        'total_fees': totalFees,
        'payouts_transferred': payoutsTransferred,
        'payouts_pending': payoutsPending,
        'recon_unresolved': reconUnresolved,
        'connected_marketplaces': connectedMarketplaces,
        'last_sync': lastSync,
      };

  DashboardSummary toEntity({
    bool isFromCache = false,
    String? sellerNameOverride,
    String? organizationOverride,
  }) {
    return DashboardSummary(
      sellerName:   sellerNameOverride ?? sellerName,
      organization: organizationOverride ?? organization,
      totalReports: totalReports,
      totalOrders:  totalOrders,
      netSettlement: netSettlement,
      grossRevenue:  grossRevenue,
      totalFees:     totalFees,
      payoutsTransferred: payoutsTransferred,
      payoutsPending: payoutsPending,
      reconUnresolved: reconUnresolved,
      totalVariance: totalVariance,
      connectedMarketplaces: connectedMarketplaces,
      lastSync: lastSync != null ? DateTime.tryParse(lastSync!) : null,
      isFromCache: isFromCache,
    );
  }

  factory DashboardSummaryModel.fromEntity(DashboardSummary e) {
    return DashboardSummaryModel(
      sellerName:    e.sellerName,
      organization:  e.organization,
      totalReports:  e.totalReports,
      totalOrders:   e.totalOrders,
      netSettlement: e.netSettlement,
      grossRevenue:  e.grossRevenue,
      totalFees:     e.totalFees,
      payoutsTransferred: e.payoutsTransferred,
      payoutsPending: e.payoutsPending,
      reconUnresolved: e.reconUnresolved,
      totalVariance: e.totalVariance,
      connectedMarketplaces: e.connectedMarketplaces,
      lastSync: e.lastSync?.toIso8601String(),
    );
  }

  // ── Helpers ──────────────────────────────────────────────────────────────

  static double _d(dynamic v) => (v as num?)?.toDouble() ?? 0.0;
  static int    _i(dynamic v) => (v as num?)?.toInt() ?? 0;

  static String _normalisePlatform(String p) => switch (p.toLowerCase()) {
        'flipkart' => 'Flipkart',
        'amazon'   => 'Amazon',
        'meesho'   => 'Meesho',
        'shopify'  => 'Shopify',
        'myntra'   => 'Myntra',
        _          => p.isNotEmpty
            ? '${p[0].toUpperCase()}${p.substring(1)}'
            : '',
      };
}
