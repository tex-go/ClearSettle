import '../entities/auth_entity.dart';
import '../repositories/auth_repository.dart';

class LoginUseCase {
  const LoginUseCase(this._repository);

  final AuthRepository _repository;

  Future<AuthAuthenticated> call(String email, String password) {
    return _repository.login(email, password);
  }
}
