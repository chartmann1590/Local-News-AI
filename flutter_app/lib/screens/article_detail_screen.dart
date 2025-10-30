import 'package:flutter/material.dart';
import 'package:flutter_html/flutter_html.dart';
import 'package:url_launcher/url_launcher.dart';
import '../models/article.dart';
import '../services/api_service.dart';
import '../services/logger_service.dart';
import '../widgets/audio_player_widget.dart';
import '../widgets/chat_widget.dart';
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
  
  @override
  void initState() {
    super.initState();
    LoggerService().logInfo('ArticleDetailScreen', 'Screen Initialized', details: 'Article ID: ${widget.article.id}');
    _checkTtsEnabled();
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
    if (dateStr == null) return '';
    try {
      final date = DateTime.parse(dateStr);
      return DateFormat('MMMM d, y • h:mm a').format(date);
    } catch (e) {
      return dateStr;
    }
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
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Article'),
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
                  if (widget.article.aiBody != null)
                    Html(
                      data: widget.article.aiBody!.replaceAll('\n', '<br/>'),
                      style: {
                        'body': Style(
                          fontSize: FontSize(16),
                          lineHeight: const LineHeight(1.6),
                        ),
                      },
                    )
                  else
                    Padding(
                      padding: const EdgeInsets.all(16),
                      child: Text(
                        'AI rewrite pending…',
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
                  if (_ttsEnabled && widget.article.aiBody != null) ...[
                    const SizedBox(height: 24),
                    AudioPlayerWidget(
                      fetchUrl: 'api/tts/article/${widget.article.id}',
                    ),
                  ],
                  if (widget.article.aiBody != null) ...[
                    const SizedBox(height: 24),
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
