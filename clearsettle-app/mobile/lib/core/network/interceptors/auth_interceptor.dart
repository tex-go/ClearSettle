import 'package:dio/dio.dart';

import '../../constants/route_constants.dart';

typedef TokenReader = Future<String?> Function();
typedef SessionClearer = Future<void> Function();

class AuthInterceptor extends Interceptor {
  AuthInterceptor({
    required this.readToken,
    required this.clearSession,
  });

  final TokenReader readToken;
  final SessionClearer clearSession;

  @override
  Future<void> onRequest(
    RequestOptions options,
    RequestInterceptorHandler handler,
  ) async {
    final token = await readToken();
    if (token != null) {
      options.headers['Authorization'] = 'Bearer $token';
    }
    handler.next(options);
  }

  @override
  Future<void> onError(
    DioException err,
    ErrorInterceptorHandler handler,
  ) async {
    if (err.response?.statusCode == 401) {
      await clearSession();
    }
    handler.next(err);
  }
}

// Placeholder so route_constants import doesn't warn — used by caller to redirect
const _loginRoute = RouteConstants.login;
