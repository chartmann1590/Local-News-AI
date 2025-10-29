import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_html/flutter_html.dart';
import 'package:webview_flutter/webview_flutter.dart';
import '../models/weather.dart';
import '../services/api_service.dart';
import '../services/logger_service.dart';
import '../widgets/audio_player_widget.dart';
import 'package:intl/intl.dart';

class WeatherScreen extends StatefulWidget {
  const WeatherScreen({super.key});
  
  @override
  State<WeatherScreen> createState() => _WeatherScreenState();
}

class _WeatherScreenState extends State<WeatherScreen> {
  Weather? _weather;
  bool _isLoading = true;
  bool _isRefreshing = false;
  String? _error;
  bool _ttsEnabled = false;
  
  Timer? _refreshTimer;
  
  @override
  void initState() {
    super.initState();
    LoggerService().logInfo('WeatherScreen', 'Screen Initialized');
    _loadWeather();
    _checkTtsEnabled();
    _startAutoRefresh();
  }
  
  void _startAutoRefresh() {
    LoggerService().logInfo('WeatherScreen', 'Start Auto Refresh');
    _refreshTimer = Timer.periodic(
      const Duration(seconds: 30),
      (_) {
        LoggerService().logInfo('WeatherScreen', 'Auto Refresh Triggered');
        _loadWeather(isBackground: true);
      },
    );
  }
  
  @override
  void dispose() {
    LoggerService().logInfo('WeatherScreen', 'Screen Disposed');
    _refreshTimer?.cancel();
    super.dispose();
  }
  
  Future<void> _checkTtsEnabled() async {
    try {
      LoggerService().logInfo('WeatherScreen', 'Check TTS Enabled');
      final ttsSettings = await ApiService.getTtsSettings(screenContext: 'WeatherScreen');
      if (mounted) {
        setState(() {
          _ttsEnabled = ttsSettings['enabled'] == true;
        });
        LoggerService().logInfo('WeatherScreen', 'TTS Status', details: 'TTS Enabled: $_ttsEnabled');
      }
    } catch (e) {
      LoggerService().logError('WeatherScreen', 'Check TTS Enabled', e);
    }
  }
  
  Future<void> _loadWeather({bool isBackground = false}) async {
    LoggerService().logInfo('WeatherScreen', 'Load Weather', details: 'Background: $isBackground');
    
    if (!isBackground && mounted) {
      setState(() {
        _isLoading = true;
        _error = null;
      });
    }
    
    try {
      final weather = await ApiService.getWeather(screenContext: 'WeatherScreen');
      
      LoggerService().logInfo('WeatherScreen', 'Weather Loaded', details: 'Location: ${weather.location}, Has Report: ${weather.report != null}');
      
      if (mounted) {
        setState(() {
          _weather = weather;
          _isLoading = false;
          _isRefreshing = false;
          _error = null;
        });
      }
    } catch (e) {
      LoggerService().logError('WeatherScreen', 'Load Weather', e);
      if (mounted) {
        setState(() {
          _isLoading = false;
          _isRefreshing = false;
          _error = 'Failed to load weather: ${e.toString()}';
        });
      }
    }
  }
  
