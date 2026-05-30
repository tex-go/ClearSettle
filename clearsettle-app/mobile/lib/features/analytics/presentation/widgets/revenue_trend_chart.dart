import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';

import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_text_styles.dart';
import '../../../../core/utils/currency_formatter.dart';
import '../../domain/entities/analytics_entity.dart';

// ── Revenue vs Settlement Line Chart ──────────────────────────────────────────

class RevenueTrendChart extends StatelessWidget {
  const RevenueTrendChart({
    super.key,
    required this.revenueTrend,
    required this.settlementTrend,
  });

  final List<ChartPoint> revenueTrend;
  final List<ChartPoint> settlementTrend;

  @override
  Widget build(BuildContext context) {
    if (revenueTrend.isEmpty) return const _NoData();

    final maxY = revenueTrend
            .map((p) => p.value)
            .fold(0.0, (a, b) => a > b ? a : b) *
        1.2;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _Legend(items: const [
          _LegendItem(label: 'Gross Revenue', color: AppColors.primary),
          _LegendItem(label: 'Net Settlement', color: AppColors.accent),
        ]),
        const SizedBox(height: 12),
        SizedBox(
          height: 180,
          child: LineChart(_lineData(maxY)),
        ),
      ],
    );
  }

  LineChartData _lineData(double maxY) {
    return LineChartData(
      minY: 0,
      maxY: maxY > 0 ? maxY : 10000,
      gridData: FlGridData(
        show: true,
        drawVerticalLine: false,
        horizontalInterval: maxY > 0 ? maxY / 4 : 2500,
        getDrawingHorizontalLine: (_) =>
            const FlLine(color: AppColors.divider, strokeWidth: 1),
      ),
      titlesData: FlTitlesData(
        topTitles:
            const AxisTitles(sideTitles: SideTitles(showTitles: false)),
        rightTitles:
            const AxisTitles(sideTitles: SideTitles(showTitles: false)),
        leftTitles: AxisTitles(
          sideTitles: SideTitles(
            showTitles: true,
            reservedSize: 64,
            getTitlesWidget: (v, _) => Text(
              CurrencyFormatter.formatCompact(v),
              style: AppTextStyles.labelSmall,
            ),
          ),
        ),
        bottomTitles: AxisTitles(
          sideTitles: SideTitles(
            showTitles: true,
            getTitlesWidget: (v, _) {
              final i = v.toInt();
              if (i < 0 || i >= revenueTrend.length) {
                return const SizedBox.shrink();
              }
              return Padding(
                padding: const EdgeInsets.only(top: 4),
                child:
                    Text(revenueTrend[i].label, style: AppTextStyles.labelSmall),
              );
            },
          ),
        ),
      ),
      borderData: FlBorderData(show: false),
      lineBarsData: [
        _line(revenueTrend, AppColors.primary),
        if (settlementTrend.isNotEmpty)
          _line(settlementTrend, AppColors.accent),
      ],
    );
  }

  LineChartBarData _line(List<ChartPoint> points, Color color) {
    return LineChartBarData(
      spots: points.map((p) => FlSpot(p.x, p.value)).toList(),
      isCurved: true,
      color: color,
      barWidth: 2.5,
      dotData: const FlDotData(show: false),
      belowBarData:
          BarAreaData(show: true, color: color.withValues(alpha: 0.08)),
    );
  }
}

// ── Settlement Trend (standalone) ─────────────────────────────────────────────

class SettlementTrendChart extends StatelessWidget {
  const SettlementTrendChart({super.key, required this.settlementTrend});

  final List<ChartPoint> settlementTrend;

