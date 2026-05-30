import '../entities/auth_entity.dart';

abstract interface class AuthRepository {
  Future<AuthAuthenticated> login(String email, String password);
  Future<void> logout();
  Future<AuthAuthenticated?> getStoredSession();
}
