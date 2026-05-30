import 'package:hive_flutter/hive_flutter.dart';

import '../../core/constants/hive_constants.dart';

class PendingActionHiveObject extends HiveObject {
  PendingActionHiveObject({
    required this.id,
    required this.type,
    required this.entity,
    required this.data,
    required this.createdAt,
    this.synced = false,
    this.syncedAt,
  });

  String id;
  String type; // 'create', 'update', 'delete'
  String entity; // 'report', 'settings', 'marketplace'
  String data; // JSON-encoded entity snapshot
  String createdAt;
  bool synced;
  String? syncedAt;
}

class PendingActionHiveObjectAdapter extends TypeAdapter<PendingActionHiveObject> {
  @override
  final int typeId = HiveConstants.pendingActionTypeId;

  @override
  PendingActionHiveObject read(BinaryReader reader) {
    final numOfFields = reader.readByte();
    final fields = <int, dynamic>{
      for (int i = 0; i < numOfFields; i++) reader.readByte(): reader.read(),
    };
    return PendingActionHiveObject(
      id: fields[0] as String,
      type: fields[1] as String,
      entity: fields[2] as String,
      data: fields[3] as String,
      createdAt: fields[4] as String,
      synced: fields[5] as bool? ?? false,
      syncedAt: fields[6] as String?,
    );
  }

  @override
  void write(BinaryWriter writer, PendingActionHiveObject obj) {
    writer
      ..writeByte(7)
      ..writeByte(0)
      ..write(obj.id)
      ..writeByte(1)
      ..write(obj.type)
      ..writeByte(2)
      ..write(obj.entity)
      ..writeByte(3)
      ..write(obj.data)
      ..writeByte(4)
      ..write(obj.createdAt)
      ..writeByte(5)
      ..write(obj.synced)
      ..writeByte(6)
      ..write(obj.syncedAt);
  }
}
