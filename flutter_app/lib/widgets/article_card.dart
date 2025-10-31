import 'package:flutter/material.dart';
import '../models/article.dart';
import '../services/api_service.dart';
import '../services/logger_service.dart';
import 'package:intl/intl.dart';

class ArticleCard extends StatefulWidget {
  final Article article;
  final VoidCallback onTap;
  final Function(int articleId, bool bookmarked)? onBookmarkChanged;
  
  const ArticleCard({
    super.key,
    required this.article,
    required this.onTap,
    this.onBookmarkChanged,
  });
  
  @override
  State<ArticleCard> createState() => _ArticleCardState();
}

class _ArticleCardState extends State<ArticleCard> {
  bool? _isBookmarked;
  bool _bookmarkLoading = false;
  
  @override
  void initState() {
    super.initState();
    _isBookmarked = widget.article.isBookmarked;
  }
  
  Future<void> _toggleBookmark() async {
    if (_bookmarkLoading) return;
    setState(() {
      _bookmarkLoading = true;
    });
    try {
      final result = await ApiService.toggleBookmark(widget.article.id, screenContext: 'ArticleCard');
      final bookmarked = result['bookmarked'] as bool? ?? false;
      setState(() {
        _isBookmarked = bookmarked;
        _bookmarkLoading = false;
      });
      if (widget.onBookmarkChanged != null) {
        widget.onBookmarkChanged!(widget.article.id, bookmarked);
      }
    } catch (e) {
      LoggerService().logError('ArticleCard', 'Toggle Bookmark', e);
      setState(() {
        _bookmarkLoading = false;
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to update bookmark: ${e.toString()}')),
        );
      }
    }
  }
  
  String _formatDate(String? dateStr) {
    if (dateStr == null) return '';
    try {
      final date = DateTime.parse(dateStr);
      return DateFormat('MMM d, y • h:mm a').format(date);
    } catch (e) {
      return dateStr;
    }
  }
  
  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      elevation: 2,
      child: InkWell(
        onTap: widget.onTap,
        borderRadius: BorderRadius.circular(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (widget.article.imageUrl != null)
              ClipRRect(
                borderRadius: const BorderRadius.vertical(top: Radius.circular(12)),
                child: Image.network(
                  widget.article.imageUrl!,
                  height: 200,
                  width: double.infinity,
                  fit: BoxFit.cover,
                  errorBuilder: (context, error, stackTrace) {
                    return Container(
                      height: 200,
                      color: Colors.grey[300],
                      child: const Icon(Icons.image_not_supported),
                    );
                  },
                ),
              ),
            Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          _formatDate(widget.article.publishedAt ?? widget.article.fetchedAt),
                          style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: Colors.grey[600],
                          ),
                        ),
                      ),
                      if (widget.article.source != null)
                        Text(
                          '• ${widget.article.source}',
                          style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: Colors.grey[600],
                          ),
                        ),
                      IconButton(
                        icon: Icon(
                          _isBookmarked == true ? Icons.star : Icons.star_border,
                          color: _isBookmarked == true ? Colors.amber : Colors.grey,
                        ),
                        onPressed: _bookmarkLoading ? null : _toggleBookmark,
                        tooltip: _isBookmarked == true ? 'Remove bookmark' : 'Add bookmark',
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          widget.article.displayTitle,
                          style: Theme.of(context).textTheme.titleLarge?.copyWith(
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ),
                      if (widget.article.rewriteNote != null)
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
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
                    const SizedBox(height: 4),
                    Text(
                      'By ${widget.article.byline}',
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: Colors.grey[600],
                      ),
                    ),
                  ],
                  const SizedBox(height: 12),
                  Text(
                    widget.article.preview,
                    style: Theme.of(context).textTheme.bodyMedium,
                    maxLines: 4,
                    overflow: TextOverflow.ellipsis,
                  ),
                  if (widget.article.hasMore) ...[
                    const SizedBox(height: 8),
                    Text(
                      'Read more →',
                      style: TextStyle(
                        color: Colors.blue.shade600,
                        fontWeight: FontWeight.w500,
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





