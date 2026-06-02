abstract final class AppConstants {
  static const String currentUserKey = 'current_user';
  static const String syncStatusKey = 'global';
  static const String settingsKey = 'app_settings';

  static const List<String> supportedMarketplaces = ['flipkart'];

  static const Map<String, String> marketplaceDisplayNames = {
    'flipkart': 'Flipkart',
    'amazon': 'Amazon',
    'meesho': 'Meesho',
    'myntra': 'Myntra',
    'ajio': 'Ajio',
  };

  static const Map<String, String> marketplaceColors = {
    'flipkart': '#2874F0',
    'amazon': '#FF9900',
    'meesho': '#F43397',
    'myntra': '#FF3F6C',
    'ajio': '#000000',
  };
}
