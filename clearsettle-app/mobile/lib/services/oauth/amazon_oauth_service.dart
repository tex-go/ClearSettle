import 'dart:developer' as dev;

import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_web_auth_2/flutter_web_auth_2.dart';

import '../../core/constants/amazon_oauth_constants.dart';
import '../../core/network/api_client.dart';

final amazonOAuthServiceProvider = Provider<AmazonOAuthService>((ref) {
  return AmazonOAuthService(apiClient: ref.read(apiClientProvider));
});

/// Result returned after a successful Amazon SP-API OAuth flow.
class AmazonOAuthResult {
  const AmazonOAuthResult({
    required this.connectionId,
    required this.status,
    this.sellingPartnerId,
    this.marketplaceId,
    this.tokenExpiresAt,
  });

  final String connectionId;
  final String status;
  final String? sellingPartnerId;
  final String? marketplaceId;
  final DateTime? tokenExpiresAt;

  factory AmazonOAuthResult.fromStatusJson(
    String connectionId,
    Map<String, dynamic> json,
  ) {
    return AmazonOAuthResult(
      connectionId: connectionId,
      status: json['status'] as String? ?? 'connected',
      sellingPartnerId: json['selling_partner_id'] as String?,
      marketplaceId: json['marketplace_id'] as String?,
      tokenExpiresAt: json['token_expires_at'] != null
          ? DateTime.tryParse(json['token_expires_at'] as String)
          : null,
    );
  }
}

/// Orchestrates the Amazon SP-API OAuth 2.0 flow via the ClearSettle backend.
///
/// Flow:
///   1. [authorize] calls GET /sp-api/authorize?source=mobile on the backend.
///      Backend generates a CSRF state token and returns the Amazon authorization URL.
///   2. The URL is opened in Chrome Custom Tabs via flutter_web_auth_2.
///   3. Seller logs in and authorizes on Amazon Seller Central.
///   4. Amazon redirects to the backend callback URL (SP_API_REDIRECT_URI).
///   5. Backend exchanges the auth code for tokens, stores them, then redirects
///      to clearsettle://oauth/amazon/callback?status=success&connection_id=xxx.
///   6. Android CallbackActivity captures the deep link; flutter_web_auth_2 resolves.
///   7. This service calls GET /sp-api/connections/{id}/status to confirm and
///      return the final connection details.
///
/// Prerequisites:
///   - SP_API_REDIRECT_URI must point to a publicly accessible backend URL,
///     e.g. https://clearsettle.in/api/sp-api/callback
///   - That URL must be registered in the Amazon Developer Console application.
class AmazonOAuthService {
  const AmazonOAuthService({required ApiClient apiClient})
      : _apiClient = apiClient;

  final ApiClient _apiClient;
  static const _tag = 'AmazonOAuth';

  Future<AmazonOAuthResult> authorize() async {
    dev.log('[$_tag] Starting Amazon SP-API OAuth (backend-mediated)', name: _tag);

    // ── Step 1: Fetch authorization URL from backend ──────────────────────────
    dev.log('[$_tag] GET ${AmazonOAuthConstants.authorizeEndpoint}?source=mobile', name: _tag);
    final authorizeResp = await _apiClient.get<Map<String, dynamic>>(
      AmazonOAuthConstants.authorizeEndpoint,
      queryParameters: {'source': 'mobile'},
    );

    final data = authorizeResp.data!;
    final authUrl = data['authorization_url'] as String;
    final connectionId = data['connection_id'] as String;
    final state = data['state'] as String;

    dev.log('[$_tag] Authorization URL: $authUrl', name: _tag);
    dev.log('[$_tag] Connection ID: $connectionId', name: _tag);
    dev.log('[$_tag] State (CSRF): $state', name: _tag);
    dev.log('[$_tag] Callback scheme: ${AmazonOAuthConstants.callbackUrlScheme}', name: _tag);
    dev.log('[$_tag] Opening Chrome Custom Tabs…', name: _tag);

    // ── Step 2: Open Chrome Custom Tabs, wait for clearsettle:// deep link ────
    String resultUrl;
    try {
      resultUrl = await FlutterWebAuth2.authenticate(
        url: authUrl,
        callbackUrlScheme: AmazonOAuthConstants.callbackUrlScheme,
      );
      dev.log('[$_tag] Browser closed — deep link received', name: _tag);
      dev.log('[$_tag] Result URL: $resultUrl', name: _tag);
    } on PlatformException catch (e, st) {
      dev.log(
        '[$_tag] PlatformException from flutter_web_auth_2',
        name: _tag,
        error: e,
        stackTrace: st,
      );
      dev.log('[$_tag] Code: ${e.code}  Message: ${e.message}', name: _tag);

      if (e.code == 'CANCELED') {
        throw const AmazonOAuthException(
          'Amazon login was cancelled. '
          'If you completed the login and still see this error, '
          'the redirect URI may not be registered in the Amazon Developer Console. '
          'Expected redirect URI: SP_API_REDIRECT_URI (backend /sp-api/callback)',
        );
      }
      throw AmazonOAuthException(
        'OAuth browser error (${e.code}): ${e.message ?? 'unknown'}',
      );
    }

    // ── Step 3: Parse deep link parameters ───────────────────────────────────
    final callbackUri = Uri.parse(resultUrl);
    final status = callbackUri.queryParameters['status'];
    final errorMessage = callbackUri.queryParameters['message'];
    final returnedConnectionId =
        callbackUri.queryParameters['connection_id'] ?? connectionId;

    dev.log('[$_tag] Callback params: status=$status connection_id=$returnedConnectionId', name: _tag);

    if (status != 'success') {
      dev.log('[$_tag] OAuth failed: $errorMessage', name: _tag);
      throw AmazonOAuthException(
        errorMessage != null && errorMessage.isNotEmpty
            ? 'Amazon authorization failed: $errorMessage'
            : 'Amazon authorization failed (status: $status)',
      );
    }

    // ── Step 4: Confirm connection status with backend ────────────────────────
    final statusPath =
        '${AmazonOAuthConstants.connectionStatusBasePath}/$returnedConnectionId/status';
    dev.log('[$_tag] Verifying connection: GET $statusPath', name: _tag);

    final statusResp = await _apiClient.get<Map<String, dynamic>>(statusPath);
    final result = AmazonOAuthResult.fromStatusJson(
      returnedConnectionId,
      statusResp.data!,
    );

    dev.log(
      '[$_tag] Connected ✓ selling_partner_id=${result.sellingPartnerId} '
      'marketplace=${result.marketplaceId}',
      name: _tag,
    );

    return result;
  }
}

class AmazonOAuthException implements Exception {
  const AmazonOAuthException(this.message);
  final String message;

  @override
  String toString() => 'AmazonOAuthException: $message';
}
