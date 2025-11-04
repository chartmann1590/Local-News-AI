import 'package:intl/intl.dart';
import 'package:timezone/timezone.dart' as tz;
import 'package:timezone/data/latest_all.dart' as tzdata;
import '../services/api_service.dart';

class DateFormatter {
  static String? _cachedTimezone;
  static DateTime? _cacheTime;
  static bool _initialized = false;
  static const Duration _cacheExpiry = Duration(minutes: 5);
  
  /// Initialize timezone data
  static void _ensureInitialized() {
    if (!_initialized) {
      tzdata.initializeTimeZones();
      _initialized = true;
    }
  }
  
  /// Get the server timezone from config, with caching
  static Future<String?> getServerTimezone() async {
    try {
      // Use cached timezone if available and fresh
      if (_cachedTimezone != null && _cacheTime != null) {
        if (DateTime.now().difference(_cacheTime!) < _cacheExpiry) {
          return _cachedTimezone;
        }
      }
      
      // Fetch from server
      final config = await ApiService.getConfig();
      final timezone = config['timezone'] as String?;
      
      if (timezone != null) {
        _cachedTimezone = timezone;
        _cacheTime = DateTime.now();
        return timezone;
      }
      
      return null;
    } catch (e) {
      // If fetching fails, return cached value or null
      return _cachedTimezone;
    }
  }
  
  /// Format a date string using the server's timezone
  /// The backend sends ISO datetime strings with timezone offset in the location timezone
  /// Format: "MMM d, y h:mm a" (e.g., "Jan 15, 2024 3:45 PM")
  static Future<String> formatDate(String? dateStr, {String? format}) async {
    if (dateStr == null || dateStr.isEmpty) return '';
    
    _ensureInitialized();
    
    try {
      // Parse the ISO date string (includes timezone offset)
      final parsedDate = DateTime.parse(dateStr);
      
      // Get server timezone
      final timezoneName = await getServerTimezone();
      
      if (timezoneName != null) {
        try {
          // Get the timezone location
          final location = tz.getLocation(timezoneName);
          
          // Convert the parsed UTC date to the server timezone
          // DateTime.parse converts to local, so we need to get the UTC equivalent first
          final utcDate = parsedDate.toUtc();
          final tzDate = tz.TZDateTime.from(utcDate, location);
          
          // Format with the requested format or default
          final formatter = DateFormat(format ?? 'MMM d, y h:mm a');
          return formatter.format(tzDate);
        } catch (e) {
          // If timezone conversion fails, fall back to simple formatting
          final formatter = DateFormat(format ?? 'MMM d, y h:mm a');
          return formatter.format(parsedDate);
        }
      }
      
      // No timezone info - format as-is
      final formatter = DateFormat(format ?? 'MMM d, y h:mm a');
      return formatter.format(parsedDate);
    } catch (e) {
      // If parsing fails, return the original string
      return dateStr;
    }
  }
  
  /// Synchronous version - uses cached timezone if available
  /// The backend sends ISO strings with timezone offset (e.g., "2025-11-02T16:37:43-05:00")
  /// This represents the time in the server's location timezone.
  /// Format: "MMM d, y h:mm a" (e.g., "Jan 15, 2024 3:45 PM")
  static String formatDateSync(String? dateStr, {String? format, String? timezone}) {
    if (dateStr == null || dateStr.isEmpty) return '';
    
    _ensureInitialized();
    
    try {
      // Parse the ISO date string which includes timezone offset
      // DateTime.parse() interprets the offset and creates a DateTime object
      final parsedDate = DateTime.parse(dateStr);
      
      // Use provided timezone or cached timezone
      final timezoneName = timezone ?? _cachedTimezone;
      
      if (timezoneName != null) {
        try {
          // Get the server timezone location
          final location = tz.getLocation(timezoneName);
          
          // The ISO string has timezone offset (e.g., "-05:00")
          // DateTime.parse() converts this to a DateTime in device local timezone
          // We need to get the UTC equivalent, then convert to server timezone
          final utcDate = parsedDate.toUtc();
          
          // Convert from UTC to server timezone
          // This gives us the time as it was in the server's location timezone
          final tzDate = tz.TZDateTime.from(utcDate, location);
          
          // Format in server timezone
          final formatter = DateFormat(format ?? 'MMM d, y h:mm a');
          return formatter.format(tzDate);
        } catch (e) {
          // If timezone conversion fails, use UTC for consistency
          try {
            final utcDate = parsedDate.toUtc();
            final formatter = DateFormat(format ?? 'MMM d, y h:mm a');
            return formatter.format(utcDate);
          } catch (e2) {
            // Ultimate fallback
            final formatter = DateFormat(format ?? 'MMM d, y h:mm a');
            return formatter.format(parsedDate);
          }
        }
      }
      
      // No timezone info available yet - format as UTC to be consistent
      // (This will be corrected once timezone is fetched)
      try {
        final utcDate = parsedDate.toUtc();
        final formatter = DateFormat(format ?? 'MMM d, y h:mm a');
        return formatter.format(utcDate);
      } catch (e) {
        final formatter = DateFormat(format ?? 'MMM d, y h:mm a');
        return formatter.format(parsedDate);
      }
    } catch (e) {
      return dateStr;
    }
  }
  
  /// Clear the timezone cache (useful when location changes)
  static void clearCache() {
    _cachedTimezone = null;
    _cacheTime = null;
  }
}

