/**
 * PermissionGuard — renders children only when the user has the required permission(s).
 *
 * Usage:
 *   <PermissionGuard permission="reports.upload">
 *     <UploadButton />
 *   </PermissionGuard>
 *
 *   <PermissionGuard anyOf={["marketplace.connect", "marketplace.sync"]}>
 *     <ConnectPanel />
 *   </PermissionGuard>
 *
 *   <PermissionGuard allOf={["users.create", "roles.assign"]}>
 *     <InviteUserModal />
 *   </PermissionGuard>
 *
 *   <PermissionGuard permission="audit.view" fallback={<p>Access denied</p>}>
 *     <AuditLog />
 *   </PermissionGuard>
 */
import usePermissions from '../../hooks/usePermissions'

export default function PermissionGuard({ permission, anyOf, allOf, fallback = null, children }) {
  const { can, canAny, canAll } = usePermissions()

  let allowed = false
  if (permission) allowed = can(permission)
  else if (anyOf) allowed = canAny(anyOf)
  else if (allOf) allowed = canAll(allOf)
  else allowed = true  // no constraint — always show

  if (!allowed) return fallback
  return children
}
