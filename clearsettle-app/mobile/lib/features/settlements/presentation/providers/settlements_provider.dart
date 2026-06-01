import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../domain/entities/settlement_entity.dart';

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

class SettlementsState {
  const SettlementsState({
    required this.settlements,
    required this.isLoading,
    this.filterMarketplace,
    this.filterStatus,
    this.error,
  });

  final List<SettlementEntity> settlements;
  final bool isLoading;
  final String? filterMarketplace;
  final SettlementStatus? filterStatus;
  final String? error;

  List<SettlementEntity> get filtered {
    var list = settlements;
    if (filterMarketplace != null && filterMarketplace!.isNotEmpty) {
      list = list
          .where((s) =>
              s.marketplace.toLowerCase() ==
              filterMarketplace!.toLowerCase())
          .toList();
    }
    if (filterStatus != null) {
      list = list.where((s) => s.status == filterStatus).toList();
    }
    return list;
  }

  double get totalExpected =>
      settlements.fold(0, (sum, s) => sum + s.expectedAmount);

  double get totalReceived =>
      settlements.fold(0, (sum, s) => sum + s.receivedAmount);

  double get totalDifference => totalReceived - totalExpected;

  int get mismatchCount =>
      settlements.where((s) => s.status == SettlementStatus.mismatch).length;

  SettlementsState copyWith({
    List<SettlementEntity>? settlements,
    bool? isLoading,
    String? filterMarketplace,
    SettlementStatus? filterStatus,
    bool clearFilterStatus = false,
    String? error,
  }) =>
      SettlementsState(
        settlements: settlements ?? this.settlements,
        isLoading: isLoading ?? this.isLoading,
        filterMarketplace: filterMarketplace ?? this.filterMarketplace,
        filterStatus:
            clearFilterStatus ? null : (filterStatus ?? this.filterStatus),
        error: error,
      );
}

// ---------------------------------------------------------------------------
// Notifier
// ---------------------------------------------------------------------------

class SettlementsNotifier extends Notifier<SettlementsState> {
  @override
  SettlementsState build() {
    Future.microtask(load);
    return const SettlementsState(settlements: [], isLoading: true);
  }

  Future<void> load() async {
    state = state.copyWith(isLoading: true, error: null);
    await Future.delayed(const Duration(milliseconds: 500));
    state = state.copyWith(isLoading: false, settlements: _stubSettlements());
  }

  Future<void> refresh() => load();

  void setMarketplaceFilter(String? mp) {
    state = state.copyWith(filterMarketplace: mp ?? '');
  }

  void setStatusFilter(SettlementStatus? status) {
    if (status == null) {
      state = state.copyWith(clearFilterStatus: true);
    } else {
      state = state.copyWith(filterStatus: status);
    }
  }
}

final settlementsProvider =
    NotifierProvider<SettlementsNotifier, SettlementsState>(
        SettlementsNotifier.new);

// ---------------------------------------------------------------------------
// Stub data
// ---------------------------------------------------------------------------

List<SettlementEntity> _stubSettlements() {
  final now = DateTime.now();
  return [
    SettlementEntity(
      id: 'FK-2025-0598',
      marketplace: 'Flipkart',
      settlementDate: now.subtract(const Duration(days: 2)),
      expectedAmount: 84320.00,
      receivedAmount: 80000.00,
      status: SettlementStatus.mismatch,
      notes: '₹4,320 short — under review',
    ),
    SettlementEntity(
      id: 'AMZ-2025-1123',
      marketplace: 'Amazon',
      settlementDate: now.subtract(const Duration(days: 3)),
      expectedAmount: 125000.00,
      receivedAmount: 125000.00,
      status: SettlementStatus.matched,
    ),
    SettlementEntity(
      id: 'MEE-2025-0441',
      marketplace: 'Meesho',
      settlementDate: now.subtract(const Duration(days: 5)),
      expectedAmount: 38750.00,
      receivedAmount: 0,
      status: SettlementStatus.pending,
      notes: 'Settlement delayed — 3 days overdue',
    ),
    SettlementEntity(
      id: 'SH-2025-1023',
      marketplace: 'Shopify',
      settlementDate: now.subtract(const Duration(days: 6)),
      expectedAmount: 11500.00,
      receivedAmount: 8200.00,
      status: SettlementStatus.underInvestigation,
      notes: 'Partial payment — dispute raised',
    ),
    SettlementEntity(
      id: 'FK-2025-0590',
      marketplace: 'Flipkart',
      settlementDate: now.subtract(const Duration(days: 9)),
      expectedAmount: 62100.00,
      receivedAmount: 62100.00,
      status: SettlementStatus.matched,
    ),
    SettlementEntity(
      id: 'AMZ-2025-1098',
      marketplace: 'Amazon',
      settlementDate: now.subtract(const Duration(days: 11)),
      expectedAmount: 95500.00,
      receivedAmount: 95500.00,
      status: SettlementStatus.matched,
    ),
    SettlementEntity(
      id: 'FK-2025-0577',
      marketplace: 'Flipkart',
      settlementDate: now.subtract(const Duration(days: 16)),
      expectedAmount: 71800.00,
      receivedAmount: 68900.00,
      status: SettlementStatus.mismatch,
      notes: '₹2,900 deducted without reason code',
    ),
    SettlementEntity(
      id: 'MEE-2025-0410',
      marketplace: 'Meesho',
      settlementDate: now.subtract(const Duration(days: 18)),
      expectedAmount: 29300.00,
      receivedAmount: 29300.00,
      status: SettlementStatus.matched,
    ),
  ];
}
