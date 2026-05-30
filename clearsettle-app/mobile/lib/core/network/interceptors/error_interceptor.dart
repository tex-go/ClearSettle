import 'package:dio/dio.dart';

import '../../errors/exceptions.dart';

class ErrorInterceptor extends Interceptor {
  @override
  void onError(DioException err, ErrorInterceptorHandler handler) {
    switch (err.type) {
      case DioExceptionType.connectionTimeout:
      case DioExceptionType.receiveTimeout:
      case DioExceptionType.sendTimeout:
      case DioExceptionType.connectionError:
        handler.reject(
          DioException(
            requestOptions: err.requestOptions,
            error: const NetworkException(),
            type: err.type,
          ),
        );

      default:
        final statusCode = err.response?.statusCode;
        if (statusCode == 401) {
          handler.reject(
            DioException(
              requestOptions: err.requestOptions,
              error: const UnauthorizedException(),
              type: err.type,
              response: err.response,
            ),
          );
        } else if (statusCode != null) {
          final body = err.response?.data;
          final message = body is Map ? (body['detail'] ?? body['message'] ?? 'Server error.') : 'Server error.';
          handler.reject(
            DioException(
              requestOptions: err.requestOptions,
              error: ServerException(message: message.toString(), statusCode: statusCode),
              type: err.type,
              response: err.response,
            ),
          );
        } else {
          handler.next(err);
        }
    }
  }
}
