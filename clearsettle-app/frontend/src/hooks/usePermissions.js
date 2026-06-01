/**
 * Permission hooks for ClearSettle RBAC.
 *
 * Permissions are fetched once on login and cached in authStore.
 * The role-based fallback works without a DB round-trip for the common case.
 */
import { useMemo } from 'react'
import useAuthStore from '../store/authStore'

// Role → permission set (mirrors backend static fallback)
const ROLE_PERMISSIONS = {
  superadmin: new Set(['*']),
  admin: new Set([
    'dashboard.view', 'reports.view', 'reports.upload', 'reports.delete', 'reports.download',
    'reconciliation.view', 'reconciliation.run', 'reconciliation.export',
    'bank_reconciliation.view', 'bank_reconciliation.run',
    'marketplace.view', 'marketplace.connect', 'marketplace.disconnect', 'marketplace.sync',
    'settlements.view', 'settlements.export',
    'disputes.view', 'disputes.create', 'disputes.update', 'disputes.close',
    'gst.view', 'gst.file', 'gst.export', 'gstr1.view', 'gstr1.file', 'gstr3b.view', 'gstr3b.file',
    'ai.view', 'ai.generate',
    'users.view', 'users.create', 'users.update', 'users.delete', 'roles.assign',
    'audit.view', 'subscription.view', 'subscription.manage', 'settings.update', 'notifications.manage',
  ]),
  company_admin: new Set([
    'dashboard.view', 'reports.view', 'reports.upload', 'reports.delete', 'reports.download',
    'reconciliation.view', 'reconciliation.run', 'reconciliation.export',
    'bank_reconciliation.view', 'bank_reconciliation.run',
    'marketplace.view', 'marketplace.connect', 'marketplace.disconnect', 'marketplace.sync',
    'settlements.view', 'settlements.export',
    'disputes.view', 'disputes.create', 'disputes.update', 'disputes.close',
    'gst.view', 'gst.file', 'gst.export', 'gstr1.view', 'gstr1.file', 'gstr3b.view', 'gstr3b.file',
    'ai.view', 'ai.generate',
    'users.view', 'users.create', 'users.update', 'users.delete', 'roles.assign',
    'audit.view', 'subscription.view', 'subscription.manage', 'settings.update', 'notifications.manage',
  ]),
  business_owner: new Set([
    'dashboard.view', 'reports.view', 'reports.download',
    'reconciliation.view', 'bank_reconciliation.view',
    'marketplace.view', 'marketplace.connect', 'marketplace.disconnect', 'marketplace.sync',
    'settlements.view', 'settlements.export',
    'disputes.view',
    'gst.view', 'gstr1.view', 'gstr3b.view',
    'ai.view', 'ai.generate',
    'users.view', 'audit.view', 'subscription.view', 'subscription.manage', 'settings.update',
  ]),
  finance_manager: new Set([
    'dashboard.view', 'reports.view', 'reports.upload', 'reports.download',
    'reconciliation.view', 'reconciliation.run', 'reconciliation.export',
    'bank_reconciliation.view', 'bank_reconciliation.run',
    'marketplace.view',
    'settlements.view', 'settlements.export',
    'disputes.view', 'disputes.create', 'disputes.update', 'disputes.close',
    'gst.view', 'gst.file', 'gst.export', 'gstr1.view', 'gstr1.file', 'gstr3b.view', 'gstr3b.file',
    'ai.view', 'users.view',
  ]),
  accountant: new Set([
    'dashboard.view', 'reports.view', 'reports.upload', 'reports.download',
    'reconciliation.view', 'bank_reconciliation.view',
    'settlements.view', 'disputes.view',
    'gst.view', 'gstr1.view', 'gstr3b.view', 'ai.view',
  ]),
  reconciliation_analyst: new Set([
    'dashboard.view', 'reports.view', 'reports.download',
    'reconciliation.view', 'reconciliation.run', 'reconciliation.export',
    'bank_reconciliation.view', 'bank_reconciliation.run',
    'settlements.view', 'disputes.view', 'ai.view',
  ]),
  gst_consultant: new Set([
    'dashboard.view',
    'gst.view', 'gst.file', 'gst.export', 'gstr1.view', 'gstr1.file', 'gstr3b.view', 'gstr3b.file',
  ]),
  auditor: new Set([
    'dashboard.view', 'reports.view', 'reports.download',
    'reconciliation.view', 'bank_reconciliation.view',
    'settlements.view', 'disputes.view',
    'gst.view', 'gstr1.view', 'gstr3b.view',
    'ai.view', 'users.view', 'audit.view',
  ]),
  ca_admin: new Set([
    'dashboard.view', 'reports.view', 'reports.download',
    'reconciliation.view', 'reconciliation.run', 'reconciliation.export',
    'bank_reconciliation.view', 'bank_reconciliation.run',
    'settlements.view', 'settlements.export',
    'disputes.view',
    'gst.view', 'gst.export', 'gstr1.view', 'gstr3b.view',
    'ai.view', 'users.view', 'audit.view',
  ]),
  ca_reviewer: new Set([
    'dashboard.view', 'reports.view', 'reports.download',
    'reconciliation.view', 'settlements.view',
    'gst.view', 'gstr1.view', 'gstr3b.view',
  ]),
  ca_staff: new Set(['dashboard.view', 'reports.view', 'reconciliation.view', 'settlements.view']),
  ca_viewer: new Set(['dashboard.view', 'reports.view', 'settlements.view']),
  branch_manager: new Set([
    'dashboard.view', 'reports.view', 'reports.upload', 'reports.download',
    'reconciliation.view', 'reconciliation.run',
    'settlements.view', 'disputes.view', 'disputes.create', 'disputes.update',
    'users.view',
  ]),
  branch_accountant: new Set([
    'dashboard.view', 'reports.view', 'reports.upload', 'reports.download',
    'reconciliation.view', 'settlements.view', 'disputes.view', 'gst.view',
  ]),
  branch_viewer: new Set(['dashboard.view', 'reports.view', 'settlements.view', 'disputes.view']),
  // Legacy roles
  member: new Set([
    'dashboard.view', 'reports.view', 'reports.upload', 'reports.download',
    'reconciliation.view', 'reconciliation.run',
    'marketplace.view', 'settlements.view', 'disputes.view', 'disputes.create',
  ]),
  finance: new Set([
    'dashboard.view', 'reports.view', 'reports.download',
    'reconciliation.view', 'settlements.view', 'disputes.view',
  ]),
  ca: new Set([
    'dashboard.view', 'reports.view', 'settlements.view',
    'reconciliation.view', 'disputes.view',
  ]),
  viewer: new Set(['settlements.view', 'dashboard.view']),
  seller: new Set([
    'dashboard.view', 'reports.view', 'reports.upload', 'reports.download',
    'reconciliation.view', 'reconciliation.run', 'marketplace.view', 'marketplace.connect',
    'marketplace.sync', 'settlements.view', 'disputes.view', 'disputes.create',
  ]),
}

