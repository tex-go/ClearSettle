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
    this.lastSyncAt,
  });

  final String platform;
  final ConnectionStatus status;
  final String? sellerId;
  final String? sellerName;
  final DateTime? connectedAt;
  final DateTime? tokenExpiresAt;
  final DateTime? lastSyncAt;

  bool get isConnected => status == ConnectionStatus.connected;

  PlatformConnection copyWith({DateTime? lastSyncAt}) => PlatformConnection(
        platform: platform,
        status: status,
        sellerId: sellerId,
        sellerName: sellerName,
        connectedAt: connectedAt,
        tokenExpiresAt: tokenExpiresAt,
        lastSyncAt: lastSyncAt ?? this.lastSyncAt,
      );

  @override
  List<Object?> get props =>
      [platform, status, sellerId, sellerName, connectedAt, tokenExpiresAt, lastSyncAt];
}
