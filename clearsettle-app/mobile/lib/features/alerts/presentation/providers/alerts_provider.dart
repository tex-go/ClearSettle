import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../domain/entities/alert_entity.dart';

// ---------------------------------------------------------------------------
// State
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
  @override
  AlertsState build() {
    Future.microtask(load);
    return const AlertsState(alerts: [], isLoading: true);
  }

  Future<void> load() async {
    state = state.copyWith(isLoading: true, error: null);
    // Stub data — replace with real API call when backend implements /alerts
    await Future.delayed(const Duration(milliseconds: 600));
    state = state.copyWith(isLoading: false, alerts: _stubAlerts());
  }

  void markRead(String id) {
    state = state.copyWith(
      alerts: state.alerts
          .map((a) => a.id == id ? a.copyWith(isRead: true) : a)
          .toList(),
    );
  }

  void markAllRead() {
    state = state.copyWith(
      alerts: state.alerts.map((a) => a.copyWith(isRead: true)).toList(),
    );
  }

  Future<void> refresh() => load();
}

final alertsProvider =
    NotifierProvider<AlertsNotifier, AlertsState>(AlertsNotifier.new);

// Derived count for badge overlay
final unreadAlertCountProvider = Provider<int>((ref) {
  return ref.watch(alertsProvider).unreadCount;
});

// ---------------------------------------------------------------------------
// Stub data
// ---------------------------------------------------------------------------

List<AlertEntity> _stubAlerts() {
  final now = DateTime.now();
  return [
    AlertEntity(
      id: '1',
      type: AlertType.settlementMismatch,
      severity: AlertSeverity.critical,
      title: 'Settlement Mismatch Detected',
      message: 'Flipkart settlement #FK-2025-0598 shows ₹4,320 less than expected.',
      marketplace: 'Flipkart',
      createdAt: now.subtract(const Duration(minutes: 35)),
      isRead: false,
      actionRoute: '/settlements',
    ),
    AlertEntity(
      id: '2',
      type: AlertType.highDeduction,
      severity: AlertSeverity.warning,
      title: 'High Commission Deduction',
      message: 'Amazon deducted ₹12,800 in commissions — 22% higher than last month.',
      marketplace: 'Amazon',
      createdAt: now.subtract(const Duration(hours: 2)),
      isRead: false,
      actionRoute: '/settlements',
    ),
    AlertEntity(
      id: '3',
      type: AlertType.disputeUpdate,
      severity: AlertSeverity.info,
      title: 'Dispute Accepted',
      message: 'Your dispute for order #FKP-882214 was accepted. ₹1,450 will be recovered.',
      marketplace: 'Flipkart',
      createdAt: now.subtract(const Duration(hours: 5)),
      isRead: false,
      actionRoute: '/disputes',
    ),
    AlertEntity(
      id: '4',
      type: AlertType.settlementDelay,
      severity: AlertSeverity.warning,
      title: 'Settlement Delayed',
      message: 'Meesho settlement cycle for 24–30 May is 3 days overdue.',
      marketplace: 'Meesho',
      createdAt: now.subtract(const Duration(days: 1)),
      isRead: true,
      actionRoute: '/settlements',
    ),
    AlertEntity(
      id: '5',
      type: AlertType.syncFailure,
      severity: AlertSeverity.critical,
      title: 'Sync Failed',
      message: 'Amazon data sync failed at 02:15. Retry scheduled in 30 minutes.',
      marketplace: 'Amazon',
      createdAt: now.subtract(const Duration(days: 1, hours: 3)),
      isRead: true,
    ),
    AlertEntity(
      id: '6',
      type: AlertType.settlementMismatch,
      severity: AlertSeverity.warning,
      title: 'Partial Settlement Received',
      message: 'Shopify settlement #SH-1023 partially received — ₹8,200 of ₹11,500 expected.',
      marketplace: 'Shopify',
      createdAt: now.subtract(const Duration(days: 2)),
      isRead: true,
      actionRoute: '/settlements',
    ),
  ];
}
