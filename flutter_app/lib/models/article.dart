class Article {
  final int id;
  final String title;
  final String? source;
  final String? sourceUrl;
  final String? imageUrl;
  final String? publishedAt;
  final String? fetchedAt;
  final int? sortTs;
  final String? aiBody;
  final String? aiModel;
  final String? rewriteNote;
  final String? byline;
  final String? sourceTitle;
  final bool? isBookmarked;
  final String? rawContent;
  
  Article({
    required this.id,
    required this.title,
    this.source,
    this.sourceUrl,
    this.imageUrl,
    this.publishedAt,
    this.fetchedAt,
    this.sortTs,
    this.aiBody,
    this.aiModel,
    this.rewriteNote,
    this.byline,
    this.sourceTitle,
    this.isBookmarked,
    this.rawContent,
  });
  
  factory Article.fromJson(Map<String, dynamic> json) {
    return Article(
      id: json['id'] as int,
      title: json['title'] as String? ?? json['source_title'] as String? ?? 'Untitled',
      source: json['source'] as String?,
      sourceUrl: json['source_url'] as String?,
      imageUrl: json['image_url'] as String?,
      publishedAt: json['published_at'] as String?,
      fetchedAt: json['fetched_at'] as String?,
      sortTs: json['sort_ts'] as int?,
      aiBody: json['ai_body'] as String?,
      aiModel: json['ai_model'] as String?,
      rewriteNote: json['rewrite_note'] as String?,
      byline: json['byline'] as String?,
      sourceTitle: json['source_title'] as String?,
      isBookmarked: json['is_bookmarked'] as bool?,
      rawContent: json['raw_content'] as String?,
    );
  }
  
  String get displayTitle => title;
  String get displayContent => aiBody ?? rawContent ?? '';
  String get preview => displayContent.length > 500 
    ? displayContent.substring(0, 500)
    : displayContent;
  bool get hasMore => displayContent.length > 500;
}



