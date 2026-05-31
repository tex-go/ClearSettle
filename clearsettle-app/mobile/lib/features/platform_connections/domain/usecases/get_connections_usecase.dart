import '../entities/platform_connection.dart';
import '../repositories/platform_connection_repository.dart';

class GetConnectionsUseCase {
  const GetConnectionsUseCase(this.repository);

  final PlatformConnectionRepository repository;

  Future<List<PlatformConnection>> execute() => repository.getConnections();
}
