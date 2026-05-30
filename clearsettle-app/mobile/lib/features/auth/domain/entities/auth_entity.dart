sealed class AuthState {
  const AuthState();

  bool get isAuthenticated => this is AuthAuthenticated;
}

final class AuthAuthenticated extends AuthState {
  const AuthAuthenticated({
    required this.accessToken,
    required this.userId,
    required this.email,
    required this.sellerName,
    required this.organization,
    required this.role,
  });

  final String accessToken;
  final String userId;
  final String email;
  final String sellerName;
  final String organization;
  final String role;

  AuthAuthenticated copyWith({
    String? accessToken,
    String? userId,
    String? email,
    String? sellerName,
    String? organization,
    String? role,
  }) {
    return AuthAuthenticated(
      accessToken: accessToken ?? this.accessToken,
      userId: userId ?? this.userId,
      email: email ?? this.email,
      sellerName: sellerName ?? this.sellerName,
      organization: organization ?? this.organization,
      role: role ?? this.role,
    );
  }
}

final class AuthUnauthenticated extends AuthState {
  const AuthUnauthenticated();
}
