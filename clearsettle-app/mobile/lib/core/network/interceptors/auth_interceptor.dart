import 'package:dio/dio.dart';

typedef TokenReader  = Future<String?> Function();
typedef TokenWriter  = Future<void>    Function(String token);
typedef TokenRefresher = Future<String?> Function();
typedef SessionClearer = Future<void>  Function();

/// Injects Bearer token on every request and transparently refreshes on 401.
///
/// Flow on 401:
///   1. Try to refresh via [refreshToken] callback.
///   2. If new token obtained: save it + retry the original request once.
///   3. If refresh fails or no refresh token: call [clearSession] (force logout).
///
/// A boolean lock prevents concurrent refresh storms.
class AuthInterceptor extends Interceptor {
  AuthInterceptor({
    required this.readToken,
    required this.saveToken,
    required this.refreshToken,
    required this.clearSession,
  });

  final TokenReader    readToken;
  final TokenWriter    saveToken;
  final TokenRefresher refreshToken;
  final SessionClearer clearSession;

  bool _refreshing = false;

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
    if (err.response?.statusCode != 401 || _refreshing) {
      handler.next(err);
      return;
    }

    // Mark as refreshing to prevent concurrent refresh loops
    _refreshing = true;
    try {
      final newToken = await refreshToken();

      if (newToken != null && newToken.isNotEmpty) {
        await saveToken(newToken);

        // Retry the original request with the new token
        final opts = err.requestOptions;
        opts.headers['Authorization'] = 'Bearer $newToken';

        try {
          final response = await Dio().fetch<dynamic>(opts);
          handler.resolve(response);
        } on DioException catch (retryErr) {
          handler.next(retryErr);
        }
      } else {
        // Refresh failed — force logout
        await clearSession();
        handler.next(err);
      }
    } catch (_) {
      await clearSession();
      handler.next(err);
    } finally {
      _refreshing = false;
    }
  }
}
