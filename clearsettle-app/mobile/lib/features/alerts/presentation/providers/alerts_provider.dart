import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/errors/exceptions.dart';
import '../../../../core/network/api_client.dart';
import '../../domain/entities/alert_entity.dart';

// ---------------------------------------------------------------------------
// Local read/unread state (backend doesn't store it — managed on device)
// ---------------------------------------------------------------------------

class AlertsState {
  const AlertsState({
    required this.alerts,
    required this.isLoading,
    this.error,
  });

  final List<AlertEntity> alerts;
  final bool isLoading;
  final String? error;

  int get unreadCount => alerts.where((a) => !a.isRead).length;

  AlertsState copyWith({
    List<AlertEntity>? alerts,
    bool? isLoading,
    String? error,
  }) =>
      AlertsState(
        alerts: alerts ?? this.alerts,
        isLoading: isLoading ?? this.isLoading,
        error: error,
      );
}

// ---------------------------------------------------------------------------
// Notifier
// ---------------------------------------------------------------------------

class AlertsNotifier extends Notifier<AlertsState> {
  // IDs acknowledged by the user in this session (persisted in memory only)
  final Set<String> _readIds = {};

  @override
  AlertsState build() {
    Future.microtask(load);
    return const AlertsState(alerts: [], isLoading: true);
  }

  Future<void> load() async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      final client = ref.read(apiClientProvider);
      final resp = await client.get<dynamic>('/dashboard/notifications');

      final raw = resp.data;
      List<dynamic> list;

      if (raw is List) {
        list = raw;
      } else if (raw is Map && raw.containsKey('items')) {
        list = (raw['items'] as List? ?? []);
      } else {
        list = [];
      }

      final alerts = list
          .cast<Map<String, dynamic>>()
          .asMap()
          .entries
          .map((entry) => _fromJson(entry.key, entry.value, _readIds))
          .toList();

      state = state.copyWith(isLoading: false, alerts: alerts);
    } on NetworkException {
      state = state.copyWith(
          isLoading: false,
          error: 'Cannot reach the server.');
    } on UnauthorizedException {
      state = state.copyWith(isLoading: false, error: 'Session expired.');
    } catch (e) {
      state = state.copyWith(
          isLoading: false,
          error: 'Could not load notifications.');
    }
  }

  void markRead(String id) {
    _readIds.add(id);
    state = state.copyWith(
      alerts: state.alerts
          .map((a) => a.id == id ? a.copyWith(isRead: true) : a)
          .toList(),
    );
  }

  void markAllRead() {
    for (final a in state.alerts) {
      _readIds.add(a.id);
    }
    state = state.copyWith(
      alerts: state.alerts.map((a) => a.copyWith(isRead: true)).toList(),
    );
  }

  Future<void> refresh() => load();
}

final alertsProvider =
    NotifierProvider<AlertsNotifier, AlertsState>(AlertsNotifier.new);

/// Badge count for bottom-nav overlay
final unreadAlertCountProvider = Provider<int>((ref) {
  return ref.watch(alertsProvider).unreadCount;
});

// ---------------------------------------------------------------------------
// JSON mapping — backend /dashboard/notifications response
// ---------------------------------------------------------------------------

AlertEntity _fromJson(
    int index, Map<String, dynamic> j, Set<String> readIds) {
  final id       = (j['id'] ?? j['alert_id'] ?? 'alert_$index').toString();
  final typeStr  = (j['type'] ?? j['alert_type'] ?? '').toString().toLowerCase();
  final sevStr   = (j['severity'] ?? j['level'] ?? 'info').toString().toLowerCase();
  final title    = (j['title'] ?? j['message'] ?? _titleFromType(typeStr)).toString();
  final body     = (j['body'] ?? j['description'] ?? j['message'] ?? '').toString();
  final platform = (j['platform'] ?? j['marketplace'] ?? '').toString();
  final createdAt = _parseDate(j['created_at']);

  return AlertEntity(
    id: id,
    type: _alertType(typeStr),
    severity: _severity(sevStr),
    title: title,
    message: body.isNotEmpty ? body : title,
    marketplace: _normalisePlatform(platform),
    createdAt: createdAt,
    isRead: readIds.contains(id),
    actionRoute: _actionRoute(typeStr),
  );
}

AlertType _alertType(String t) {
  if (t.contains('mismatch') || t.contains('settlement')) return AlertType.settlementMismatch;
  if (t.contains('deduction') || t.contains('fee') || t.contains('loss')) return AlertType.highDeduction;
  if (t.contains('delay') || t.contains('pending')) return AlertType.settlementDelay;
  if (t.contains('dispute') || t.contains('recon')) return AlertType.disputeUpdate;
  if (t.contains('sync') || t.contains('fail') || t.contains('error')) return AlertType.syncFailure;
  return AlertType.settlementMismatch;
}

AlertSeverity _severity(String s) => switch (s) {
      'critical' || 'high'   => AlertSeverity.critical,
      'warning' || 'medium'  => AlertSeverity.warning,
      _                      => AlertSeverity.info,
    };

String? _actionRoute(String t) {
  if (t.contains('dispute') || t.contains('recon')) return '/disputes';
  if (t.contains('settlement') || t.contains('payout')) return '/settlements';
  return null;
}

String _titleFromType(String t) {
  if (t.contains('mismatch'))  return 'Settlement Mismatch Detected';
  if (t.contains('dispute'))   return 'Dispute Update';
  if (t.contains('recon'))     return 'Reconciliation Issue';
  if (t.contains('sync'))      return 'Sync Failed';
  if (t.contains('pending'))   return 'Settlement Pending';
  return 'New Notification';
}

String _normalisePlatform(String p) => switch (p.toLowerCase()) {
      'flipkart' => 'Flipkart',
      'amazon'   => 'Amazon',
      'meesho'   => 'Meesho',
      'shopify'  => 'Shopify',
      _          => p.isNotEmpty ? '${p[0].toUpperCase()}${p.substring(1)}' : 'Platform',
    };

DateTime _parseDate(dynamic v) {
  if (v == null) return DateTime.now();
  try { return DateTime.parse(v.toString()); } catch (_) { return DateTime.now(); }
}
