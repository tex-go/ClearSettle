enum DateRangeFilter { last7Days, last30Days, last3Months, last6Months, allTime }

enum DiscrepancyFilter { all, hasIssues, clean }

enum SettlementFilter { all, settled, pending }

class AnalyticsFilter {
  const AnalyticsFilter({
    this.dateRange = DateRangeFilter.last6Months,
    this.marketplace,
    this.settlementStatus = SettlementFilter.all,
    this.discrepancyStatus = DiscrepancyFilter.all,
  });

  final DateRangeFilter dateRange;
  final String? marketplace; // null = all
  final SettlementFilter settlementStatus;
  final DiscrepancyFilter discrepancyStatus;

  DateTime get startDate {
    final now = DateTime.now();
    switch (dateRange) {
      case DateRangeFilter.last7Days:
        return now.subtract(const Duration(days: 7));
      case DateRangeFilter.last30Days:
        return now.subtract(const Duration(days: 30));
      case DateRangeFilter.last3Months:
        return DateTime(now.year, now.month - 3, now.day);
      case DateRangeFilter.last6Months:
        return DateTime(now.year, now.month - 6, now.day);
      case DateRangeFilter.allTime:
        return DateTime(2020);
    }
  }

  String get dateRangeLabel {
    switch (dateRange) {
      case DateRangeFilter.last7Days:
        return 'Last 7 days';
      case DateRangeFilter.last30Days:
        return 'Last 30 days';
      case DateRangeFilter.last3Months:
        return 'Last 3 months';
      case DateRangeFilter.last6Months:
        return 'Last 6 months';
      case DateRangeFilter.allTime:
        return 'All time';
    }
  }

  AnalyticsFilter copyWith({
    DateRangeFilter? dateRange,
    String? marketplace,
    bool clearMarketplace = false,
    SettlementFilter? settlementStatus,
    DiscrepancyFilter? discrepancyStatus,
  }) {
    return AnalyticsFilter(
      dateRange: dateRange ?? this.dateRange,
      marketplace: clearMarketplace ? null : (marketplace ?? this.marketplace),
      settlementStatus: settlementStatus ?? this.settlementStatus,
      discrepancyStatus: discrepancyStatus ?? this.discrepancyStatus,
    );
  }
}

class ChartPoint {
  const ChartPoint({
    required this.x,
    required this.value,
    required this.label,
  });

  final double x;
  final double value;
  final String label;
}

class FeeBreakdownSlice {
  const FeeBreakdownSlice({
    required this.label,
    required this.amount,
    required this.colorHex,
  });

  final String label;
  final double amount;
  final String colorHex;
}

class AnalyticsSummary {
  const AnalyticsSummary({
    required this.totalGrossRevenue,
    required this.totalNetSettlement,
    required this.totalOrders,
    required this.totalReports,
    required this.totalDiscrepancies,
    required this.totalFees,
    required this.revenueTrend,
    required this.settlementTrend,
    required this.orderGrowth,
    required this.feeBreakdown,
    this.avgSettlementRate = 0.0,
  });

  final double totalGrossRevenue;
  final double totalNetSettlement;
  final int totalOrders;
  final int totalReports;
  final int totalDiscrepancies;
  final double totalFees;
  final List<ChartPoint> revenueTrend;
  final List<ChartPoint> settlementTrend;
  final List<ChartPoint> orderGrowth;
  final List<FeeBreakdownSlice> feeBreakdown;
  final double avgSettlementRate;

  bool get hasData => totalReports > 0;

  static const empty = AnalyticsSummary(
    totalGrossRevenue: 0,
    totalNetSettlement: 0,
    totalOrders: 0,
    totalReports: 0,
    totalDiscrepancies: 0,
    totalFees: 0,
    revenueTrend: [],
    settlementTrend: [],
    orderGrowth: [],
    feeBreakdown: [],
  );
}
