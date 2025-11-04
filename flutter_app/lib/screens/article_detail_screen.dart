import 'package:flutter/material.dart';
import 'package:flutter_html/flutter_html.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:share_plus/share_plus.dart';
import '../models/article.dart';
import '../services/api_service.dart';
import '../services/logger_service.dart';
import '../widgets/audio_player_widget.dart';
import '../widgets/chat_widget.dart';
import '../utils/date_formatter.dart';
import 'package:intl/intl.dart';

class ArticleDetailScreen extends StatefulWidget {
  final Article article;
  
  const ArticleDetailScreen({
    super.key,
    required this.article,
  });
  
  @override
  State<ArticleDetailScreen> createState() => _ArticleDetailScreenState();
}

class _ArticleDetailScreenState extends State<ArticleDetailScreen> {
  bool _showChat = false;
  bool _ttsEnabled = false;
  bool _rewriteLoading = false;
  
  @override
  void initState() {
    super.initState();
    LoggerService().logInfo('ArticleDetailScreen', 'Screen Initialized', details: 'Article ID: ${widget.article.id}');
    _checkTtsEnabled();
    _prefetchTimezone();
  }
  
  Future<void> _prefetchTimezone() async {
    // Prefetch timezone from server so date formatting works correctly
    try {
      await ApiService.getConfig(screenContext: 'ArticleDetailScreen');
    } catch (e) {
      // Ignore errors - date formatter will handle fallback
    }
  }
  
  Future<void> _checkTtsEnabled() async {
    try {
      LoggerService().logInfo('ArticleDetailScreen', 'Check TTS Enabled');
      final ttsSettings = await ApiService.getTtsSettings(screenContext: 'ArticleDetailScreen');
      if (mounted) {
        setState(() {
          _ttsEnabled = ttsSettings['enabled'] == true;
        });
        LoggerService().logInfo('ArticleDetailScreen', 'TTS Status', details: 'TTS Enabled: $_ttsEnabled');
      }
    } catch (e) {
      LoggerService().logError('ArticleDetailScreen', 'Check TTS Enabled', e);
    }
  }
  
  String _formatDate(String? dateStr) {
    // Use the DateFormatter utility which handles timezone correctly
    // The backend sends dates in location timezone
    return DateFormatter.formatDateSync(dateStr, format: 'MMMM d, y h:mm a');
  }
  
  Future<void> _openSourceUrl() async {
    LoggerService().logInfo('ArticleDetailScreen', 'Open Source URL', details: widget.article.sourceUrl);
    
    if (widget.article.sourceUrl == null) {
      LoggerService().logWarning('ArticleDetailScreen', 'Open Source URL', details: 'No source URL');
      return;
    }
    
    try {
      final uri = Uri.parse(widget.article.sourceUrl!);
      LoggerService().logInfo('ArticleDetailScreen', 'Launching URL');
      final launched = await launchUrl(uri, mode: LaunchMode.externalApplication);
      if (!launched) {
        throw Exception('Cannot launch URL');
      }
    } catch (e) {
      LoggerService().logError('ArticleDetailScreen', 'Open Source URL', e);
    }
  }
  
