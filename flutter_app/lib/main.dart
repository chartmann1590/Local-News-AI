import 'dart:ui' as ui;
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import 'services/storage_service.dart';
import 'services/theme_service.dart';
import 'services/api_service.dart';
import 'services/logger_service.dart';
import 'screens/server_config_screen.dart';
import 'screens/splash_screen.dart';
import 'screens/news_screen.dart';
import 'screens/weather_screen.dart';
import 'screens/settings_screen.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  
  // Initialize logging
  LoggerService().logInfo('App', 'Application Started', details: 'Version 1.0.0');
  
  // Initialize services
  try {
    await StorageService.init();
    LoggerService().logInfo('App', 'Storage Initialized');
  } catch (e) {
    LoggerService().logError('App', 'Storage Init', e);
  }
  
  // Set up global error handler
  FlutterError.onError = (FlutterErrorDetails details) {
    LoggerService().logError('App', 'Flutter Error', details.exception, details: details.stack.toString());
    FlutterError.presentError(details);
  };
  
  // Set up platform error handler
  ui.PlatformDispatcher.instance.onError = (error, stack) {
    LoggerService().logError('App', 'Platform Error', error, details: stack.toString());
    return true;
  };
  
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});
  
  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider(
      create: (_) => ThemeService(),
      child: Consumer<ThemeService>(
        builder: (context, themeService, child) {
          return MaterialApp(
            title: 'News AI',
            debugShowCheckedModeBanner: false,
            theme: themeService.lightTheme,
            darkTheme: themeService.darkTheme,
            themeMode: themeService.themeMode,
            initialRoute: '/splash',
            routes: {
              '/splash': (context) => const SplashScreen(),
              '/server-config': (context) => const ServerConfigScreen(),
              '/home': (context) => const MainScreen(),
            },
          );
        },
      ),
    );
  }
}

class MainScreen extends StatefulWidget {
  const MainScreen({super.key});
  
  @override
  State<MainScreen> createState() => _MainScreenState();
}

class _MainScreenState extends State<MainScreen> {
  int _currentIndex = 0;
  
  final List<Widget> _screens = [
    const NewsScreen(),
    const WeatherScreen(),
    const SettingsScreen(),
  ];
  
  final List<String> _screenNames = ['NewsScreen', 'WeatherScreen', 'SettingsScreen'];
  
  @override
  void initState() {
    super.initState();
    LoggerService().logInfo('MainScreen', 'Screen Initialized');
  }
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: IndexedStack(
        index: _currentIndex,
        children: _screens,
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _currentIndex,
        onDestinationSelected: (index) {
          LoggerService().logInfo('MainScreen', 'Navigate', details: 'From ${_screenNames[_currentIndex]} to ${_screenNames[index]}');
          setState(() {
            _currentIndex = index;
          });
        },
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.article_outlined),
            selectedIcon: Icon(Icons.article),
            label: 'News',
          ),
          NavigationDestination(
            icon: Icon(Icons.wb_sunny_outlined),
            selectedIcon: Icon(Icons.wb_sunny),
            label: 'Weather',
          ),
          NavigationDestination(
            icon: Icon(Icons.settings_outlined),
            selectedIcon: Icon(Icons.settings),
            label: 'Settings',
          ),
        ],
      ),
    );
  }
}

