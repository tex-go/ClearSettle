import 'package:flutter/services.dart' show PlatformException;

import 'exceptions.dart';

/// Translates any OAuth-related exception into a user-facing string.
///
/// Rules:
///  - Never expose raw exception class names, status codes, or internal details.
///  - Every path returns a complete, actionable sentence.
///  - Kept in core/errors/ so it only imports core types + flutter/services;
///    marketplace-specific exception classes are not referenced here.
class OAuthErrorMapper {
  const OAuthErrorMapper._();

  static String toUserMessage(Object error) {
    if (error is NetworkException) {
      return 'No internet connection. Please check your network and try again.';
    }

    if (error is UnauthorizedException) {
      return 'Your session has expired. Please log in and try again.';
    }

    if (error is ServerException) {
      return _fromServerException(error);
    }

    if (error is PlatformException) {
      // flutter_web_auth_2 throws CANCELED when the browser closes
      // without delivering a redirect (real cancellation or misconfigured
      // redirect URI / missing CallbackActivity).
      return error.code == 'CANCELED'
          ? 'Connection cancelled. You can try again anytime.'
          : 'Connection failed. Please try again.';
    }

    // Covers FlipkartOAuthException, AmazonOAuthException, and any other
    // internal exceptions — none of their messages should reach the user.
    return 'Unable to connect right now. Please try again in a few minutes.';
  }

  static String _fromServerException(ServerException e) {
    switch (e.statusCode) {
      case 401:
        return 'Authentication failed. Please log in and try again.';
      case 403:
        return 'Access denied. Please contact support if this continues.';
      case 408:
      case 504:
        return 'Connection timed out. Please check your network and try again.';
      case 429:
        return 'Too many requests. Please wait a moment and try again.';
      case 502:
      case 503:
        return 'Marketplace connection is temporarily unavailable. '
            'Our team has been notified. Please try again later.';
      default:
        return 'Something went wrong. Please try again.';
    }
  }
}
