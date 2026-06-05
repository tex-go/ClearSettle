abstract final class ApiEndpoints {
  // ── Auth ──────────────────────────────────────────────────────────────────
  static const String login          = '/auth/login';
  static const String logout         = '/auth/logout';
  static const String me             = '/auth/me';
  static const String refreshToken   = '/auth/refresh';
  static const String forgotPassword = '/auth/forgot-password';
  static const String register       = '/auth/register';
  static const String authRoles      = '/auth/roles';
  static const String checkEmail     = '/auth/check-email';
  static const String acceptInvite   = '/auth/accept-invite';

  // ── Social Auth ───────────────────────────────────────────────────────────
  static const String googleLogin       = '/auth/google';
  static const String instagramLogin    = '/auth/instagram';
  static const String socialAccounts    = '/auth/social';
  static String unlinkSocial(String provider) => '/auth/social/$provider';

  // ── Dashboard ─────────────────────────────────────────────────────────────
  static const String dashboardSummary = '/dashboard/summary';

  // ── Settlements ───────────────────────────────────────────────────────────
  static const String settlements      = '/settlements';
  static String settlementById(String id) => '/settlements/$id';

  // ── Alerts ────────────────────────────────────────────────────────────────
  static const String alerts          = '/alerts';
  static const String alertsMarkRead  = '/alerts/mark-read';
  static const String alertsMarkAll   = '/alerts/mark-all-read';

  // ── Disputes ──────────────────────────────────────────────────────────────
  static const String disputes         = '/disputes';
  static String disputeById(String id) => '/disputes/$id';

  // ── Reports ───────────────────────────────────────────────────────────────
  static const String reports      = '/reports';
  static const String reportUpload = '/reports/upload';

  // ── Ingestion (14-agent intelligent pipeline) ─────────────────────────────
  static const String ingestionUpload   = '/ingestion/upload';
  static const String ingestionFiles    = '/ingestion/files';
  static String ingestionFile(String id)          => '/ingestion/files/$id';
  static String ingestionLogs(String id)          => '/ingestion/files/$id/logs';
  static String ingestionSummary(String id)       => '/ingestion/files/$id/summary';
  static String ingestionReconciliation(String id) => '/ingestion/files/$id/reconciliation';
  static String ingestionIntelligence(String id)  => '/ingestion/files/$id/intelligence';
  static String ingestionReprocess(String id)     => '/ingestion/files/$id/reprocess';
  static String ingestionReport(String id)        => '/ingestion/files/$id/report';

  // ── Marketplace ───────────────────────────────────────────────────────────
  static const String marketplaceList        = '/marketplace/';
  static const String marketplaceConnections = '/marketplace/connections/';
}
