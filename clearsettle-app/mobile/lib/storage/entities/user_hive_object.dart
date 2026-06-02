import 'package:hive_flutter/hive_flutter.dart';

import '../../core/constants/hive_constants.dart';

class UserHiveObject extends HiveObject {
  UserHiveObject({
    required this.id,
    required this.email,
    required this.sellerName,
    required this.organization,
    required this.companyId,
    required this.role,
    required this.createdAt,
    this.phone,
    this.gstin,
  });

  String id;
  String email;
  String sellerName;
  String organization;
  String companyId;
  String role;
  String createdAt;
  String? phone;
  String? gstin;
}

class UserHiveObjectAdapter extends TypeAdapter<UserHiveObject> {
  @override
  final int typeId = HiveConstants.userTypeId;

  @override
  UserHiveObject read(BinaryReader reader) {
    final numOfFields = reader.readByte();
    final fields = <int, dynamic>{
      for (int i = 0; i < numOfFields; i++) reader.readByte(): reader.read(),
    };
    return UserHiveObject(
      id: fields[0] as String,
      email: fields[1] as String,
      sellerName: fields[2] as String,
      organization: fields[3] as String,
      companyId: fields[4] as String,
      role: fields[5] as String? ?? 'seller',
      createdAt: fields[6] as String,
      phone: fields[7] as String?,
      gstin: fields[8] as String?,
    );
  }

  @override
  void write(BinaryWriter writer, UserHiveObject obj) {
    writer
      ..writeByte(9)
      ..writeByte(0)
      ..write(obj.id)
      ..writeByte(1)
      ..write(obj.email)
      ..writeByte(2)
      ..write(obj.sellerName)
      ..writeByte(3)
      ..write(obj.organization)
      ..writeByte(4)
      ..write(obj.companyId)
      ..writeByte(5)
      ..write(obj.role)
      ..writeByte(6)
      ..write(obj.createdAt)
      ..writeByte(7)
      ..write(obj.phone)
      ..writeByte(8)
      ..write(obj.gstin);
  }
}
