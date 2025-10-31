import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:path_provider/path_provider.dart';
import 'dart:io';
import 'package:http/http.dart' as http;
import 'dart:convert';
import '../services/storage_service.dart';
import '../services/api_service.dart';
import '../services/theme_service.dart';
import '../services/logger_service.dart';
import '../screens/server_config_screen.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});
  
  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  bool _isLoading = true;
  Map<String, dynamic> _settings = {};
  Map<String, dynamic> _ttsSettings = {};
  Map<String, dynamic> _config = {};
  String? _error;
  
  final _locationController = TextEditingController();
  final _ttsBaseUrlController = TextEditingController();
  final _ttsVoiceController = TextEditingController();
  bool _ttsEnabled = false;
  String _ttsBaseUrl = '';
  String _ttsVoice = '';
  double _ttsSpeed = 1.0;
  String _tempUnit = 'F';
  String _windSpeedUnit = 'mph';
  
  @override
  void initState() {
    super.initState();
    _loadSettings();
  }
  
  @override
  void dispose() {
    _locationController.dispose();
    _ttsBaseUrlController.dispose();
    _ttsVoiceController.dispose();
    super.dispose();
  }
  
  Future<void> _loadSettings() async {
    LoggerService().logInfo('SettingsScreen', 'Load Settings');
    setState(() {
      _isLoading = true;
      _error = null;
    });
    
    try {
      final settings = await ApiService.getSettings(screenContext: 'SettingsScreen');
      final ttsSettings = await ApiService.getTtsSettings(screenContext: 'SettingsScreen');
      final config = await ApiService.getConfig(screenContext: 'SettingsScreen');
      
      LoggerService().logInfo('SettingsScreen', 'Settings Loaded', details: 'Location: ${config['location']}, TTS Enabled: ${ttsSettings['enabled']}');
      
      if (mounted) {
        setState(() {
          _settings = settings;
          _ttsSettings = ttsSettings;
          _config = config;
          _locationController.text = config['location'] as String? ?? '';
          _ttsEnabled = ttsSettings['enabled'] == true;
          _ttsBaseUrl = ttsSettings['base_url'] as String? ?? '';
          _ttsVoice = ttsSettings['voice'] as String? ?? '';
          _ttsSpeed = (ttsSettings['speed'] as num?)?.toDouble() ?? 1.0;
          _tempUnit = settings['temp_unit'] as String? ?? 'F';
          _windSpeedUnit = settings['wind_speed_unit'] as String? ?? 'mph';
          _ttsBaseUrlController.text = _ttsBaseUrl;
          _ttsVoiceController.text = _ttsVoice;
          _isLoading = false;
        });
      }
    } catch (e) {
      LoggerService().logError('SettingsScreen', 'Load Settings', e);
      if (mounted) {
        setState(() {
          _isLoading = false;
          _error = 'Failed to load settings: ${e.toString()}';
        });
      }
    }
  }
  
  Future<void> _saveSettings() async {
    LoggerService().logInfo('SettingsScreen', 'Save Settings', details: 'Temp Unit: $_tempUnit, TTS Enabled: $_ttsEnabled');
    try {
      await ApiService.updateSettings({
        'temp_unit': _tempUnit,
        'wind_speed_unit': _windSpeedUnit,
      }, screenContext: 'SettingsScreen');
      
      await ApiService.updateTtsSettings({
        'enabled': _ttsEnabled,
        'base_url': _ttsBaseUrl,
        'voice': _ttsVoice.isEmpty ? null : _ttsVoice,
        'speed': _ttsSpeed,
      }, screenContext: 'SettingsScreen');
      
      LoggerService().logInfo('SettingsScreen', 'Settings Saved');
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Settings saved'),
            backgroundColor: Colors.green,
          ),
        );
      }
    } catch (e) {
      LoggerService().logError('SettingsScreen', 'Save Settings', e);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to save: ${e.toString()}'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }
  
  Future<void> _updateLocation() async {
    final location = _locationController.text.trim();
    if (location.isEmpty) {
      LoggerService().logWarning('SettingsScreen', 'Update Location', details: 'Empty location');
      return;
    }
    
    LoggerService().logInfo('SettingsScreen', 'Update Location', details: 'Location: $location');
    try {
      await ApiService.updateLocation(location, screenContext: 'SettingsScreen');
      
      LoggerService().logInfo('SettingsScreen', 'Location Updated');
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Location updated'),
            backgroundColor: Colors.green,
          ),
        );
        _loadSettings();
      }
    } catch (e) {
      LoggerService().logError('SettingsScreen', 'Update Location', e);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to update location: ${e.toString()}'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }
  
  Future<void> _testServerConnection() async {
    LoggerService().logInfo('SettingsScreen', 'Test Server Connection');
    try {
      final config = await StorageService.getServerConfigAsync();
      if (config == null) {
        LoggerService().logWarning('SettingsScreen', 'Test Connection', details: 'Server not configured');
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Server not configured'),
            backgroundColor: Colors.orange,
          ),
        );
        return;
      }
      
      final success = await ApiService.testConnection(config, screenContext: 'SettingsScreen');
      
      if (mounted) {
        LoggerService().logInfo('SettingsScreen', 'Connection Test Result', details: success ? 'Success' : 'Failed');
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(success ? 'Connection successful!' : 'Connection failed'),
            backgroundColor: success ? Colors.green : Colors.red,
          ),
        );
      }
    } catch (e) {
      LoggerService().logError('SettingsScreen', 'Test Server Connection', e);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Connection error: ${e.toString()}'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }
  
  Future<void> _emailLogs() async {
    LoggerService().logInfo('SettingsScreen', 'Email Logs');
    try {
      final logContent = await LoggerService().getLogsAsString();
      final logFile = await LoggerService().getLogFile();

      if (logContent.isEmpty) {
        LoggerService().logWarning('SettingsScreen', 'Email Logs', details: 'No logs to send');
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('No logs available'),
              backgroundColor: Colors.orange,
            ),
          );
        }
        return;
      }

      // Create mailto URI with subject and body
      final subject = Uri.encodeComponent('News AI App Logs - ${DateTime.now().toIso8601String()}');
      final body = Uri.encodeComponent('Please find attached the app logs.\n\n${logContent.substring(0, logContent.length > 10000 ? 10000 : logContent.length)}');

      final uri = Uri.parse('mailto:?subject=$subject&body=$body');

      // Try to launch email client directly with external application mode
      // Don't use canLaunchUrl as it often returns false for mailto on Android
      try {
        LoggerService().logInfo('SettingsScreen', 'Launch Email Client');
        final launched = await launchUrl(uri, mode: LaunchMode.externalApplication);
        if (!launched) {
          throw Exception('Failed to launch email client');
        }
      } catch (launchError) {
        LoggerService().logError('SettingsScreen', 'Email Logs', launchError);
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('Cannot open email client. Please make sure you have an email app installed.'),
              backgroundColor: Colors.red,
              duration: Duration(seconds: 4),
            ),
          );
        }
      }
    } catch (e) {
      LoggerService().logError('SettingsScreen', 'Email Logs', e);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to email logs: ${e.toString()}'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  Future<void> _uploadLogs() async {
    LoggerService().logInfo('SettingsScreen', 'Upload Logs');
    try {
      final baseUrl = await ApiService.getBaseUrl();
      if (baseUrl == null) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Server not configured'), backgroundColor: Colors.orange),
          );
        }
        return;
      }
      final file = await LoggerService().getLogFile();
      final content = await LoggerService().getLogsAsString();
      if ((file == null || !(await file.exists())) && content.isEmpty) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('No logs available'), backgroundColor: Colors.orange),
          );
        }
        return;
      }
      final uri = Uri.parse('$baseUrl/api/logs/upload');
      final req = http.MultipartRequest('POST', uri);
      req.fields['deviceId'] = '';
      req.fields['platform'] = Platform.isAndroid ? 'android' : 'ios';
      req.fields['appVersion'] = '';
      req.fields['buildNumber'] = '';
      if (file != null && await file.exists()) {
        req.files.add(await http.MultipartFile.fromPath('log', file.path, filename: 'app_logs.txt'));
      } else {
        final bytes = utf8.encode(content);
        req.files.add(http.MultipartFile.fromBytes('log', bytes, filename: 'app_logs.txt'));
      }
      final resp = await req.send();
      if (resp.statusCode >= 200 && resp.statusCode < 300) {
        final body = await resp.stream.bytesToString();
        LoggerService().logInfo('SettingsScreen', 'Upload Logs Success', details: body);
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Logs uploaded'), backgroundColor: Colors.green),
          );
        }
      } else if (resp.statusCode == 429) {
        throw Exception('Rate limited');
      } else if (resp.statusCode == 413) {
        throw Exception('Log file too large');
      } else {
        throw Exception('HTTP ${resp.statusCode}');
      }
    } catch (e) {
      LoggerService().logError('SettingsScreen', 'Upload Logs', e);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Upload failed: ${e.toString()}'), backgroundColor: Colors.red),
        );
      }
    }
  }
  
  @override
  Widget build(BuildContext context) {
    final themeService = Provider.of<ThemeService>(context);
    
    return Scaffold(
      appBar: AppBar(
        title: const Text('Settings'),
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Text(
                        _error!,
                        textAlign: TextAlign.center,
                        style: TextStyle(color: Colors.red[700]),
                      ),
                      const SizedBox(height: 16),
                      ElevatedButton(
                        onPressed: _loadSettings,
                        child: const Text('Retry'),
                      ),
                    ],
                  ),
                )
              : ListView(
                  padding: const EdgeInsets.all(16),
                  children: [
                    _buildSection(
                      title: 'Appearance',
                      children: [
                        ListTile(
                          leading: const Icon(Icons.brightness_6),
                          title: const Text('Theme'),
                          subtitle: Text(_getThemeModeString(themeService.themeMode)),
                          trailing: PopupMenuButton<ThemeMode>(
                            onSelected: (mode) {
                              themeService.setTheme(mode);
                            },
                            itemBuilder: (context) => [
                              const PopupMenuItem(
                                value: ThemeMode.system,
                                child: Text('System'),
                              ),
                              const PopupMenuItem(
                                value: ThemeMode.light,
                                child: Text('Light'),
                              ),
                              const PopupMenuItem(
                                value: ThemeMode.dark,
                                child: Text('Dark'),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 24),
                    _buildSection(
                      title: 'Server Configuration',
                      children: [
                        FutureBuilder(
                          future: StorageService.getServerConfigAsync(),
                          builder: (context, snapshot) {
                            final config = snapshot.data;
                            return ListTile(
                              leading: const Icon(Icons.settings_ethernet),
                              title: const Text('Server Address'),
                              subtitle: Text(config?.baseUrl ?? 'Not configured'),
                              trailing: Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  IconButton(
                                    icon: const Icon(Icons.refresh),
                                    onPressed: _testServerConnection,
                                    tooltip: 'Test Connection',
                                  ),
                                  IconButton(
                                    icon: const Icon(Icons.edit),
                                    onPressed: () async {
                                      await Navigator.push(
                                        context,
                                        MaterialPageRoute(
                                          builder: (context) => const ServerConfigScreen(),
                                        ),
                                      );
                                      await ApiService.updateBaseUrl();
                                      setState(() {});
                                    },
                                  ),
                                ],
                              ),
                            );
                          },
                        ),
                      ],
                    ),
                    const SizedBox(height: 24),
                    _buildSection(
                      title: 'Location',
                      children: [
                        TextField(
                          controller: _locationController,
                          decoration: const InputDecoration(
                            labelText: 'Location',
                            hintText: 'City, State or ZIP',
                            border: OutlineInputBorder(),
                            prefixIcon: Icon(Icons.location_on),
                          ),
                        ),
                        const SizedBox(height: 8),
                        SizedBox(
                          width: double.infinity,
                          child: ElevatedButton(
                            onPressed: _updateLocation,
                            child: const Text('Update Location'),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 24),
                    _buildSection(
                      title: 'Text-to-Speech',
                      children: [
                        SwitchListTile(
                          value: _ttsEnabled,
                          onChanged: (value) {
                            setState(() {
                              _ttsEnabled = value;
                            });
                          },
                          title: const Text('Enable TTS'),
                        ),
                        TextField(
                          enabled: _ttsEnabled,
                          decoration: const InputDecoration(
                            labelText: 'TTS Base URL',
                            hintText: 'http://tts:5500',
                            border: OutlineInputBorder(),
                            prefixIcon: Icon(Icons.mic),
                          ),
                          onChanged: (value) {
                            _ttsBaseUrl = value;
                          },
                          controller: _ttsBaseUrlController,
                        ),
                        const SizedBox(height: 8),
                        TextField(
                          enabled: _ttsEnabled,
                          decoration: const InputDecoration(
                            labelText: 'Voice',
                            hintText: 'Leave empty for default',
                            border: OutlineInputBorder(),
                            prefixIcon: Icon(Icons.record_voice_over),
                          ),
                          onChanged: (value) {
                            _ttsVoice = value;
                          },
                          controller: _ttsVoiceController,
                        ),
                        const SizedBox(height: 8),
                        Text(
                          'Speed: ${_ttsSpeed.toStringAsFixed(1)}x',
                        ),
                        Slider(
                          value: _ttsSpeed,
                          min: 0.5,
                          max: 2.0,
                          divisions: 15,
                          label: '${_ttsSpeed.toStringAsFixed(1)}x',
                          onChanged: _ttsEnabled
                              ? (value) {
                                  setState(() {
                                    _ttsSpeed = value;
                                  });
                                }
                              : null,
                        ),
                      ],
                    ),
                    const SizedBox(height: 24),
                    _buildSection(
                      title: 'Logs',
                      children: [
                        SizedBox(
                          width: double.infinity,
                          child: ElevatedButton.icon(
                            onPressed: _emailLogs,
                            icon: const Icon(Icons.email),
                            label: const Text('Email Logs'),
                            style: ElevatedButton.styleFrom(
                              padding: const EdgeInsets.symmetric(vertical: 16),
                              backgroundColor: Colors.green.shade700,
                              foregroundColor: Colors.white,
                            ),
                          ),
                        ),
                        const SizedBox(height: 8),
                        SizedBox(
                          width: double.infinity,
                          child: ElevatedButton.icon(
                            onPressed: _uploadLogs,
                            icon: const Icon(Icons.cloud_upload),
                            label: const Text('Upload Logs to Server'),
                            style: ElevatedButton.styleFrom(
                              padding: const EdgeInsets.symmetric(vertical: 16),
                              backgroundColor: Colors.blue.shade700,
                              foregroundColor: Colors.white,
                            ),
                          ),
                        ),
                        const SizedBox(height: 8),
                        Text(
                          'Email or upload logs to the server for debugging',
                          style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: Colors.grey[600],
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 24),
                    _buildSection(
                      title: 'Weather Units',
                      children: [
                        RadioListTile<String>(
                          value: 'F',
                          groupValue: _tempUnit,
                          onChanged: (value) {
                            if (value != null) {
                              setState(() {
                                _tempUnit = value;
                              });
                            }
                          },
                          title: const Text('Fahrenheit (°F)'),
                        ),
                        RadioListTile<String>(
                          value: 'C',
                          groupValue: _tempUnit,
                          onChanged: (value) {
                            if (value != null) {
                              setState(() {
                                _tempUnit = value;
                              });
                            }
                          },
                          title: const Text('Celsius (°C)'),
                        ),
                      ],
                    ),
                    const SizedBox(height: 24),
                    _buildSection(
                      title: 'Wind Speed Units',
                      children: [
                        RadioListTile<String>(
                          value: 'mph',
                          groupValue: _windSpeedUnit,
                          onChanged: (value) {
                            if (value != null) {
                              setState(() {
                                _windSpeedUnit = value;
                              });
                            }
                          },
                          title: const Text('Miles per hour (mph)'),
                        ),
                        RadioListTile<String>(
                          value: 'kmh',
                          groupValue: _windSpeedUnit,
                          onChanged: (value) {
                            if (value != null) {
                              setState(() {
                                _windSpeedUnit = value;
                              });
                            }
                          },
                          title: const Text('Kilometers per hour (km/h)'),
                        ),
                      ],
                    ),
                    const SizedBox(height: 32),
                    SizedBox(
                      width: double.infinity,
                      child: ElevatedButton(
                        onPressed: _saveSettings,
                        style: ElevatedButton.styleFrom(
                          padding: const EdgeInsets.symmetric(vertical: 16),
                          backgroundColor: Colors.blue.shade700,
                          foregroundColor: Colors.white,
                        ),
                        child: const Text('Save Settings'),
                      ),
                    ),
                  ],
                ),
    );
  }
  
  Widget _buildSection({
    required String title,
    required List<Widget> children,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          title,
          style: Theme.of(context).textTheme.titleLarge?.copyWith(
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: 12),
        ...children,
      ],
    );
  }
  
  String _getThemeModeString(ThemeMode mode) {
    switch (mode) {
      case ThemeMode.light:
        return 'Light';
      case ThemeMode.dark:
        return 'Dark';
      case ThemeMode.system:
        return 'System';
    }
  }
}

