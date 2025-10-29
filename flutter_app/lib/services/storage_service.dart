import 'package:shared_preferences/shared_preferences.dart';
import '../models/server_config.dart';
import '../utils/constants.dart';

class StorageService {
  static SharedPreferences? _prefs;
  
  static Future<void> init() async {
    try {
      _prefs = await SharedPreferences.getInstance();
      if (_prefs == null) {
        throw Exception('SharedPreferences.getInstance() returned null');
      }
    } catch (e) {
      _prefs = null;
      rethrow;
    }
  }
  
  // Server Configuration
  static Future<bool> saveServerConfig(ServerConfig config) async {
    try {
      if (_prefs == null) {
        await init();
      }
      final prefs = _prefs;
      if (prefs == null) {
        throw Exception('Failed to initialize SharedPreferences');
      }
      if (config.ip.isEmpty || config.port.isEmpty) {
        throw Exception('Server IP and port cannot be empty');
      }
      final ipSaved = await prefs.setString(Constants.serverIpKey, config.ip);
      final portSaved = await prefs.setString(Constants.serverPortKey, config.port);
      return ipSaved && portSaved;
    } catch (e) {
      throw Exception('Error saving server config: ${e.toString()}');
    }
  }
  
  static ServerConfig? getServerConfig() {
    if (_prefs == null) {
      // Sync initialization for getters (not ideal but works)
      return null;
    }
    final ip = _prefs!.getString(Constants.serverIpKey);
    final port = _prefs!.getString(Constants.serverPortKey);
    
    if (ip == null || port == null) {
      return null;
    }
    
    return ServerConfig(ip: ip, port: port);
  }
  
  static Future<ServerConfig?> getServerConfigAsync() async {
    try {
      if (_prefs == null) {
        await init();
      }
      final prefs = _prefs;
      if (prefs == null) {
        return null;
      }
      final ip = prefs.getString(Constants.serverIpKey);
      final port = prefs.getString(Constants.serverPortKey);
      
      if (ip == null || port == null || ip.isEmpty || port.isEmpty) {
        return null;
      }
      
      return ServerConfig(ip: ip, port: port);
    } catch (e) {
      return null;
    }
  }
  
  // Theme
  static Future<bool> saveTheme(String theme) async {
    if (_prefs == null) {
      await init();
    }
    final prefs = _prefs;
    if (prefs == null) {
      throw Exception('Failed to initialize SharedPreferences');
    }
    return await prefs.setString(Constants.themeKey, theme);
  }
  
  static String getTheme() {
    if (_prefs == null) return Constants.defaultTheme;
    return _prefs!.getString(Constants.themeKey) ?? Constants.defaultTheme;
  }
}

