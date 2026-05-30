import '../../domain/entities/dashboard_summary_entity.dart';

class DashboardSummaryModel {
  const DashboardSummaryModel({
    required this.sellerName,
    required this.organization,
    required this.totalReports,
    required this.totalOrders,
    required this.netSettlement,
    required this.connectedMarketplaces,
    this.lastSync,
  });

  final String sellerName;
  final String organization;
  final int totalReports;
  final int totalOrders;
  final double netSettlement;
  final List<String> connectedMarketplaces;
  final String? lastSync;

  factory DashboardSummaryModel.fromJson(Map<String, dynamic> json) {
    return DashboardSummaryModel(
      sellerName: (json['seller_name'] as String?) ?? '',
      organization: (json['organization'] as String?) ??
          (json['company_name'] as String?) ??
          '',
      totalReports: (json['total_reports'] as int?) ?? 0,
      totalOrders: (json['total_orders'] as int?) ?? 0,
      netSettlement: ((json['net_settlement'] as num?) ?? 0).toDouble(),
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
        'connected_marketplaces': connectedMarketplaces,
        'last_sync': lastSync,
      };

  DashboardSummary toEntity({bool isFromCache = false}) {
    return DashboardSummary(
      sellerName: sellerName,
      organization: organization,
      totalReports: totalReports,
      totalOrders: totalOrders,
      netSettlement: netSettlement,
      connectedMarketplaces: connectedMarketplaces,
      lastSync: lastSync != null ? DateTime.tryParse(lastSync!) : null,
      isFromCache: isFromCache,
    );
  }

  factory DashboardSummaryModel.fromEntity(DashboardSummary entity) {
    return DashboardSummaryModel(
      sellerName: entity.sellerName,
      organization: entity.organization,
      totalReports: entity.totalReports,
      totalOrders: entity.totalOrders,
      netSettlement: entity.netSettlement,
      connectedMarketplaces: entity.connectedMarketplaces,
      lastSync: entity.lastSync?.toIso8601String(),
    );
  }
}
