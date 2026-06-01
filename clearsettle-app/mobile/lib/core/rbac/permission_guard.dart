import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'rbac_provider.dart';

/// Renders [child] only when the user holds the required permission(s).
///
/// Examples:
/// ```dart
/// // Single permission
/// PermissionGuard(
///   permission: Permission.reportsUpload,
///   child: UploadButton(),
/// )
///
/// // Any of these permissions
/// PermissionGuard(
///   anyOf: [Permission.marketplaceConnect, Permission.marketplaceSync],
///   child: ConnectPanel(),
/// )
///
/// // All of these permissions
/// PermissionGuard(
///   allOf: [Permission.usersCreate, Permission.rolesAssign],
///   child: InviteUserDialog(),
/// )
///
/// // With a fallback widget when access is denied
/// PermissionGuard(
///   permission: Permission.auditView,
///   fallback: Center(child: Text('Access denied')),
///   child: AuditLogScreen(),
/// )
/// ```
class PermissionGuard extends ConsumerWidget {
  const PermissionGuard({
    super.key,
    this.permission,
    this.anyOf,
    this.allOf,
    this.fallback,
    required this.child,
  }) : assert(
          permission != null || anyOf != null || allOf != null,
          'Provide at least one of: permission, anyOf, allOf',
        );

  final String? permission;
  final List<String>? anyOf;
  final List<String>? allOf;
  final Widget? fallback;
  final Widget child;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final rbac = ref.watch(rbacProvider);

    final bool allowed;
    if (permission != null) {
      allowed = rbac.can(permission!);
    } else if (anyOf != null) {
      allowed = rbac.canAny(anyOf!);
    } else if (allOf != null) {
      allowed = rbac.canAll(allOf!);
    } else {
      allowed = true;
    }

    if (!allowed) return fallback ?? const SizedBox.shrink();
    return child;
  }
}
