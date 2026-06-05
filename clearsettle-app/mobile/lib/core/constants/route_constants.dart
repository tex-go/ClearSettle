abstract final class RouteConstants {
  // ── Auth ──────────────────────────────────────────────────────────────────
  static const String splash            = '/';
  static const String login             = '/login';
  static const String register          = '/register';
  static const String forgotPassword    = '/forgot-password';
  static const String socialOnboarding  = '/social-onboarding';

  // ── Shell (bottom-nav) tabs ───────────────────────────────────────────────
  static const String dashboard   = '/dashboard';
  static const String settlements = '/settlements';
  static const String alerts      = '/alerts';
  static const String disputes    = '/disputes';
  static const String settings    = '/settings';

  // ── Full-screen modals ────────────────────────────────────────────────────
  static const String search = '/search';

  // ── Finance ───────────────────────────────────────────────────────────────
  static const String bankReconciliation = '/bank-reconciliation';
  static const String returns            = '/returns';
  static const String commissionAudit    = '/commission-audit';
  static const String cashFlow           = '/cash-flow';

  // ── Operations ────────────────────────────────────────────────────────────
  static const String connectors    = '/connectors';
  static const String profitability = '/profitability';
  static const String inventorySync = '/inventory-sync';

  // ── Compliance / GST ─────────────────────────────────────────────────────
  static const String gst               = '/gst';
  static const String gstr1             = '/gst/gstr1';
  static const String gstr3b            = '/gst/gstr3b';
  static const String gstReconciliation = '/gst/reconciliation';
  static const String gstSummary        = '/gst/summary';

  // ── Intelligence ──────────────────────────────────────────────────────────
  static const String disputeRules     = '/dispute-rules';
  static const String anomalyDetection = '/anomaly-detection';
  static const String aiInsights       = '/ai-insights';

  // ── Administration ────────────────────────────────────────────────────────
  static const String connectedPlatforms = '/settings/connected-platforms';
  static const String analytics          = '/settings/analytics';
  static const String helpCenter         = '/help';

  // ── Upload Center / Reconciliation ────────────────────────────────────────
  static const String uploadCenter    = '/reports';          // reuses reports
  static const String reconciliation  = '/reconciliation';

  // ── Coming Soon ───────────────────────────────────────────────────────────
  static const String comingSoon = '/coming-soon';
  static String comingSoonPath(String feature) => '/coming-soon/$feature';

  // ── Settlement detail ─────────────────────────────────────────────────────
  static const String settlementDetail = '/settlements/:id';
  static String settlementDetailPath(String id) => '/settlements/$id';

  // ── Dispute detail ────────────────────────────────────────────────────────
  static const String disputeDetail = '/disputes/:id';
  static String disputeDetailPath(String id) => '/disputes/$id';

  // ── Report routes ─────────────────────────────────────────────────────────
  static const String reports                = '/reports';
  static const String reportDetail           = '/reports/:reportId';
  static const String reportSettlementDetail = '/reports/:reportId/settlement';
  static const String reconciliationSummary  = '/reports/:reportId/reconciliation';
  static String reportDetailPath(String id)     => '/reports/$id';
  static String reportSettlementPath(String id) => '/reports/$id/settlement';
  static String reconciliationPath(String id)   => '/reports/$id/reconciliation';
}
