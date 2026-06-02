import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'core/theme/app_theme.dart';
import 'features/settings/presentation/providers/settings_provider.dart';
import 'routing/app_router.dart';
import 'services/flipkart_api/flipkart_auto_sync_service.dart';

class ClearSettleApp extends ConsumerWidget {
  const ClearSettleApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final router = ref.watch(routerProvider);
    final themeMode = ref.watch(themeModeProvider);

    // Kick off auto-sync on every app build (provider keeps it alive & deduped)
    ref.read(flipkartAutoSyncProvider);

    return MaterialApp.router(
      title: 'ClearSettle',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light,
      darkTheme: AppTheme.dark,
      themeMode: themeMode,
      routerConfig: router,
    );
  }
}
