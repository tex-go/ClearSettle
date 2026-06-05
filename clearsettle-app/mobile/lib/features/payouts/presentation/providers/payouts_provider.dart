import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../domain/entities/payout_entity.dart';

class PayoutsNotifier extends Notifier<PayoutsState> {
  @override
  PayoutsState build() {
    Future.microtask(_load);
    return const PayoutsState(isLoading: true);
  }

  Future<void> _load() async {
    state = state.copyWith(isLoading: true);
    try {
      await Future.delayed(const Duration(milliseconds: 500));
      state = state.copyWith(
        nextPayoutAmount: 245800,
        nextPayoutDate: DateTime(2025, 5, 20),
        history: _mockHistory,
        isLoading: false,
      );
    } catch (e) {
      state = state.copyWith(
          isLoading: false, error: 'Could not load payouts.');
    }
  }

  Future<void> refresh() => _load();
}

final payoutsProvider =
    NotifierProvider<PayoutsNotifier, PayoutsState>(PayoutsNotifier.new);

// ── Mock payout history ───────────────────────────────────────────────────────

final _mockHistory = <PayoutEntity>[
  PayoutEntity(id: '1', date: DateTime(2025, 5, 15),
      amount: 235640, status: PayoutStatus.paid),
  PayoutEntity(id: '2', date: DateTime(2025, 5, 8),
      amount: 228950, status: PayoutStatus.paid),
  PayoutEntity(id: '3', date: DateTime(2025, 5, 1),
      amount: 215430, status: PayoutStatus.paid),
  PayoutEntity(id: '4', date: DateTime(2025, 4, 24),
      amount: 201860, status: PayoutStatus.paid),
  PayoutEntity(id: '5', date: DateTime(2025, 4, 17),
      amount: 195620, status: PayoutStatus.paid),
  PayoutEntity(id: '6', date: DateTime(2025, 4, 10),
      amount: 188340, status: PayoutStatus.paid),
];
