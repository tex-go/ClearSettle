import 'package:fl_chart/fl_chart.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/network/api_client.dart';

/// Fetches 30-day net settlement trend from /analytics/revenue.
/// Returns an empty list when no data is available — callers show empty state.
final settlementTrendProvider =
    FutureProvider.autoDispose<List<FlSpot>>((ref) async {
  final client = ref.read(apiClientProvider);
  try {
    final response = await client.get<Map<String, dynamic>>(
      '/analytics/revenue',
      queryParameters: {'granularity': 'daily'},
    );
    final data = response.data;
    if (data == null) return [];
    final series = data['series'] as List<dynamic>?;
    if (series == null || series.isEmpty) return [];
    return series.asMap().entries.map((entry) {
      final row = entry.value as Map<String, dynamic>;
      final net = (row['net'] as num?)?.toDouble() ?? 0.0;
      return FlSpot(entry.key.toDouble(), net / 1000); // display in ₹K
    }).toList();
  } catch (_) {
    return [];
  }
});

/// Fetches per-platform revenue share from /analytics/marketplace.
/// Returns map of platform → percentage (0-100).
/// Returns empty map when no data — callers show empty state.
final platformMixProvider =
    FutureProvider.autoDispose<Map<String, double>>((ref) async {
  final client = ref.read(apiClientProvider);
  try {
    final response = await client.get<Map<String, dynamic>>('/analytics/marketplace');
    final data = response.data;
    if (data == null) return {};

    // The endpoint may return 'items' list or 'platforms' map
    final items = data['items'] as List<dynamic>?;
    final Map<String, double> totals = {};

    if (items != null && items.isNotEmpty) {
      for (final item in items) {
        final m = item as Map<String, dynamic>;
        final platform = (m['platform'] as String?)?.toLowerCase() ?? 'other';
        totals[platform] =
            (totals[platform] ?? 0) + ((m['gross_revenue'] as num?)?.toDouble() ?? 0);
      }
    } else {
      // Try 'platforms' map format
      final platforms = data['platforms'] as Map<String, dynamic>?;
      if (platforms == null || platforms.isEmpty) return {};
      for (final entry in platforms.entries) {
        final val = entry.value as Map<String, dynamic>;
        totals[entry.key.toLowerCase()] =
            (val['gross_revenue'] as num?)?.toDouble() ?? 0;
      }
    }

    final total = totals.values.fold(0.0, (a, b) => a + b);
    if (total == 0) return {};

    // Convert to percentages, sorted descending
    final pct = <String, double>{};
    final sorted = totals.entries.toList()
      ..sort((a, b) => b.value.compareTo(a.value));
    for (final e in sorted) {
      pct[e.key] = (e.value / total) * 100;
    }
    return pct;
  } catch (_) {
    return {};
  }
});
