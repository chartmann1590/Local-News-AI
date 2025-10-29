import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/server_config.dart';
import '../services/storage_service.dart';
import '../services/api_service.dart';
import '../services/logger_service.dart';
import '../utils/constants.dart';

class ServerConfigScreen extends StatefulWidget {
  const ServerConfigScreen({super.key});
  
  @override
  State<ServerConfigScreen> createState() => _ServerConfigScreenState();
}

class _ServerConfigScreenState extends State<ServerConfigScreen> {
  final _formKey = GlobalKey<FormState>();
  final _ipController = TextEditingController();
  final _portController = TextEditingController(text: Constants.defaultServerPort);
  
  bool _isTesting = false;
  bool _isSaving = false;
  String? _testMessage;
  bool _testSuccess = false;
  
  @override
  void initState() {
    super.initState();
    LoggerService().logInfo('ServerConfigScreen', 'Screen Initialized');
    _loadCurrentConfig();
  }
  
  Future<void> _loadCurrentConfig() async {
    LoggerService().logInfo('ServerConfigScreen', 'Load Current Config');
    try {
      final config = await StorageService.getServerConfigAsync();
      if (config != null) {
        LoggerService().logInfo('ServerConfigScreen', 'Config Loaded', details: 'IP: ${config.ip}, Port: ${config.port}');
        setState(() {
          _ipController.text = config.ip;
          _portController.text = config.port;
        });
      } else {
        LoggerService().logInfo('ServerConfigScreen', 'No Config Found');
      }
    } catch (e) {
      LoggerService().logError('ServerConfigScreen', 'Load Current Config', e);
    }
  }
  
  Future<void> _testConnection() async {
    LoggerService().logInfo('ServerConfigScreen', 'Test Connection');
    
    if (!_formKey.currentState!.validate()) {
      LoggerService().logWarning('ServerConfigScreen', 'Test Connection', details: 'Validation failed');
      return;
    }
    
    setState(() {
      _isTesting = true;
      _testMessage = null;
      _testSuccess = false;
    });
    
    try {
      final config = ServerConfig(
        ip: _ipController.text.trim(),
        port: _portController.text.trim(),
      );
      
      LoggerService().logInfo('ServerConfigScreen', 'Testing Connection', details: 'Server: ${config.baseUrl}');
      final success = await ApiService.testConnection(config, screenContext: 'ServerConfigScreen');
      
      LoggerService().logInfo('ServerConfigScreen', 'Connection Test Result', details: success ? 'Success' : 'Failed');
      
      setState(() {
        _isTesting = false;
        _testSuccess = success;
        _testMessage = success
            ? 'Connection successful!'
            : 'Connection failed. Please check your server IP and port.';
      });
    } catch (e) {
      LoggerService().logError('ServerConfigScreen', 'Test Connection', e);
      setState(() {
        _isTesting = false;
        _testSuccess = false;
        _testMessage = 'Connection error: ${e.toString()}';
      });
    }
  }
  
  Future<void> _saveConfig() async {
    LoggerService().logInfo('ServerConfigScreen', 'Save Config');
    
    if (!_formKey.currentState!.validate()) {
      LoggerService().logWarning('ServerConfigScreen', 'Save Config', details: 'Validation failed');
      return;
    }
    
    // Test connection before saving
    if (!_testSuccess) {
      LoggerService().logWarning('ServerConfigScreen', 'Save Config', details: 'Connection not tested');
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Please test the connection first'),
          backgroundColor: Colors.orange,
        ),
      );
      return;
    }
    
    setState(() {
      _isSaving = true;
    });
    
    try {
      final config = ServerConfig(
        ip: _ipController.text.trim(),
        port: _portController.text.trim(),
      );
      
      LoggerService().logInfo('ServerConfigScreen', 'Saving Config', details: 'Server: ${config.baseUrl}');
      await StorageService.saveServerConfig(config);
      await ApiService.updateBaseUrl();
      
      LoggerService().logInfo('ServerConfigScreen', 'Config Saved', details: 'Navigating to home');
      
      if (mounted) {
        Navigator.of(context).pushReplacementNamed('/');
      }
    } catch (e) {
      LoggerService().logError('ServerConfigScreen', 'Save Config', e);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to save: ${e.toString()}'),
            backgroundColor: Colors.red,
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          _isSaving = false;
        });
      }
    }
  }
  
  @override
  void dispose() {
    _ipController.dispose();
    _portController.dispose();
    super.dispose();
  }
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Server Configuration'),
        backgroundColor: Colors.blue.shade600,
      ),
      body: SafeArea(
        child: Form(
          key: _formKey,
          child: ListView(
            padding: const EdgeInsets.all(24.0),
            children: [
              const SizedBox(height: 32),
              Text(
                'Configure Server',
                style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 8),
              Text(
                'Enter your News AI server address',
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: Colors.grey[600],
                ),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 48),
              TextFormField(
                controller: _ipController,
                decoration: const InputDecoration(
                  labelText: 'Server IP Address',
                  hintText: '192.168.1.100 or localhost',
                  border: OutlineInputBorder(),
                  prefixIcon: Icon(Icons.computer),
                ),
                keyboardType: TextInputType.url,
                validator: (value) {
                  if (value == null || value.trim().isEmpty) {
                    return 'Please enter server IP';
                  }
                  return null;
                },
              ),
              const SizedBox(height: 16),
              TextFormField(
                controller: _portController,
                decoration: const InputDecoration(
                  labelText: 'Port',
                  hintText: '8000',
                  border: OutlineInputBorder(),
                  prefixIcon: Icon(Icons.numbers),
                ),
                keyboardType: TextInputType.number,
                validator: (value) {
                  if (value == null || value.trim().isEmpty) {
                    return 'Please enter port number';
                  }
                  final port = int.tryParse(value.trim());
                  if (port == null || port < 1 || port > 65535) {
                    return 'Please enter a valid port (1-65535)';
                  }
                  return null;
                },
              ),
              const SizedBox(height: 24),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton.icon(
                  onPressed: _isTesting ? null : _testConnection,
                  icon: _isTesting
                      ? const SizedBox(
                          width: 20,
                          height: 20,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.wifi_find),
                  label: Text(_isTesting ? 'Testing...' : 'Test Connection'),
                  style: ElevatedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(vertical: 16),
                    backgroundColor: Colors.blue.shade700,
                    foregroundColor: Colors.white,
                  ),
                ),
              ),
              if (_testMessage != null) ...[
                const SizedBox(height: 16),
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: _testSuccess
                        ? Colors.green.shade50
                        : Colors.red.shade50,
                    border: Border.all(
                      color: _testSuccess
                          ? Colors.green.shade300
                          : Colors.red.shade300,
                    ),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Row(
                    children: [
                      Icon(
                        _testSuccess ? Icons.check_circle : Icons.error,
                        color: _testSuccess
                            ? Colors.green.shade700
                            : Colors.red.shade700,
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Text(
                          _testMessage!,
                          style: TextStyle(
                            color: _testSuccess
                                ? Colors.green.shade700
                                : Colors.red.shade700,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
              const SizedBox(height: 24),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton.icon(
                  onPressed: (_isSaving || !_testSuccess) ? null : _saveConfig,
                  icon: _isSaving
                      ? const SizedBox(
                          width: 20,
                          height: 20,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.save),
                  label: Text(_isSaving ? 'Saving...' : 'Save Configuration'),
                  style: ElevatedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(vertical: 16),
                    backgroundColor: Colors.green.shade700,
                    foregroundColor: Colors.white,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

