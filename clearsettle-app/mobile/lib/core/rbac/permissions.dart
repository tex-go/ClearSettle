/// ClearSettle Enterprise RBAC — Permission constants and role matrix.
///
/// Usage:
///   final rbac = ref.watch(rbacProvider);
///   if (rbac.can(Permission.reportsUpload)) { ... }
library clearsettle_rbac;

class Permission {
  Permission._();

  // Dashboard
  static const dashboardView = 'dashboard.view';

  // Reports
  static const reportsView     = 'reports.view';
  static const reportsUpload   = 'reports.upload';
  static const reportsDelete   = 'reports.delete';
  static const reportsDownload = 'reports.download';

  // Reconciliation
  static const reconciliationView   = 'reconciliation.view';
  static const reconciliationRun    = 'reconciliation.run';
  static const reconciliationExport = 'reconciliation.export';

  // Bank Reconciliation
  static const bankReconView = 'bank_reconciliation.view';
  static const bankReconRun  = 'bank_reconciliation.run';

  // Marketplace
  static const marketplaceView       = 'marketplace.view';
  static const marketplaceConnect    = 'marketplace.connect';
  static const marketplaceDisconnect = 'marketplace.disconnect';
  static const marketplaceSync       = 'marketplace.sync';

  // Settlements
  static const settlementsView   = 'settlements.view';
  static const settlementsExport = 'settlements.export';

  // Disputes
  static const disputesView   = 'disputes.view';
  static const disputesCreate = 'disputes.create';
  static const disputesUpdate = 'disputes.update';
  static const disputesClose  = 'disputes.close';

  // GST
  static const gstView    = 'gst.view';
  static const gstFile    = 'gst.file';
  static const gstExport  = 'gst.export';
  static const gstr1View  = 'gstr1.view';
  static const gstr1File  = 'gstr1.file';
  static const gstr3bView = 'gstr3b.view';
  static const gstr3bFile = 'gstr3b.file';

  // AI
  static const aiView     = 'ai.view';
  static const aiGenerate = 'ai.generate';

  // Users
  static const usersView   = 'users.view';
  static const usersCreate = 'users.create';
  static const usersUpdate = 'users.update';
  static const usersDelete = 'users.delete';
  static const rolesAssign = 'roles.assign';

  // Audit
  static const auditView = 'audit.view';

  // Subscription
  static const subscriptionView   = 'subscription.view';
  static const subscriptionManage = 'subscription.manage';

  // Settings
  static const settingsUpdate = 'settings.update';

  // Notifications
  static const notificationsManage = 'notifications.manage';
}

