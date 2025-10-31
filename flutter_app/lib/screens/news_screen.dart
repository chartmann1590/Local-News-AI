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
  Timer? _searchDebounceTimer;
  
  String _searchQuery = '';
  String _filterSource = '';
  String _sortBy = 'date_desc';
  List<String> _sources = [];
  bool _showFilters = false;
  
  final TextEditingController _searchController = TextEditingController();
  
  @override
  void initState() {
    super.initState();
    LoggerService().logInfo('NewsScreen', 'Screen Initialized');
    _searchController.addListener(_onSearchChanged);
    _loadSources();
    _loadArticles();
    _startAutoRefresh();
  }
  
  void _onSearchChanged() {
    _searchDebounceTimer?.cancel();
    _searchDebounceTimer = Timer(const Duration(milliseconds: 500), () {
      setState(() {
        _searchQuery = _searchController.text;
        _currentPage = 1;
        _loadArticles();
      });
    });
  }
  
  Future<void> _loadSources() async {
    try {
      final sources = await ApiService.getArticleSources(screenContext: 'NewsScreen');
      if (mounted) {
        setState(() {
          _sources = sources;
        });
      }
    } catch (e) {
      LoggerService().logError('NewsScreen', 'Load Sources', e);
    }
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
    _searchDebounceTimer?.cancel();
    _searchController.dispose();
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
      final response = await ApiService.getArticles(
        page: _currentPage,
        limit: 10,
        q: _searchQuery.isNotEmpty ? _searchQuery : null,
        source: _filterSource.isNotEmpty ? _filterSource : null,
        sortBy: _sortBy,
        screenContext: 'NewsScreen',
      );
      
      if (mounted) {
        final items = (response['items'] as List<dynamic>? ?? [])
            .map((item) => Article.fromJson(item as Map<String, dynamic>))
            .toList();
        // Sort newest first using server-provided sortTs when available
        items.sort((a, b) {
          final int sb = b.sortTs ?? DateTime.tryParse(b.publishedAt ?? b.fetchedAt ?? '')?.millisecondsSinceEpoch ?? 0;
          final int sa = a.sortTs ?? DateTime.tryParse(a.publishedAt ?? a.fetchedAt ?? '')?.millisecondsSinceEpoch ?? 0;
          return sb.compareTo(sa);
        });
        
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
            icon: Icon(_showFilters ? Icons.filter_list : Icons.filter_list_outlined),
            onPressed: () {
              setState(() {
                _showFilters = !_showFilters;
              });
            },
            tooltip: 'Filters',
          ),
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _refresh,
            tooltip: 'Refresh',
          ),
        ],
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(56),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            child: TextField(
              controller: _searchController,
              decoration: InputDecoration(
                hintText: 'Search articles...',
                prefixIcon: const Icon(Icons.search),
                suffixIcon: _searchQuery.isNotEmpty
                    ? IconButton(
                        icon: const Icon(Icons.clear),
                        onPressed: () {
                          _searchController.clear();
                          setState(() {
                            _searchQuery = '';
                            _currentPage = 1;
                          });
                          _loadArticles();
                        },
                      )
                    : null,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
                filled: true,
                fillColor: Theme.of(context).brightness == Brightness.dark
                    ? Colors.grey[800]
                    : Colors.grey[100],
              ),
            ),
          ),
        ),
      ),
      body: Column(
        children: [
          if (_showFilters) _buildFilters(),
          Expanded(child: _buildBody()),
        ],
      ),
    );
  }
  
  Widget _buildFilters() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Theme.of(context).brightness == Brightness.dark
            ? Colors.grey[900]
            : Colors.grey[50],
        border: Border(
          bottom: BorderSide(
            color: Colors.grey.withOpacity(0.3),
            width: 1,
          ),
        ),
      ),
      child: Column(
        children: [
          Row(
            children: [
              Expanded(
                child: DropdownButtonFormField<String>(
                  value: _filterSource.isEmpty ? null : _filterSource,
                  decoration: const InputDecoration(
                    labelText: 'Source',
                    border: OutlineInputBorder(),
                    contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                  ),
                  items: [
                    const DropdownMenuItem<String>(
                      value: null,
                      child: Text('All Sources'),
                    ),
                    ..._sources.map((s) => DropdownMenuItem<String>(
                      value: s,
                      child: Text(s),
                    )),
                  ],
                  onChanged: (value) {
                    setState(() {
                      _filterSource = value ?? '';
                      _currentPage = 1;
                    });
                    _loadArticles();
                  },
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: DropdownButtonFormField<String>(
                  value: _sortBy,
                  decoration: const InputDecoration(
                    labelText: 'Sort By',
                    border: OutlineInputBorder(),
                    contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                  ),
                  items: const [
                    DropdownMenuItem<String>(
                      value: 'date_desc',
                      child: Text('Date (Newest)'),
                    ),
                    DropdownMenuItem<String>(
                      value: 'date_asc',
                      child: Text('Date (Oldest)'),
                    ),
                    DropdownMenuItem<String>(
                      value: 'title',
                      child: Text('Title (A-Z)'),
                    ),
                    DropdownMenuItem<String>(
                      value: 'source',
                      child: Text('Source (A-Z)'),
                    ),
                  ],
                  onChanged: (value) {
                    if (value != null) {
                      setState(() {
                        _sortBy = value;
                        _currentPage = 1;
                      });
                      _loadArticles();
                    }
                  },
                ),
              ),
            ],
          ),
          if (_searchQuery.isNotEmpty || _filterSource.isNotEmpty || _sortBy != 'date_desc')
            Padding(
              padding: const EdgeInsets.only(top: 8),
              child: TextButton(
                onPressed: () {
                  setState(() {
                    _searchQuery = '';
                    _filterSource = '';
                    _sortBy = 'date_desc';
                    _currentPage = 1;
                  });
                  _searchController.clear();
                  _loadArticles();
                },
                child: const Text('Clear Filters'),
              ),
            ),
        ],
      ),
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
                    onBookmarkChanged: (articleId, bookmarked) {
                      // Update article in list
                      setState(() {
                        _articles = _articles.map((a) => 
                          a.id == articleId 
                            ? Article(
                                id: a.id,
                                title: a.title,
                                source: a.source,
                                sourceUrl: a.sourceUrl,
                                imageUrl: a.imageUrl,
                                publishedAt: a.publishedAt,
                                fetchedAt: a.fetchedAt,
                                sortTs: a.sortTs,
                                aiBody: a.aiBody,
                                aiModel: a.aiModel,
                                rewriteNote: a.rewriteNote,
                                byline: a.byline,
                                sourceTitle: a.sourceTitle,
                                isBookmarked: bookmarked,
                              )
                            : a
                        ).toList();
                      });
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

