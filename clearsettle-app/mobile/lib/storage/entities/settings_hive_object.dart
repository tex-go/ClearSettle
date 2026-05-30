import 'package:hive_flutter/hive_flutter.dart';

import '../../core/constants/hive_constants.dart';

class SettingsHiveObject extends HiveObject {
  SettingsHiveObject({
    required this.id,
    this.isDarkMode = false,
    this.notificationsEnabled = true,
    this.biometricEnabled = false,
    this.autoSyncEnabled = true,
    this.defaultMarketplace = 'flipkart',
    this.currencyLocale = 'en_IN',
    this.updatedAt,
  });

  String id;
  bool isDarkMode;
  bool notificationsEnabled;
  bool biometricEnabled;
  bool autoSyncEnabled;
  String defaultMarketplace;
  String currencyLocale;
  String? updatedAt;
}

class SettingsHiveObjectAdapter extends TypeAdapter<SettingsHiveObject> {
  @override
  final int typeId = HiveConstants.settingsTypeId;

  @override
  SettingsHiveObject read(BinaryReader reader) {
    final numOfFields = reader.readByte();
    final fields = <int, dynamic>{
      for (int i = 0; i < numOfFields; i++) reader.readByte(): reader.read(),
    };
    return SettingsHiveObject(
      id: fields[0] as String,
      isDarkMode: fields[1] as bool? ?? false,
      notificationsEnabled: fields[2] as bool? ?? true,
      biometricEnabled: fields[3] as bool? ?? false,
      autoSyncEnabled: fields[4] as bool? ?? true,
      defaultMarketplace: fields[5] as String? ?? 'flipkart',
      currencyLocale: fields[6] as String? ?? 'en_IN',
      updatedAt: fields[7] as String?,
    );
  }

  @override
  void write(BinaryWriter writer, SettingsHiveObject obj) {
    writer
      ..writeByte(8)
      ..writeByte(0)
      ..write(obj.id)
      ..writeByte(1)
      ..write(obj.isDarkMode)
      ..writeByte(2)
      ..write(obj.notificationsEnabled)
      ..writeByte(3)
      ..write(obj.biometricEnabled)
      ..writeByte(4)
      ..write(obj.autoSyncEnabled)
      ..writeByte(5)
      ..write(obj.defaultMarketplace)
      ..writeByte(6)
      ..write(obj.currencyLocale)
      ..writeByte(7)
      ..write(obj.updatedAt);
  }
}
