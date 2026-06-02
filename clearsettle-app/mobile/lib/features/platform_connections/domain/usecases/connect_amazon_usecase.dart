import '../../../../services/oauth/amazon_oauth_service.dart';
import '../entities/platform_connection.dart';
import '../repositories/platform_connection_repository.dart';

class ConnectAmazonUseCase {
  const ConnectAmazonUseCase({
    required this.oauthService,
    required this.repository,
  });

  final AmazonOAuthService oauthService;
  final PlatformConnectionRepository repository;

  Future<PlatformConnection> execute() async {
    final result = await oauthService.authorize();

    final connection = PlatformConnection(
      platform: 'amazon',
      status: ConnectionStatus.connected,
      sellerId: result.sellingPartnerId,
      sellerName: null,
      connectedAt: DateTime.now(),
      tokenExpiresAt: result.tokenExpiresAt,
    );

    await repository.saveConnection(connection);
    return connection;
  }
}
