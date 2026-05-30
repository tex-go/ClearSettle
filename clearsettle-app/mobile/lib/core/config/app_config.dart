abstract final class AppConfig {
  static const String apiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://localhost:8000',
  );

  static const Duration connectTimeout = Duration(seconds: 30);
  static const Duration receiveTimeout = Duration(seconds: 30);
  static const Duration sendTimeout = Duration(seconds: 60);

  static const String appName = 'ClearSettle';
  static const String appVersion = '1.0.0';

  static const Duration syncInterval = Duration(minutes: 15);
  static const int maxSyncRetries = 3;
  static const int defaultPageSize = 20;

  static const int maxFileUploadMb = 50;
}
