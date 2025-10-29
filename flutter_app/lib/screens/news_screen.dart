import 'dart:async';
import 'package:flutter/material.dart';
import '../models/article.dart';
import '../services/api_service.dart';
import '../services/logger_service.dart';
import '../widgets/article_card.dart';
import 'article_detail_screen.dart';

class NewsScreen extends StatefulWidget {
  const NewsScreen({super.key});
  
  @override
  State<NewsScreen> createState() => _NewsScreenState();
}

class _NewsScreenState extends State<NewsScreen> {
  List<Article> _articles = [];
  bool _isLoading = true;
  bool _isRefreshing = false;
  String? _error;
  int _currentPage = 1;
  int _totalPages = 1;
  int _totalArticles = 0;
  
  Timer? _refreshTimer;
  
  @override
  void initState() {
    super.initState();
    LoggerService().logInfo('NewsScreen', 'Screen Initialized');
    _loadArticles();
    _startAutoRefresh();
  }
  
  void _startAutoRefresh() {
    LoggerService().logInfo('NewsScreen', 'Start Auto Refresh');
    _refreshTimer = Timer.periodic(
      const Duration(seconds: 30),
      (_) {
        LoggerService().logInfo('NewsScreen', 'Auto Refresh Triggered');
        _loadArticles(isBackground: true);
      },
    );
  }
  
  @override
  void dispose() {
    LoggerService().logInfo('NewsScreen', 'Screen Disposed');
    _refreshTimer?.cancel();
    super.dispose();
  }
  
  Future<void> _loadArticles({bool isBackground = false}) async {
    LoggerService().logInfo('NewsScreen', 'Load Articles', details: 'Page: $_currentPage, Background: $isBackground');
    
    if (!isBackground && mounted) {
      setState(() {
        _isLoading = true;
        _error = null;
      });
    }
    
    try {
      final response = await ApiService.getArticles(page: _currentPage, limit: 10, screenContext: 'NewsScreen');
      
      if (mounted) {
        final items = (response['items'] as List<dynamic>? ?? [])
            .map((item) => Article.fromJson(item as Map<String, dynamic>))
            .toList();
        
        LoggerService().logInfo('NewsScreen', 'Articles Loaded', details: 'Count: ${items.length}, Total: ${response['total']}, Pages: ${response['pages']}');
        
        setState(() {
          _articles = items;
          _totalPages = response['pages'] as int? ?? 1;
          _totalArticles = response['total'] as int? ?? 0;
          _isLoading = false;
          _isRefreshing = false;
          _error = null;
        });
      }
    } catch (e) {
      LoggerService().logError('NewsScreen', 'Load Articles', e, details: 'Page: $_currentPage');
      if (mounted) {
        setState(() {
          _isLoading = false;
          _isRefreshing = false;
          _error = 'Failed to load articles: ${e.toString()}';
        });
      }
    }
  }
  
  Future<void> _refresh() async {
    LoggerService().logInfo('NewsScreen', 'Refresh Articles');
    setState(() {
      _isRefreshing = true;
    });
    await _loadArticles();
  }
  
  void _navigateToPage(int page) {
    if (page < 1 || page > _totalPages) {
      LoggerService().logWarning('NewsScreen', 'Navigate Page', details: 'Invalid page: $page');
      return;
    }
    
    LoggerService().logInfo('NewsScreen', 'Navigate Page', details: 'From $_currentPage to $page');
    setState(() {
      _currentPage = page;
    });
    _loadArticles();
  }
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Latest Local News'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _refresh,
            tooltip: 'Refresh',
          ),
        ],
      ),
      body: _buildBody(),
    );
  }
  
  Widget _buildBody() {
    if (_isLoading && _articles.isEmpty) {
      return const Center(child: CircularProgressIndicator());
    }
    
    if (_error != null && _articles.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.error_outline,
              size: 64,
              color: Colors.red[300],
            ),
            const SizedBox(height: 16),
            Text(
              _error!,
              textAlign: TextAlign.center,
              style: TextStyle(color: Colors.red[700]),
            ),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: _loadArticles,
              child: const Text('Retry'),
            ),
          ],
        ),
      );
    }
    
    return RefreshIndicator(
      onRefresh: _refresh,
      child: CustomScrollView(
        slivers: [
          SliverList(
            delegate: SliverChildBuilderDelegate(
              (context, index) {
                if (index < _articles.length) {
                  final article = _articles[index];
                  return ArticleCard(
                    article: article,
                    onTap: () {
                      LoggerService().logInfo('NewsScreen', 'Article Tapped', details: 'Article ID: ${article.id}, Title: ${article.title}');
                      Navigator.push(
                        context,
                        MaterialPageRoute(
                          builder: (context) => ArticleDetailScreen(article: article),
                        ),
                      );
                    },
                  );
                }
                return null;
              },
              childCount: _articles.length,
            ),
          ),
          if (!_isLoading && _articles.isEmpty)
            SliverFillRemaining(
              child: Center(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(
                      Icons.article_outlined,
                      size: 64,
                      color: Colors.grey[400],
                    ),
                    const SizedBox(height: 16),
                    Text(
                      'No articles yet',
                      style: TextStyle(color: Colors.grey[600]),
                    ),
                  ],
                ),
              ),
            ),
          if (_articles.isNotEmpty)
            SliverPadding(
              padding: const EdgeInsets.all(16),
              sliver: SliverToBoxAdapter(
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      'Page $_currentPage of $_totalPages',
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                    Row(
                      children: [
                        IconButton(
                          icon: const Icon(Icons.chevron_left),
                          onPressed: _currentPage > 1
                              ? () => _navigateToPage(_currentPage - 1)
                              : null,
                        ),
                        IconButton(
                          icon: const Icon(Icons.chevron_right),
                          onPressed: _currentPage < _totalPages
                              ? () => _navigateToPage(_currentPage + 1)
                              : null,
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
        ],
      ),
    );
  }
}

