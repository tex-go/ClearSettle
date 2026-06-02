// Generated from google-services.json for project clearsettle-mobile.
// App ID: 1:684235532058:android:80f406a4891f42791deea3 (com.clearsettle.mobile)
// Re-run `flutterfire configure` after updating google-services.json.
import 'package:firebase_core/firebase_core.dart' show FirebaseOptions;
import 'package:flutter/foundation.dart'
    show defaultTargetPlatform, kIsWeb, TargetPlatform;

class DefaultFirebaseOptions {
  static FirebaseOptions get currentPlatform {
    if (kIsWeb) throw UnsupportedError('Web not configured.');
    switch (defaultTargetPlatform) {
      case TargetPlatform.android:
        return android;
      case TargetPlatform.iOS:
        throw UnsupportedError('iOS not configured.');
      default:
        throw UnsupportedError(
          'DefaultFirebaseOptions are not supported for this platform.',
        );
    }
  }

  static const FirebaseOptions android = FirebaseOptions(
    apiKey: 'AIzaSyCF-MGq7sSc89l6mEEoPheM6jE3Ml-QBOo',
    appId: '1:684235532058:android:80f406a4891f42791deea3',
    messagingSenderId: '684235532058',
    projectId: 'clearsettle-mobile',
    storageBucket: 'clearsettle-mobile.firebasestorage.app',
  );
}
