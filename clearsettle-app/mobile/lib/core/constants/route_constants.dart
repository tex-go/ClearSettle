abstract final class RouteConstants {
  static const String login = '/login';
  static const String dashboard = '/dashboard';
  static const String reports = '/reports';
  static const String reportDetail = '/reports/:reportId';
  static const String settlementDetail = '/reports/:reportId/settlement';
  static const String reconciliationSummary = '/reports/:reportId/reconciliation';
  static const String analytics = '/analytics';
  static const String settings = '/settings';
  static const String search = '/search';

  static String reportDetailPath(String reportId) => '/reports/$reportId';
  static String settlementDetailPath(String reportId) => '/reports/$reportId/settlement';
  static String reconciliationPath(String reportId) => '/reports/$reportId/reconciliation';
}
