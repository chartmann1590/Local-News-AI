import 'dart:io';
import 'package:path_provider/path_provider.dart';
import 'package:intl/intl.dart';

class LoggerService {
  static final LoggerService _instance = LoggerService._internal();
  factory LoggerService() => _instance;
  LoggerService._internal();

  List<String> _logs = [];
  static const int _maxLogs = 5000; // Keep last 5000 log entries
  
  Future<void> log(String level, String screen, String action, {String? details, Object? error}) async {
    final timestamp = DateFormat('yyyy-MM-dd HH:mm:ss.SSS').format(DateTime.now());
    final logEntry = _formatLogEntry(timestamp, level, screen, action, details: details, error: error);
    
    _logs.add(logEntry);
    
    // Keep only the last _maxLogs entries
    if (_logs.length > _maxLogs) {
      _logs.removeRange(0, _logs.length - _maxLogs);
    }
    
    // Also print to console
    print(logEntry);
    
    // Write to file asynchronously
    _writeToFile(logEntry);
  }
  
  String _formatLogEntry(String timestamp, String level, String screen, String action, {String? details, Object? error}) {
    final buffer = StringBuffer();
    buffer.write('[$timestamp] [$level] [Screen: $screen] [Action: $action]');
    
    if (details != null && details.isNotEmpty) {
      buffer.write(' [Details: $details]');
    }
    
    if (error != null) {
      buffer.write(' [Error: ${error.toString()}]');
      if (error is Exception) {
        buffer.write(' [Stack: ${StackTrace.current}]');
      }
    }
    
    return buffer.toString();
  }
  
  Future<void> _writeToFile(String logEntry) async {
    try {
      final directory = await _getLogDirectory();
      final file = File('${directory.path}/app_logs.txt');
      
      // Append to file
      await file.writeAsString('$logEntry\n', mode: FileMode.append);
    } catch (e) {
      print('Failed to write log to file: $e');
    }
  }
  
  Future<Directory> _getLogDirectory() async {
    final directory = await getApplicationDocumentsDirectory();
    return directory;
  }
  
  Future<File?> getLogFile() async {
    try {
      final directory = await _getLogDirectory();
      final file = File('${directory.path}/app_logs.txt');
      if (await file.exists()) {
        return file;
      }
      return null;
    } catch (e) {
      print('Failed to get log file: $e');
      return null;
    }
  }
  
  Future<String> getAllLogs() async {
    return _logs.join('\n');
  }
  
  Future<String> getLogsAsString() async {
    try {
      final directory = await _getLogDirectory();
      final file = File('${directory.path}/app_logs.txt');
      
      if (await file.exists()) {
        return await file.readAsString();
      } else {
        return _logs.join('\n');
      }
    } catch (e) {
      return _logs.join('\n');
    }
  }
  
  Future<void> clearLogs() async {
    _logs.clear();
    try {
      final directory = await _getLogDirectory();
      final file = File('${directory.path}/app_logs.txt');
      if (await file.exists()) {
        await file.delete();
      }
    } catch (e) {
      print('Failed to clear log file: $e');
    }
  }
  
  void logInfo(String screen, String action, {String? details}) {
    log('INFO', screen, action, details: details);
  }
  
  void logError(String screen, String action, Object error, {String? details}) {
    log('ERROR', screen, action, details: details, error: error);
  }
  
  void logWarning(String screen, String action, {String? details}) {
    log('WARNING', screen, action, details: details);
  }
  
  void logDebug(String screen, String action, {String? details}) {
    log('DEBUG', screen, action, details: details);
  }
}

