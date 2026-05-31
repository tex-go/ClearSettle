import 'package:equatable/equatable.dart';

enum ConnectionStatus { connected, disconnected, expired }

class PlatformConnection extends Equatable {
  const PlatformConnection({
    required this.platform,
    required this.status,
    this.sellerId,
    this.sellerName,
    this.connectedAt,
    this.tokenExpiresAt,
  });

  final String platform;
  final ConnectionStatus status;
  final String? sellerId;
  final String? sellerName;
  final DateTime? connectedAt;
  final DateTime? tokenExpiresAt;

  bool get isConnected => status == ConnectionStatus.connected;

  @override
  List<Object?> get props =>
      [platform, status, sellerId, sellerName, connectedAt, tokenExpiresAt];
}
