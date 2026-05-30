import '../../../../core/errors/exceptions.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/network/api_endpoints.dart';
import '../models/auth_response_model.dart';
import '../models/login_request_model.dart';

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

  Future<void> logout() async {
    try {
      await apiClient.post<void>(ApiEndpoints.logout);
    } on NetworkException {
      // Offline logout is acceptable — local session cleared regardless
    }
  }
}
