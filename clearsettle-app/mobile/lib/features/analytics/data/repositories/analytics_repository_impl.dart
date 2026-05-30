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

    // Aggregate top-line metrics
    double totalGross = 0;
    double totalNet = 0;
    double totalFees = 0;
    int totalOrders = 0;
    int totalDiscrepancies = 0;

    double totalCommission = 0;
    double totalShipping = 0;
    double totalGst = 0;
    double totalTcs = 0;
    double totalTds = 0;

    for (final s in summaries) {
      totalGross += s.grossRevenue;
      totalNet += s.netSettlement;
      totalFees += s.totalFees;
      totalOrders += s.totalOrders;
      totalDiscrepancies += s.discrepancyCount;
      totalCommission += s.totalCommission;
      totalShipping += s.totalShipping;
      totalGst += s.totalGstOnFees;
      totalTcs += s.totalTcs;
      totalTds += s.totalTds;
    }

    final revenueTrend = _buildTrend(
      summaries,
      (s) => s.grossRevenue,
      filter.dateRange,
    );
    final settlementTrend = _buildTrend(
      summaries,
      (s) => s.netSettlement,
      filter.dateRange,
    );
    final orderGrowth = _buildIntTrend(summaries, filter.dateRange);

    final feeBreakdown = _buildFeeBreakdown(
      totalCommission,
      totalShipping,
      totalGst,
      totalTcs,
      totalTds,
      totalFees -
          totalCommission -
          totalShipping -
          totalGst -
          totalTcs -
          totalTds,
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
      avgSettlementRate:
          totalGross > 0 ? (totalNet / totalGross) * 100 : 0,
    );
  }

  // ── Filtering helpers ──────────────────────────────────────────────────────

  List<LocalReportHiveObject> _filteredReports(AnalyticsFilter filter) {
    return HiveManager.localReportBox.values.where((r) {
      if (r.status != 'parsed') return false;
      final date = DateTime.tryParse(r.uploadedAt);
      if (date == null || date.isBefore(filter.startDate)) return false;
      if (filter.marketplace != null && r.platform != filter.marketplace) {
        return false;
      }
      if (filter.discrepancyStatus == DiscrepancyFilter.hasIssues &&
          r.discrepancyCount == 0) {
        return false;
      }
      if (filter.discrepancyStatus == DiscrepancyFilter.clean &&
          r.discrepancyCount > 0) {
        return false;
      }
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

  List<ChartPoint> _buildTrend(
    List<ReportSummaryHiveObject> summaries,
    double Function(ReportSummaryHiveObject) valueFn,
    DateRangeFilter range,
  ) {
    final grouped = <String, double>{};
    for (final s in summaries) {
      final date = DateTime.tryParse(s.reconciledAt);
      if (date == null) continue;
      final key = _periodKey(date, range);
      grouped[key] = (grouped[key] ?? 0) + valueFn(s);
    }

    final sorted = grouped.entries.toList()
      ..sort((a, b) => a.key.compareTo(b.key));

    return List.generate(sorted.length, (i) {
      final entry = sorted[i];
      return ChartPoint(
        x: i.toDouble(),
        value: entry.value,
        label: _shortLabel(entry.key, range),
      );
    });
  }

  List<ChartPoint> _buildIntTrend(
    List<ReportSummaryHiveObject> summaries,
    DateRangeFilter range,
  ) {
    final grouped = <String, int>{};
    for (final s in summaries) {
      final date = DateTime.tryParse(s.reconciledAt);
      if (date == null) continue;
      final key = _periodKey(date, range);
      grouped[key] = (grouped[key] ?? 0) + s.totalOrders;
    }

    final sorted = grouped.entries.toList()
      ..sort((a, b) => a.key.compareTo(b.key));

    return List.generate(sorted.length, (i) {
      final entry = sorted[i];
      return ChartPoint(
        x: i.toDouble(),
        value: entry.value.toDouble(),
        label: _shortLabel(entry.key, range),
      );
    });
  }

  String _periodKey(DateTime date, DateRangeFilter range) {
    if (range == DateRangeFilter.last7Days) {
      return '${date.year}-${date.month.toString().padLeft(2, '0')}-${date.day.toString().padLeft(2, '0')}';
    }
    return '${date.year}-${date.month.toString().padLeft(2, '0')}';
  }

  String _shortLabel(String key, DateRangeFilter range) {
    if (range == DateRangeFilter.last7Days) {
      final parts = key.split('-');
      return '${parts[2]}/${parts[1]}';
    }
    final parts = key.split('-');
    final months = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                     'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    final month = int.tryParse(parts[1]) ?? 0;
    return months[month];
  }

  // ── Fee breakdown ──────────────────────────────────────────────────────────

  List<FeeBreakdownSlice> _buildFeeBreakdown(
    double commission,
    double shipping,
    double gst,
    double tcs,
    double tds,
    double other,
  ) {
    final slices = [
      FeeBreakdownSlice(
          label: 'Commission', amount: commission, colorHex: '#1A3A5C'),
      FeeBreakdownSlice(
          label: 'Shipping', amount: shipping, colorHex: '#2196F3'),
      FeeBreakdownSlice(
          label: 'GST on Fees', amount: gst, colorHex: '#F5A623'),
      FeeBreakdownSlice(
          label: 'TCS', amount: tcs, colorHex: '#E53935'),
      FeeBreakdownSlice(
          label: 'TDS', amount: tds, colorHex: '#9C27B0'),
      FeeBreakdownSlice(
          label: 'Other', amount: other > 0 ? other : 0, colorHex: '#607D8B'),
    ];
    return slices.where((s) => s.amount > 0).toList();
  }
}
