import 'package:equatable/equatable.dart';

enum PayoutStatus { paid, pending, failed }

class PayoutEntity extends Equatable {
  const PayoutEntity({
    required this.id,
    required this.date,
    required this.amount,
    required this.status,
    this.marketplace,
  });

  final String id;
  final DateTime date;
  final double amount;
  final PayoutStatus status;
  final String? marketplace;

  @override
  List<Object?> get props => [id];
}

class PayoutsState extends Equatable {
  const PayoutsState({
    this.nextPayoutAmount = 0,
    this.nextPayoutDate,
    this.history = const [],
    this.isLoading = false,
    this.error,
  });

  final double nextPayoutAmount;
  final DateTime? nextPayoutDate;
  final List<PayoutEntity> history;
  final bool isLoading;
  final String? error;

  PayoutsState copyWith({
    double? nextPayoutAmount,
    DateTime? nextPayoutDate,
    List<PayoutEntity>? history,
    bool? isLoading,
    String? error,
  }) =>
      PayoutsState(
        nextPayoutAmount: nextPayoutAmount ?? this.nextPayoutAmount,
        nextPayoutDate: nextPayoutDate ?? this.nextPayoutDate,
        history: history ?? this.history,
        isLoading: isLoading ?? this.isLoading,
        error: error,
      );

  @override
  List<Object?> get props =>
      [nextPayoutAmount, nextPayoutDate, history, isLoading, error];
}
