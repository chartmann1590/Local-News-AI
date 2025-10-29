import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/article.dart';
import '../models/weather.dart';
import '../models/chat_message.dart';
import '../models/server_config.dart';
import '../services/storage_service.dart';
import '../services/logger_service.dart';
import '../utils/constants.dart';

class ApiService {
  static String? _baseUrl;
  
  static Future<String?> getBaseUrl() async {
    if (_baseUrl == null) {
      final config = await StorageService.getServerConfigAsync();
      if (config != null) {
        _baseUrl = config.baseUrl;
      }
    }
    return _baseUrl;
  }
  
  static Future<void> updateBaseUrl() async {
    final config = await StorageService.getServerConfigAsync();
    _baseUrl = config?.baseUrl;
  }
  
  static Future<Map<String, dynamic>> _get(String endpoint, {Map<String, String>? headers, String? screenContext}) async {
    final baseUrl = await getBaseUrl();
    if (baseUrl == null) {
      LoggerService().logError('API', 'GET $endpoint', Exception('Server not configured'), details: screenContext ?? 'Unknown');
      throw Exception('Server not configured');
    }
    
    final url = Uri.parse('$baseUrl$endpoint');
    LoggerService().logInfo('API', 'GET Request', details: 'URL: $url, Screen: ${screenContext ?? "Unknown"}');
    
    try {
      final response = await http.get(
        url,
        headers: headers ?? {'Content-Type': 'application/json'},
      ).timeout(Constants.connectionTimeout);
      
      LoggerService().logInfo('API', 'GET Response', details: 'Status: ${response.statusCode}, Endpoint: $endpoint');
      
      if (response.statusCode == 200) {
        return json.decode(response.body) as Map<String, dynamic>;
      } else {
        final error = Exception('Failed to load: ${response.statusCode}');
        LoggerService().logError('API', 'GET $endpoint', error, details: 'Status: ${response.statusCode}, Body: ${response.body.substring(0, response.body.length > 200 ? 200 : response.body.length)}');
        throw error;
      }
    } catch (e) {
      LoggerService().logError('API', 'GET $endpoint', e, details: 'URL: $url');
      rethrow;
    }
  }
  
  static Future<Map<String, dynamic>> _post(String endpoint, {Map<String, dynamic>? body, Map<String, String>? headers, String? screenContext}) async {
    final baseUrl = await getBaseUrl();
    if (baseUrl == null) {
      LoggerService().logError('API', 'POST $endpoint', Exception('Server not configured'), details: screenContext ?? 'Unknown');
      throw Exception('Server not configured');
    }
    
    final url = Uri.parse('$baseUrl$endpoint');
    LoggerService().logInfo('API', 'POST Request', details: 'URL: $url, Body: ${body != null ? json.encode(body).substring(0, body.toString().length > 200 ? 200 : body.toString().length) : "null"}, Screen: ${screenContext ?? "Unknown"}');
    
    try {
      final response = await http.post(
        url,
        headers: headers ?? {'Content-Type': 'application/json'},
        body: body != null ? json.encode(body) : null,
      ).timeout(Constants.connectionTimeout);
      
      LoggerService().logInfo('API', 'POST Response', details: 'Status: ${response.statusCode}, Endpoint: $endpoint');
      
      if (response.statusCode >= 200 && response.statusCode < 300) {
        if (response.body.isEmpty) {
          return {};
        }
        return json.decode(response.body) as Map<String, dynamic>;
      } else if (response.statusCode == 429) {
        final error = Exception('Rate limit exceeded. Please wait a moment.');
        LoggerService().logError('API', 'POST $endpoint', error, details: 'Rate limited');
        throw error;
      } else {
        final error = Exception('Failed to post: ${response.statusCode}');
        LoggerService().logError('API', 'POST $endpoint', error, details: 'Status: ${response.statusCode}, Body: ${response.body.substring(0, response.body.length > 200 ? 200 : response.body.length)}');
        throw error;
      }
    } catch (e) {
      LoggerService().logError('API', 'POST $endpoint', e, details: 'URL: $url');
      rethrow;
    }
  }
  
