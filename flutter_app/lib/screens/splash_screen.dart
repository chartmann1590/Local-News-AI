import 'dart:async';
import 'package:flutter/material.dart';
import '../services/storage_service.dart';
import '../services/logger_service.dart';
import '../models/server_config.dart';

class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});
  
  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen> with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _fadeAnimation;
  late Animation<double> _scaleAnimation;
  
  @override
  void initState() {
    super.initState();
    LoggerService().logInfo('SplashScreen', 'Screen Initialized');
    
    _controller = AnimationController(
      duration: const Duration(milliseconds: 1500),
      vsync: this,
    );
    
    _fadeAnimation = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(
        parent: _controller,
        curve: Curves.easeIn,
      ),
    );
    
    _scaleAnimation = Tween<double>(begin: 0.5, end: 1.0).animate(
      CurvedAnimation(
        parent: _controller,
        curve: Curves.easeOutBack,
      ),
    );
    
    LoggerService().logInfo('SplashScreen', 'Starting Animation');
    _controller.forward();
    _checkServerConfig();
  }
  
  Future<void> _checkServerConfig() async {
    LoggerService().logInfo('SplashScreen', 'Checking Server Config', details: 'Waiting 5 seconds');
    await Future.delayed(const Duration(seconds: 5));
    
    if (!mounted) {
      LoggerService().logWarning('SplashScreen', 'Check Config', details: 'Widget not mounted');
      return;
    }
    
    try {
      final config = await StorageService.getServerConfigAsync();
      
      if (!mounted) {
        LoggerService().logWarning('SplashScreen', 'Check Config', details: 'Widget not mounted after config load');
        return;
      }
      
      if (config == null) {
        LoggerService().logInfo('SplashScreen', 'Navigate to Server Config', details: 'No server config found');
        Navigator.of(context).pushReplacementNamed('/server-config');
      } else {
        LoggerService().logInfo('SplashScreen', 'Navigate to Home', details: 'Server config found: ${config.baseUrl}');
        Navigator.of(context).pushReplacementNamed('/home');
      }
    } catch (e) {
      LoggerService().logError('SplashScreen', 'Check Server Config', e);
      if (mounted) {
        Navigator.of(context).pushReplacementNamed('/server-config');
      }
    }
  }
  
  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }
  
  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    
    return Scaffold(
      body: Container(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: isDark
                ? [
                    const Color(0xFF0F172A),
                    const Color(0xFF1E293B),
                    const Color(0xFF334155),
                  ]
                : [
                    Colors.white,
                    Colors.blue.shade50,
                    Colors.cyan.shade50,
                  ],
          ),
        ),
        child: Center(
          child: FadeTransition(
            opacity: _fadeAnimation,
            child: ScaleTransition(
              scale: _scaleAnimation,
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Text(
                    '📰',
                    style: TextStyle(fontSize: 80),
                  ),
                  const SizedBox(height: 24),
                  Text(
                    'Local News & Weather',
                    style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                      fontWeight: FontWeight.bold,
                      color: isDark ? Colors.white : Colors.black87,
                    ),
                  ),
                  const SizedBox(height: 32),
                  SizedBox(
                    width: 40,
                    height: 40,
                    child: CircularProgressIndicator(
                      strokeWidth: 3,
                      valueColor: AlwaysStoppedAnimation<Color>(
                        Colors.blue.shade600,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

