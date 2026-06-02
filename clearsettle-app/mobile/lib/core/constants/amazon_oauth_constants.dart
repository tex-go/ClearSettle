abstract final class AmazonOAuthConstants {
  // Callback URL scheme — must match AndroidManifest CallbackActivity data scheme
  static const String callbackUrlScheme = 'clearsettle';

  // Deep link path Amazon/backend redirects to after authorization
  // Full deep link: clearsettle://oauth/amazon/callback?status=success&connection_id=xxx
  static const String callbackPath = '/oauth/amazon/callback';

  // Backend endpoints (relative to ApiClient baseUrl)
  static const String authorizeEndpoint = '/sp-api/authorize';
  static const String connectionStatusBasePath = '/sp-api/connections';

  // Hive / storage key
  static const String connectionKey = 'amazon';
}
