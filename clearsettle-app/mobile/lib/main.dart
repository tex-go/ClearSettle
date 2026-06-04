import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_crashlytics/firebase_crashlytics.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'app.dart';
import 'core/utils/cs_logger.dart';
import 'firebase_options.dart';
import 'storage/hive_manager.dart';

/// Top-level handler — runs in an isolate when the app is terminated/backgrounded.
@pragma('vm:entry-point')
Future<void> _firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  await Firebase.initializeApp(options: DefaultFirebaseOptions.currentPlatform);
}

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  await Firebase.initializeApp(options: DefaultFirebaseOptions.currentPlatform);

  // ── Crashlytics — catch all Flutter framework errors ──────────────────────
  FlutterError.onError = FirebaseCrashlytics.instance.recordFlutterFatalError;

  // ── Initialize structured logger (sets up Crashlytics bridge) ────────────
  CsLogger.init();
  CsLogger.section('ClearSettle App Starting');

  FirebaseMessaging.onBackgroundMessage(_firebaseMessagingBackgroundHandler);

  await SystemChrome.setPreferredOrientations([
    DeviceOrientation.portraitUp,
    DeviceOrientation.portraitDown,
  ]);

  await HiveManager.initialize();
  CsLogger.info('Startup', 'Hive initialized');

  // Wrap runApp in PlatformDispatcher error zone to catch async errors
  runApp(
    const ProviderScope(
      child: ClearSettleApp(),
    ),
  );
}
