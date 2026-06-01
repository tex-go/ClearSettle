import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/errors/exceptions.dart';
import '../../../../core/network/api_client.dart';
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
    this.totalClaimAmount = 0,
    this.totalRecoveredAmount = 0,
    this.error,
  });

  final List<DisputeEntity> disputes;
  final bool isLoading;
  final DisputeStatus? filterStatus;
  final String? filterMarketplace;
  final double totalClaimAmount;
  final double totalRecoveredAmount;
  final String? error;

  List<DisputeEntity> get filtered {
    var list = disputes;
    if (filterStatus != null) {
      list = list.where((d) => d.status == filterStatus).toList();
    }
    if (filterMarketplace != null && filterMarketplace!.isNotEmpty) {
      list = list.where((d) =>
          d.marketplace.toLowerCase() == filterMarketplace!.toLowerCase()).toList();
    }
    return list;
  }

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
    double? totalClaimAmount,
    double? totalRecoveredAmount,
    String? error,
  }) =>
      DisputesState(
        disputes: disputes ?? this.disputes,
        isLoading: isLoading ?? this.isLoading,
        filterStatus:
            clearFilterStatus ? null : (filterStatus ?? this.filterStatus),
        filterMarketplace: filterMarketplace ?? this.filterMarketplace,
        totalClaimAmount: totalClaimAmount ?? this.totalClaimAmount,
        totalRecoveredAmount:
            totalRecoveredAmount ?? this.totalRecoveredAmount,
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
    try {
      final client = ref.read(apiClientProvider);
      final resp = await client.get<Map<String, dynamic>>(
        '/disputes/',
        queryParameters: {'size': 50, 'page': 1},
      );

      final data = resp.data;
      if (data == null) throw const ServerException(message: 'Empty response');

      final items = (data['items'] as List? ?? [])
          .cast<Map<String, dynamic>>()
          .map(_fromJson)
          .toList();

      final summary = data['summary'] as Map<String, dynamic>? ?? {};
      final totalAmount  = _d(summary['total_amount']);
      final wonAmount    = _d(summary['won_amount']);

      state = state.copyWith(
        isLoading: false,
        disputes: items,
        totalClaimAmount: totalAmount,
        totalRecoveredAmount: wonAmount,
      );
    } on NetworkException {
      state = state.copyWith(
          isLoading: false,
          error: 'Cannot reach the server. Check your connection.');
    } on UnauthorizedException {
      state = state.copyWith(isLoading: false, error: 'Session expired.');
    } catch (e) {
      state = state.copyWith(
          isLoading: false,
          error: 'Could not load disputes. Please try again.');
    }
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
// JSON mapping — backend /disputes/ response
// ---------------------------------------------------------------------------

DisputeEntity _fromJson(Map<String, dynamic> j) {
  return DisputeEntity(
    id: (j['id'] ?? '').toString(),
    orderId: (j['order_id'] ?? j['external_id'] ?? '—').toString(),
    marketplace: _normalisePlatform(
        (j['platform'] as String?) ?? (j['marketplace'] as String?) ?? ''),
    status: _statusFromBackend(
        (j['workflow_state'] as String?) ?? 'detected'),
    claimAmount: _d(j['variance_amount'] ?? j['claim_amount'] ?? 0),
    recoveredAmount: _d(j['resolved_amount'] ?? j['recovered_amount'] ?? 0),
    reason: (j['discrepancy_type'] as String?)
            ?.replaceAll('_', ' ')
            .toLowerCase()
            .split(' ')
            .map((w) => w.isNotEmpty
                ? '${w[0].toUpperCase()}${w.substring(1)}'
                : w)
            .join(' ') ??
        (j['reason'] as String?) ??
        'Discrepancy detected',
    createdAt: _parseDate(j['created_at']),
    updatedAt: _parseDate(j['updated_at'] ?? j['created_at']),
    notes: (j['resolution_note'] ?? j['notes']) as String?,
  );
}

DisputeStatus _statusFromBackend(String s) => switch (s.toLowerCase()) {
      'detected'                  => DisputeStatus.submitted,
      'reviewed'                  => DisputeStatus.inReview,
      'filed' || 'acknowledged'   => DisputeStatus.inReview,
      'resolved'                  => DisputeStatus.recovered,
      'rejected' || 'dismissed'   => DisputeStatus.rejected,
      'draft'                     => DisputeStatus.draft,
      _                           => DisputeStatus.submitted,
    };

String _normalisePlatform(String p) => switch (p.toLowerCase()) {
      'flipkart' => 'Flipkart',
      'amazon'   => 'Amazon',
      'meesho'   => 'Meesho',
      'shopify'  => 'Shopify',
      _          => p.isNotEmpty ? '${p[0].toUpperCase()}${p.substring(1)}' : 'Unknown',
    };

double _d(dynamic v) => (v as num?)?.toDouble() ?? 0.0;

DateTime _parseDate(dynamic v) {
  if (v == null) return DateTime.now();
  try { return DateTime.parse(v.toString()); } catch (_) { return DateTime.now(); }
}
