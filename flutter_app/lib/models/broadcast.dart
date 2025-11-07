class Broadcast {
  final int id;
  final String? createdAt;
  final String? transcript;
  final double? durationSeconds;
  final int? articleCount;
  final bool? includesWeather;
  final String? srtPath;
  
  Broadcast({
    required this.id,
    this.createdAt,
    this.transcript,
    this.durationSeconds,
    this.articleCount,
    this.includesWeather,
    this.srtPath,
  });
  
  factory Broadcast.fromJson(Map<String, dynamic> json) {
    return Broadcast(
      id: json['id'] as int,
      createdAt: json['created_at'] as String?,
      transcript: json['transcript'] as String?,
      durationSeconds: (json['duration_seconds'] as num?)?.toDouble(),
      articleCount: json['article_count'] as int?,
      includesWeather: json['includes_weather'] as bool?,
      srtPath: json['srt_path'] as String?,
    );
  }
}


