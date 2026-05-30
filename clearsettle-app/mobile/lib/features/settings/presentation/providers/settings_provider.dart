import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:path_provider/path_provider.dart';

import '../../../../core/constants/app_constants.dart';
import '../../../../storage/entities/settings_hive_object.dart';
import '../../../../storage/hive_manager.dart';
import '../../domain/entities/app_settings_entity.dart';

final settingsProvider = NotifierProvider<SettingsNotifier, AppSettingsEntity>(
  SettingsNotifier.new,
);

final themeModeProvider = Provider<ThemeMode>((ref) {
  final settings = ref.watch(settingsProvider);
  return settings.isDarkMode ? ThemeMode.dark : ThemeMode.light;
});

class SettingsNotifier extends Notifier<AppSettingsEntity> {
  @override
  AppSettingsEntity build() => _fromHive();

  AppSettingsEntity _fromHive() {
    final obj = HiveManager.settingsBox.get(AppConstants.settingsKey);
    if (obj == null) {
      final defaults = SettingsHiveObject(id: AppConstants.settingsKey);
      HiveManager.settingsBox.put(AppConstants.settingsKey, defaults);
      return const AppSettingsEntity();
    }
    return AppSettingsEntity(
      isDarkMode: obj.isDarkMode,
      notificationsEnabled: obj.notificationsEnabled,
      biometricEnabled: obj.biometricEnabled,
      autoSyncEnabled: obj.autoSyncEnabled,
      defaultMarketplace: obj.defaultMarketplace,
    );
  }

  Future<void> setDarkMode(bool value) async {
    await _mutate((obj) => obj.isDarkMode = value);
    state = state.copyWith(isDarkMode: value);
  }

  Future<void> setNotifications(bool value) async {
    await _mutate((obj) => obj.notificationsEnabled = value);
    state = state.copyWith(notificationsEnabled: value);
  }

  Future<void> setAutoSync(bool value) async {
    await _mutate((obj) => obj.autoSyncEnabled = value);
    state = state.copyWith(autoSyncEnabled: value);
  }

  Future<int> calculateStorageUsed() async {
    try {
      final docs = await getApplicationDocumentsDirectory();
      final dir = Directory('${docs.path}/ClearSettle/reports');
      if (!dir.existsSync()) return 0;
      int total = 0;
      await for (final entity in dir.list(recursive: true)) {
        if (entity is File) total += await entity.length();
      }
      state = state.copyWith(storageUsedBytes: total);
      return total;
    } catch (_) {
      return 0;
    }
  }

  Future<void> clearAllData() async {
    await HiveManager.clearAll();
    try {
      final docs = await getApplicationDocumentsDirectory();
      final dir = Directory('${docs.path}/ClearSettle');
      if (dir.existsSync()) await dir.delete(recursive: true);
    } catch (_) {}
    state = const AppSettingsEntity();
  }

  Future<void> _mutate(void Function(SettingsHiveObject) apply) async {
    final obj = HiveManager.settingsBox.get(AppConstants.settingsKey) ??
        SettingsHiveObject(id: AppConstants.settingsKey);
    apply(obj);
    obj.updatedAt = DateTime.now().toIso8601String();
    await HiveManager.settingsBox.put(AppConstants.settingsKey, obj);
  }
}
