import '../entities/platform_connection.dart';
import '../repositories/platform_connection_repository.dart';

/// Creates a Flipkart manual-upload connection locally.
///
/// Flipkart does not expose a public OAuth API for third-party apps.
/// The backend FlipkartProvider is MANUAL_UPLOAD; tokens are never required.
/// Connecting simply marks the platform as active so the user can upload
/// settlement reports from the Reports section.
class ConnectFlipkartUseCase {
  const ConnectFlipkartUseCase({required this.repository});

  final PlatformConnectionRepository repository;

  Future<PlatformConnection> execute() async {
    final connection = PlatformConnection(
      platform: 'flipkart',
      status: ConnectionStatus.connected,
      sellerId: null,
      sellerName: null,
      connectedAt: DateTime.now(),
      tokenExpiresAt: null, // manual upload — no token expiry
    );
    await repository.saveConnection(connection);
    return connection;
  }
}
