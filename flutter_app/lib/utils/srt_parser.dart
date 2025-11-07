class SrtEntry {
  final int number;
  final double start; // in seconds
  final double end; // in seconds
  final String text;
  
  SrtEntry({
    required this.number,
    required this.start,
    required this.end,
    required this.text,
  });
}

class SrtParser {
  /// Parses SRT timestamp (HH:MM:SS,mmm) to seconds
  static double parseSrtTime(String timeStr) {
    final parts = timeStr.split(',');
    if (parts.length != 2) return 0.0;
    
    final time = parts[0].trim();
    final millis = int.tryParse(parts[1].trim()) ?? 0;
    
    final timeParts = time.split(':');
    if (timeParts.length != 3) return 0.0;
    
    final hours = int.tryParse(timeParts[0]) ?? 0;
    final minutes = int.tryParse(timeParts[1]) ?? 0;
    final seconds = int.tryParse(timeParts[2]) ?? 0;
    
    return hours * 3600.0 + minutes * 60.0 + seconds + (millis / 1000.0);
  }
  
  /// Parses SRT file content into structured data
  static List<SrtEntry> parseSrt(String srtContent) {
    final entries = <SrtEntry>[];
    final blocks = srtContent.trim().split(RegExp(r'\n\s*\n'));
    
    for (final block in blocks) {
      final lines = block.trim().split('\n');
      if (lines.length < 3) continue;
      
      final number = int.tryParse(lines[0].trim()) ?? 0;
      if (number == 0) continue;
      
      final timeLine = lines[1].trim();
      if (!timeLine.contains('-->')) continue;
      
      final timeParts = timeLine.split('-->');
      if (timeParts.length != 2) continue;
      
      final startStr = timeParts[0].trim();
      final endStr = timeParts[1].trim();
      final start = parseSrtTime(startStr);
      final end = parseSrtTime(endStr);
      
      final text = lines.sublist(2).join(' ').trim();
      if (text.isEmpty) continue;
      
      entries.add(SrtEntry(
        number: number,
        start: start,
        end: end,
        text: text,
      ));
    }
    
    // Sort by start time
    entries.sort((a, b) => a.start.compareTo(b.start));
    
    return entries;
  }
}

