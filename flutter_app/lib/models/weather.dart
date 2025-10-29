class Weather {
  final String? location;
  final String? timezone;
  final double? latitude;
  final double? longitude;
  final String? report;
  final Map<String, dynamic>? forecast;
  final String? updatedAt;
  final String? reportNote;
  
  Weather({
    this.location,
    this.timezone,
    this.latitude,
    this.longitude,
    this.report,
    this.forecast,
    this.updatedAt,
    this.reportNote,
  });
  
  factory Weather.fromJson(Map<String, dynamic> json) {
    return Weather(
      location: json['location'] as String?,
      timezone: json['timezone'] as String?,
      latitude: json['latitude'] as double?,
      longitude: json['longitude'] as double?,
      report: json['report'] as String?,
      forecast: json['forecast'] as Map<String, dynamic>?,
      updatedAt: json['updated_at'] as String?,
      reportNote: json['report_note'] as String?,
    );
  }
  
  List<DailyForecast> get dailyForecast {
    if (forecast == null || forecast!['daily'] == null) return [];
    
    final daily = forecast!['daily'] as Map<String, dynamic>;
    final times = daily['time'] as List<dynamic>? ?? [];
    final maxTemps = daily['temperature_2m_max'] as List<dynamic>? ?? [];
    final minTemps = daily['temperature_2m_min'] as List<dynamic>? ?? [];
    final codes = daily['weathercode'] as List<dynamic>? ?? [];
    
    final List<DailyForecast> forecasts = [];
    for (int i = 0; i < times.length && i < 5; i++) {
      forecasts.add(DailyForecast(
        date: times[i] as String,
        maxTemp: maxTemps[i]?.toString() ?? '',
        minTemp: minTemps[i]?.toString() ?? '',
        weatherCode: codes[i]?.toString() ?? '0',
      ));
    }
    
    return forecasts;
  }
}

class DailyForecast {
  final String date;
  final String maxTemp;
  final String minTemp;
  final String weatherCode;
  
  DailyForecast({
    required this.date,
    required this.maxTemp,
    required this.minTemp,
    required this.weatherCode,
  });
  
  String getWeatherIcon() {
    final code = int.tryParse(weatherCode) ?? 0;
    if ([0].contains(code)) return '☀️';
    if ([1, 2].contains(code)) return '🌤️';
    if ([3].contains(code)) return '☁️';
    if ([45, 48].contains(code)) return '🌫️';
    if ([51, 53, 55, 56, 57].contains(code)) return '🌦️';
    if ([61, 63, 65, 66, 67].contains(code)) return '🌧️';
    if ([71, 73, 75, 77, 85, 86].contains(code)) return '❄️';
    if ([80, 81, 82].contains(code)) return '🌧️';
    if ([95, 96, 99].contains(code)) return '⛈️';
    return '🌡️';
  }
}

