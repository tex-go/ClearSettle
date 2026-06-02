import '../entities/auth_entity.dart';
import '../repositories/auth_repository.dart';

class GetCurrentSessionUseCase {
  const GetCurrentSessionUseCase(this._repository);

  final AuthRepository _repository;

  Future<AuthAuthenticated?> call() => _repository.getStoredSession();
}
