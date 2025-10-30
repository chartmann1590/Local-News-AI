class Constants {
  // Storage Keys
  static const String serverIpKey = 'server_ip';
  static const String serverPortKey = 'server_port';
  static const String themeKey = 'theme';
  
  // Defaults
  static const String defaultServerPort = '8000';
  static const String defaultTheme = 'system';
  
  // API Endpoints
  static const String healthEndpoint = '/health';
  static const String configEndpoint = '/api/config';
  static const String articlesEndpoint = '/api/articles';
  static const String weatherEndpoint = '/api/weather';
  static const String settingsEndpoint = '/api/settings';
  static const String ttsSettingsEndpoint = '/api/tts/settings';
  static const String locationEndpoint = '/api/location';
  
  // Timeouts
  // Mobile networks can be variable; allow a bit more time and retry in ApiService
  static const Duration connectionTimeout = Duration(minutes: 3);
  static const Duration ttsTimeout = Duration(minutes: 3);
  static const Duration splashScreenDuration = Duration(seconds: 5);
  static const Duration autoRefreshInterval = Duration(seconds: 30);
}
