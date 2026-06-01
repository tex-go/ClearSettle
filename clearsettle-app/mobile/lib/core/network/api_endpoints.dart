abstract final class ApiEndpoints {
  // ── Auth ──────────────────────────────────────────────────────────────────
  static const String login          = '/auth/login';
  static const String logout         = '/auth/logout';
  static const String me             = '/auth/me';
  static const String refreshToken   = '/auth/refresh';
  static const String forgotPassword = '/auth/forgot-password';

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

  // ── Marketplace ───────────────────────────────────────────────────────────
  static const String marketplaceList        = '/marketplace/';
  static const String marketplaceConnections = '/marketplace/connections/';
}
