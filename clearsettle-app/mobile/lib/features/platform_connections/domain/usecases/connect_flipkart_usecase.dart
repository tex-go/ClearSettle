import '../../../../services/oauth/flipkart_oauth_service.dart';
import '../entities/platform_connection.dart';
import '../repositories/platform_connection_repository.dart';

class ConnectFlipkartUseCase {
  const ConnectFlipkartUseCase({
    required this.oauthService,
    required this.repository,
  });

  final FlipkartOAuthService oauthService;
  final PlatformConnectionRepository repository;

  Future<PlatformConnection> execute() async {
    final result = await oauthService.authorize();

    final connection = PlatformConnection(
      platform: 'flipkart',
      status: ConnectionStatus.connected,
      sellerId: result.sellerId,
      sellerName: result.sellerName,
      connectedAt: DateTime.now(),
      tokenExpiresAt: result.expiresAt,
    );

    await repository.saveConnection(connection);
    return connection;
  }
}
