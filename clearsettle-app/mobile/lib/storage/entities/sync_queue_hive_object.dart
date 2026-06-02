import 'package:hive_flutter/hive_flutter.dart';

import '../../core/constants/hive_constants.dart';

class SyncQueueHiveObject extends HiveObject {
  SyncQueueHiveObject({
    required this.id,
    required this.actionType,
    required this.payload,
    required this.createdAt,
    this.retryCount = 0,
    this.status = 'pending',
    this.errorMessage,
    this.scheduledAt,
  });

  String id;
  String actionType; // 'upload_report', 'sync_dashboard', 'sync_marketplace'
  String payload; // JSON-encoded payload
  String createdAt;
  int retryCount;
  String status; // 'pending', 'processing', 'failed', 'completed'
  String? errorMessage;
  String? scheduledAt;
}

class SyncQueueHiveObjectAdapter extends TypeAdapter<SyncQueueHiveObject> {
  @override
  final int typeId = HiveConstants.syncQueueTypeId;

  @override
  SyncQueueHiveObject read(BinaryReader reader) {
    final numOfFields = reader.readByte();
    final fields = <int, dynamic>{
      for (int i = 0; i < numOfFields; i++) reader.readByte(): reader.read(),
    };
    return SyncQueueHiveObject(
      id: fields[0] as String,
      actionType: fields[1] as String,
      payload: fields[2] as String,
      createdAt: fields[3] as String,
      retryCount: fields[4] as int? ?? 0,
      status: fields[5] as String? ?? 'pending',
      errorMessage: fields[6] as String?,
      scheduledAt: fields[7] as String?,
    );
  }

  @override
  void write(BinaryWriter writer, SyncQueueHiveObject obj) {
    writer
      ..writeByte(8)
      ..writeByte(0)
      ..write(obj.id)
      ..writeByte(1)
      ..write(obj.actionType)
      ..writeByte(2)
      ..write(obj.payload)
      ..writeByte(3)
      ..write(obj.createdAt)
      ..writeByte(4)
      ..write(obj.retryCount)
      ..writeByte(5)
      ..write(obj.status)
      ..writeByte(6)
      ..write(obj.errorMessage)
      ..writeByte(7)
      ..write(obj.scheduledAt);
  }
}
