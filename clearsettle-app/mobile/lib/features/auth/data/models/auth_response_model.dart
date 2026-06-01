import '../../domain/entities/auth_entity.dart';

class AuthResponseModel {
  const AuthResponseModel({
    required this.accessToken,
    required this.refreshToken,
    required this.userId,
    required this.email,
    required this.sellerName,
    required this.organization,
    required this.role,
  });

  final String accessToken;
  final String refreshToken;
  final String userId;
  final String email;
  final String sellerName;
  final String organization;
  final String role;

  factory AuthResponseModel.fromJson(Map<String, dynamic> json) {
    final user = json['user'] as Map<String, dynamic>? ?? json;
    return AuthResponseModel(
      accessToken: json['access_token'] as String,
      refreshToken: json['refresh_token'] as String? ?? '',
      userId: (user['id'] ?? user['user_id'] ?? '').toString(),
      email: (user['email'] as String?) ?? '',
      sellerName: (user['seller_name'] as String?) ??
          (user['name'] as String?) ??
          (user['full_name'] as String?) ??
          '',
      organization: (user['organization'] as String?) ??
          (user['company_name'] as String?) ??
          (user['company'] as String?) ??
          '',
      role: (user['role'] as String?) ?? 'seller',
    );
  }

  AuthAuthenticated toAuthState() {
    return AuthAuthenticated(
      accessToken: accessToken,
      userId: userId,
      email: email,
      sellerName: sellerName,
      organization: organization,
      role: role,
    );
  }
}
