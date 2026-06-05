import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/network/api_client.dart';
import '../../../../core/utils/cs_logger.dart';
import '../../../../services/secure_storage/secure_storage_service.dart';
import '../../data/datasources/auth_local_datasource.dart';
import '../../data/datasources/auth_remote_datasource.dart';
import '../../data/datasources/social_auth_datasource.dart';
import '../../data/repositories/auth_repository_impl.dart';
import '../../domain/entities/auth_entity.dart';
import '../../domain/repositories/auth_repository.dart';
import '../../domain/usecases/get_current_session_usecase.dart';
import '../../domain/usecases/login_usecase.dart';
import '../../domain/usecases/logout_usecase.dart';

// — DI providers —

final authLocalDataSourceProvider = Provider<AuthLocalDataSource>((ref) {
  return AuthLocalDataSource(
    secureStorage: ref.read(secureStorageServiceProvider),
  );
});

final authRemoteDataSourceProvider = Provider<AuthRemoteDataSource>((ref) {
  return AuthRemoteDataSource(apiClient: ref.read(apiClientProvider));
});

final authRepositoryProvider = Provider<AuthRepository>((ref) {
  return AuthRepositoryImpl(
    localDataSource: ref.read(authLocalDataSourceProvider),
    remoteDataSource: ref.read(authRemoteDataSourceProvider),
  );
});


// — Notifier —

class AuthNotifier extends AsyncNotifier<AuthState> {
  late final LoginUseCase _login;
  late final LogoutUseCase _logout;
  late final GetCurrentSessionUseCase _getSession;

  @override
  Future<AuthState> build() async {
    final repo = ref.read(authRepositoryProvider);
    _login = LoginUseCase(repo);
    _logout = LogoutUseCase(repo);
    _getSession = GetCurrentSessionUseCase(repo);

    final session = await _getSession();
    return session ?? const AuthUnauthenticated();
  }

  Future<void> login(String email, String password) async {
    state = const AsyncValue.loading();
    state = await AsyncValue.guard(() => _login(email, password));
  }

  Future<void> logout() async {
    state = const AsyncValue.loading();
    await AsyncValue.guard(_logout.call);
    state = const AsyncValue.data(AuthUnauthenticated());
  }

  // ── Social login ──────────────────────────────────────────────────────────

  Future<SocialAuthResult> loginWithGoogle() async {
    state = const AsyncValue.loading();
    try {
      final socialDS = ref.read(socialAuthDataSourceProvider);
      final result   = await socialDS.loginWithGoogle();
      await _persistSocialSession(result);
      return SocialAuthResult(needsEmail: result.needsEmail, placeholderEmail: result.placeholderEmail);
    } catch (e, st) {
      CsLogger.error('AuthProvider', 'Google login failed', error: e, stack: st);
      state = const AsyncValue.data(AuthUnauthenticated());
      rethrow;
    }
  }

  Future<SocialAuthResult> loginWithInstagram() async {
    state = const AsyncValue.loading();
    try {
      final socialDS = ref.read(socialAuthDataSourceProvider);
      final result   = await socialDS.loginWithInstagram();
      await _persistSocialSession(result);
      return SocialAuthResult(needsEmail: result.needsEmail, placeholderEmail: result.placeholderEmail);
    } catch (e, st) {
      CsLogger.error('AuthProvider', 'Instagram login failed', error: e, stack: st);
      state = const AsyncValue.data(AuthUnauthenticated());
      rethrow;
    }
  }

  Future<void> _persistSocialSession(SocialAuthResponse result) async {
    final localDS   = ref.read(authLocalDataSourceProvider);
    final authState = result.auth.toAuthState();
    await localDS.saveSession(authState, refreshToken: result.auth.refreshToken);
    state = AsyncValue.data(authState);
  }
}

final authProvider = AsyncNotifierProvider<AuthNotifier, AuthState>(
  AuthNotifier.new,
);

// Convenience selector — true when authenticated and not loading
final isAuthenticatedProvider = Provider<bool>((ref) {
  return ref.watch(authProvider).valueOrNull?.isAuthenticated ?? false;
});

/// Returned from social login — tells the caller whether to prompt for email.
class SocialAuthResult {
  const SocialAuthResult({
    required this.needsEmail,
    this.placeholderEmail = '',
  });
  final bool needsEmail;
  final String placeholderEmail;
}
