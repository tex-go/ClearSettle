import 'package:hive_flutter/hive_flutter.dart';

import '../../core/constants/hive_constants.dart';

class MarketplaceHiveObject extends HiveObject {
  MarketplaceHiveObject({
    required this.id,
    required this.platform,
    required this.displayName,
    required this.connectedAt,
    this.isActive = true,
    this.lastSyncAt,
    this.sellerId,
  });

  String id;
  String platform;
  String displayName;
  String connectedAt;
  bool isActive;
  String? lastSyncAt;
  String? sellerId;
}

class MarketplaceHiveObjectAdapter extends TypeAdapter<MarketplaceHiveObject> {
  @override
  final int typeId = HiveConstants.marketplaceTypeId;

  @override
  MarketplaceHiveObject read(BinaryReader reader) {
    final numOfFields = reader.readByte();
    final fields = <int, dynamic>{
      for (int i = 0; i < numOfFields; i++) reader.readByte(): reader.read(),
    };
    return MarketplaceHiveObject(
      id: fields[0] as String,
      platform: fields[1] as String,
      displayName: fields[2] as String,
      connectedAt: fields[3] as String,
      isActive: fields[4] as bool? ?? true,
      lastSyncAt: fields[5] as String?,
      sellerId: fields[6] as String?,
    );
  }

  @override
  void write(BinaryWriter writer, MarketplaceHiveObject obj) {
    writer
      ..writeByte(7)
      ..writeByte(0)
      ..write(obj.id)
      ..writeByte(1)
      ..write(obj.platform)
      ..writeByte(2)
      ..write(obj.displayName)
      ..writeByte(3)
      ..write(obj.connectedAt)
      ..writeByte(4)
      ..write(obj.isActive)
      ..writeByte(5)
      ..write(obj.lastSyncAt)
      ..writeByte(6)
      ..write(obj.sellerId);
  }
}
