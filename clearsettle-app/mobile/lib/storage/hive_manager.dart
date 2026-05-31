import 'dart:convert';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:hive_flutter/hive_flutter.dart';

import '../core/constants/hive_constants.dart';
import 'entities/discrepancy_hive_object.dart';
import 'entities/local_report_hive_object.dart';
import 'entities/marketplace_hive_object.dart';
import 'entities/pending_action_hive_object.dart';
import 'entities/platform_connection_hive_object.dart';
import 'entities/report_summary_hive_object.dart';
import 'entities/settings_hive_object.dart';
import 'entities/sync_queue_hive_object.dart';
import 'entities/sync_status_hive_object.dart';
import 'entities/user_hive_object.dart';

class HiveManager {
  static const _secureStorage = FlutterSecureStorage(
    aOptions: AndroidOptions(encryptedSharedPreferences: true),
  );
  static const _encryptionKeyName = 'cs_hive_aes_key';

  static Future<void> initialize() async {
    await Hive.initFlutter();

    Hive
      ..registerAdapter(UserHiveObjectAdapter())
      ..registerAdapter(MarketplaceHiveObjectAdapter())
      ..registerAdapter(LocalReportHiveObjectAdapter())
      ..registerAdapter(SettingsHiveObjectAdapter())
      ..registerAdapter(SyncQueueHiveObjectAdapter())
      ..registerAdapter(PendingActionHiveObjectAdapter())
      ..registerAdapter(SyncStatusHiveObjectAdapter())
      ..registerAdapter(ReportSummaryHiveObjectAdapter())
      ..registerAdapter(DiscrepancyHiveObjectAdapter())
      ..registerAdapter(PlatformConnectionHiveObjectAdapter());

    final cipher = HiveAesCipher(await _encryptionKey());

    await Future.wait([
      // Sensitive boxes — encrypted with AES-256
      Hive.openBox<UserHiveObject>(HiveConstants.userBox, encryptionCipher: cipher),
      Hive.openBox<LocalReportHiveObject>(HiveConstants.localReportBox, encryptionCipher: cipher),
      Hive.openBox<ReportSummaryHiveObject>(HiveConstants.reportSummaryBox, encryptionCipher: cipher),
      Hive.openBox<DiscrepancyHiveObject>(HiveConstants.discrepancyBox, encryptionCipher: cipher),
      // Non-sensitive boxes — unencrypted for performance
      Hive.openBox<MarketplaceHiveObject>(HiveConstants.marketplaceBox),
      Hive.openBox<SettingsHiveObject>(HiveConstants.settingsBox),
      Hive.openBox<SyncQueueHiveObject>(HiveConstants.syncQueueBox),
      Hive.openBox<PendingActionHiveObject>(HiveConstants.pendingActionsBox),
      Hive.openBox<SyncStatusHiveObject>(HiveConstants.syncStatusBox),
      Hive.openBox<String>(HiveConstants.cacheBox),
      // Encrypted — stores OAuth tokens & seller identifiers
      Hive.openBox<PlatformConnectionHiveObject>(
        HiveConstants.platformConnectionBox,
        encryptionCipher: cipher,
      ),
    ]);
  }

  // ── Getters ───────────────────────────────────────────────────────────────

  static Box<UserHiveObject> get userBox =>
      Hive.box<UserHiveObject>(HiveConstants.userBox);

  static Box<MarketplaceHiveObject> get marketplaceBox =>
      Hive.box<MarketplaceHiveObject>(HiveConstants.marketplaceBox);

  static Box<LocalReportHiveObject> get localReportBox =>
      Hive.box<LocalReportHiveObject>(HiveConstants.localReportBox);

  static Box<SettingsHiveObject> get settingsBox =>
      Hive.box<SettingsHiveObject>(HiveConstants.settingsBox);

  static Box<SyncQueueHiveObject> get syncQueueBox =>
      Hive.box<SyncQueueHiveObject>(HiveConstants.syncQueueBox);

  static Box<PendingActionHiveObject> get pendingActionsBox =>
      Hive.box<PendingActionHiveObject>(HiveConstants.pendingActionsBox);

  static Box<SyncStatusHiveObject> get syncStatusBox =>
      Hive.box<SyncStatusHiveObject>(HiveConstants.syncStatusBox);

  static Box<ReportSummaryHiveObject> get reportSummaryBox =>
      Hive.box<ReportSummaryHiveObject>(HiveConstants.reportSummaryBox);

  static Box<DiscrepancyHiveObject> get discrepancyBox =>
      Hive.box<DiscrepancyHiveObject>(HiveConstants.discrepancyBox);

  static Box<String> get cacheBox =>
      Hive.box<String>(HiveConstants.cacheBox);

  static Box<PlatformConnectionHiveObject> get platformConnectionBox =>
      Hive.box<PlatformConnectionHiveObject>(
          HiveConstants.platformConnectionBox);

  // ── Lifecycle ─────────────────────────────────────────────────────────────

  static Future<void> clearAll() async {
    await Future.wait([
      userBox.clear(),
      marketplaceBox.clear(),
      localReportBox.clear(),
      settingsBox.clear(),
      syncQueueBox.clear(),
      pendingActionsBox.clear(),
      syncStatusBox.clear(),
      reportSummaryBox.clear(),
      discrepancyBox.clear(),
      cacheBox.clear(),
      platformConnectionBox.clear(),
    ]);
  }

  static Future<void> close() async => Hive.close();

  // ── AES-256 key management (security-agent) ───────────────────────────────

  static Future<List<int>> _encryptionKey() async {
    final stored = await _secureStorage.read(key: _encryptionKeyName);
    if (stored != null) return base64.decode(stored);

    final key = Hive.generateSecureKey();
    await _secureStorage.write(
      key: _encryptionKeyName,
      value: base64.encode(key),
    );
    return key;
  }
}
