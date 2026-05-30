sealed class SearchResult {
  const SearchResult();

  String get id;
  String get title;
  String get subtitle;
  String get resultType;
}

final class ReportSearchResult extends SearchResult {
  const ReportSearchResult({
    required this.id,
    required this.fileName,
    required this.marketplace,
    required this.uploadedAt,
    required this.status,
  });

  @override
  final String id;
  final String fileName;
  final String marketplace;
  final String uploadedAt;
  final String status;

  @override
  String get title => fileName;
  @override
  String get subtitle => '${marketplace.toUpperCase()} · $uploadedAt';
  @override
  String get resultType => 'report';
}

final class DiscrepancySearchResult extends SearchResult {
  const DiscrepancySearchResult({
    required this.id,
    required this.reportId,
    required this.orderId,
    required this.discrepancyType,
    required this.severity,
  });

  @override
  final String id;
  final String reportId;
  final String? orderId;
  final String discrepancyType;
  final String severity;

  @override
  String get title => orderId != null ? 'Order $orderId' : discrepancyType;
  @override
  String get subtitle => '$discrepancyType · $severity';
  @override
  String get resultType => 'discrepancy';
}
