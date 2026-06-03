import '../../../../core/constants/app_constants.dart';
import '../../../../services/secure_storage/secure_storage_service.dart';
import '../../../../storage/entities/user_hive_object.dart';
import '../../../../storage/hive_manager.dart';
import '../../domain/entities/auth_entity.dart';

class AuthLocalDataSource {
  const AuthLocalDataSource({required this.secureStorage});

  final SecureStorageService secureStorage;

  Future<void> saveSession(AuthAuthenticated state, {String? refreshToken}) async {
    await secureStorage.saveAccessToken(state.accessToken);
    await secureStorage.saveUserId(state.userId);
    if (refreshToken != null && refreshToken.isNotEmpty) {
      await secureStorage.saveRefreshToken(refreshToken);
    }

    final user = UserHiveObject(
      id: state.userId,
      email: state.email,
      sellerName: state.sellerName,
      organization: state.organization,
      companyId: state.userId,
      role: state.role,
      createdAt: DateTime.now().toIso8601String(),
    );
    await HiveManager.userBox.put(AppConstants.currentUserKey, user);
  }

  Future<AuthAuthenticated?> loadSession() async {
    final token = await secureStorage.getAccessToken();
    if (token == null || token.isEmpty) return null;

    final user = HiveManager.userBox.get(AppConstants.currentUserKey);
    if (user == null) return null;

    return AuthAuthenticated(
      accessToken: token,
      userId: user.id,
      email: user.email,
      sellerName: user.sellerName,
      organization: user.organization,
      role: user.role,
    );
  }

  Future<void> clearSession() async {
    await secureStorage.clearAll();
    await HiveManager.userBox.delete(AppConstants.currentUserKey);
  }
}
