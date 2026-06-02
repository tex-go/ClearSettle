class NetworkException implements Exception {
  const NetworkException([this.message = 'No internet connection.']);
  final String message;

  @override
  String toString() => 'NetworkException: $message';
}

class UnauthorizedException implements Exception {
  const UnauthorizedException([this.message = 'Session expired. Please login again.']);
  final String message;

  @override
  String toString() => 'UnauthorizedException: $message';
}

class ServerException implements Exception {
  const ServerException({this.message = 'Server error. Please try again.', this.statusCode});
  final String message;
  final int? statusCode;

  @override
  String toString() => 'ServerException($statusCode): $message';
}

class CacheException implements Exception {
  const CacheException([this.message = 'Local storage error.']);
  final String message;

  @override
  String toString() => 'CacheException: $message';
}

class ValidationException implements Exception {
  const ValidationException(this.message);
  final String message;

  @override
  String toString() => 'ValidationException: $message';
}
