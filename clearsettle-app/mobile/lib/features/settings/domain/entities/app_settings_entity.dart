class AppSettingsEntity {
  const AppSettingsEntity({
    this.isDarkMode = false,
    this.notificationsEnabled = true,
    this.biometricEnabled = false,
    this.autoSyncEnabled = true,
    this.defaultMarketplace = 'flipkart',
    this.storageUsedBytes = 0,
  });

  final bool isDarkMode;
  final bool notificationsEnabled;
  final bool biometricEnabled;
  final bool autoSyncEnabled;
  final String defaultMarketplace;
  final int storageUsedBytes;

  String get storageUsedLabel {
    if (storageUsedBytes < 1024) return '$storageUsedBytes B';
    if (storageUsedBytes < 1024 * 1024) {
      return '${(storageUsedBytes / 1024).toStringAsFixed(1)} KB';
    }
    return '${(storageUsedBytes / (1024 * 1024)).toStringAsFixed(1)} MB';
  }

  AppSettingsEntity copyWith({
    bool? isDarkMode,
    bool? notificationsEnabled,
    bool? biometricEnabled,
    bool? autoSyncEnabled,
    String? defaultMarketplace,
    int? storageUsedBytes,
  }) {
    return AppSettingsEntity(
      isDarkMode: isDarkMode ?? this.isDarkMode,
      notificationsEnabled: notificationsEnabled ?? this.notificationsEnabled,
      biometricEnabled: biometricEnabled ?? this.biometricEnabled,
      autoSyncEnabled: autoSyncEnabled ?? this.autoSyncEnabled,
      defaultMarketplace: defaultMarketplace ?? this.defaultMarketplace,
      storageUsedBytes: storageUsedBytes ?? this.storageUsedBytes,
    );
  }
}
