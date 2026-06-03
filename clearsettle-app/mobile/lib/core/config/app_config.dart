abstract final class AppConfig {
  // Production: http://clearsettle.in/api (nginx strips /api before forwarding to backend)
  // Local dev:  --dart-define=API_BASE_URL=http://10.0.2.2:8000  (Android emulator)
  //             --dart-define=API_BASE_URL=http://localhost:8000  (iOS simulator / desktop)
  static const String apiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'https://clearsettle.in/api',
  );

  // Super-admin email prefill on the login screen.
  // This is the default display email — not a secret.
  // Override at build time: --dart-define=SUPER_ADMIN_EMAIL=...
  static const String superAdminEmail = String.fromEnvironment(
    'SUPER_ADMIN_EMAIL',
    defaultValue: 'admin@clearsettle.com',
  );

  static const String superAdminPassword = String.fromEnvironment(
    'SUPER_ADMIN_PASSWORD',
    defaultValue: 'Admin@12345',
  );

  static const Duration connectTimeout = Duration(seconds: 30);
  static const Duration receiveTimeout = Duration(seconds: 30);
  static const Duration sendTimeout = Duration(seconds: 60);

  static const String appName = 'ClearSettle';
  static const String appVersion = '1.5.3';

  static const Duration syncInterval = Duration(minutes: 15);
  static const int maxSyncRetries = 3;
  static const int defaultPageSize = 20;

  static const int maxFileUploadMb = 50;
}
