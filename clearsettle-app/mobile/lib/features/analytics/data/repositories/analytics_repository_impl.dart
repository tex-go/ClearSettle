import '../../domain/entities/analytics_entity.dart';
import '../../domain/repositories/analytics_repository.dart';
import '../../../../storage/hive_manager.dart';
import '../../../../storage/entities/report_summary_hive_object.dart';
import '../../../../storage/entities/local_report_hive_object.dart';

class AnalyticsRepositoryImpl implements AnalyticsRepository {
  @override
  Future<AnalyticsSummary> getSummary(AnalyticsFilter filter) async {
    final reports = _filteredReports(filter);
    final summaries = _filteredSummaries(filter, reports);

    if (reports.isEmpty) return AnalyticsSummary.empty;

    // ── Top-line aggregation ────────────────────────────────────────────────
    double totalGross = 0;
    double totalNet = 0;
    double totalFees = 0;
    int totalOrders = 0;
    int totalDiscrepancies = 0;

    double totalCommission = 0;
    double totalShipping = 0;
    double totalGst = 0;
    double totalTds = 0;
    double totalTcs = 0;

    final byPeriod = <String, _PeriodBucket>{};

    for (final s in summaries) {
      totalGross += s.grossRevenue;
      totalNet += s.netSettlement;
      totalFees += s.totalFees;
      totalOrders += s.totalOrders;
      totalDiscrepancies += s.discrepancyCount;
      totalCommission += s.totalCommission;
      totalShipping    += s.totalShipping;
      totalGst         += s.totalGstOnFees;
      totalTcs         += s.totalTcs;
      totalTds         += s.totalTds;

      final date = DateTime.tryParse(s.reconciledAt);
      if (date != null) {
        final key = _periodKey(date, filter.dateRange);
        final bucket = byPeriod[key] ??= _PeriodBucket(key);
        bucket.grossRevenue += s.grossRevenue;
        bucket.netSettlement += s.netSettlement;
        bucket.totalFees += s.totalFees;
        bucket.orders += s.totalOrders;
      }
    }

    // We don't have fixedFee/collectionFee/reverseShipping in the summary hive
    // object — estimate as remainders split from totalFees.
    // (Phase 4: add those columns to ReportSummaryHiveObject)

    // ── Chart series ────────────────────────────────────────────────────────
    final sorted = byPeriod.entries.toList()
      ..sort((a, b) => a.key.compareTo(b.key));

    final revenueTrend = _trendFrom(sorted, (b) => b.grossRevenue);
    final settlementTrend = _trendFrom(sorted, (b) => b.netSettlement);
    final orderGrowth = _trendFrom(sorted, (b) => b.orders.toDouble());

    // ── Fee breakdown slices ────────────────────────────────────────────────
    final feeBreakdown = _buildFeeBreakdown(
      totalCommission,
      totalShipping,
      totalGst,
      totalTcs,
      totalTds,
    );

    // ── Monthly comparison (always by calendar month, independent of filter) ─
    final monthlyComparison = _buildMonthlyComparison(summaries);

    // ── FeeDetail ──────────────────────────────────────────────────────────
    final feeDetail = FeeDetail(
      commission: totalCommission,
      gstOnFees: totalGst,
      tcs: totalTcs,
      tds: totalTds,
      shippingFee: totalShipping,
    );

    // ── Insights ───────────────────────────────────────────────────────────
    final insights = _buildInsights(
      byPeriod,
      totalCommission,
      totalGross,
      totalFees,
    );

    return AnalyticsSummary(
      totalGrossRevenue: totalGross,
      totalNetSettlement: totalNet,
      totalOrders: totalOrders,
      totalReports: reports.length,
      totalDiscrepancies: totalDiscrepancies,
      totalFees: totalFees,
      revenueTrend: revenueTrend,
      settlementTrend: settlementTrend,
      orderGrowth: orderGrowth,
      feeBreakdown: feeBreakdown,
      feeDetail: feeDetail,
      monthlyComparison: monthlyComparison,
      insights: insights,
      chargePercentage:
          totalGross > 0 ? (totalFees / totalGross) * 100 : 0,
      avgOrderValue: totalOrders > 0 ? totalGross / totalOrders : 0,
      avgSettlementRate:
          totalGross > 0 ? (totalNet / totalGross) * 100 : 0,
    );
  }

  // ── Filtering ──────────────────────────────────────────────────────────────

  List<LocalReportHiveObject> _filteredReports(AnalyticsFilter filter) {
    return HiveManager.localReportBox.values.where((r) {
      if (r.status != 'parsed') return false;
      final date = DateTime.tryParse(r.uploadedAt);
      if (date == null) return false;
      if (date.isBefore(filter.startDate) || date.isAfter(filter.endDate)) {
        return false;
      }
      if (filter.marketplace != null && r.platform != filter.marketplace) {
        return false;
      }
      if (filter.discrepancyStatus == DiscrepancyFilter.hasIssues &&
          r.discrepancyCount == 0) { return false; }
      if (filter.discrepancyStatus == DiscrepancyFilter.clean &&
          r.discrepancyCount > 0) { return false; }
      return true;
    }).toList();
  }

  List<ReportSummaryHiveObject> _filteredSummaries(
    AnalyticsFilter filter,
    List<LocalReportHiveObject> reports,
  ) {
    final ids = reports.map((r) => r.id).toSet();
    return HiveManager.reportSummaryBox.values
        .where((s) => ids.contains(s.reportId))
        .toList();
  }

