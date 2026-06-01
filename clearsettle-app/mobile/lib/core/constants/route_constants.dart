abstract final class RouteConstants {
  // ── Auth ──────────────────────────────────────────────────────────────────
  static const String splash         = '/';
  static const String login          = '/login';
  static const String forgotPassword = '/forgot-password';

  // ── Shell (bottom-nav) tabs ───────────────────────────────────────────────
  static const String dashboard   = '/dashboard';
  static const String settlements = '/settlements';
  static const String alerts      = '/alerts';
  static const String disputes    = '/disputes';
  static const String settings    = '/settings';

  // ── Nested under Dashboard ────────────────────────────────────────────────
  static const String search = '/search';

  // ── Nested under Settlements ──────────────────────────────────────────────
  static const String settlementDetail = '/settlements/:id';
  static String settlementDetailPath(String id) => '/settlements/$id';

  // ── Nested under Disputes ─────────────────────────────────────────────────
  static const String disputeDetail = '/disputes/:id';
  static String disputeDetailPath(String id) => '/disputes/$id';

  // ── Nested under Settings ─────────────────────────────────────────────────
  static const String connectedPlatforms = '/settings/connected-platforms';

  // ── Legacy report routes (kept for Reports feature in Settings) ───────────
  static const String reports               = '/reports';
  static const String reportDetail          = '/reports/:reportId';
  static const String reportSettlementDetail = '/reports/:reportId/settlement';
  static const String reconciliationSummary  = '/reports/:reportId/reconciliation';
  static String reportDetailPath(String reportId)  => '/reports/$reportId';
  static String reportSettlementPath(String id)    => '/reports/$id/settlement';
  static String reconciliationPath(String id)      => '/reports/$id/reconciliation';
}
