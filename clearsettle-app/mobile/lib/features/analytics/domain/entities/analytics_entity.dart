enum DateRangeFilter {
  today,
  yesterday,
  last7Days,
  last30Days,
  thisMonth,
  lastMonth,
  last6Months,
  allTime,
  custom,
}

enum DiscrepancyFilter { all, hasIssues, clean }

enum SettlementFilter { all, settled, pending }

class AnalyticsFilter {
  const AnalyticsFilter({
    this.dateRange = DateRangeFilter.last30Days,
    this.marketplace,
    this.settlementStatus = SettlementFilter.all,
    this.discrepancyStatus = DiscrepancyFilter.all,
    this.customStart,
    this.customEnd,
  });

  final DateRangeFilter dateRange;
  final String? marketplace;
  final SettlementFilter settlementStatus;
  final DiscrepancyFilter discrepancyStatus;
  final DateTime? customStart;
  final DateTime? customEnd;

  DateTime get startDate {
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    switch (dateRange) {
      case DateRangeFilter.today:
        return today;
      case DateRangeFilter.yesterday:
        return today.subtract(const Duration(days: 1));
      case DateRangeFilter.last7Days:
        return today.subtract(const Duration(days: 6));
      case DateRangeFilter.last30Days:
        return today.subtract(const Duration(days: 29));
      case DateRangeFilter.thisMonth:
        return DateTime(now.year, now.month, 1);
      case DateRangeFilter.lastMonth:
        final lm = DateTime(now.year, now.month - 1, 1);
        return lm;
      case DateRangeFilter.last6Months:
        return DateTime(now.year, now.month - 6, now.day);
      case DateRangeFilter.allTime:
        return DateTime(2020);
      case DateRangeFilter.custom:
        return customStart ?? DateTime(2020);
    }
  }

  DateTime get endDate {
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day, 23, 59, 59);
    switch (dateRange) {
      case DateRangeFilter.yesterday:
        final y = today.subtract(const Duration(days: 1));
        return DateTime(y.year, y.month, y.day, 23, 59, 59);
      case DateRangeFilter.lastMonth:
        // last day of last month
        return DateTime(now.year, now.month, 0, 23, 59, 59);
      case DateRangeFilter.custom:
        return customEnd ?? today;
      default:
        return today;
    }
  }

  String get label {
    switch (dateRange) {
      case DateRangeFilter.today:
        return 'Today';
      case DateRangeFilter.yesterday:
        return 'Yesterday';
      case DateRangeFilter.last7Days:
        return 'Last 7 Days';
      case DateRangeFilter.last30Days:
        return 'Last 30 Days';
      case DateRangeFilter.thisMonth:
        return 'This Month';
      case DateRangeFilter.lastMonth:
        return 'Last Month';
      case DateRangeFilter.last6Months:
        return 'Last 6 Months';
      case DateRangeFilter.allTime:
        return 'All Time';
      case DateRangeFilter.custom:
        if (customStart != null && customEnd != null) {
          return '${_fmt(customStart!)} – ${_fmt(customEnd!)}';
        }
        return 'Custom';
    }
  }

  String _fmt(DateTime d) =>
      '${d.day.toString().padLeft(2, '0')}/${d.month.toString().padLeft(2, '0')}/${d.year}';

  AnalyticsFilter copyWith({
    DateRangeFilter? dateRange,
    String? marketplace,
    bool clearMarketplace = false,
    SettlementFilter? settlementStatus,
    DiscrepancyFilter? discrepancyStatus,
    DateTime? customStart,
    DateTime? customEnd,
  }) {
    return AnalyticsFilter(
      dateRange: dateRange ?? this.dateRange,
      marketplace: clearMarketplace ? null : (marketplace ?? this.marketplace),
      settlementStatus: settlementStatus ?? this.settlementStatus,
      discrepancyStatus: discrepancyStatus ?? this.discrepancyStatus,
      customStart: customStart ?? this.customStart,
      customEnd: customEnd ?? this.customEnd,
    );
  }
}

// ── Chart models ───────────────────────────────────────────────────────────────

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

class MonthlyData {
  const MonthlyData({
    required this.period,
    required this.label,
    required this.grossRevenue,
    required this.netSettlement,
    required this.totalFees,
    required this.orders,
  });

  final String period; // 'YYYY-MM'
  final String label; // 'Jan', 'Feb' …
  final double grossRevenue;
  final double netSettlement;
  final double totalFees;
  final int orders;
}

// ── Fee detail ─────────────────────────────────────────────────────────────────

class FeeDetail {
  const FeeDetail({
    this.commission = 0.0,
    this.fixedFee = 0.0,
    this.collectionFee = 0.0,
    this.shippingFee = 0.0,
    this.reverseShippingFee = 0.0,
    this.gstOnFees = 0.0,
    this.tds = 0.0,
    this.tcs = 0.0,
  });

  final double commission;
  final double fixedFee;
  final double collectionFee;
  final double shippingFee;
  final double reverseShippingFee;
  final double gstOnFees;
  final double tds;
  final double tcs;

  double get totalFees =>
      commission +
      fixedFee +
      collectionFee +
      shippingFee +
      reverseShippingFee +
      gstOnFees +
      tds +
      tcs;

  static const empty = FeeDetail();
}

// ── Insights ───────────────────────────────────────────────────────────────────

class InsightSummary {
  const InsightSummary({
    this.highestRevenueMonth,
    this.highestFeeMonth,
    this.avgCommissionPct = 0.0,
    this.totalMarketplaceCharges = 0.0,
    this.lowestSettlementMonth,
  });

  final String? highestRevenueMonth;
  final String? highestFeeMonth;
  final String? lowestSettlementMonth;
  final double avgCommissionPct;
  final double totalMarketplaceCharges;

  static const empty = InsightSummary();
}

// ── Aggregated analytics summary ───────────────────────────────────────────────

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
    required this.feeDetail,
    required this.monthlyComparison,
    this.insights = InsightSummary.empty,
    this.chargePercentage = 0.0,
    this.avgOrderValue = 0.0,
    this.avgSettlementRate = 0.0,
  });

  final double totalGrossRevenue;
  final double totalNetSettlement;
  final int totalOrders;
  final int totalReports;
  final int totalDiscrepancies;
  final double totalFees;

  // Chart data
  final List<ChartPoint> revenueTrend;
  final List<ChartPoint> settlementTrend;
  final List<ChartPoint> orderGrowth;
  final List<FeeBreakdownSlice> feeBreakdown;
  final List<MonthlyData> monthlyComparison;

  // Fee breakdown
  final FeeDetail feeDetail;

  // KPI derived
  final double chargePercentage;
  final double avgOrderValue;
  final double avgSettlementRate;

  // Insights
  final InsightSummary insights;

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
    feeDetail: FeeDetail.empty,
    monthlyComparison: [],
  );
}
