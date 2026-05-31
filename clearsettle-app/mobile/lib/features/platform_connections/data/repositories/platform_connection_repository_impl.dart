import '../../../../storage/entities/platform_connection_hive_object.dart';
import '../../../../storage/hive_manager.dart';
import '../../domain/entities/platform_connection.dart';
import '../../domain/repositories/platform_connection_repository.dart';

class PlatformConnectionRepositoryImpl implements PlatformConnectionRepository {
  @override
  Future<List<PlatformConnection>> getConnections() async {
    return HiveManager.platformConnectionBox.values.map(_toEntity).toList();
  }

  @override
  Future<void> saveConnection(PlatformConnection connection) async {
    await HiveManager.platformConnectionBox.put(
      connection.platform,
      PlatformConnectionHiveObject(
        platform: connection.platform,
        isConnected: connection.isConnected,
        sellerId: connection.sellerId,
        sellerName: connection.sellerName,
        connectedAt: connection.connectedAt?.toIso8601String(),
        tokenExpiresAt: connection.tokenExpiresAt?.toIso8601String(),
      ),
    );
  }

  @override
  Future<void> removeConnection(String platform) async {
    await HiveManager.platformConnectionBox.delete(platform);
  }

  PlatformConnection _toEntity(PlatformConnectionHiveObject obj) {
    final ConnectionStatus status;
    if (!obj.isConnected) {
      status = ConnectionStatus.disconnected;
    } else if (obj.tokenExpiresAt != null &&
        DateTime.now().isAfter(DateTime.parse(obj.tokenExpiresAt!))) {
      status = ConnectionStatus.expired;
    } else {
      status = ConnectionStatus.connected;
    }

    return PlatformConnection(
      platform: obj.platform,
      status: status,
      sellerId: obj.sellerId,
      sellerName: obj.sellerName,
      connectedAt:
          obj.connectedAt != null ? DateTime.parse(obj.connectedAt!) : null,
      tokenExpiresAt: obj.tokenExpiresAt != null
          ? DateTime.parse(obj.tokenExpiresAt!)
          : null,
    );
  }
}
