sealed class Failure {
  const Failure(this.message);
  final String message;
}

final class NetworkFailure extends Failure {
  const NetworkFailure([super.message = 'No internet connection. Please check your network.']);
}

final class AuthFailure extends Failure {
  const AuthFailure([super.message = 'Authentication failed. Please login again.']);
}

final class ServerFailure extends Failure {
  const ServerFailure([super.message = 'Server error. Please try again later.']);
  factory ServerFailure.withCode(int code) =>
      ServerFailure('Server returned error $code. Please try again.');
}

final class CacheFailure extends Failure {
  const CacheFailure([super.message = 'Failed to read from local storage.']);
}

final class ValidationFailure extends Failure {
  const ValidationFailure(super.message);
}
