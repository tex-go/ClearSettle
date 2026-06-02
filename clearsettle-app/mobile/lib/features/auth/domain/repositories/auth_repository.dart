import '../../data/models/register_request_model.dart';
import '../entities/auth_entity.dart';

abstract interface class AuthRepository {
  Future<AuthAuthenticated> login(String email, String password);
  Future<AuthAuthenticated> register(RegisterRequestModel request);
  Future<List<RegistrationRoleModel>> getRoles();
  Future<bool> checkEmailAvailable(String email);
  Future<void> logout();
  Future<AuthAuthenticated?> getStoredSession();
}
