import 'package:hive_flutter/hive_flutter.dart';

import '../../core/constants/hive_constants.dart';

class LocalReportHiveObject extends HiveObject {
  LocalReportHiveObject({
    required this.id,
    required this.fileName,
    required this.platform,
    required this.reportType,
    required this.uploadedAt,
    required this.status,
    this.filePath,
    this.totalOrders = 0,
    this.totalAmount = 0.0,
    this.errorMessage,
    this.serverId,
    // Fields 11–18: added in Phase 2 (backward-compatible)
    this.fileSize = 0,
    this.fileHash,
    this.parsedAt,
    this.grossRevenue = 0.0,
    this.totalFees = 0.0,
    this.netSettlement = 0.0,
    this.discrepancyCount = 0,
    this.parserVersion,
  });

  String id;
  String fileName;
  String platform;
  String reportType;
  String uploadedAt;
  String status; // 'pending_parse' | 'parsing' | 'parsed' | 'failed'
  String? filePath;
  int totalOrders;
  double totalAmount;     // kept for backward compat; use grossRevenue for new code
  String? errorMessage;
  String? serverId;

  // Phase 2 additions
  int fileSize;           // bytes
  String? fileHash;       // SHA-256 hex
  String? parsedAt;       // ISO-8601
  double grossRevenue;
  double totalFees;
  double netSettlement;
  int discrepancyCount;
  String? parserVersion;
}

class LocalReportHiveObjectAdapter extends TypeAdapter<LocalReportHiveObject> {
  @override
  final int typeId = HiveConstants.localReportTypeId;

  @override
  LocalReportHiveObject read(BinaryReader reader) {
    final numOfFields = reader.readByte();
    final fields = <int, dynamic>{
      for (int i = 0; i < numOfFields; i++) reader.readByte(): reader.read(),
    };
    return LocalReportHiveObject(
      id: fields[0] as String,
      fileName: fields[1] as String,
      platform: fields[2] as String,
      reportType: fields[3] as String,
      uploadedAt: fields[4] as String,
      status: fields[5] as String,
      filePath: fields[6] as String?,
      totalOrders: fields[7] as int? ?? 0,
      totalAmount: fields[8] as double? ?? 0.0,
      errorMessage: fields[9] as String?,
      serverId: fields[10] as String?,
      fileSize: fields[11] as int? ?? 0,
      fileHash: fields[12] as String?,
      parsedAt: fields[13] as String?,
      grossRevenue: fields[14] as double? ?? 0.0,
      totalFees: fields[15] as double? ?? 0.0,
      netSettlement: fields[16] as double? ?? 0.0,
      discrepancyCount: fields[17] as int? ?? 0,
      parserVersion: fields[18] as String?,
    );
  }

  @override
  void write(BinaryWriter writer, LocalReportHiveObject obj) {
    writer
      ..writeByte(19)
      ..writeByte(0)
      ..write(obj.id)
      ..writeByte(1)
      ..write(obj.fileName)
      ..writeByte(2)
      ..write(obj.platform)
      ..writeByte(3)
      ..write(obj.reportType)
      ..writeByte(4)
      ..write(obj.uploadedAt)
      ..writeByte(5)
      ..write(obj.status)
      ..writeByte(6)
      ..write(obj.filePath)
      ..writeByte(7)
      ..write(obj.totalOrders)
      ..writeByte(8)
      ..write(obj.totalAmount)
      ..writeByte(9)
      ..write(obj.errorMessage)
      ..writeByte(10)
      ..write(obj.serverId)
      ..writeByte(11)
      ..write(obj.fileSize)
      ..writeByte(12)
      ..write(obj.fileHash)
      ..writeByte(13)
      ..write(obj.parsedAt)
      ..writeByte(14)
      ..write(obj.grossRevenue)
      ..writeByte(15)
      ..write(obj.totalFees)
      ..writeByte(16)
      ..write(obj.netSettlement)
      ..writeByte(17)
      ..write(obj.discrepancyCount)
      ..writeByte(18)
      ..write(obj.parserVersion);
  }
}
