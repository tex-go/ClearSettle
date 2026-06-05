import 'package:equatable/equatable.dart';

import '../../../../shared/widgets/priority_badge.dart';

enum IssueType { missingPayment, excessFee, pendingClaim }

class IssueEntity extends Equatable {
  const IssueEntity({
    required this.id,
    required this.marketplace,
    required this.marketplaceId,
    required this.type,
    required this.amount,
    required this.detailLabel,
    required this.detailValue,
    required this.detectedAt,
    required this.priority,
  });

  final String id;
  final String marketplace;
  final String marketplaceId;  // 'amazon' | 'flipkart' | 'meesho' | 'myntra'
  final IssueType type;
  final double amount;
  final String detailLabel;
  final String detailValue;
  final DateTime detectedAt;
  final IssuePriority priority;

  String get typeLabel => switch (type) {
        IssueType.missingPayment => 'Missing Payment',
        IssueType.excessFee      => 'Excess Fee',
        IssueType.pendingClaim   => 'Pending Claim',
      };

  @override
  List<Object?> get props => [id];
}

class IssuesState extends Equatable {
  const IssuesState({
    this.issues = const [],
    this.filter = IssueFilter.all,
    this.sortByImpact = true,
    this.isLoading = false,
    this.error,
  });

  final List<IssueEntity> issues;
  final IssueFilter filter;
  final bool sortByImpact;
  final bool isLoading;
  final String? error;

  double get totalImpact =>
      filteredIssues.fold(0.0, (sum, i) => sum + i.amount);

  List<IssueEntity> get filteredIssues {
    var list = switch (filter) {
      IssueFilter.all          => issues,
      IssueFilter.missing      => issues.where((i) => i.type == IssueType.missingPayment).toList(),
      IssueFilter.excessFee    => issues.where((i) => i.type == IssueType.excessFee).toList(),
      IssueFilter.pendingClaim => issues.where((i) => i.type == IssueType.pendingClaim).toList(),
    };
    if (sortByImpact) {
      list = [...list]..sort((a, b) => b.amount.compareTo(a.amount));
    }
    return list;
  }

  int countFor(IssueFilter f) => switch (f) {
        IssueFilter.all          => issues.length,
        IssueFilter.missing      => issues.where((i) => i.type == IssueType.missingPayment).length,
        IssueFilter.excessFee    => issues.where((i) => i.type == IssueType.excessFee).length,
        IssueFilter.pendingClaim => issues.where((i) => i.type == IssueType.pendingClaim).length,
      };

  IssuesState copyWith({
    List<IssueEntity>? issues,
    IssueFilter? filter,
    bool? sortByImpact,
    bool? isLoading,
    String? error,
  }) =>
      IssuesState(
        issues: issues ?? this.issues,
        filter: filter ?? this.filter,
        sortByImpact: sortByImpact ?? this.sortByImpact,
        isLoading: isLoading ?? this.isLoading,
        error: error,
      );

  @override
  List<Object?> get props => [issues, filter, sortByImpact, isLoading, error];
}

enum IssueFilter { all, missing, excessFee, pendingClaim }
