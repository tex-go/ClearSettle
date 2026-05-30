import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/repositories/analytics_repository_impl.dart';
import '../../domain/entities/analytics_entity.dart';
import '../../domain/repositories/analytics_repository.dart';

final analyticsRepositoryProvider = Provider<AnalyticsRepository>(
  (_) => AnalyticsRepositoryImpl(),
);

// ── Filter state ─────────────────────────────────────────────────────────────

final analyticsFilterProvider =
    NotifierProvider<AnalyticsFilterNotifier, AnalyticsFilter>(
  AnalyticsFilterNotifier.new,
);

class AnalyticsFilterNotifier extends Notifier<AnalyticsFilter> {
  @override
  AnalyticsFilter build() => const AnalyticsFilter();

  void setDateRange(DateRangeFilter range) {
    state = state.copyWith(dateRange: range);
  }

  void setMarketplace(String? marketplace) {
    if (marketplace == null) {
      state = state.copyWith(clearMarketplace: true);
    } else {
      state = state.copyWith(marketplace: marketplace);
    }
  }

  void setSettlement(SettlementFilter settlement) {
    state = state.copyWith(settlementStatus: settlement);
  }

  void setDiscrepancy(DiscrepancyFilter discrepancy) {
    state = state.copyWith(discrepancyStatus: discrepancy);
  }

  void reset() => state = const AnalyticsFilter();
}

// ── Data provider ─────────────────────────────────────────────────────────────

final analyticsProvider =
    AsyncNotifierProvider<AnalyticsNotifier, AnalyticsSummary>(
  AnalyticsNotifier.new,
);

class AnalyticsNotifier extends AsyncNotifier<AnalyticsSummary> {
  @override
  Future<AnalyticsSummary> build() async {
    final filter = ref.watch(analyticsFilterProvider);
    return ref.read(analyticsRepositoryProvider).getSummary(filter);
  }

  Future<void> refresh() async {
    state = const AsyncValue.loading();
    state = await AsyncValue.guard(() => build());
  }
}
