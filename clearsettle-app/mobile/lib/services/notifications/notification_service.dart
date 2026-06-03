import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/network/api_client.dart';

/// Notification service — polling-based with FCM registration support.
///
/// ## How it works (current)
/// 1. On login: register a placeholder device token with the backend
///    POST /notifications/register
/// 2. Alerts are fetched via polling: GET /dashboard/notifications
///    (see alerts_provider.dart)
///
/// ## Enabling real push notifications (Firebase setup required)
/// 1. Create a Firebase project at https://console.firebase.google.com
/// 2. Add an Android app with package name: com.clearsettle.mobile
/// 3. Download google-services.json → place in clearsettle-app/mobile/android/app/
/// 4. Add to pubspec.yaml:
///      firebase_core: ^3.x
///      firebase_messaging: ^15.x
/// 5. Update android/build.gradle to include Google Services plugin
/// 6. Uncomment the FirebaseMessaging code below and call initialize() on app start
/// 7. On server: set FIREBASE_SERVICE_ACCOUNT_JSON env var with the JSON key file content
class NotificationService {
  NotificationService({required this.apiClient});

  final ApiClient apiClient;

  /// Call once after successful login.
  /// Registers this device with the backend for future push delivery.
  Future<void> registerDevice() async {
    try {
      // NOTE: Replace with real FCM token once Firebase is configured:
      //   final fcmToken = await FirebaseMessaging.instance.getToken();
      //   if (fcmToken == null) return;
      const fcmToken = 'polling_mode'; // placeholder until Firebase is configured

      await apiClient.post<void>(
        '/notifications/register',
        data: {
          'fcm_token': fcmToken,
          'platform': 'android',
        },
      );
    } catch (_) {
      // Non-fatal: app continues without push notifications
    }
  }

  /// Call on logout. Removes this device's token from the backend.
  Future<void> unregisterDevice() async {
    try {
      await apiClient.delete<void>('/notifications/device?fcm_token=polling_mode');
    } catch (_) {}
  }
}

final notificationServiceProvider = Provider<NotificationService>((ref) {
  return NotificationService(apiClient: ref.read(apiClientProvider));
});
