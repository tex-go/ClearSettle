import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/errors/exceptions.dart';
import '../../../../core/network/api_client.dart';
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
      list = list.where((s) =>
          s.marketplace.toLowerCase() == filterMarketplace!.toLowerCase()).toList();
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
    try {
      final client = ref.read(apiClientProvider);
      final resp = await client.get<Map<String, dynamic>>(
        '/settlements/',
        queryParameters: {'size': 50, 'page': 1},
      );

      final data = resp.data;
      if (data == null) throw const ServerException(message: 'Empty response');

      final items = (data['items'] as List? ?? [])
          .cast<Map<String, dynamic>>()
          .map(_fromJson)
          .toList();

      state = state.copyWith(isLoading: false, settlements: items);
    } on NetworkException {
      state = state.copyWith(
          isLoading: false,
          error: 'Cannot reach the server. Check your connection.');
    } on UnauthorizedException {
      state = state.copyWith(isLoading: false, error: 'Session expired.');
    } catch (e) {
      state = state.copyWith(
          isLoading: false,
          error: 'Could not load settlements. Please try again.');
    }
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
// JSON mapping — backend /settlements/ response
// ---------------------------------------------------------------------------

SettlementEntity _fromJson(Map<String, dynamic> j) {
  return SettlementEntity(
    id: (j['id'] ?? j['external_id'] ?? '').toString(),
    marketplace: _normalisePlatform(
        (j['platform'] as String?) ?? (j['marketplace'] as String?) ?? ''),
    settlementDate: _parseDate(j['period_end'] ?? j['created_at']),
    expectedAmount: _d(j['total_amount']),
    receivedAmount: _d(j['fund_transfer_amount'] ?? j['net_amount'] ?? 0),
    status: _statusFromBackend(
        (j['status'] as String?) ?? 'pending'),
    notes: j['notes'] as String?,
  );
}

SettlementStatus _statusFromBackend(String s) => switch (s.toLowerCase()) {
      'closed' || 'matched' => SettlementStatus.matched,
      'mismatch'            => SettlementStatus.mismatch,
      'open' || 'pending'   => SettlementStatus.pending,
      'processing' || 'under_investigation' => SettlementStatus.underInvestigation,
      _                     => SettlementStatus.pending,
    };

String _normalisePlatform(String p) {
  return switch (p.toLowerCase()) {
    'flipkart' => 'Flipkart',
    'amazon'   => 'Amazon',
    'meesho'   => 'Meesho',
    'shopify'  => 'Shopify',
    'myntra'   => 'Myntra',
    _          => p.isNotEmpty ? '${p[0].toUpperCase()}${p.substring(1)}' : 'Unknown',
  };
}

double _d(dynamic v) => (v as num?)?.toDouble() ?? 0.0;

DateTime _parseDate(dynamic v) {
  if (v == null) return DateTime.now();
  try { return DateTime.parse(v.toString()); } catch (_) { return DateTime.now(); }
}