  @override
  Widget build(BuildContext context) {
    if (settlementTrend.isEmpty) return const _NoData();
    final maxY = settlementTrend
            .map((p) => p.value)
            .fold(0.0, (a, b) => a > b ? a : b) *
        1.2;

    return SizedBox(
      height: 160,
      child: LineChart(
        LineChartData(
          minY: 0,
          maxY: maxY > 0 ? maxY : 10000,
          gridData: FlGridData(
            show: true,
            drawVerticalLine: false,
            horizontalInterval: maxY > 0 ? maxY / 4 : 2500,
            getDrawingHorizontalLine: (_) =>
                const FlLine(color: AppColors.divider, strokeWidth: 1),
          ),
          titlesData: FlTitlesData(
            topTitles:
                const AxisTitles(sideTitles: SideTitles(showTitles: false)),
            rightTitles:
                const AxisTitles(sideTitles: SideTitles(showTitles: false)),
            leftTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                reservedSize: 64,
                getTitlesWidget: (v, _) => Text(
                  CurrencyFormatter.formatCompact(v),
                  style: AppTextStyles.labelSmall,
                ),
              ),
            ),
            bottomTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                getTitlesWidget: (v, _) {
                  final i = v.toInt();
                  if (i < 0 || i >= settlementTrend.length) {
                    return const SizedBox.shrink();
                  }
                  return Padding(
                    padding: const EdgeInsets.only(top: 4),
                    child: Text(settlementTrend[i].label,
                        style: AppTextStyles.labelSmall),
                  );
                },
              ),
            ),
          ),
          borderData: FlBorderData(show: false),
          lineBarsData: [
            LineChartBarData(
              spots: settlementTrend
                  .map((p) => FlSpot(p.x, p.value))
                  .toList(),
              isCurved: true,
              color: AppColors.accent,
              barWidth: 2.5,
              dotData: const FlDotData(show: false),
              belowBarData: BarAreaData(
                show: true,
                color: AppColors.accent.withValues(alpha: 0.1),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ── Order Growth Bar Chart ─────────────────────────────────────────────────────

class OrderGrowthChart extends StatelessWidget {
  const OrderGrowthChart({super.key, required this.data});

  final List<ChartPoint> data;

  @override
  Widget build(BuildContext context) {
    if (data.isEmpty) return const _NoData();

    final maxY = data.map((p) => p.value).fold(0.0, (a, b) => a > b ? a : b) *
        1.2;

    return SizedBox(
      height: 160,
      child: BarChart(
        BarChartData(
          maxY: maxY > 0 ? maxY : 100,
          barGroups: data.asMap().entries.map((e) {
            return BarChartGroupData(
              x: e.key,
              barRods: [
                BarChartRodData(
                  toY: e.value.value,
                  color: AppColors.primary,
                  width: data.length > 6 ? 12 : 20,
                  borderRadius:
                      const BorderRadius.vertical(top: Radius.circular(4)),
                ),
              ],
            );
          }).toList(),
          gridData: FlGridData(
            show: true,
            drawVerticalLine: false,
            horizontalInterval: maxY > 0 ? maxY / 4 : 25,
            getDrawingHorizontalLine: (_) =>
                const FlLine(color: AppColors.divider, strokeWidth: 1),
          ),
          titlesData: FlTitlesData(
            topTitles:
                const AxisTitles(sideTitles: SideTitles(showTitles: false)),
            rightTitles:
                const AxisTitles(sideTitles: SideTitles(showTitles: false)),
            leftTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                reservedSize: 40,
                getTitlesWidget: (v, _) => Text(
                  v.toInt().toString(),
                  style: AppTextStyles.labelSmall,
                ),
              ),
            ),
            bottomTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                getTitlesWidget: (v, _) {
                  final i = v.toInt();
                  if (i < 0 || i >= data.length) return const SizedBox.shrink();
                  return Padding(
                    padding: const EdgeInsets.only(top: 4),
                    child: Text(data[i].label, style: AppTextStyles.labelSmall),
                  );
                },
              ),
            ),
          ),
          borderData: FlBorderData(show: false),
        ),
      ),
    );
  }
}

// ── Fee Breakdown Pie Chart ────────────────────────────────────────────────────

class FeeBreakdownChart extends StatefulWidget {
  const FeeBreakdownChart({super.key, required this.slices});

  final List<FeeBreakdownSlice> slices;

  @override
  State<FeeBreakdownChart> createState() => _FeeBreakdownChartState();
}

class _FeeBreakdownChartState extends State<FeeBreakdownChart> {
  int? _touchedIndex;

