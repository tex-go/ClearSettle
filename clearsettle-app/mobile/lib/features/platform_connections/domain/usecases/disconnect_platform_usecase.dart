import '../../../../services/oauth/flipkart_oauth_service.dart';
import '../repositories/platform_connection_repository.dart';

class DisconnectPlatformUseCase {
  const DisconnectPlatformUseCase({
    required this.repository,
    required this.oauthService,
  });

  final PlatformConnectionRepository repository;
  final FlipkartOAuthService oauthService;

  Future<void> execute(String platform) async {
    if (platform == 'flipkart') await oauthService.revokeTokens();
    await repository.removeConnection(platform);
  }
}
