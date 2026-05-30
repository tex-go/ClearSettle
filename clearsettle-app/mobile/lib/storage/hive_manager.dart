import 'package:hive_flutter/hive_flutter.dart';

import '../core/constants/hive_constants.dart';
import 'entities/local_report_hive_object.dart';
import 'entities/marketplace_hive_object.dart';
import 'entities/pending_action_hive_object.dart';
import 'entities/settings_hive_object.dart';
import 'entities/sync_queue_hive_object.dart';
import 'entities/discrepancy_hive_object.dart';
import 'entities/report_summary_hive_object.dart';
import 'entities/sync_status_hive_object.dart';
import 'entities/user_hive_object.dart';

class HiveManager {
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
      ..registerAdapter(DiscrepancyHiveObjectAdapter());

    await Future.wait([
      Hive.openBox<UserHiveObject>(HiveConstants.userBox),
      Hive.openBox<MarketplaceHiveObject>(HiveConstants.marketplaceBox),
      Hive.openBox<LocalReportHiveObject>(HiveConstants.localReportBox),
      Hive.openBox<SettingsHiveObject>(HiveConstants.settingsBox),
      Hive.openBox<SyncQueueHiveObject>(HiveConstants.syncQueueBox),
      Hive.openBox<PendingActionHiveObject>(HiveConstants.pendingActionsBox),
      Hive.openBox<SyncStatusHiveObject>(HiveConstants.syncStatusBox),
      Hive.openBox<ReportSummaryHiveObject>(HiveConstants.reportSummaryBox),
      Hive.openBox<DiscrepancyHiveObject>(HiveConstants.discrepancyBox),
    ]);
  }

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
    ]);
  }

  static Future<void> close() async {
    await Hive.close();
  }
}
