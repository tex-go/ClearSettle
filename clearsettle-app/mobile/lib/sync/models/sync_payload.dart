enum SyncEntityType { report, discrepancy, settings, marketplace }

enum SyncOperation { create, update, delete }

class SyncPayload {
  const SyncPayload({
    required this.id,
    required this.entityType,
    required this.operation,
    required this.data,
    required this.timestamp,
    this.userId,
    this.deviceId,
    this.version = 1,
  });

  final String id;
  final SyncEntityType entityType;
  final SyncOperation operation;
  final Map<String, dynamic> data;
  final DateTime timestamp;
  final String? userId;
  final String? deviceId;
  final int version;

  Map<String, dynamic> toJson() => {
        'id': id,
        'entity_type': entityType.name,
        'operation': operation.name,
        'data': data,
        'timestamp': timestamp.toIso8601String(),
        'user_id': userId,
        'device_id': deviceId,
        'version': version,
      };

  factory SyncPayload.fromJson(Map<String, dynamic> json) => SyncPayload(
        id: json['id'] as String,
        entityType: SyncEntityType.values.byName(json['entity_type'] as String),
        operation: SyncOperation.values.byName(json['operation'] as String),
        data: Map<String, dynamic>.from(json['data'] as Map),
        timestamp: DateTime.parse(json['timestamp'] as String),
        userId: json['user_id'] as String?,
        deviceId: json['device_id'] as String?,
        version: json['version'] as int? ?? 1,
      );
}