  static Future<void> _delete(String endpoint, {String? screenContext}) async {
    final baseUrl = await getBaseUrl();
    if (baseUrl == null) {
      LoggerService().logError('API', 'DELETE $endpoint', Exception('Server not configured'), details: screenContext ?? 'Unknown');
      throw Exception('Server not configured');
    }
    
    final url = Uri.parse('$baseUrl$endpoint');
    LoggerService().logInfo('API', 'DELETE Request', details: 'URL: $url, Screen: ${screenContext ?? "Unknown"}');
    
    try {
      final response = await http.delete(
        url,
        headers: {'Content-Type': 'application/json'},
      ).timeout(Constants.connectionTimeout);
      
      LoggerService().logInfo('API', 'DELETE Response', details: 'Status: ${response.statusCode}, Endpoint: $endpoint');
      
      if (response.statusCode < 200 || response.statusCode >= 300) {
        final error = Exception('Failed to delete: ${response.statusCode}');
        LoggerService().logError('API', 'DELETE $endpoint', error, details: 'Status: ${response.statusCode}');
        throw error;
      }
    } catch (e) {
      LoggerService().logError('API', 'DELETE $endpoint', e, details: 'URL: $url');
      rethrow;
    }
  }
  
  // Health/Config Check
  static Future<bool> testConnection(ServerConfig config, {String? screenContext}) async {
    LoggerService().logInfo('API', 'Test Connection', details: 'Testing: ${config.baseUrl}, Screen: ${screenContext ?? "Unknown"}');
    try {
      final url = Uri.parse('${config.baseUrl}${Constants.healthEndpoint}');
      final response = await http.get(url).timeout(Constants.connectionTimeout);
      
      LoggerService().logInfo('API', 'Connection Test', details: 'Health endpoint response: ${response.statusCode}');
      
      if (response.statusCode == 200) {
        LoggerService().logInfo('API', 'Connection Test Success', details: 'Connected to: ${config.baseUrl}');
        return true;
      }
      
      // Try /api/config as fallback
      final configUrl = Uri.parse('${config.baseUrl}${Constants.configEndpoint}');
      final configResponse = await http.get(configUrl).timeout(Constants.connectionTimeout);
      LoggerService().logInfo('API', 'Connection Test', details: 'Config endpoint response: ${configResponse.statusCode}');
      
      final success = configResponse.statusCode == 200;
      if (success) {
        LoggerService().logInfo('API', 'Connection Test Success', details: 'Connected to: ${config.baseUrl}');
      }
      return success;
    } catch (e) {
      LoggerService().logError('API', 'Connection Test Failed', e, details: 'Server: ${config.baseUrl}');
      return false;
    }
  }
  
  // Articles
  static Future<Map<String, dynamic>> getArticles({int page = 1, int limit = 10, String? screenContext}) async {
    final response = await _get('${Constants.articlesEndpoint}?page=$page&limit=$limit', screenContext: screenContext ?? 'NewsScreen');
    return response;
  }
  
  // Weather
  static Future<Weather> getWeather({String? screenContext}) async {
    final response = await _get(Constants.weatherEndpoint, screenContext: screenContext ?? 'WeatherScreen');
    return Weather.fromJson(response);
  }
  
  // Chat
  static Future<ChatResponse> getChat(int articleId, {String? screenContext}) async {
    final response = await _get('${Constants.articlesEndpoint}/$articleId/chat', screenContext: screenContext ?? 'ChatWidget');
    return ChatResponse.fromJson(response);
  }
  
