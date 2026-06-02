import '../entities/platform_connection.dart';

abstract interface class PlatformConnectionRepository {
  Future<List<PlatformConnection>> getConnections();
  Future<void> saveConnection(PlatformConnection connection);
  Future<void> removeConnection(String platform);
}
