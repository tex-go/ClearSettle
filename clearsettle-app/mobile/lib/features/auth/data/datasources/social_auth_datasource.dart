import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_web_auth_2/flutter_web_auth_2.dart';
import 'package:google_sign_in/google_sign_in.dart';

import '../../../../core/network/api_client.dart';
import '../../../../core/network/api_endpoints.dart';
import '../../../../core/utils/cs_logger.dart';
import '../models/auth_response_model.dart';

// ── Provider ──────────────────────────────────────────────────────────────────

final socialAuthDataSourceProvider = Provider<SocialAuthDataSource>((ref) {
  return SocialAuthDataSource(apiClient: ref.read(apiClientProvider));
});

// ── Social login result ───────────────────────────────────────────────────────

class SocialAuthResponse {
  const SocialAuthResponse({
    required this.auth,
    required this.isNewUser,
    required this.isNewLink,
    required this.needsEmail,
    this.placeholderEmail = '',
  });

  final AuthResponseModel auth;
  final bool isNewUser;
  final bool isNewLink;
  /// True for Instagram personal accounts — no email from IdP.
  /// When true, show an email-input dialog before completing setup.
  final bool needsEmail;
  final String placeholderEmail;

  factory SocialAuthResponse.fromJson(Map<String, dynamic> json) {
    return SocialAuthResponse(
      auth:             AuthResponseModel.fromJson(json),
      isNewUser:        json['is_new_user'] as bool? ?? false,
      isNewLink:        json['is_new_link'] as bool? ?? false,
      needsEmail:       json['needs_email'] as bool? ?? false,
      placeholderEmail: json['placeholder_email'] as String? ?? '',
    );
  }
}

// ── Instagram OAuth constants ─────────────────────────────────────────────────

abstract final class InstagramOAuthConstants {
  /// Registered in Meta App dashboard → Instagram Basic Display → OAuth Redirect URIs
  static const String redirectUri = 'clearsettle://oauth/instagram/callback';
  static const String callbackScheme = 'clearsettle';

  /// Replace with your Meta App ID
  static const String appId = String.fromEnvironment(
    'INSTAGRAM_APP_ID',
    defaultValue: 'YOUR_INSTAGRAM_APP_ID',
  );

  static String authUrl() =>
      'https://api.instagram.com/oauth/authorize'
      '?client_id=$appId'
      '&redirect_uri=${Uri.encodeComponent(redirectUri)}'
      '&scope=user_profile,user_media'
      '&response_type=code';
}

// ── Data source ───────────────────────────────────────────────────────────────

class SocialAuthDataSource {
  const SocialAuthDataSource({required this.apiClient});

  final ApiClient apiClient;

  // ── Google Login ─────────────────────────────────────────────────────────

  /// Signs in with Google and returns a ClearSettle JWT.
  ///
  /// Uses [google_sign_in] which opens a native Google account picker.
  /// The ID token is validated server-side.
  Future<SocialAuthResponse> loginWithGoogle() async {
    CsLogger.info('SocialAuth', 'Google login started');

    final googleSignIn = GoogleSignIn(
      // serverClientId is the Web OAuth 2.0 Client ID from Google Cloud Console.
      // The ID token sent to the backend must be issued for this client ID.
      serverClientId: const String.fromEnvironment(
        'GOOGLE_SERVER_CLIENT_ID',
        defaultValue: '',
      ),
      scopes: ['email', 'profile'],
    );

    GoogleSignInAccount? account;
    try {
      account = await googleSignIn.signIn();
    } catch (e) {
      CsLogger.error('SocialAuth', 'Google sign-in UI error', error: e);
      rethrow;
    }

    if (account == null) {
      // User cancelled the sign-in dialog
      throw Exception('Google sign-in was cancelled.');
    }

    final auth = await account.authentication;
    final idToken = auth.idToken;

    if (idToken == null || idToken.isEmpty) {
      throw Exception(
        'Google did not return an ID token. '
        'Ensure serverClientId is set correctly in GoogleSignIn.',
      );
    }

    CsLogger.info('SocialAuth', 'Google ID token obtained', data: {
      'email':    account.email,
      'has_token': true,
    });

    final response = await apiClient.post<Map<String, dynamic>>(
      ApiEndpoints.googleLogin,
      data: {'id_token': idToken},
    );

    final body = response.data as Map<String, dynamic>;
    CsLogger.info('SocialAuth', 'Google login response', data: {
      'is_new_user': body['is_new_user'],
      'is_new_link': body['is_new_link'],
      'needs_email': body['needs_email'],
    });

    return SocialAuthResponse.fromJson(body);
  }

  // ── Instagram Login ──────────────────────────────────────────────────────

  /// Opens Instagram OAuth via [flutter_web_auth_2] and returns a ClearSettle JWT.
  ///
  /// Uses Instagram Basic Display API (personal accounts, no email returned).
  /// When the response has [SocialAuthResponse.needsEmail] = true, show an
  /// email-input dialog so the user can set their real email address.
  Future<SocialAuthResponse> loginWithInstagram() async {
    CsLogger.info('SocialAuth', 'Instagram OAuth started');

    // Open Instagram auth in Chrome Custom Tab
    String result;
    try {
      result = await FlutterWebAuth2.authenticate(
        url:           InstagramOAuthConstants.authUrl(),
        callbackUrlScheme: InstagramOAuthConstants.callbackScheme,
      );
    } catch (e) {
      CsLogger.error('SocialAuth', 'Instagram OAuth UI error', error: e);
      if (e.toString().contains('cancel') || e.toString().contains('Cancel')) {
        throw Exception('Instagram login was cancelled.');
      }
      rethrow;
    }

    // Extract authorization code from redirect URI
    final uri  = Uri.parse(result);
    final code = uri.queryParameters['code'];
    final error = uri.queryParameters['error'];

    if (error != null) {
      throw Exception('Instagram OAuth error: $error');
    }
    if (code == null || code.isEmpty) {
      throw Exception('Instagram did not return an authorization code.');
    }

    CsLogger.info('SocialAuth', 'Instagram code received', data: {'has_code': true});

    final response = await apiClient.post<Map<String, dynamic>>(
      ApiEndpoints.instagramLogin,
      data: {
        'code':         code,
        'redirect_uri': InstagramOAuthConstants.redirectUri,
      },
    );

    final body = response.data as Map<String, dynamic>;
    CsLogger.info('SocialAuth', 'Instagram login response', data: {
      'is_new_user': body['is_new_user'],
      'needs_email': body['needs_email'],
    });

    return SocialAuthResponse.fromJson(body);
  }

  // ── List linked providers ────────────────────────────────────────────────

  Future<List<Map<String, dynamic>>> fetchLinkedProviders() async {
    final response = await apiClient.get<Map<String, dynamic>>(
      ApiEndpoints.socialAccounts,
    );
    final body = response.data as Map<String, dynamic>;
    final list  = body['providers'] as List? ?? [];
    return list.cast<Map<String, dynamic>>();
  }

  // ── Unlink provider ──────────────────────────────────────────────────────

  Future<void> unlinkProvider(String provider) async {
    await apiClient.delete<Map<String, dynamic>>(
      ApiEndpoints.unlinkSocial(provider),
    );
  }
}
