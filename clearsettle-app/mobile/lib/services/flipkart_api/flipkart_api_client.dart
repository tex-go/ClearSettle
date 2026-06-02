import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../oauth/flipkart_oauth_service.dart';

final flipkartApiClientProvider = Provider<FlipkartApiClient>((ref) {
  final oauthService = ref.read(flipkartOAuthServiceProvider);
  return FlipkartApiClient(oauthService: oauthService);
});

/// Authenticated Dio client for the Flipkart Seller API.
///
/// Injects a Bearer token before every request and retries once on 401
/// by calling [FlipkartOAuthService.refreshTokens].
class FlipkartApiClient {
  FlipkartApiClient({required this.oauthService}) {
    _dio = Dio(
      BaseOptions(
        baseUrl: 'https://api.flipkart.com/sellers',
        connectTimeout: const Duration(seconds: 30),
        receiveTimeout: const Duration(seconds: 60),
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
      ),
    );

    _dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) async {
          final token = await oauthService.getValidAccessToken();
          options.headers['Authorization'] = 'Bearer $token';
          handler.next(options);
        },
        onError: (error, handler) async {
          if (error.response?.statusCode == 401) {
            // Token expired between getValidAccessToken check and request —
            // refresh once and retry.
            try {
              await oauthService.refreshTokens();
              final token = await oauthService.getAccessToken();
              final opts = error.requestOptions;
              opts.headers['Authorization'] = 'Bearer $token';
              final retryResponse = await _dio.fetch(opts);
              return handler.resolve(retryResponse);
            } catch (_) {
              return handler.next(error);
            }
          }
          handler.next(error);
        },
      ),
    );
  }

  late final Dio _dio;
  final FlipkartOAuthService oauthService;

  Future<Map<String, dynamic>> get(
    String path, {
    Map<String, dynamic>? queryParameters,
  }) async {
    final response = await _dio.get<Map<String, dynamic>>(
      path,
      queryParameters: queryParameters,
    );
    return response.data ?? {};
  }
}