  Future<void> _shareArticle() async {
    try {
      final shareUrl = widget.article.sourceUrl ?? '';
      final shareText = '${widget.article.displayTitle}\n\n'
          '${widget.article.source != null ? 'Source: ${widget.article.source}\n' : ''}'
          '${widget.article.displayContent}\n\n'
          '$shareUrl';
      
      LoggerService().logInfo('ArticleDetailScreen', 'Share Article');
      await Share.share(
        shareText,
        subject: widget.article.displayTitle,
      );
    } catch (e) {
      LoggerService().logError('ArticleDetailScreen', 'Share Article', e);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to share article: ${e.toString()}')),
        );
      }
    }
  }
  
  Future<void> _forceRewrite() async {
    setState(() {
      _rewriteLoading = true;
    });
    
    try {
      LoggerService().logInfo('ArticleDetailScreen', 'Force Rewrite', details: 'Article ID: ${widget.article.id}');
      await ApiService.forceRewriteArticle(widget.article.id, screenContext: 'ArticleDetailScreen');
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Rewrite queued. The article will be updated shortly.'),
            duration: Duration(seconds: 3),
          ),
        );
        // Refresh after a delay to check for updates
        Future.delayed(const Duration(seconds: 5), () {
          if (mounted) {
            Navigator.of(context).pop();
          }
        });
      }
    } catch (e) {
      LoggerService().logError('ArticleDetailScreen', 'Force Rewrite', e);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to trigger rewrite: ${e.toString()}')),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          _rewriteLoading = false;
        });
      }
    }
  }
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Article'),
        actions: [
          IconButton(
            icon: const Icon(Icons.share),
            onPressed: _shareArticle,
            tooltip: 'Share article',
          ),
        ],
      ),
      body: SingleChildScrollView(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (widget.article.imageUrl != null)
              Image.network(
                widget.article.imageUrl!,
                width: double.infinity,
                height: 300,
                fit: BoxFit.cover,
                errorBuilder: (context, error, stackTrace) {
                  return Container(
                    height: 300,
                    color: Colors.grey[300],
                    child: const Icon(Icons.image_not_supported),
                  );
                },
              ),
            Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    _formatDate(widget.article.publishedAt ?? widget.article.fetchedAt),
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: Colors.grey[600],
                    ),
                  ),
                  if (widget.article.source != null) ...[
                    const SizedBox(height: 4),
                    Text(
                      widget.article.source!,
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: Colors.grey[600],
                      ),
                    ),
                  ],
                  const SizedBox(height: 16),
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          widget.article.displayTitle,
                          style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ),
                      if (widget.article.rewriteNote != null)
                        Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 8,
                            vertical: 4,
                          ),
                          decoration: BoxDecoration(
                            color: Colors.amber.shade100,
                            borderRadius: BorderRadius.circular(4),
                          ),
                          child: Text(
                            widget.article.rewriteNote!,
                            style: TextStyle(
                              fontSize: 10,
                              color: Colors.amber.shade900,
                            ),
                          ),
                        ),
                    ],
                  ),
                  if (widget.article.byline != null) ...[
                    const SizedBox(height: 8),
                    Text(
                      'By ${widget.article.byline}',
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: Colors.grey[600],
                      ),
                    ),
                  ],
                  const SizedBox(height: 24),
                  if (widget.article.displayContent.isNotEmpty)
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        if (widget.article.aiBody == null && widget.article.rawContent != null)
                          Padding(
                            padding: const EdgeInsets.only(bottom: 8),
                            child: Text(
                              'Showing original content (AI rewrite pending or unavailable)',
                              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                                fontStyle: FontStyle.italic,
                                color: Colors.amber.shade700,
                              ),
                            ),
                          ),
                        Html(
                          data: widget.article.displayContent.replaceAll('\n', '<br/>'),
                          style: {
                            'body': Style(
                              fontSize: FontSize(16),
                              lineHeight: const LineHeight(1.6),
                            ),
                          },
                        ),
                      ],
                    )
                  else
                    Padding(
                      padding: const EdgeInsets.all(16),
                      child: Text(
                        'No content available',
                        style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                          fontStyle: FontStyle.italic,
                          color: Colors.grey[600],
                        ),
                      ),
                    ),
                  const SizedBox(height: 24),
                  if (widget.article.sourceUrl != null)
                    OutlinedButton.icon(
                      onPressed: _openSourceUrl,
                      icon: const Icon(Icons.open_in_new),
                      label: const Text('View original article'),
                    ),
                  if (_ttsEnabled && (widget.article.aiBody != null || widget.article.rawContent != null)) ...[
                    const SizedBox(height: 24),
                    AudioPlayerWidget(
                      fetchUrl: 'api/tts/article/${widget.article.id}',
                    ),
                  ],
                  const SizedBox(height: 24),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      if ((widget.article.aiBody == null || (widget.article.aiModel ?? '').startsWith('fallback:'))) ...[
                        OutlinedButton.icon(
                          onPressed: _rewriteLoading ? null : _forceRewrite,
                          icon: _rewriteLoading
                              ? const SizedBox(
                                  width: 16,
                                  height: 16,
                                  child: CircularProgressIndicator(strokeWidth: 2),
                                )
                              : const Icon(Icons.refresh),
                          label: Text(_rewriteLoading ? 'Rewriting…' : 'Force Rewrite'),
                          style: OutlinedButton.styleFrom(
                            foregroundColor: Colors.blue,
                            side: const BorderSide(color: Colors.blue),
                          ),
                        ),
                      ],
                      if (widget.article.aiBody != null) ...[
                        OutlinedButton.icon(
                          onPressed: () {
                            LoggerService().logInfo('ArticleDetailScreen', 'Toggle Chat', details: 'Show: ${!_showChat}');
                            setState(() {
                              _showChat = !_showChat;
                            });
                          },
                          icon: Icon(_showChat ? Icons.comment : Icons.comment_outlined),
                          label: Text(_showChat ? 'Hide Comments' : 'Comments'),
                        ),
                      ],
                    ],
                  ),
                  if (_showChat && widget.article.aiBody != null) ...[
                    const SizedBox(height: 24),
                    SizedBox(
                      height: 400,
                      child: ChatWidget(
                        articleId: widget.article.id,
                        initialAuthor: widget.article.byline ?? 'Local Desk',
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
