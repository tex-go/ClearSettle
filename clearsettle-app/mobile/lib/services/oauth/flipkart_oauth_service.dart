import 'dart:convert';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_web_auth_2/flutter_web_auth_2.dart';
import 'package:uuid/uuid.dart';

import '../../core/constants/flipkart_oauth_constants.dart';

final flipkartOAuthServiceProvider = Provider<FlipkartOAuthService>((_) {
  return FlipkartOAuthService();
});

/// Result returned after a successful OAuth authorization flow.
class OAuthResult {
  const OAuthResult({
    required this.accessToken,
    required this.refreshToken,
    required this.expiresAt,
    this.sellerId,
    this.sellerName,
  });

  final String accessToken;
  final String refreshToken;
  final DateTime expiresAt;
  final String? sellerId;
  final String? sellerName;
}

/// Orchestrates the Flipkart OAuth 2.0 Authorization Code flow.
///
/// Flow:
///   1. [authorize] — open Flipkart auth page in Chrome Custom Tabs,
///      capture redirect code via custom URI scheme.
///   2. Exchange code for access + refresh tokens via Basic-auth POST.
///   3. Fetch seller profile and return [OAuthResult].
///   4. Tokens are persisted in flutter_secure_storage.
class FlipkartOAuthService {
  static const _storage = FlutterSecureStorage(
    aOptions: AndroidOptions(encryptedSharedPreferences: true),
  );

  // Standalone Dio — not the app's authenticated client — for token exchange.
  static final _dio = Dio(
    BaseOptions(
      connectTimeout: const Duration(seconds: 30),
      receiveTimeout: const Duration(seconds: 30),
    ),
  );

  /// Starts the OAuth flow. Opens the system browser, waits for the redirect,
  /// exchanges the code, persists tokens, and returns the result.
  Future<OAuthResult> authorize() async {
    // Generate and persist a random state token for CSRF protection.
    final state = const Uuid().v4();
    await _storage.write(
      key: FlipkartOAuthConstants.oauthStateKey,
      value: state,
    );

    final authUrl = Uri.https(
      'seller.flipkart.com',
      '/oauth-service/oauth/authorize',
      {
        'client_id': FlipkartOAuthConstants.clientId,
        'redirect_uri': FlipkartOAuthConstants.redirectUri,
        'response_type': 'code',
        'scope': FlipkartOAuthConstants.scope,
        'state': state,
      },
    ).toString();

    final resultUrl = await FlutterWebAuth2.authenticate(
      url: authUrl,
      callbackUrlScheme: FlipkartOAuthConstants.callbackUrlScheme,
    );

    final uri = Uri.parse(resultUrl);
    final returnedState = uri.queryParameters['state'];
    final code = uri.queryParameters['code'];
    final error = uri.queryParameters['error'];

    if (error != null) {
      throw FlipkartOAuthException('Flipkart denied access: $error');
    }
    if (code == null) {
      throw const FlipkartOAuthException('No authorization code received');
    }
    if (returnedState != state) {
      throw const FlipkartOAuthException(
        'OAuth state mismatch — possible CSRF attack',
      );
    }

    await _storage.delete(key: FlipkartOAuthConstants.oauthStateKey);
    return _exchangeCodeForTokens(code);
  }

  Future<OAuthResult> _exchangeCodeForTokens(String code) async {
    // Flipkart token endpoint expects Basic auth: base64(clientId:clientSecret)
    final credentials = base64.encode(
      utf8.encode(
        '${FlipkartOAuthConstants.clientId}:${FlipkartOAuthConstants.clientSecret}',
      ),
    );

    final response = await _dio.post<Map<String, dynamic>>(
      FlipkartOAuthConstants.tokenEndpoint,
      data: {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': FlipkartOAuthConstants.redirectUri,
      },
      options: Options(
        headers: {'Authorization': 'Basic $credentials'},
        contentType: 'application/x-www-form-urlencoded',
      ),
    );

    final data = response.data!;
    final accessToken = data['access_token'] as String;
    final refreshToken = data['refresh_token'] as String;
    final expiresIn = (data['expires_in'] as num).toInt();
    final expiresAt = DateTime.now().add(Duration(seconds: expiresIn));

    await Future.wait([
      _storage.write(
          key: FlipkartOAuthConstants.accessTokenKey, value: accessToken),
      _storage.write(
          key: FlipkartOAuthConstants.refreshTokenKey, value: refreshToken),
      _storage.write(
          key: FlipkartOAuthConstants.tokenExpiryKey,
          value: expiresAt.toIso8601String()),
    ]);

    final (sellerId, sellerName) = await _fetchSellerProfile(accessToken);

    return OAuthResult(
      accessToken: accessToken,
      refreshToken: refreshToken,
      expiresAt: expiresAt,
      sellerId: sellerId,
      sellerName: sellerName,
    );
  }