  static Future<ChatResponse> postChat(int articleId, String message, List<ChatMessage> history, {String? screenContext}) async {
    final body = {
      'message': message,
      'history': history.map((m) => {
        'role': m.role == 'user' ? 'user' : 'assistant',
        'content': m.content,
      }).toList(),
    };
    final response = await _post('${Constants.articlesEndpoint}/$articleId/chat', body: body);
    return ChatResponse.fromJson({
      'author': response['author'] ?? 'Local Desk',
      'messages': [
        ...history.map((m) => {'role': m.role, 'content': m.content}),
        {'role': 'user', 'content': message},
        {'role': 'assistant', 'content': response['reply'] ?? ''},
      ],
    });
  }
  
  static Future<void> deleteChat(int articleId, {String? screenContext}) async {
    await _delete('${Constants.articlesEndpoint}/$articleId/chat', screenContext: screenContext ?? 'ChatWidget');
  }
  
  // TTS
  static Future<List<int>> getTtsArticle(int articleId, {String? voice}) async {
    final baseUrl = await getBaseUrl();
    if (baseUrl == null) {
      throw Exception('Server not configured');
    }
    
    String url = '$baseUrl/api/tts/article/$articleId';
    if (voice != null && voice.isNotEmpty) {
      url += '?voice=${Uri.encodeComponent(voice)}';
    }
    
    LoggerService().logInfo('API', 'GET TTS Article', details: 'Article ID: $articleId, Timeout: ${Constants.ttsTimeout.inSeconds}s');
    final response = await http.get(Uri.parse(url)).timeout(Constants.ttsTimeout);
    if (response.statusCode == 200) {
      LoggerService().logInfo('API', 'TTS Article Received', details: 'Size: ${response.bodyBytes.length} bytes');
      return response.bodyBytes;
    } else {
      throw Exception('Failed to load audio: ${response.statusCode}');
    }
  }
  
  static Future<List<int>> getTtsWeather({String? voice}) async {
    final baseUrl = await getBaseUrl();
    if (baseUrl == null) {
      throw Exception('Server not configured');
    }
    
    String url = '$baseUrl/api/tts/weather';
    if (voice != null && voice.isNotEmpty) {
      url += '?voice=${Uri.encodeComponent(voice)}';
    }
    
    LoggerService().logInfo('API', 'GET TTS Weather', details: 'Timeout: ${Constants.ttsTimeout.inSeconds}s');
    final response = await http.get(Uri.parse(url)).timeout(Constants.ttsTimeout);
    if (response.statusCode == 200) {
      LoggerService().logInfo('API', 'TTS Weather Received', details: 'Size: ${response.bodyBytes.length} bytes');
      return response.bodyBytes;
    } else {
      throw Exception('Failed to load audio: ${response.statusCode}');
    }
  }
  
  // Settings
  static Future<Map<String, dynamic>> getSettings({String? screenContext}) async {
    return await _get(Constants.settingsEndpoint, screenContext: screenContext ?? 'SettingsScreen');
  }
  
  static Future<void> updateSettings(Map<String, dynamic> settings, {String? screenContext}) async {
    await _post(Constants.settingsEndpoint, body: settings, screenContext: screenContext ?? 'SettingsScreen');
  }
  
  static Future<Map<String, dynamic>> getTtsSettings({String? screenContext}) async {
    try {
      return await _get(Constants.ttsSettingsEndpoint, screenContext: screenContext ?? 'SettingsScreen');
    } catch (e) {
      LoggerService().logError('API', 'GET TTS Settings', e);
      return {};
    }
  }
  
  static Future<void> updateTtsSettings(Map<String, dynamic> settings, {String? screenContext}) async {
    await _post(Constants.ttsSettingsEndpoint, body: settings, screenContext: screenContext ?? 'SettingsScreen');
  }
  
  // Config
  static Future<Map<String, dynamic>> getConfig({String? screenContext}) async {
    return await _get(Constants.configEndpoint, screenContext: screenContext ?? 'Unknown');
  }
  
  // Location
  static Future<void> updateLocation(String location, {String? screenContext}) async {
    await _post(Constants.locationEndpoint, body: {'location': location}, screenContext: screenContext ?? 'SettingsScreen');
  }
}

