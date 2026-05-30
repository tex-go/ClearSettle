import '../../domain/entities/auth_entity.dart';
import '../../domain/repositories/auth_repository.dart';
import '../datasources/auth_local_datasource.dart';
import '../datasources/auth_remote_datasource.dart';

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
    await localDataSource.saveSession(state);
    return state;
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