  @override
  Widget build(BuildContext context) {
    if (widget.slices.isEmpty) return const _NoData();

    final total = widget.slices.fold(0.0, (s, e) => s + e.amount);

    return Row(
      children: [
        Expanded(
          child: SizedBox(
            height: 180,
            child: PieChart(
              PieChartData(
                sections: List.generate(widget.slices.length, (i) {
                  final sl = widget.slices[i];
                  final isTouched = i == _touchedIndex;
                  final pct = total > 0
                      ? (sl.amount / total * 100).toStringAsFixed(1)
                      : '0';
                  return PieChartSectionData(
                    value: sl.amount,
                    title: isTouched ? '$pct%' : '',
                    color: _hex(sl.colorHex),
                    radius: isTouched ? 72 : 60,
                    titleStyle: const TextStyle(
                      fontSize: 11,
                      color: Colors.white,
                      fontWeight: FontWeight.w700,
                    ),
                  );
                }),
                centerSpaceRadius: 36,
                sectionsSpace: 2,
                pieTouchData: PieTouchData(
                  touchCallback: (_, r) => setState(() {
                    _touchedIndex =
                        r?.touchedSection?.touchedSectionIndex;
                  }),
                ),
              ),
            ),
          ),
        ),
        const SizedBox(width: 12),
        Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: widget.slices.map((s) {
            final pct = total > 0
                ? (s.amount / total * 100).toStringAsFixed(0)
                : '0';
            return Padding(
              padding: const EdgeInsets.only(bottom: 6),
              child: Row(
                children: [
                  Container(
                    width: 10,
                    height: 10,
                    decoration: BoxDecoration(
                      color: _hex(s.colorHex),
                      shape: BoxShape.circle,
                    ),
                  ),
                  const SizedBox(width: 6),
                  Text('${s.label} ($pct%)',
                      style: AppTextStyles.labelSmall),
                ],
              ),
            );
          }).toList(),
        ),
      ],
    );
  }

  Color _hex(String h) {
    final v = h.replaceFirst('#', '');
    return Color(int.parse('FF$v', radix: 16));
  }
}

// ── Monthly Comparison Grouped Bar Chart ──────────────────────────────────────

class MonthlyComparisonChart extends StatelessWidget {
  const MonthlyComparisonChart({super.key, required this.data});

  final List<MonthlyData> data;

  @override
  Widget build(BuildContext context) {
    if (data.isEmpty) return const _NoData();

    final maxY = data
            .expand((d) => [d.grossRevenue, d.netSettlement])
            .fold(0.0, (a, b) => a > b ? a : b) *
        1.2;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _Legend(items: const [
          _LegendItem(label: 'Gross', color: AppColors.primary),
          _LegendItem(label: 'Net', color: AppColors.accent),
          _LegendItem(label: 'Fees', color: AppColors.warning),
        ]),
        const SizedBox(height: 12),
        SizedBox(
          height: 180,
          child: BarChart(
            BarChartData(
              maxY: maxY > 0 ? maxY : 10000,
              groupsSpace: 12,
              barGroups: data.asMap().entries.map((e) {
                final d = e.value;
                return BarChartGroupData(
                  x: e.key,
                  groupVertically: false,
                  barsSpace: 3,
                  barRods: [
                    BarChartRodData(
                      toY: d.grossRevenue,
                      color: AppColors.primary,
                      width: 8,
                      borderRadius:
                          const BorderRadius.vertical(top: Radius.circular(3)),
                    ),
                    BarChartRodData(
                      toY: d.netSettlement,
                      color: AppColors.accent,
                      width: 8,
                      borderRadius:
                          const BorderRadius.vertical(top: Radius.circular(3)),
                    ),
                    BarChartRodData(
                      toY: d.totalFees,
                      color: AppColors.warning,
                      width: 8,
                      borderRadius:
                          const BorderRadius.vertical(top: Radius.circular(3)),
                    ),
                  ],
                );
              }).toList(),
              gridData: FlGridData(
                show: true,
                drawVerticalLine: false,
                horizontalInterval: maxY > 0 ? maxY / 4 : 2500,
                getDrawingHorizontalLine: (_) =>
                    const FlLine(color: AppColors.divider, strokeWidth: 1),
              ),
              titlesData: FlTitlesData(
                topTitles: const AxisTitles(
                    sideTitles: SideTitles(showTitles: false)),
                rightTitles: const AxisTitles(
                    sideTitles: SideTitles(showTitles: false)),
                leftTitles: AxisTitles(
                  sideTitles: SideTitles(
                    showTitles: true,
                    reservedSize: 64,
                    getTitlesWidget: (v, _) => Text(
                      CurrencyFormatter.formatCompact(v),
                      style: AppTextStyles.labelSmall,
                    ),
                  ),
                ),
                bottomTitles: AxisTitles(
                  sideTitles: SideTitles(
                    showTitles: true,
                    getTitlesWidget: (v, _) {
                      final i = v.toInt();
                      if (i < 0 || i >= data.length) {
                        return const SizedBox.shrink();
                      }
                      return Padding(
                        padding: const EdgeInsets.only(top: 4),
                        child: Text(data[i].label,
                            style: AppTextStyles.labelSmall),
                      );
                    },
                  ),
                ),
              ),
              borderData: FlBorderData(show: false),
            ),
          ),
        ),
      ],
    );
  }
}

