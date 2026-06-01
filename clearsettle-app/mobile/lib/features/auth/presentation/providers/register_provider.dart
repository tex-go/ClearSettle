import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/models/register_request_model.dart';
import '../providers/auth_provider.dart';

// ── Registration state ────────────────────────────────────────────────────────

class RegisterState {
  const RegisterState({
    this.isLoading = false,
    this.error,
    this.success = false,
  });

  final bool isLoading;
  final String? error;
  final bool success;

  RegisterState copyWith({bool? isLoading, String? error, bool? success}) {
    return RegisterState(
      isLoading: isLoading ?? this.isLoading,
      error: error,
      success: success ?? this.success,
    );
  }
}

// ── Register notifier ─────────────────────────────────────────────────────────

class RegisterNotifier extends StateNotifier<RegisterState> {
  RegisterNotifier(this._ref) : super(const RegisterState());

  final Ref _ref;

  Future<void> register(RegisterRequestModel request) async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      final repo = _ref.read(authRepositoryProvider);
      await repo.register(request);
      // Sync into authProvider so the app navigates to dashboard automatically
      await _ref.read(authProvider.notifier).login(
            request.email,
            request.password,
          );
      state = state.copyWith(isLoading: false, success: true);
    } catch (e) {
      state = state.copyWith(isLoading: false, error: _parseError(e));
    }
  }

  void clearError() => state = state.copyWith(error: null);

  String _parseError(Object e) {
    final msg = e.toString();
    if (msg.contains('409') || msg.contains('already registered')) {
      return 'An account with this email already exists.';
    }
    if (msg.contains('422')) return 'Please check your details and try again.';
    if (msg.contains('Network') || msg.contains('connection')) {
      return 'Cannot reach the server. Check your internet connection.';
    }
    if (msg.contains('ServerException')) {
      final detail =
          RegExp(r'ServerException\(\d*\): (.+)').firstMatch(msg)?.group(1);
      if (detail != null && detail != 'Server error.') return detail;
    }
    return 'Registration failed. Please try again.';
  }
}

final registerProvider =
    StateNotifierProvider.autoDispose<RegisterNotifier, RegisterState>(
  (ref) => RegisterNotifier(ref),
);

// ── Roles provider ────────────────────────────────────────────────────────────

final registrationRolesProvider =
    FutureProvider.autoDispose<List<RegistrationRoleModel>>((ref) async {
  final repo = ref.read(authRepositoryProvider);
  return repo.getRoles();
});