/// Static role → permission mapping (mirrors backend fallback).
const _rolePermissions = <String, Set<String>>{
  'superadmin': {'*'},
  'admin': {
    Permission.dashboardView,
    Permission.reportsView, Permission.reportsUpload, Permission.reportsDelete, Permission.reportsDownload,
    Permission.reconciliationView, Permission.reconciliationRun, Permission.reconciliationExport,
    Permission.bankReconView, Permission.bankReconRun,
    Permission.marketplaceView, Permission.marketplaceConnect, Permission.marketplaceDisconnect, Permission.marketplaceSync,
    Permission.settlementsView, Permission.settlementsExport,
    Permission.disputesView, Permission.disputesCreate, Permission.disputesUpdate, Permission.disputesClose,
    Permission.gstView, Permission.gstFile, Permission.gstExport, Permission.gstr1View, Permission.gstr1File, Permission.gstr3bView, Permission.gstr3bFile,
    Permission.aiView, Permission.aiGenerate,
    Permission.usersView, Permission.usersCreate, Permission.usersUpdate, Permission.usersDelete, Permission.rolesAssign,
    Permission.auditView, Permission.subscriptionView, Permission.subscriptionManage, Permission.settingsUpdate, Permission.notificationsManage,
  },
  'company_admin': {
    Permission.dashboardView,
    Permission.reportsView, Permission.reportsUpload, Permission.reportsDelete, Permission.reportsDownload,
    Permission.reconciliationView, Permission.reconciliationRun, Permission.reconciliationExport,
    Permission.bankReconView, Permission.bankReconRun,
    Permission.marketplaceView, Permission.marketplaceConnect, Permission.marketplaceDisconnect, Permission.marketplaceSync,
    Permission.settlementsView, Permission.settlementsExport,
    Permission.disputesView, Permission.disputesCreate, Permission.disputesUpdate, Permission.disputesClose,
    Permission.gstView, Permission.gstFile, Permission.gstExport, Permission.gstr1View, Permission.gstr1File, Permission.gstr3bView, Permission.gstr3bFile,
    Permission.aiView, Permission.aiGenerate,
    Permission.usersView, Permission.usersCreate, Permission.usersUpdate, Permission.usersDelete, Permission.rolesAssign,
    Permission.auditView, Permission.subscriptionView, Permission.subscriptionManage, Permission.settingsUpdate, Permission.notificationsManage,
  },
  'business_owner': {
    Permission.dashboardView, Permission.reportsView, Permission.reportsDownload,
    Permission.reconciliationView, Permission.bankReconView,
    Permission.marketplaceView, Permission.marketplaceConnect, Permission.marketplaceDisconnect, Permission.marketplaceSync,
    Permission.settlementsView, Permission.settlementsExport,
    Permission.disputesView,
    Permission.gstView, Permission.gstr1View, Permission.gstr3bView,
    Permission.aiView, Permission.aiGenerate,
    Permission.usersView, Permission.auditView, Permission.subscriptionView, Permission.subscriptionManage, Permission.settingsUpdate,
  },
  'finance_manager': {
    Permission.dashboardView, Permission.reportsView, Permission.reportsUpload, Permission.reportsDownload,
    Permission.reconciliationView, Permission.reconciliationRun, Permission.reconciliationExport,
    Permission.bankReconView, Permission.bankReconRun,
    Permission.marketplaceView,
    Permission.settlementsView, Permission.settlementsExport,
    Permission.disputesView, Permission.disputesCreate, Permission.disputesUpdate, Permission.disputesClose,
    Permission.gstView, Permission.gstFile, Permission.gstExport, Permission.gstr1View, Permission.gstr1File, Permission.gstr3bView, Permission.gstr3bFile,
    Permission.aiView, Permission.usersView,
  },
  'accountant': {
    Permission.dashboardView, Permission.reportsView, Permission.reportsUpload, Permission.reportsDownload,
    Permission.reconciliationView, Permission.bankReconView,
    Permission.settlementsView, Permission.disputesView,
    Permission.gstView, Permission.gstr1View, Permission.gstr3bView, Permission.aiView,
  },
  'reconciliation_analyst': {
    Permission.dashboardView, Permission.reportsView, Permission.reportsDownload,
    Permission.reconciliationView, Permission.reconciliationRun, Permission.reconciliationExport,
    Permission.bankReconView, Permission.bankReconRun,
    Permission.settlementsView, Permission.disputesView, Permission.aiView,
  },
  'gst_consultant': {
    Permission.dashboardView,
    Permission.gstView, Permission.gstFile, Permission.gstExport,
    Permission.gstr1View, Permission.gstr1File, Permission.gstr3bView, Permission.gstr3bFile,
  },
  'auditor': {
    Permission.dashboardView, Permission.reportsView, Permission.reportsDownload,
    Permission.reconciliationView, Permission.bankReconView,
    Permission.settlementsView, Permission.disputesView,
    Permission.gstView, Permission.gstr1View, Permission.gstr3bView,
    Permission.aiView, Permission.usersView, Permission.auditView,
  },
  'ca_admin': {
    Permission.dashboardView, Permission.reportsView, Permission.reportsDownload,
    Permission.reconciliationView, Permission.reconciliationRun, Permission.reconciliationExport,
    Permission.bankReconView, Permission.bankReconRun,
    Permission.settlementsView, Permission.settlementsExport,
    Permission.disputesView,
    Permission.gstView, Permission.gstExport, Permission.gstr1View, Permission.gstr3bView,
    Permission.aiView, Permission.usersView, Permission.auditView,
  },
  'ca_reviewer': {
    Permission.dashboardView, Permission.reportsView, Permission.reportsDownload,
    Permission.reconciliationView, Permission.settlementsView,
    Permission.gstView, Permission.gstr1View, Permission.gstr3bView,
  },
  'ca_staff':  {Permission.dashboardView, Permission.reportsView, Permission.reconciliationView, Permission.settlementsView},
  'ca_viewer': {Permission.dashboardView, Permission.reportsView, Permission.settlementsView},
  'branch_manager': {
    Permission.dashboardView, Permission.reportsView, Permission.reportsUpload, Permission.reportsDownload,
    Permission.reconciliationView, Permission.reconciliationRun,
    Permission.settlementsView, Permission.disputesView, Permission.disputesCreate, Permission.disputesUpdate,
    Permission.usersView,
  },
  'branch_accountant': {
    Permission.dashboardView, Permission.reportsView, Permission.reportsUpload, Permission.reportsDownload,
    Permission.reconciliationView, Permission.settlementsView, Permission.disputesView, Permission.gstView,
  },
  'branch_viewer': {Permission.dashboardView, Permission.reportsView, Permission.settlementsView, Permission.disputesView},
  // Legacy roles
  'member': {
    Permission.dashboardView, Permission.reportsView, Permission.reportsUpload, Permission.reportsDownload,
    Permission.reconciliationView, Permission.reconciliationRun,
    Permission.marketplaceView, Permission.settlementsView, Permission.disputesView, Permission.disputesCreate,
  },
  'finance': {
    Permission.dashboardView, Permission.reportsView, Permission.reportsDownload,
    Permission.reconciliationView, Permission.settlementsView, Permission.disputesView,
  },
  'ca': {Permission.dashboardView, Permission.reportsView, Permission.settlementsView, Permission.reconciliationView, Permission.disputesView},
  'viewer': {Permission.settlementsView, Permission.dashboardView},
  'seller': {
    Permission.dashboardView, Permission.reportsView, Permission.reportsUpload, Permission.reportsDownload,
    Permission.reconciliationView, Permission.reconciliationRun,
    Permission.marketplaceView, Permission.marketplaceConnect, Permission.marketplaceSync,
    Permission.settlementsView, Permission.disputesView, Permission.disputesCreate,
  },
};

Set<String> getPermissionsForRole(String role) {
  return _rolePermissions[role] ?? {};
}
