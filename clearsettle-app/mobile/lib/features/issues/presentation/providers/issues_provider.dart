import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../shared/widgets/priority_badge.dart';
import '../../domain/entities/issue_entity.dart';

class IssuesNotifier extends Notifier<IssuesState> {
  @override
  IssuesState build() {
    // Seed with mock data — replace with real API call when backend ready
    Future.microtask(_load);
    return const IssuesState(isLoading: true);
  }

  Future<void> _load() async {
    state = state.copyWith(isLoading: true);
    try {
      await Future.delayed(const Duration(milliseconds: 600));
      state = state.copyWith(
        issues: _mockIssues,
        isLoading: false,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: 'Could not load issues. Pull to refresh.',
      );
    }
  }

  Future<void> refresh() => _load();

  void setFilter(IssueFilter filter) =>
      state = state.copyWith(filter: filter);

  void setSortByImpact({required bool high}) =>
      state = state.copyWith(sortByImpact: high);
}

final issuesProvider =
    NotifierProvider<IssuesNotifier, IssuesState>(IssuesNotifier.new);

/// Exposes unresolved issue count for the bottom nav badge.
final issueCountProvider = Provider<int>((ref) {
  return ref.watch(issuesProvider).issues.length;
});

// ── Mock data (replace with remote datasource) ────────────────────────────────

final _mockIssues = <IssueEntity>[
  IssueEntity(
    id: '1',
    marketplace: 'Amazon',
    marketplaceId: 'amazon',
    type: IssueType.missingPayment,
    amount: 8420,
    detailLabel: 'Order ID',
    detailValue: '405-857Sxxxx',
    detectedAt: DateTime(2025, 5, 15),
    priority: IssuePriority.high,
  ),
  IssueEntity(
    id: '2',
    marketplace: 'Flipkart',
    marketplaceId: 'flipkart',
    type: IssueType.excessFee,
    amount: 2143,
    detailLabel: 'Fee Type',
    detailValue: 'Shipping Fee',
    detectedAt: DateTime(2025, 5, 14),
    priority: IssuePriority.medium,
  ),
  IssueEntity(
    id: '3',
    marketplace: 'Meesho',
    marketplaceId: 'meesho',
    type: IssueType.missingPayment,
    amount: 5680,
    detailLabel: 'Order ID',
    detailValue: '123456xxxx',
    detectedAt: DateTime(2025, 5, 13),
    priority: IssuePriority.high,
  ),
  IssueEntity(
    id: '4',
    marketplace: 'Amazon',
    marketplaceId: 'amazon',
    type: IssueType.excessFee,
    amount: 1920,
    detailLabel: 'Fee Type',
    detailValue: 'Referral Fee',
    detectedAt: DateTime(2025, 5, 12),
    priority: IssuePriority.low,
  ),
  IssueEntity(
    id: '5',
    marketplace: 'Myntra',
    marketplaceId: 'myntra',
    type: IssueType.pendingClaim,
    amount: 3200,
    detailLabel: 'Claim ID',
    detailValue: 'CLM-789xxxx',
    detectedAt: DateTime(2025, 5, 10),
    priority: IssuePriority.medium,
  ),
  IssueEntity(
    id: '6',
    marketplace: 'Flipkart',
    marketplaceId: 'flipkart',
    type: IssueType.pendingClaim,
    amount: 4270,
    detailLabel: 'Claim ID',
    detailValue: 'CLM-456xxxx',
    detectedAt: DateTime(2025, 5, 8),
    priority: IssuePriority.high,
  ),
];
