import 'package:hive_flutter/hive_flutter.dart';

import '../../core/constants/hive_constants.dart';

class ReportSummaryHiveObject extends HiveObject {
  ReportSummaryHiveObject({
    required this.reportId,
    required this.marketplace,
    required this.totalOrders,
    required this.grossRevenue,
    required this.totalFees,
    required this.totalCommission,
    required this.totalShipping,
    required this.totalGstOnFees,
    required this.totalTcs,
    required this.totalTds,
    required this.netSettlement,
    required this.discrepancyCount,
    required this.criticalCount,
    required this.totalVariance,
    required this.reconciledAt,
    this.amountSettled = 0.0,
    this.amountPending = 0.0,
    this.parserVersion = '1.0.0',
  });

  String reportId;
  String marketplace;
  int totalOrders;
  double grossRevenue;
  double totalFees;
  double totalCommission;
  double totalShipping;
  double totalGstOnFees;
  double totalTcs;
  double totalTds;
  double netSettlement;
  int discrepancyCount;
  int criticalCount;
  double totalVariance;
  String reconciledAt;
  double amountSettled;
  double amountPending;
  String parserVersion;
}

class ReportSummaryHiveObjectAdapter extends TypeAdapter<ReportSummaryHiveObject> {
  @override
  final int typeId = HiveConstants.reportSummaryTypeId;

  @override
  ReportSummaryHiveObject read(BinaryReader reader) {
    final numOfFields = reader.readByte();
    final fields = <int, dynamic>{
      for (int i = 0; i < numOfFields; i++) reader.readByte(): reader.read(),
    };
    return ReportSummaryHiveObject(
      reportId: fields[0] as String,
      marketplace: fields[1] as String,
      totalOrders: fields[2] as int? ?? 0,
      grossRevenue: fields[3] as double? ?? 0.0,
      totalFees: fields[4] as double? ?? 0.0,
      totalCommission: fields[5] as double? ?? 0.0,
      totalShipping: fields[6] as double? ?? 0.0,
      totalGstOnFees: fields[7] as double? ?? 0.0,
      totalTcs: fields[8] as double? ?? 0.0,
      totalTds: fields[9] as double? ?? 0.0,
      netSettlement: fields[10] as double? ?? 0.0,
      discrepancyCount: fields[11] as int? ?? 0,
      criticalCount: fields[12] as int? ?? 0,
      totalVariance: fields[13] as double? ?? 0.0,
      reconciledAt: fields[14] as String? ?? DateTime.now().toIso8601String(),
      amountSettled: fields[15] as double? ?? 0.0,
      amountPending: fields[16] as double? ?? 0.0,
      parserVersion: fields[17] as String? ?? '1.0.0',
    );
  }

  @override
  void write(BinaryWriter writer, ReportSummaryHiveObject obj) {
    writer
      ..writeByte(18)
      ..writeByte(0)
      ..write(obj.reportId)
      ..writeByte(1)
      ..write(obj.marketplace)
      ..writeByte(2)
      ..write(obj.totalOrders)
      ..writeByte(3)
      ..write(obj.grossRevenue)
      ..writeByte(4)
      ..write(obj.totalFees)
      ..writeByte(5)
      ..write(obj.totalCommission)
      ..writeByte(6)
      ..write(obj.totalShipping)
      ..writeByte(7)
      ..write(obj.totalGstOnFees)
      ..writeByte(8)
      ..write(obj.totalTcs)
      ..writeByte(9)
      ..write(obj.totalTds)
      ..writeByte(10)
      ..write(obj.netSettlement)
      ..writeByte(11)
      ..write(obj.discrepancyCount)
      ..writeByte(12)
      ..write(obj.criticalCount)
      ..writeByte(13)
      ..write(obj.totalVariance)
      ..writeByte(14)
      ..write(obj.reconciledAt)
      ..writeByte(15)
      ..write(obj.amountSettled)
      ..writeByte(16)
      ..write(obj.amountPending)
      ..writeByte(17)
      ..write(obj.parserVersion);
  }
}