// ── Fee Trend Line Chart ───────────────────────────────────────────────────────

class FeeTrendChart extends StatelessWidget {
  const FeeTrendChart({super.key, required this.data});

  // Pass settlementTrend mapped to fees: grossRevenue - netSettlement per period
  final List<ChartPoint> data;

  @override
  Widget build(BuildContext context) {
    if (data.isEmpty) return const _NoData();

    final maxY =
        data.map((p) => p.value).fold(0.0, (a, b) => a > b ? a : b) * 1.2;

    return SizedBox(
      height: 160,
      child: LineChart(
        LineChartData(
          minY: 0,
          maxY: maxY > 0 ? maxY : 1000,
          gridData: FlGridData(
            show: true,
            drawVerticalLine: false,
            horizontalInterval: maxY > 0 ? maxY / 4 : 250,
            getDrawingHorizontalLine: (_) =>
                const FlLine(color: AppColors.divider, strokeWidth: 1),
          ),
          titlesData: FlTitlesData(
            topTitles:
                const AxisTitles(sideTitles: SideTitles(showTitles: false)),
            rightTitles:
                const AxisTitles(sideTitles: SideTitles(showTitles: false)),
            leftTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                reservedSize: 64,
                getTitlesWidget: (v, _) => Text(
                  CurrencyFormatter.formatCompact(v),
                  style: AppTextStyles.labelSmall,
                ),
              ),
            ),
            bottomTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                getTitlesWidget: (v, _) {
                  final i = v.toInt();
                  if (i < 0 || i >= data.length) {
                    return const SizedBox.shrink();
                  }
                  return Padding(
                    padding: const EdgeInsets.only(top: 4),
                    child:
                        Text(data[i].label, style: AppTextStyles.labelSmall),
                  );
                },
              ),
            ),
          ),
          borderData: FlBorderData(show: false),
          lineBarsData: [
            LineChartBarData(
              spots: data.map((p) => FlSpot(p.x, p.value)).toList(),
              isCurved: true,
              color: AppColors.warning,
              barWidth: 2.5,
              dotData: const FlDotData(show: false),
              belowBarData: BarAreaData(
                show: true,
                color: AppColors.warning.withValues(alpha: 0.1),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ── Shared helpers ─────────────────────────────────────────────────────────────

class _NoData extends StatelessWidget {
  const _NoData();

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 120,
      child: Center(
        child: Text(
          'No data for selected period',
          style: AppTextStyles.bodySmall
              .copyWith(color: AppColors.textDisabled),
        ),
      ),
    );
  }
}

class _Legend extends StatelessWidget {
  const _Legend({required this.items});

  final List<_LegendItem> items;

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: 16,
      children: items.map((item) {
        return Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(width: 12, height: 3, color: item.color),
            const SizedBox(width: 4),
            Text(item.label, style: AppTextStyles.labelSmall),
          ],
        );
      }).toList(),
    );
  }
}

class _LegendItem {
  const _LegendItem({required this.label, required this.color});

  final String label;
  final Color color;
}
