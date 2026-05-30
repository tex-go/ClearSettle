import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';

import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_text_styles.dart';
import '../../../../core/utils/currency_formatter.dart';
import '../../domain/entities/analytics_entity.dart';

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
    if (revenueTrend.isEmpty) {
      return const _NoData();
    }

    final maxY = revenueTrend
            .map((p) => p.value)
            .fold(0.0, (a, b) => a > b ? a : b) *
        1.2;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _ChartLegend(
          items: const [
            _LegendItem(label: 'Gross Revenue', color: AppColors.primary),
            _LegendItem(label: 'Net Settlement', color: AppColors.accent),
          ],
        ),
        const SizedBox(height: 12),
        SizedBox(
          height: 180,
          child: LineChart(
            LineChartData(
              minY: 0,
              maxY: maxY > 0 ? maxY : 10000,
              gridData: FlGridData(
                show: true,
                drawVerticalLine: false,
                horizontalInterval: maxY > 0 ? maxY / 4 : 2500,
                getDrawingHorizontalLine: (value) => FlLine(
                  color: AppColors.divider,
                  strokeWidth: 1,
                ),
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
                    getTitlesWidget: (value, _) => Text(
                      CurrencyFormatter.formatCompact(value),
                      style: AppTextStyles.labelSmall,
                    ),
                  ),
                ),
                bottomTitles: AxisTitles(
                  sideTitles: SideTitles(
                    showTitles: true,
                    getTitlesWidget: (value, _) {
                      final idx = value.toInt();
                      if (idx < 0 || idx >= revenueTrend.length) {
                        return const SizedBox.shrink();
                      }
                      return Padding(
                        padding: const EdgeInsets.only(top: 4),
                        child: Text(
                          revenueTrend[idx].label,
                          style: AppTextStyles.labelSmall,
                        ),
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
            ),
          ),
        ),
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
      belowBarData: BarAreaData(
        show: true,
        color: color.withValues(alpha: 0.08),
      ),
    );
  }
}

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

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Expanded(
              child: SizedBox(
                height: 180,
                child: PieChart(
                  PieChartData(
                    sections: List.generate(widget.slices.length, (i) {
                      final slice = widget.slices[i];
                      final isTouched = i == _touchedIndex;
                      final pct = total > 0
                          ? (slice.amount / total * 100).toStringAsFixed(1)
                          : '0';
                      return PieChartSectionData(
                        value: slice.amount,
                        title: isTouched ? '$pct%' : '',
                        color: _hexToColor(slice.colorHex),
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
                      touchCallback: (event, response) {
                        setState(() {
                          _touchedIndex =
                              response?.touchedSection?.touchedSectionIndex;
                        });
                      },
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
                          color: _hexToColor(s.colorHex),
                          shape: BoxShape.circle,
                        ),
                      ),
                      const SizedBox(width: 6),
                      Text(
                        '${s.label} ($pct%)',
                        style: AppTextStyles.labelSmall,
                      ),
                    ],
                  ),
                );
              }).toList(),
            ),
          ],
        ),
      ],
    );
  }

  Color _hexToColor(String hex) {
    final h = hex.replaceFirst('#', '');
    return Color(int.parse('FF$h', radix: 16));
  }
}

class OrderGrowthChart extends StatelessWidget {
  const OrderGrowthChart({super.key, required this.data});

  final List<ChartPoint> data;

  @override
  Widget build(BuildContext context) {
    if (data.isEmpty) return const _NoData();

    final maxY = data.map((p) => p.value).fold(0.0, (a, b) => a > b ? a : b) *
        1.2;

    return SizedBox(
      height: 180,
      child: BarChart(
        BarChartData(
          maxY: maxY > 0 ? maxY : 100,
          barGroups: data.asMap().entries.map((entry) {
            return BarChartGroupData(
              x: entry.key,
              barRods: [
                BarChartRodData(
                  toY: entry.value.value,
                  color: AppColors.primary,
                  width: data.length > 6 ? 12 : 20,
                  borderRadius: const BorderRadius.vertical(
                    top: Radius.circular(4),
                  ),
                ),
              ],
            );
          }).toList(),
          gridData: FlGridData(
            show: true,
            drawVerticalLine: false,
            horizontalInterval: maxY > 0 ? maxY / 4 : 25,
            getDrawingHorizontalLine: (value) => FlLine(
              color: AppColors.divider,
              strokeWidth: 1,
            ),
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
                getTitlesWidget: (value, _) => Text(
                  value.toInt().toString(),
                  style: AppTextStyles.labelSmall,
                ),
              ),
            ),
            bottomTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                getTitlesWidget: (value, _) {
                  final idx = value.toInt();
                  if (idx < 0 || idx >= data.length) {
                    return const SizedBox.shrink();
                  }
                  return Padding(
                    padding: const EdgeInsets.only(top: 4),
                    child: Text(
                      data[idx].label,
                      style: AppTextStyles.labelSmall,
                    ),
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

// ── Shared private widgets ─────────────────────────────────────────────────

class _NoData extends StatelessWidget {
  const _NoData();

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 120,
      child: Center(
        child: Text(
          'No data for selected period',
          style: AppTextStyles.bodySmall.copyWith(
            color: AppColors.textDisabled,
          ),
        ),
      ),
    );
  }
}

class _ChartLegend extends StatelessWidget {
  const _ChartLegend({required this.items});

  final List<_LegendItem> items;

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: 16,
      children: items
          .map(
            (item) => Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  width: 12,
                  height: 3,
                  color: item.color,
                ),
                const SizedBox(width: 4),
                Text(item.label, style: AppTextStyles.labelSmall),
              ],
            ),
          )
          .toList(),
    );
  }
}

class _LegendItem {
  const _LegendItem({required this.label, required this.color});

  final String label;
  final Color color;
}
