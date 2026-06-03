import '../../../../core/errors/exceptions.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/network/api_endpoints.dart';
import '../models/auth_response_model.dart';
import '../models/login_request_model.dart';
import '../models/register_request_model.dart';

class AuthRemoteDataSource {
  const AuthRemoteDataSource({required this.apiClient});

  final ApiClient apiClient;

  Future<AuthResponseModel> login(String email, String password) async {
    final response = await apiClient.post<Map<String, dynamic>>(
      ApiEndpoints.login,
      data: LoginRequestModel(email: email, password: password).toJson(),
    );

    final data = response.data;
    if (data == null) throw const ServerException(message: 'Empty response from server.');

    return AuthResponseModel.fromJson(data);
  }

  Future<AuthResponseModel> register(RegisterRequestModel request) async {
    final response = await apiClient.post<Map<String, dynamic>>(
      ApiEndpoints.register,
      data: request.toJson(),
    );

    final data = response.data;
    if (data == null) throw const ServerException(message: 'Empty response from server.');

    return AuthResponseModel.fromJson(data);
  }

  Future<List<RegistrationRoleModel>> getRoles() async {
    final response = await apiClient.get<Map<String, dynamic>>(
      ApiEndpoints.authRoles,
    );

    final data = response.data;
    if (data == null) throw const ServerException(message: 'Empty response from server.');

    final roles = (data['roles'] as List<dynamic>? ?? [])
        .map((e) => RegistrationRoleModel.fromJson(e as Map<String, dynamic>))
        .toList();
    return roles;
  }

  Future<bool> checkEmailAvailable(String email) async {
    try {
      final response = await apiClient.post<Map<String, dynamic>>(
        ApiEndpoints.checkEmail,
        data: {'email': email},
      );
      return (response.data?['available'] as bool?) ?? false;
    } catch (_) {
      return false;
    }
  }

  Future<String?> refreshAccessToken(String refreshToken) async {
    try {
      final response = await apiClient.post<Map<String, dynamic>>(
        ApiEndpoints.refreshToken,
        data: {'refresh_token': refreshToken},
      );
      return response.data?['access_token'] as String?;
    } catch (_) {
      return null;
    }
  }

  Future<void> logout() async {
    try {
      await apiClient.post<void>(ApiEndpoints.logout);
    } on NetworkException {
      // Offline logout is acceptable — local session cleared regardless
    }
  }
}
