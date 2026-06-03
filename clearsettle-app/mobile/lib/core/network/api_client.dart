import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../config/app_config.dart';
import '../errors/exceptions.dart';
import 'interceptors/auth_interceptor.dart';
import 'interceptors/error_interceptor.dart';
import '../../services/secure_storage/secure_storage_service.dart';

final apiClientProvider = Provider<ApiClient>((ref) {
  final secureStorage = ref.read(secureStorageServiceProvider);
  return ApiClient(secureStorage: secureStorage);
});

class ApiClient {
  ApiClient({required SecureStorageService secureStorage})
      : _secureStorage = secureStorage {
    _dio = Dio(
      BaseOptions(
        baseUrl: AppConfig.apiBaseUrl,
        connectTimeout: AppConfig.connectTimeout,
        receiveTimeout: AppConfig.receiveTimeout,
        sendTimeout: AppConfig.sendTimeout,
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
      ),
    );

    _dio.interceptors.addAll([
      AuthInterceptor(
        readToken:    _secureStorage.getAccessToken,
        saveToken:    _secureStorage.saveAccessToken,
        refreshToken: _refreshAccessToken,
        clearSession: _secureStorage.clearAll,
      ),
      ErrorInterceptor(),
      LogInterceptor(
        requestBody: false,
        responseBody: false,
        error: true,
        logPrint: (_) {},
      ),
    ]);
  }

  late final Dio _dio;
  final SecureStorageService _secureStorage;

  /// Called by AuthInterceptor on 401: try to exchange the stored refresh
  /// token for a new access token. Returns null if no refresh token or if the
  /// server rejects it (caller will then force logout).
  Future<String?> _refreshAccessToken() async {
    final refreshToken = await _secureStorage.getRefreshToken();
    if (refreshToken == null || refreshToken.isEmpty) return null;

    try {
      // Bypass the interceptor-equipped _dio to avoid an infinite retry loop.
      final raw = Dio(BaseOptions(
        baseUrl: AppConfig.apiBaseUrl,
        connectTimeout: AppConfig.connectTimeout,
        receiveTimeout: AppConfig.receiveTimeout,
      ));
      final response = await raw.post<Map<String, dynamic>>(
        '/auth/refresh',
        data: {'refresh_token': refreshToken},
      );
      final data = response.data;
      final newToken = data?['access_token'] as String?;
      if (newToken != null && newToken.isNotEmpty) {
        // Persist new refresh token if server rotated it
        final newRefresh = data?['refresh_token'] as String?;
        if (newRefresh != null && newRefresh.isNotEmpty) {
          await _secureStorage.saveRefreshToken(newRefresh);
        }
      }
      return newToken;
    } catch (_) {
      return null;
    }
  }

  Future<Response<T>> get<T>(
    String path, {
    Map<String, dynamic>? queryParameters,
  }) async {
    try {
      return await _dio.get<T>(path, queryParameters: queryParameters);
    } on DioException catch (e) {
      throw _mapError(e);
    }
  }

  Future<Response<T>> post<T>(
    String path, {
    dynamic data,
    Map<String, dynamic>? queryParameters,
  }) async {
    try {
      return await _dio.post<T>(path, data: data, queryParameters: queryParameters);
    } on DioException catch (e) {
      throw _mapError(e);
    }
  }

  Future<Response<T>> put<T>(String path, {dynamic data}) async {
    try {
      return await _dio.put<T>(path, data: data);
    } on DioException catch (e) {
      throw _mapError(e);
    }
  }

  Future<Response<T>> delete<T>(String path) async {
    try {
      return await _dio.delete<T>(path);
    } on DioException catch (e) {
      throw _mapError(e);
    }
  }

  /// Multipart file upload — used by the ingestion pipeline endpoint.
  Future<Response<T>> uploadFile<T>(
    String path, {
    required List<int> fileBytes,
    required String fileName,
    Map<String, String>? fields,
  }) async {
    try {
      final formData = FormData.fromMap({
        'file': MultipartFile.fromBytes(
          fileBytes,
          filename: fileName,
          contentType: DioMediaType(
            'application',
            fileName.toLowerCase().endsWith('.xlsx')
                ? 'vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                : 'octet-stream',
          ),
        ),
        if (fields != null) ...fields,
      });

      return await _dio.post<T>(
        path,
        data: formData,
        options: Options(
          // Allow up to 3 minutes for large file uploads
          sendTimeout: const Duration(minutes: 3),
          receiveTimeout: const Duration(minutes: 2),
          headers: {'Content-Type': 'multipart/form-data'},
        ),
      );
    } on DioException catch (e) {
      throw _mapError(e);
    }
  }

  Exception _mapError(DioException e) {
    if (e.error is Exception) return e.error as Exception;
    if (e.type == DioExceptionType.connectionError ||
        e.type == DioExceptionType.connectionTimeout) {
      return const NetworkException();
    }
    return ServerException(message: e.message ?? 'Unknown error');
  }
}
