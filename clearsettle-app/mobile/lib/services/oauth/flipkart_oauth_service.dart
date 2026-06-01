import 'dart:convert';
import 'dart:developer' as dev;

import 'package:dio/dio.dart';
import 'package:flutter/services.dart';
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

  static const _tag = 'FlipkartOAuth';

  /// Starts the OAuth flow. Opens Chrome Custom Tabs, waits for the redirect,
  /// exchanges the code, persists tokens, and returns the result.
  Future<OAuthResult> authorize() async {
    _validateCredentials();

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

    dev.log('[$_tag] Starting OAuth flow', name: _tag);
    dev.log('[$_tag] Auth URL: $authUrl', name: _tag);
    dev.log('[$_tag] Redirect URI: ${FlipkartOAuthConstants.redirectUri}', name: _tag);
    dev.log('[$_tag] Callback scheme: ${FlipkartOAuthConstants.callbackUrlScheme}', name: _tag);
    dev.log('[$_tag] Scope: ${FlipkartOAuthConstants.scope}', name: _tag);
    dev.log('[$_tag] State (CSRF): $state', name: _tag);
    dev.log('[$_tag] Opening Chrome Custom Tabs…', name: _tag);

    String resultUrl;
    try {
      resultUrl = await FlutterWebAuth2.authenticate(
        url: authUrl,
        callbackUrlScheme: FlipkartOAuthConstants.callbackUrlScheme,
      );
      dev.log('[$_tag] Browser closed — callback received', name: _tag);
      dev.log('[$_tag] Result URL: $resultUrl', name: _tag);
    } on PlatformException catch (e, st) {
      dev.log(
        '[$_tag] PlatformException from flutter_web_auth_2',
        name: _tag,
        error: e,
        stackTrace: st,
      );
      dev.log('[$_tag] Code: ${e.code}', name: _tag);
      dev.log('[$_tag] Message: ${e.message}', name: _tag);
      dev.log('[$_tag] Details: ${e.details}', name: _tag);

      // Distinguish real user cancellation from redirect-capture failures.
      if (e.code == 'CANCELED') {
        throw const FlipkartOAuthException(
          'Login was cancelled. If you completed login but still see this error, '
          'the OAuth redirect URI may not be registered correctly in the '
          'Flipkart Partner Console. '
          'Expected redirect URI: ${FlipkartOAuthConstants.redirectUri}',
        );
      }
      throw FlipkartOAuthException(
        'OAuth browser error (${e.code}): ${e.message ?? 'unknown'}',
      );
    } catch (e, st) {
      dev.log('[$_tag] Unexpected error during browser auth', name: _tag, error: e, stackTrace: st);
      rethrow;
    }

    final uri = Uri.parse(resultUrl);
    final returnedState = uri.queryParameters['state'];
    final code = uri.queryParameters['code'];
    final error = uri.queryParameters['error'];
    final errorDescription = uri.queryParameters['error_description'];

    dev.log('[$_tag] Callback parameters:', name: _tag);
    dev.log('[$_tag]   code present: ${code != null}', name: _tag);
    dev.log('[$_tag]   state: $returnedState', name: _tag);
    dev.log('[$_tag]   error: $error', name: _tag);
    dev.log('[$_tag]   error_description: $errorDescription', name: _tag);

    if (error != null) {
      dev.log('[$_tag] Flipkart returned error: $error — $errorDescription', name: _tag);
      throw FlipkartOAuthException(
        'Flipkart denied access: $error'
        '${errorDescription != null ? ' ($errorDescription)' : ''}',
      );
    }
    if (code == null) {
      dev.log('[$_tag] No authorization code in callback — URL: $resultUrl', name: _tag);
      throw const FlipkartOAuthException('No authorization code received in redirect');
    }
    if (returnedState != state) {
      dev.log('[$_tag] State mismatch! expected=$state got=$returnedState', name: _tag);
      throw const FlipkartOAuthException(
        'OAuth state mismatch — possible CSRF attack or stale session',
      );
    }

    dev.log('[$_tag] Authorization code received. Exchanging for tokens…', name: _tag);
    await _storage.delete(key: FlipkartOAuthConstants.oauthStateKey);
    return _exchangeCodeForTokens(code);
  }

  Future<OAuthResult> _exchangeCodeForTokens(String code) async {
    final credentials = base64.encode(
      utf8.encode(
        '${FlipkartOAuthConstants.clientId}:${FlipkartOAuthConstants.clientSecret}',
      ),
    );

    dev.log('[$_tag] POST ${FlipkartOAuthConstants.tokenEndpoint}', name: _tag);
    dev.log('[$_tag] grant_type=authorization_code redirect_uri=${FlipkartOAuthConstants.redirectUri}', name: _tag);

    try {
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

      dev.log('[$_tag] Token exchange response status: ${response.statusCode}', name: _tag);

      final data = response.data!;
      final accessToken = data['access_token'] as String;
      final refreshToken = data['refresh_token'] as String;
      final expiresIn = (data['expires_in'] as num).toInt();
      final expiresAt = DateTime.now().add(Duration(seconds: expiresIn));

      dev.log('[$_tag] Tokens received. expires_in=${expiresIn}s expiresAt=$expiresAt', name: _tag);

      await Future.wait([
        _storage.write(key: FlipkartOAuthConstants.accessTokenKey, value: accessToken),
        _storage.write(key: FlipkartOAuthConstants.refreshTokenKey, value: refreshToken),
        _storage.write(key: FlipkartOAuthConstants.tokenExpiryKey, value: expiresAt.toIso8601String()),
      ]);

      dev.log('[$_tag] Tokens persisted. Fetching seller profile…', name: _tag);
      final (sellerId, sellerName) = await _fetchSellerProfile(accessToken);
      dev.log('[$_tag] Seller profile: id=$sellerId name=$sellerName', name: _tag);

      return OAuthResult(
        accessToken: accessToken,
        refreshToken: refreshToken,
        expiresAt: expiresAt,
        sellerId: sellerId,
        sellerName: sellerName,
      );
    } on DioException catch (e, st) {
      dev.log('[$_tag] Token exchange failed', name: _tag, error: e, stackTrace: st);
      dev.log('[$_tag] Response status: ${e.response?.statusCode}', name: _tag);
      dev.log('[$_tag] Response data: ${e.response?.data}', name: _tag);
      throw FlipkartOAuthException(
        'Token exchange failed (${e.response?.statusCode ?? e.type.name}): '
        '${e.response?.data ?? e.message}',
      );
    }
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
    } catch (e) {
      dev.log('[$_tag] Seller profile fetch failed (non-fatal): $e', name: _tag);
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
    final token = await _storage.read(key: FlipkartOAuthConstants.accessTokenKey);
    if (token == null) throw const FlipkartOAuthException('No access token after refresh');
    return token;
  }

  /// Uses the stored refresh token to obtain a new access token.
  Future<void> refreshTokens() async {
    final refreshToken = await _storage.read(key: FlipkartOAuthConstants.refreshTokenKey);
    if (refreshToken == null) {
      throw const FlipkartOAuthException('No refresh token stored — user must reconnect');
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
    final newRefreshToken = data['refresh_token'] as String? ?? refreshToken;

    await Future.wait([
      _storage.write(key: FlipkartOAuthConstants.accessTokenKey, value: newAccessToken),
      _storage.write(key: FlipkartOAuthConstants.refreshTokenKey, value: newRefreshToken),
      _storage.write(key: FlipkartOAuthConstants.tokenExpiryKey, value: expiresAt.toIso8601String()),
    ]);
  }

  Future<String?> getAccessToken() =>
      _storage.read(key: FlipkartOAuthConstants.accessTokenKey);

  Future<bool> isTokenValid() async {
    final expiry = await _storage.read(key: FlipkartOAuthConstants.tokenExpiryKey);
    if (expiry == null) return false;
    return DateTime.now().isBefore(DateTime.parse(expiry));
  }

  /// Throws [FlipkartOAuthException] early if credentials are still placeholders.
  void _validateCredentials() {
    if (FlipkartOAuthConstants.clientId.startsWith('YOUR_') ||
        FlipkartOAuthConstants.clientSecret.startsWith('YOUR_')) {
      dev.log(
        '[$_tag] ERROR: Flipkart OAuth credentials are still placeholders. '
        'Register at https://seller.flipkart.com/api-docs/FMSAPI.html and '
        'update FlipkartOAuthConstants.clientId / clientSecret.',
        name: _tag,
      );
      throw const FlipkartOAuthException(
        'Flipkart API credentials not configured. '
        'Please contact support or register your app at the Flipkart Partner Console.',
      );
    }
    dev.log(
      '[$_tag] Credentials OK. client_id=${FlipkartOAuthConstants.clientId}',
      name: _tag,
    );
  }
}

class FlipkartOAuthException implements Exception {
  const FlipkartOAuthException(this.message);
  final String message;

  @override
  String toString() => 'FlipkartOAuthException: $message';
}
