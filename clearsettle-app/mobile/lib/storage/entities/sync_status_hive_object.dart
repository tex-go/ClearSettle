import 'package:hive_flutter/hive_flutter.dart';

import '../../core/constants/hive_constants.dart';

class SyncStatusHiveObject extends HiveObject {
  SyncStatusHiveObject({
    required this.id,
    required this.entityType,
    required this.status,
    required this.lastSyncAt,
    this.lastError,
    this.pendingCount = 0,
    this.successCount = 0,
    this.failureCount = 0,
  });

  String id;
  String entityType; // 'dashboard', 'reports', 'marketplace'
  String status; // 'idle', 'syncing', 'error', 'success'
  String lastSyncAt;
  String? lastError;
  int pendingCount;
  int successCount;
  int failureCount;
}

class SyncStatusHiveObjectAdapter extends TypeAdapter<SyncStatusHiveObject> {
  @override
  final int typeId = HiveConstants.syncStatusTypeId;

  @override
  SyncStatusHiveObject read(BinaryReader reader) {
    final numOfFields = reader.readByte();
    final fields = <int, dynamic>{
      for (int i = 0; i < numOfFields; i++) reader.readByte(): reader.read(),
    };
    return SyncStatusHiveObject(
      id: fields[0] as String,
      entityType: fields[1] as String,
      status: fields[2] as String,
      lastSyncAt: fields[3] as String,
      lastError: fields[4] as String?,
      pendingCount: fields[5] as int? ?? 0,
      successCount: fields[6] as int? ?? 0,
      failureCount: fields[7] as int? ?? 0,
    );
  }

  @override
  void write(BinaryWriter writer, SyncStatusHiveObject obj) {
    writer
      ..writeByte(8)
      ..writeByte(0)
      ..write(obj.id)
      ..writeByte(1)
      ..write(obj.entityType)
      ..writeByte(2)
      ..write(obj.status)
      ..writeByte(3)
      ..write(obj.lastSyncAt)
      ..writeByte(4)
      ..write(obj.lastError)
      ..writeByte(5)
      ..write(obj.pendingCount)
      ..writeByte(6)
      ..write(obj.successCount)
      ..writeByte(7)
      ..write(obj.failureCount);
  }
}
