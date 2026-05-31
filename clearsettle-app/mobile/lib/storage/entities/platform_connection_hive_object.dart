import 'package:hive_flutter/hive_flutter.dart';

import '../../core/constants/hive_constants.dart';

class PlatformConnectionHiveObject extends HiveObject {
  PlatformConnectionHiveObject({
    required this.platform,
    required this.isConnected,
    this.sellerId,
    this.sellerName,
    this.connectedAt,
    this.tokenExpiresAt,
  });

  String platform;
  bool isConnected;
  String? sellerId;
  String? sellerName;
  String? connectedAt;    // ISO-8601
  String? tokenExpiresAt; // ISO-8601
}

class PlatformConnectionHiveObjectAdapter
    extends TypeAdapter<PlatformConnectionHiveObject> {
  @override
  final int typeId = HiveConstants.platformConnectionTypeId;

  @override
  PlatformConnectionHiveObject read(BinaryReader reader) {
    final numOfFields = reader.readByte();
    final fields = <int, dynamic>{
      for (int i = 0; i < numOfFields; i++) reader.readByte(): reader.read(),
    };
    return PlatformConnectionHiveObject(
      platform: fields[0] as String,
      isConnected: fields[1] as bool? ?? false,
      sellerId: fields[2] as String?,
      sellerName: fields[3] as String?,
      connectedAt: fields[4] as String?,
      tokenExpiresAt: fields[5] as String?,
    );
  }

  @override
  void write(BinaryWriter writer, PlatformConnectionHiveObject obj) {
    writer
      ..writeByte(6)
      ..writeByte(0)
      ..write(obj.platform)
      ..writeByte(1)
      ..write(obj.isConnected)
      ..writeByte(2)
      ..write(obj.sellerId)
      ..writeByte(3)
      ..write(obj.sellerName)
      ..writeByte(4)
      ..write(obj.connectedAt)
      ..writeByte(5)
      ..write(obj.tokenExpiresAt);
  }
}
