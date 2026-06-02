abstract final class FlipkartOAuthConstants {
  // Register your app at https://seller.flipkart.com/api-docs/FMSAPI.html
  // to obtain these credentials, then replace the placeholders below.
  static const String clientId = 'YOUR_FLIPKART_CLIENT_ID';
  static const String clientSecret = 'YOUR_FLIPKART_CLIENT_SECRET';

  static const String authorizationEndpoint =
      'https://seller.flipkart.com/oauth-service/oauth/authorize';
  static const String tokenEndpoint =
      'https://api.flipkart.com/oauth-service/oauth/token';
  static const String sellerProfileEndpoint =
      'https://api.flipkart.com/sellers/account/details';

  // Must match exactly what you register in the Flipkart developer portal
  static const String redirectUri = 'clearsettle://oauth/flipkart/callback';
  static const String callbackUrlScheme = 'clearsettle';

  // Read-only seller data scope
  static const String scope = 'Seller_Api';

  // flutter_secure_storage keys — prefixed fk_ to avoid collisions
  static const String accessTokenKey = 'fk_access_token';
  static const String refreshTokenKey = 'fk_refresh_token';
  static const String tokenExpiryKey = 'fk_token_expiry';
  static const String oauthStateKey = 'fk_oauth_state';
}
