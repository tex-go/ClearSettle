import '../../domain/entities/auth_entity.dart';
import '../../domain/repositories/auth_repository.dart';
import '../datasources/auth_local_datasource.dart';
import '../datasources/auth_remote_datasource.dart';
import '../models/register_request_model.dart';

class AuthRepositoryImpl implements AuthRepository {
  const AuthRepositoryImpl({
    required this.localDataSource,
    required this.remoteDataSource,
  });

  final AuthLocalDataSource localDataSource;
  final AuthRemoteDataSource remoteDataSource;

  @override
  Future<AuthAuthenticated> login(String email, String password) async {
    final response = await remoteDataSource.login(email, password);
    final state = response.toAuthState();
    await localDataSource.saveSession(state, refreshToken: response.refreshToken);
    return state;
  }

  @override
  Future<AuthAuthenticated> register(RegisterRequestModel request) async {
    final response = await remoteDataSource.register(request);
    final state = response.toAuthState();
    await localDataSource.saveSession(state, refreshToken: response.refreshToken);
    return state;
  }

  @override
  Future<List<RegistrationRoleModel>> getRoles() {
    return remoteDataSource.getRoles();
  }

  @override
  Future<bool> checkEmailAvailable(String email) {
    return remoteDataSource.checkEmailAvailable(email);
  }

  @override
  Future<void> logout() async {
    await remoteDataSource.logout();
    await localDataSource.clearSession();
  }

  @override
  Future<AuthAuthenticated?> getStoredSession() {
    return localDataSource.loadSession();
  }
}
