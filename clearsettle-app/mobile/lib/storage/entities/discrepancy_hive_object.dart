import 'package:hive_flutter/hive_flutter.dart';

import '../../core/constants/hive_constants.dart';

class DiscrepancyHiveObject extends HiveObject {
  DiscrepancyHiveObject({
    required this.id,
    required this.reportId,
    required this.type,
    required this.severity,
    required this.description,
    required this.expectedAmount,
    required this.actualAmount,
    required this.variance,
    required this.createdAt,
    this.orderId,
    this.feeType,
    this.ruleName,
    this.isResolved = false,
  });

  String id;
  String reportId;
  String type;       // DiscrepancyType.name
  String severity;   // DiscrepancySeverity.name
  String description;
  double expectedAmount;
  double actualAmount;
  double variance;
  String createdAt;
  String? orderId;
  String? feeType;
  String? ruleName;
  bool isResolved;
}

class DiscrepancyHiveObjectAdapter extends TypeAdapter<DiscrepancyHiveObject> {
  @override
  final int typeId = HiveConstants.discrepancyTypeId;

  @override
  DiscrepancyHiveObject read(BinaryReader reader) {
    final numOfFields = reader.readByte();
    final fields = <int, dynamic>{
      for (int i = 0; i < numOfFields; i++) reader.readByte(): reader.read(),
    };
    return DiscrepancyHiveObject(
      id: fields[0] as String,
      reportId: fields[1] as String,
      type: fields[2] as String,
      severity: fields[3] as String,
      description: fields[4] as String,
      expectedAmount: fields[5] as double? ?? 0.0,
      actualAmount: fields[6] as double? ?? 0.0,
      variance: fields[7] as double? ?? 0.0,
      createdAt: fields[8] as String,
      orderId: fields[9] as String?,
      feeType: fields[10] as String?,
      ruleName: fields[11] as String?,
      isResolved: fields[12] as bool? ?? false,
    );
  }

  @override
  void write(BinaryWriter writer, DiscrepancyHiveObject obj) {
    writer
      ..writeByte(13)
      ..writeByte(0)
      ..write(obj.id)
      ..writeByte(1)
      ..write(obj.reportId)
      ..writeByte(2)
      ..write(obj.type)
      ..writeByte(3)
      ..write(obj.severity)
      ..writeByte(4)
      ..write(obj.description)
      ..writeByte(5)
      ..write(obj.expectedAmount)
      ..writeByte(6)
      ..write(obj.actualAmount)
      ..writeByte(7)
      ..write(obj.variance)
      ..writeByte(8)
      ..write(obj.createdAt)
      ..writeByte(9)
      ..write(obj.orderId)
      ..writeByte(10)
      ..write(obj.feeType)
      ..writeByte(11)
      ..write(obj.ruleName)
      ..writeByte(12)
      ..write(obj.isResolved);
  }
}
