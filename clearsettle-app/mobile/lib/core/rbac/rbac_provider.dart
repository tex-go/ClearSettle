import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../rbac/permissions.dart';
import '../../features/auth/domain/entities/auth_entity.dart';
import '../../features/auth/presentation/providers/auth_provider.dart';

/// The user's effective permission set, derived from their role.
class RbacState {
  const RbacState({
    required this.role,
    required this.permissions,
  });

  final String role;
  final Set<String> permissions;

  bool can(String permission) {
    if (permissions.contains('*')) return true;
    return permissions.contains(permission);
  }

  bool canAny(List<String> perms) => perms.any(can);
  bool canAll(List<String> perms) => perms.every(can);

  static const guest = RbacState(role: '', permissions: {});
}

final rbacProvider = Provider<RbacState>((ref) {
  final asyncAuth = ref.watch(authProvider);

  return asyncAuth.when(
    data: (authState) {
      if (authState is AuthAuthenticated) {
        final perms = getPermissionsForRole(authState.role);
        return RbacState(role: authState.role, permissions: perms);
      }
      return RbacState.guest;
    },
    error: (_, __) => RbacState.guest,
    loading: () => RbacState.guest,
  );
});