  Future<void> _refresh() async {
    LoggerService().logInfo('WeatherScreen', 'Refresh Weather');
    setState(() {
      _isRefreshing = true;
    });
    await _loadWeather();
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
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Weather'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _refresh,
            tooltip: 'Refresh',
          ),
        ],
      ),
      body: _isLoading && _weather == null
          ? const Center(child: CircularProgressIndicator())
          : _error != null && _weather == null
              ? Center(
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
                        onPressed: _loadWeather,
                        child: const Text('Retry'),
                      ),
                    ],
                  ),
                )
              : RefreshIndicator(
                  onRefresh: _refresh,
                  child: SingleChildScrollView(
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          if (_weather?.updatedAt != null) ...[
                            Text(
                              'Updated: ${_formatDate(_weather!.updatedAt)}',
                              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                                color: Colors.grey[600],
                              ),
                            ),
                            const SizedBox(height: 8),
                          ],
                          if (_weather?.reportNote != null) ...[
                            Container(
                              padding: const EdgeInsets.all(12),
                              decoration: BoxDecoration(
                                color: Colors.amber.shade50,
                                borderRadius: BorderRadius.circular(8),
                                border: Border.all(color: Colors.amber.shade300),
                              ),
                              child: Row(
                                children: [
                                  Icon(Icons.info_outline, color: Colors.amber.shade700),
                                  const SizedBox(width: 8),
                                  Expanded(
                                    child: Text(
                                      _weather!.reportNote!,
                                      style: TextStyle(color: Colors.amber.shade900),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                            const SizedBox(height: 16),
                          ],
                          if (_weather?.report != null) ...[
                            Card(
                              child: Padding(
                                padding: const EdgeInsets.all(16),
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Row(
                                      children: [
                                        const Icon(Icons.wb_sunny, size: 32),
                                        const SizedBox(width: 8),
                                        Text(
                                          'Weather Report',
                                          style: Theme.of(context).textTheme.titleLarge?.copyWith(
                                            fontWeight: FontWeight.bold,
                                          ),
                                        ),
                                      ],
                                    ),
                                    const SizedBox(height: 16),
                                    Html(
                                      data: _weather!.report!.replaceAll('\n', '<br/>'),
                                      style: {
                                        'body': Style(
                                          fontSize: FontSize(16),
                                          lineHeight: const LineHeight(1.6),
                                        ),
                                      },
                                    ),
                                  ],
                                ),
                              ),
                            ),
                            if (_ttsEnabled) ...[
                              const SizedBox(height: 16),
                              AudioPlayerWidget(
                                fetchUrl: 'api/tts/weather',
                              ),
                            ],
                            const SizedBox(height: 24),
                          ],
                          if (_weather?.dailyForecast.isNotEmpty ?? false) ...[
                            Text(
                              '5‑Day Forecast',
                              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                            const SizedBox(height: 12),
                            SizedBox(
                              height: 120,
                              child: ListView.builder(
                                scrollDirection: Axis.horizontal,
                                itemCount: _weather!.dailyForecast.length,
                                itemBuilder: (context, index) {
                                  final forecast = _weather!.dailyForecast[index];
                                  return Container(
                                    width: 140,
                                    margin: const EdgeInsets.only(right: 12),
                                    child: Card(
                                      child: Padding(
                                        padding: const EdgeInsets.all(12),
                                        child: Column(
                                          crossAxisAlignment: CrossAxisAlignment.start,
                                          children: [
                                            Text(
                                              forecast.date,
                                              style: const TextStyle(
                                                fontWeight: FontWeight.bold,
                                              ),
                                            ),
                                            const SizedBox(height: 8),
                                            Row(
                                              children: [
                                                Text(
                                                  forecast.getWeatherIcon(),
                                                  style: const TextStyle(fontSize: 24),
                                                ),
                                                const SizedBox(width: 8),
                                                Expanded(
                                                  child: Column(
                                                    crossAxisAlignment: CrossAxisAlignment.start,
                                                    children: [
                                                      Text('High: ${forecast.maxTemp}°'),
                                                      Text('Low: ${forecast.minTemp}°'),
                                                    ],
                                                  ),
                                                ),
                                              ],
                                            ),
                                          ],
                                        ),
                                      ),
                                    ),
                                  );
                                },
                              ),
                            ),
                            const SizedBox(height: 24),
                          ],
                          if (_weather?.latitude != null && _weather?.longitude != null) ...[
                            Text(
                              'Radar',
                              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                            const SizedBox(height: 12),
                            Card(
                              clipBehavior: Clip.antiAlias,
                              child: SizedBox(
                                height: 320,
                            child: Builder(
                              builder: (context) {
                                final controller = WebViewController()
                                  ..setJavaScriptMode(JavaScriptMode.unrestricted)
                                  ..loadRequest(Uri.parse('https://embed.windy.com/embed2.html?lat=${_weather!.latitude}&lon=${_weather!.longitude}&zoom=7&level=surface&overlay=radar&product=radar&menu=&message=&calendar=now&pressure=&type=map&location=coordinates&detail=&detailLat=${_weather!.latitude}&detailLon=${_weather!.longitude}&metricWind=default&metricTemp=default'));
                                return WebViewWidget(controller: controller);
                              },
                            ),
                              ),
                            ),
                          ],
                        ],
                      ),
                    ),
                  ),
                ),
    );
  }
}