  /// Attempts to fetch seller display info; non-fatal on failure.
  Future<(String?, String?)> _fetchSellerProfile(String accessToken) async {
    try {
      final response = await _dio.get<Map<String, dynamic>>(
        FlipkartOAuthConstants.sellerProfileEndpoint,
        options: Options(
          headers: {'Authorization': 'Bearer $accessToken'},
        ),
      );
      final data = response.data;
      return (
        data?['seller_id'] as String?,
        data?['display_name'] as String?,
      );
    } catch (_) {
      return (null, null);
    }
  }

  /// Deletes all stored Flipkart tokens (used on disconnect).
  Future<void> revokeTokens() async {
    await Future.wait([
      _storage.delete(key: FlipkartOAuthConstants.accessTokenKey),
      _storage.delete(key: FlipkartOAuthConstants.refreshTokenKey),
      _storage.delete(key: FlipkartOAuthConstants.tokenExpiryKey),
    ]);
  }

  /// Returns a valid access token — refreshes if expired.
  /// Throws [FlipkartOAuthException] if no refresh token is stored.
  Future<String> getValidAccessToken() async {
    if (await isTokenValid()) {
      return (await _storage.read(key: FlipkartOAuthConstants.accessTokenKey))!;
    }
    await refreshTokens();
    final token =
        await _storage.read(key: FlipkartOAuthConstants.accessTokenKey);
    if (token == null) throw const FlipkartOAuthException('No access token after refresh');
    return token;
  }

  /// Uses the stored refresh token to obtain a new access token.
  Future<void> refreshTokens() async {
    final refreshToken =
        await _storage.read(key: FlipkartOAuthConstants.refreshTokenKey);
    if (refreshToken == null) {
      throw const FlipkartOAuthException(
          'No refresh token stored — user must reconnect');
    }

    final credentials = base64.encode(
      utf8.encode(
        '${FlipkartOAuthConstants.clientId}:${FlipkartOAuthConstants.clientSecret}',
      ),
    );

    final response = await _dio.post<Map<String, dynamic>>(
      FlipkartOAuthConstants.tokenEndpoint,
      data: {
        'grant_type': 'refresh_token',
        'refresh_token': refreshToken,
      },
      options: Options(
        headers: {'Authorization': 'Basic $credentials'},
        contentType: 'application/x-www-form-urlencoded',
      ),
    );

    final data = response.data!;
    final newAccessToken = data['access_token'] as String;
    final expiresIn = (data['expires_in'] as num).toInt();
    final expiresAt = DateTime.now().add(Duration(seconds: expiresIn));
    // Some providers also rotate refresh tokens on refresh
    final newRefreshToken = data['refresh_token'] as String? ?? refreshToken;

    await Future.wait([
      _storage.write(
          key: FlipkartOAuthConstants.accessTokenKey, value: newAccessToken),
      _storage.write(
          key: FlipkartOAuthConstants.refreshTokenKey, value: newRefreshToken),
      _storage.write(
          key: FlipkartOAuthConstants.tokenExpiryKey,
          value: expiresAt.toIso8601String()),
    ]);
  }

  Future<String?> getAccessToken() =>
      _storage.read(key: FlipkartOAuthConstants.accessTokenKey);

  Future<bool> isTokenValid() async {
    final expiry =
        await _storage.read(key: FlipkartOAuthConstants.tokenExpiryKey);
    if (expiry == null) return false;
    return DateTime.now().isBefore(DateTime.parse(expiry));
  }
}

class FlipkartOAuthException implements Exception {
  const FlipkartOAuthException(this.message);
  final String message;

  @override
  String toString() => 'FlipkartOAuthException: $message';
}