function getRolePermissions(role) {
  return ROLE_PERMISSIONS[role] || new Set()
}

function hasPermission(permissions, permissionsSet, permission) {
  // permissions: array from API (highest priority)
  // permissionsSet: role-based set (fallback)
  if (permissions && permissions.length > 0) {
    return permissions.includes(permission)
  }
  const ps = permissionsSet
  if (!ps) return false
  if (ps.has('*')) return true
  return ps.has(permission)
}

/**
 * Returns { can, canAny, canAll, role, permissions }
 *
 * can('reports.upload')           — single permission check
 * canAny(['reports.view', 'reports.upload'])  — any of these
 * canAll(['marketplace.connect', 'marketplace.sync']) — all of these
 */
export function usePermissions() {
  const user = useAuthStore(s => s.user)
  const apiPermissions = useAuthStore(s => s.permissions) || []

  return useMemo(() => {
    if (!user) {
      return {
        role: null,
        permissions: [],
        can: () => false,
        canAny: () => false,
        canAll: () => false,
      }
    }

    const role = user.role || 'viewer'
    const rolePerms = getRolePermissions(role)

    const can = (permission) => hasPermission(apiPermissions, rolePerms, permission)
    const canAny = (perms) => perms.some(p => can(p))
    const canAll = (perms) => perms.every(p => can(p))

    return { role, permissions: apiPermissions.length ? apiPermissions : [...rolePerms], can, canAny, canAll }
  }, [user, apiPermissions])
}

export default usePermissions
