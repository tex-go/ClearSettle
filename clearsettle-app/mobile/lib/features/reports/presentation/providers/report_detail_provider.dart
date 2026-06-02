import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../domain/entities/report_entities.dart';
import '../../domain/usecases/get_report_detail_usecase.dart';
import 'reports_provider.dart';

final reportDetailProvider = AsyncNotifierProviderFamily<
    ReportDetailNotifier, ReportDetail, String>(
  ReportDetailNotifier.new,
);

class ReportDetailNotifier
    extends FamilyAsyncNotifier<ReportDetail, String> {
  @override
  Future<ReportDetail> build(String reportId) async {
    final repo = ref.read(reportRepositoryProvider);
    final useCase = GetReportDetailUseCase(repo);
    return useCase(reportId);
  }

  Future<void> refresh() async {
    state = const AsyncValue.loading();
    state = await AsyncValue.guard(() => build(arg));
  }
}
