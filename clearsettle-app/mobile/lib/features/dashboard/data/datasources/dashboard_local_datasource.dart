import 'dart:convert';

import '../../../../core/constants/app_constants.dart';
import '../../../../storage/hive_manager.dart';
import '../../domain/entities/dashboard_summary_entity.dart';
import '../models/dashboard_summary_model.dart';

class DashboardLocalDataSource {
  static const String _cacheKey = 'dashboard_summary';

  Future<void> cacheSummary(DashboardSummary summary) async {
    final model = DashboardSummaryModel.fromEntity(summary);
    final box = HiveManager.settingsBox;
    await box.put(_cacheKey, _encode(model.toJson()));
  }

  Future<DashboardSummary?> getCachedSummary() {
    final box = HiveManager.settingsBox;
    final raw = box.get(_cacheKey);
    if (raw == null) return Future.value();

    try {
      final json = _decode(raw.toString());
      return Future.value(
        DashboardSummaryModel.fromJson(json).toEntity(isFromCache: true),
      );
    } catch (_) {
      return Future.value();
    }
  }

  /// Builds a summary directly from locally-parsed Hive reports.
  /// Used as offline-first fallback when there is no remote connection and no cache.
  Future<DashboardSummary?> buildFromHiveReports() async {
    final reports = HiveManager.localReportBox.values
        .where((r) => r.status == 'parsed')
        .toList();

    if (reports.isEmpty) return null;

    final summaries = HiveManager.reportSummaryBox.values.toList();
    final summaryByReport = {for (final s in summaries) s.reportId: s};

    double grossRevenue = 0;
    double totalFees = 0;
    double netSettlement = 0;
    int totalOrders = 0;
    final marketplaces = <String>{};

    for (final r in reports) {
      final s = summaryByReport[r.id];
      if (s != null) {
        grossRevenue += s.grossRevenue;
        totalFees += s.totalFees;
        netSettlement += s.netSettlement;
        totalOrders += s.totalOrders;
      } else {
        // Fallback to report-level fields if no summary row
        grossRevenue += r.grossRevenue;
        totalFees += r.totalFees;
        netSettlement += r.netSettlement;
        totalOrders += r.totalOrders;
      }
      marketplaces.add(r.platform);
    }

    // Resolve seller name from userBox
    final userObj = HiveManager.userBox.get(AppConstants.currentUserKey);
    final sellerName = userObj?.sellerName ?? 'Seller';
    final organization = userObj?.organization ?? 'My Store';

    return DashboardSummary(
      sellerName: sellerName,
      organization: organization,
      totalReports: reports.length,
      totalOrders: totalOrders,
      netSettlement: netSettlement,
      grossRevenue: grossRevenue,
      totalFees: totalFees,
      connectedMarketplaces: marketplaces.toList(),
      lastSync: null,
      isFromCache: true,
    );
  }

  String _encode(Map<String, dynamic> json) => jsonEncode(json);

  Map<String, dynamic> _decode(String raw) =>
      jsonDecode(raw) as Map<String, dynamic>;
}
