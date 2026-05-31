import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../services/oauth/flipkart_oauth_service.dart';
import '../../data/repositories/platform_connection_repository_impl.dart';
import '../../domain/entities/platform_connection.dart';
import '../../domain/usecases/connect_flipkart_usecase.dart';
import '../../domain/usecases/disconnect_platform_usecase.dart';
import '../../domain/usecases/get_connections_usecase.dart';

final _repoProvider =
    Provider((_) => PlatformConnectionRepositoryImpl());

final platformConnectionProvider = AsyncNotifierProvider<
    PlatformConnectionNotifier,
    List<PlatformConnection>>(PlatformConnectionNotifier.new);

class PlatformConnectionNotifier
    extends AsyncNotifier<List<PlatformConnection>> {
  late PlatformConnectionRepositoryImpl _repo;

  @override
  Future<List<PlatformConnection>> build() async {
    _repo = ref.read(_repoProvider);
    return GetConnectionsUseCase(_repo).execute();
  }

  Future<void> connectFlipkart() async {
    state = const AsyncLoading();
    state = await AsyncValue.guard(() async {
      final oauthService = ref.read(flipkartOAuthServiceProvider);
      await ConnectFlipkartUseCase(
        oauthService: oauthService,
        repository: _repo,
      ).execute();
      return GetConnectionsUseCase(_repo).execute();
    });
  }

  Future<void> disconnect(String platform) async {
    state = const AsyncLoading();
    state = await AsyncValue.guard(() async {
      final oauthService = ref.read(flipkartOAuthServiceProvider);
      await DisconnectPlatformUseCase(
        repository: _repo,
        oauthService: oauthService,
      ).execute(platform);
      return GetConnectionsUseCase(_repo).execute();
    });
  }
}