  // ── Trend builders ─────────────────────────────────────────────────────────

  List<ChartPoint> _trendFrom(
    List<MapEntry<String, _PeriodBucket>> sorted,
    double Function(_PeriodBucket) valueFn,
  ) {
    return List.generate(sorted.length, (i) {
      final e = sorted[i];
      return ChartPoint(
        x: i.toDouble(),
        value: valueFn(e.value),
        label: _shortLabel(e.key),
      );
    });
  }

  String _periodKey(DateTime date, DateRangeFilter range) {
    if (range == DateRangeFilter.today ||
        range == DateRangeFilter.yesterday ||
        range == DateRangeFilter.last7Days) {
      return '${date.year}-${_p(date.month)}-${_p(date.day)}';
    }
    return '${date.year}-${_p(date.month)}';
  }

  String _shortLabel(String key) {
    final parts = key.split('-');
    if (parts.length == 3) return '${parts[2]}/${parts[1]}';
    final months = [
      '', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
      'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'
    ];
    final m = int.tryParse(parts[1]) ?? 0;
    return m > 0 && m <= 12 ? months[m] : key;
  }

  // ── Monthly comparison (all-time, by calendar month) ──────────────────────

  List<MonthlyData> _buildMonthlyComparison(
    List<ReportSummaryHiveObject> summaries,
  ) {
    final grouped = <String, _PeriodBucket>{};
    for (final s in summaries) {
      final date = DateTime.tryParse(s.reconciledAt);
      if (date == null) continue;
      final key = '${date.year}-${_p(date.month)}';
      final b = grouped[key] ??= _PeriodBucket(key);
      b.grossRevenue += s.grossRevenue;
      b.netSettlement += s.netSettlement;
      b.totalFees += s.totalFees;
      b.orders += s.totalOrders;
    }

    final months = [
      '', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
      'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'
    ];

    final sorted = grouped.entries.toList()
      ..sort((a, b) => a.key.compareTo(b.key));

    return sorted.map((e) {
      final parts = e.key.split('-');
      final m = int.tryParse(parts[1]) ?? 0;
      final label = m > 0 && m <= 12 ? "${months[m]} '${parts[0].substring(2)}" : e.key;
      return MonthlyData(
        period: e.key,
        label: label,
        grossRevenue: e.value.grossRevenue,
        netSettlement: e.value.netSettlement,
        totalFees: e.value.totalFees,
        orders: e.value.orders,
      );
    }).toList();
  }

  // ── Fee breakdown slices ───────────────────────────────────────────────────

  List<FeeBreakdownSlice> _buildFeeBreakdown(
    double commission,
    double shipping,
    double gst,
    double tcs,
    double tds,
  ) {
    final slices = [
      FeeBreakdownSlice(
          label: 'Commission', amount: commission, colorHex: '#1A3A5C'),
      FeeBreakdownSlice(
          label: 'Shipping', amount: shipping, colorHex: '#2196F3'),
      FeeBreakdownSlice(
          label: 'GST on Fees', amount: gst, colorHex: '#F5A623'),
      FeeBreakdownSlice(label: 'TCS', amount: tcs, colorHex: '#E53935'),
      FeeBreakdownSlice(label: 'TDS', amount: tds, colorHex: '#9C27B0'),
    ];
    return slices.where((s) => s.amount > 0).toList();
  }

  // ── Insights ───────────────────────────────────────────────────────────────

  InsightSummary _buildInsights(
    Map<String, _PeriodBucket> byPeriod,
    double totalCommission,
    double totalGross,
    double totalFees,
  ) {
    if (byPeriod.isEmpty) return InsightSummary.empty;

    String? highestRevMonth;
    String? highestFeeMonth;
    String? lowestSettlementMonth;

    double maxRev = -1;
    double maxFee = -1;
    double minSettle = double.infinity;

    final months = [
      '', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
      'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'
    ];

    for (final e in byPeriod.entries) {
      final b = e.value;
      final label = _periodLabel(e.key, months);
      if (b.grossRevenue > maxRev) {
        maxRev = b.grossRevenue;
        highestRevMonth = label;
      }
      if (b.totalFees > maxFee) {
        maxFee = b.totalFees;
        highestFeeMonth = label;
      }
      if (b.netSettlement < minSettle) {
        minSettle = b.netSettlement;
        lowestSettlementMonth = label;
      }
    }

    return InsightSummary(
      highestRevenueMonth: highestRevMonth,
      highestFeeMonth: highestFeeMonth,
      lowestSettlementMonth: lowestSettlementMonth,
      avgCommissionPct: totalGross > 0 ? (totalCommission / totalGross) * 100 : 0,
      totalMarketplaceCharges: totalFees,
    );
  }

  String _periodLabel(String key, List<String> months) {
    final parts = key.split('-');
    if (parts.length == 3) return '${parts[2]}/${parts[1]}/${parts[0]}';
    final m = int.tryParse(parts[1]) ?? 0;
    final y = parts[0];
    return m > 0 && m <= 12 ? '${months[m]} $y' : key;
  }

  String _p(int n) => n.toString().padLeft(2, '0');
}

class _PeriodBucket {
  _PeriodBucket(this.key);
  final String key;
  double grossRevenue = 0;
  double netSettlement = 0;
  double totalFees = 0;
  int orders = 0;
}
