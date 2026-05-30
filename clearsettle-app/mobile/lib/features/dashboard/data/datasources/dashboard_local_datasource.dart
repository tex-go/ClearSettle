import 'dart:convert';

import '../../../../storage/hive_manager.dart';
import '../../domain/entities/dashboard_summary_entity.dart';
import '../models/dashboard_summary_model.dart';

class DashboardLocalDataSource {
  static const String _cacheKey = 'dashboard_summary';

  Future<void> cacheSummary(DashboardSummary summary) async {
    final model = DashboardSummaryModel.fromEntity(summary);
    final box = HiveManager.settingsBox;
    // Store serialized JSON under a reserved key in settings box
    await box.put(_cacheKey, _encode(model.toJson()));
  }

  Future<DashboardSummary?> getCachedSummary() {
    final box = HiveManager.settingsBox;
    final raw = box.get(_cacheKey);
    if (raw == null) return Future.value();

    try {
      final json = _decode(raw.toString());
      return Future.value(
        DashboardSummaryModel.fromJson(json).toEntity(isFromCache: true),
      );
    } catch (_) {
      return Future.value();
    }
  }

  String _encode(Map<String, dynamic> json) => jsonEncode(json);

  Map<String, dynamic> _decode(String raw) =>
      jsonDecode(raw) as Map<String, dynamic>;
}
