import '../../../../storage/hive_manager.dart';
import '../entities/search_result_entity.dart';

class SearchUseCase {
  List<SearchResult> call(String query) {
    if (query.trim().length < 2) return [];
    final q = query.toLowerCase().trim();
    return [
      ..._searchReports(q),
      ..._searchDiscrepancies(q),
    ];
  }

  List<ReportSearchResult> _searchReports(String q) {
    return HiveManager.localReportBox.values
        .where((r) =>
            r.fileName.toLowerCase().contains(q) ||
            r.id.toLowerCase().contains(q) ||
            r.platform.toLowerCase().contains(q))
        .map((r) => ReportSearchResult(
              id: r.id,
              fileName: r.fileName,
              marketplace: r.platform,
              uploadedAt: r.uploadedAt.split('T').first,
              status: r.status,
            ))
        .toList();
  }

  List<DiscrepancySearchResult> _searchDiscrepancies(String q) {
    return HiveManager.discrepancyBox.values
        .where((d) =>
            (d.orderId?.toLowerCase().contains(q) ?? false) ||
            d.reportId.toLowerCase().contains(q) ||
            d.description.toLowerCase().contains(q) ||
            d.type.toLowerCase().contains(q))
        .map((d) => DiscrepancySearchResult(
              id: d.id,
              reportId: d.reportId,
              orderId: d.orderId,
              discrepancyType: d.type,
              severity: d.severity,
            ))
        .toList();
  }
}
