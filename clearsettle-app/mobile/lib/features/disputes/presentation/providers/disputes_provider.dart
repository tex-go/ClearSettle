import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../domain/entities/dispute_entity.dart';

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

class DisputesState {
  const DisputesState({
    required this.disputes,
    required this.isLoading,
    this.filterStatus,
    this.filterMarketplace,
    this.error,
  });

  final List<DisputeEntity> disputes;
  final bool isLoading;
  final DisputeStatus? filterStatus;
  final String? filterMarketplace;
  final String? error;

  List<DisputeEntity> get filtered {
    var list = disputes;
    if (filterStatus != null) {
      list = list.where((d) => d.status == filterStatus).toList();
    }
    if (filterMarketplace != null && filterMarketplace!.isNotEmpty) {
      list = list
          .where((d) =>
              d.marketplace.toLowerCase() ==
              filterMarketplace!.toLowerCase())
          .toList();
    }
    return list;
  }

  double get totalClaimAmount =>
      disputes.fold(0, (s, d) => s + d.claimAmount);

  double get totalRecoveredAmount =>
      disputes.fold(0, (s, d) => s + d.recoveredAmount);

  int get openCount => disputes
      .where((d) =>
          d.status == DisputeStatus.submitted ||
          d.status == DisputeStatus.inReview)
      .length;

  DisputesState copyWith({
    List<DisputeEntity>? disputes,
    bool? isLoading,
    DisputeStatus? filterStatus,
    bool clearFilterStatus = false,
    String? filterMarketplace,
    String? error,
  }) =>
      DisputesState(
        disputes: disputes ?? this.disputes,
        isLoading: isLoading ?? this.isLoading,
        filterStatus:
            clearFilterStatus ? null : (filterStatus ?? this.filterStatus),
        filterMarketplace:
            filterMarketplace ?? this.filterMarketplace,
        error: error,
      );
}

// ---------------------------------------------------------------------------
// Notifier
// ---------------------------------------------------------------------------

class DisputesNotifier extends Notifier<DisputesState> {
  @override
  DisputesState build() {
    Future.microtask(load);
    return const DisputesState(disputes: [], isLoading: true);
  }

  Future<void> load() async {
    state = state.copyWith(isLoading: true, error: null);
    await Future.delayed(const Duration(milliseconds: 500));
    state = state.copyWith(isLoading: false, disputes: _stubDisputes());
  }

  Future<void> refresh() => load();

  void setStatusFilter(DisputeStatus? status) {
    if (status == null) {
      state = state.copyWith(clearFilterStatus: true);
    } else {
      state = state.copyWith(filterStatus: status);
    }
  }

  void setMarketplaceFilter(String? marketplace) {
    state = state.copyWith(filterMarketplace: marketplace ?? '');
  }
}

final disputesProvider =
    NotifierProvider<DisputesNotifier, DisputesState>(DisputesNotifier.new);

// ---------------------------------------------------------------------------
// Stub data
// ---------------------------------------------------------------------------

List<DisputeEntity> _stubDisputes() {
  final now = DateTime.now();
  return [
    DisputeEntity(
      id: 'D-2025-001',
      orderId: 'FKP-882214',
      marketplace: 'Flipkart',
      status: DisputeStatus.accepted,
      claimAmount: 1450.0,
      recoveredAmount: 1450.0,
      reason: 'Wrong weight slab charged — 2 kg billed instead of 0.5 kg',
      createdAt: now.subtract(const Duration(days: 12)),
      updatedAt: now.subtract(const Duration(hours: 5)),
      evidence: ['weight_certificate.pdf', 'order_invoice.pdf'],
      notes: 'Flipkart confirmed wrong weight slab. Full amount approved.',
    ),
    DisputeEntity(
      id: 'D-2025-002',
      orderId: 'AMZ-991234',
      marketplace: 'Amazon',
      status: DisputeStatus.inReview,
      claimAmount: 3200.0,
      recoveredAmount: 0,
      reason: 'Return received damaged — full refund issued to customer but item unusable',
      createdAt: now.subtract(const Duration(days: 8)),
      updatedAt: now.subtract(const Duration(days: 2)),
      evidence: ['damage_photos.jpg', 'return_receipt.pdf'],
    ),
    DisputeEntity(
      id: 'D-2025-003',
      orderId: 'MEE-773491',
      marketplace: 'Meesho',
      status: DisputeStatus.submitted,
      claimAmount: 890.0,
      recoveredAmount: 0,
      reason: 'Settlement deduction not matching order-level fees',
      createdAt: now.subtract(const Duration(days: 5)),
      updatedAt: now.subtract(const Duration(days: 5)),
    ),
    DisputeEntity(
      id: 'D-2025-004',
      orderId: 'FKP-654001',
      marketplace: 'Flipkart',
      status: DisputeStatus.rejected,
      claimAmount: 2100.0,
      recoveredAmount: 0,
      reason: 'Commission overcharge on high-value order',
      createdAt: now.subtract(const Duration(days: 20)),
      updatedAt: now.subtract(const Duration(days: 15)),
      notes: 'Rejected — commission matched platform policy. Consider appeal.',
    ),
    DisputeEntity(
      id: 'D-2025-005',
      orderId: 'AMZ-445882',
      marketplace: 'Amazon',
      status: DisputeStatus.recovered,
      claimAmount: 5600.0,
      recoveredAmount: 5600.0,
      reason: 'Duplicate deduction on Prime Day settlement',
      createdAt: now.subtract(const Duration(days: 30)),
      updatedAt: now.subtract(const Duration(days: 22)),
      evidence: ['settlement_report.xlsx', 'reconciliation.pdf'],
      notes: 'Full recovery received in next settlement cycle.',
    ),
    DisputeEntity(
      id: 'D-2025-006',
      orderId: 'FKP-901177',
      marketplace: 'Flipkart',
      status: DisputeStatus.draft,
      claimAmount: 720.0,
      recoveredAmount: 0,
      reason: 'Storage fee charged for warehouse that was emptied on 1 May',
      createdAt: now.subtract(const Duration(days: 1)),
      updatedAt: now.subtract(const Duration(days: 1)),
    ),
  ];
}
