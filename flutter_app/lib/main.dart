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
import 'screens/article_detail_screen.dart';
import 'models/article.dart';

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

class MyApp extends StatefulWidget {
  const MyApp({super.key});
  
  @override
  State<MyApp> createState() => _MyAppState();
}

class _MyAppState extends State<MyApp> {
  static const platform = MethodChannel('com.newsaiapp/deep_link');
  String? pendingDeepLink;

  @override
  void initState() {
    super.initState();
    _setupDeepLinkListener();
    _checkInitialDeepLink();
  }

  void _setupDeepLinkListener() {
    platform.setMethodCallHandler((call) async {
      if (call.method == 'handleDeepLink') {
        final deepLink = call.arguments as String?;
        if (deepLink != null) {
          _handleDeepLink(deepLink);
        }
      }
    });
  }

  Future<void> _checkInitialDeepLink() async {
    try {
      final deepLink = await platform.invokeMethod<String>('getInitialDeepLink');
      if (deepLink != null) {
        pendingDeepLink = deepLink;
      }
    } catch (e) {
      LoggerService().logError('MyApp', 'Check Initial Deep Link', e);
    }
  }

  void _handleDeepLink(String deepLink) {
    LoggerService().logInfo('MyApp', 'Handle Deep Link', details: deepLink);
    
    if (deepLink.startsWith('news://article/')) {
      final articleIdStr = deepLink.replaceFirst('news://article/', '');
      final articleId = int.tryParse(articleIdStr);
      if (articleId != null) {
        _navigateToArticle(articleId);
      }
    } else if (deepLink == 'news://weather') {
      _navigateToWeather();
    }
  }

  void _navigateToArticle(int articleId) {
    // Wait for navigation context to be available
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final navigator = navigatorKey.currentState;
      if (navigator != null) {
        // First navigate to home if not already there
        navigator.pushNamedAndRemoveUntil('/home', (route) => false);
        
        // Then fetch article and navigate to detail
        _fetchAndNavigateToArticle(articleId);
      }
    });
  }

  Future<void> _fetchAndNavigateToArticle(int articleId) async {
    try {
      LoggerService().logInfo('MyApp', 'Fetch Article', details: 'Article ID: $articleId');
      
      // Fetch article from API
      final response = await ApiService.getArticles(page: 1, limit: 100, screenContext: 'DeepLink');
      final items = (response['items'] as List<dynamic>? ?? [])
          .map((item) => Article.fromJson(item as Map<String, dynamic>))
          .toList();
      
      final article = items.firstWhere(
        (a) => a.id == articleId,
        orElse: () => throw Exception('Article not found'),
      );
      
      final navigator = navigatorKey.currentState;
      if (navigator != null) {
        navigator.push(
          MaterialPageRoute(
            builder: (context) => ArticleDetailScreen(article: article),
          ),
        );
      }
    } catch (e) {
      LoggerService().logError('MyApp', 'Fetch Article', e, details: 'Article ID: $articleId');
      
      // Show error message
      final navigator = navigatorKey.currentState;
      if (navigator != null) {
        ScaffoldMessenger.of(navigator.context).showSnackBar(
          SnackBar(content: Text('Failed to load article: ${e.toString()}')),
        );
      }
    }
  }

  void _navigateToWeather() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final navigator = navigatorKey.currentState;
      if (navigator != null) {
        navigator.pushNamedAndRemoveUntil('/home', (route) => false);
        
        // Navigate to weather tab
        final mainScreenState = navigator.context.findAncestorStateOfType<_MainScreenState>();
        if (mainScreenState != null) {
          mainScreenState.navigateToWeather();
        }
      }
    });
  }

  final GlobalKey<NavigatorState> navigatorKey = GlobalKey<NavigatorState>();

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider(
      create: (_) => ThemeService(),
      child: Consumer<ThemeService>(
        builder: (context, themeService, child) {
          return MaterialApp(
            navigatorKey: navigatorKey,
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
    
    // Check for pending deep link from app initialization
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final appState = context.findAncestorStateOfType<_MyAppState>();
      if (appState != null && appState.pendingDeepLink != null) {
        appState._handleDeepLink(appState.pendingDeepLink!);
        appState.pendingDeepLink = null;
      }
    });
  }
  
  void navigateToWeather() {
    setState(() {
      _currentIndex = 1;
    });
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

