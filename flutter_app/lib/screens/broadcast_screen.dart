import 'dart:async';
import 'package:flutter/material.dart';
import 'package:video_player/video_player.dart';
import 'package:intl/intl.dart';
import '../models/broadcast.dart';
import '../services/api_service.dart';
import '../services/logger_service.dart';
import '../widgets/caption_overlay.dart';

class BroadcastScreen extends StatefulWidget {
  const BroadcastScreen({super.key});
  
  @override
  State<BroadcastScreen> createState() => _BroadcastScreenState();
}

class _BroadcastScreenState extends State<BroadcastScreen> {
  Broadcast? _broadcast;
  bool _isLoading = true;
  bool _isRefreshing = false;
  String? _error;
  VideoPlayerController? _videoController;
  bool _captionsEnabled = true;
  Timer? _refreshTimer;
  
  @override
  void initState() {
    super.initState();
    LoggerService().logInfo('BroadcastScreen', 'Screen Initialized');
    _loadBroadcast();
    _startAutoRefresh();
  }
  
  void _startAutoRefresh() {
    LoggerService().logInfo('BroadcastScreen', 'Start Auto Refresh');
    _refreshTimer = Timer.periodic(
      const Duration(seconds: 30),
      (_) {
        LoggerService().logInfo('BroadcastScreen', 'Auto Refresh Triggered');
        _loadBroadcast(isBackground: true);
      },
    );
  }
  
  @override
  void dispose() {
    LoggerService().logInfo('BroadcastScreen', 'Screen Disposed');
    _refreshTimer?.cancel();
    _videoController?.dispose();
    super.dispose();
  }
  
  Future<void> _loadBroadcast({bool isBackground = false}) async {
    LoggerService().logInfo('BroadcastScreen', 'Load Broadcast', details: 'Background: $isBackground');
    
    if (!isBackground && mounted) {
      setState(() {
        _isLoading = true;
        _error = null;
      });
    }
    
    try {
      final broadcast = await ApiService.getBroadcastLatest(screenContext: 'BroadcastScreen');
      
      if (broadcast == null) {
        LoggerService().logInfo('BroadcastScreen', 'No Broadcast Found');
        if (mounted) {
          setState(() {
            _broadcast = null;
            _isLoading = false;
            _isRefreshing = false;
            _error = 'No broadcast available yet. The broadcast will be generated automatically at scheduled intervals.';
          });
        }
        _disposeVideoController();
        return;
      }
      
      LoggerService().logInfo('BroadcastScreen', 'Broadcast Loaded', details: 'ID: ${broadcast.id}, Duration: ${broadcast.durationSeconds}s');
      
      if (mounted) {
        setState(() {
          _broadcast = broadcast;
          _isLoading = false;
          _isRefreshing = false;
          _error = null;
        });
        
        // Initialize video player if we have a broadcast
        await _initializeVideoPlayer(broadcast.id);
      }
    } catch (e) {
      LoggerService().logError('BroadcastScreen', 'Load Broadcast', e);
      if (mounted) {
        setState(() {
          _isLoading = false;
          _isRefreshing = false;
          _error = 'Failed to load broadcast: ${e.toString()}';
        });
      }
      _disposeVideoController();
    }
  }
  
  Future<void> _initializeVideoPlayer(int broadcastId) async {
    _disposeVideoController();
    
    try {
      final videoUrl = await ApiService.getBroadcastVideoUrl(broadcastId);
      LoggerService().logInfo('BroadcastScreen', 'Initialize Video Player', details: 'URL: $videoUrl');
      
      _videoController = VideoPlayerController.networkUrl(Uri.parse(videoUrl));
      await _videoController!.initialize();
      
      if (mounted) {
        setState(() {});
        LoggerService().logInfo('BroadcastScreen', 'Video Player Initialized');
      }
    } catch (e) {
      LoggerService().logError('BroadcastScreen', 'Initialize Video Player', e);
      if (mounted) {
        setState(() {
          _error = 'Failed to load video: ${e.toString()}';
        });
      }
    }
  }
  
  void _disposeVideoController() {
    _videoController?.dispose();
    _videoController = null;
  }
  
  Future<void> _refresh() async {
    LoggerService().logInfo('BroadcastScreen', 'Refresh Broadcast');
    setState(() {
      _isRefreshing = true;
    });
    await _loadBroadcast();
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
  
  String _formatDuration(double? seconds) {
    if (seconds == null) return 'N/A';
    final mins = (seconds / 60).floor();
    final secs = (seconds % 60).floor();
    return '${mins}:${secs.toString().padLeft(2, '0')}';
  }
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Broadcast'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _refresh,
            tooltip: 'Refresh',
          ),
        ],
      ),
      body: _isLoading && _broadcast == null
          ? const Center(child: CircularProgressIndicator())
          : _error != null && _broadcast == null
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
                      Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 32),
                        child: Text(
                          _error!,
                          textAlign: TextAlign.center,
                          style: TextStyle(color: Colors.red[700]),
                        ),
                      ),
                      const SizedBox(height: 16),
                      ElevatedButton(
                        onPressed: _loadBroadcast,
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
                          // Broadcast metadata
                          if (_broadcast != null) ...[
                            Row(
                              children: [
                                const Icon(Icons.videocam, size: 32),
                                const SizedBox(width: 8),
                                Expanded(
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Text(
                                        'News Broadcast',
                                        style: Theme.of(context).textTheme.titleLarge?.copyWith(
                                          fontWeight: FontWeight.bold,
                                        ),
                                      ),
                                      if (_broadcast!.createdAt != null)
                                        Text(
                                          'Created: ${_formatDate(_broadcast!.createdAt)}',
                                          style: Theme.of(context).textTheme.bodySmall?.copyWith(
                                            color: Colors.grey[600],
                                          ),
                                        ),
                                      Text(
                                        'Duration: ${_formatDuration(_broadcast!.durationSeconds)} • ${_broadcast!.articleCount ?? 0} articles${_broadcast!.includesWeather == true ? ' • Weather included' : ''}',
                                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                                          color: Colors.grey[600],
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: 16),
                          ],
                          
                          // Video player
                          if (_videoController != null && _videoController!.value.isInitialized) ...[
                            Card(
                              clipBehavior: Clip.antiAlias,
                              child: AspectRatio(
                                aspectRatio: _videoController!.value.aspectRatio,
                                child: Stack(
                                  alignment: Alignment.center,
                                  children: [
                                    // Video player - no blocking overlay, allows interaction
                                    VideoPlayer(_videoController!),
                                    if (_broadcast != null && _broadcast!.srtPath != null)
                                      CaptionOverlay(
                                        videoController: _videoController!,
                                        broadcastId: _broadcast!.id,
                                        captionsEnabled: _captionsEnabled,
                                        onToggleCaptions: () {
                                          setState(() {
                                            _captionsEnabled = !_captionsEnabled;
                                          });
                                        },
                                      ),
                                  ],
                                ),
                              ),
                            ),
                            const SizedBox(height: 16),
                            
                            // Video controls
                            Row(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                IconButton(
                                  icon: Icon(
                                    _videoController!.value.isPlaying
                                        ? Icons.pause
                                        : Icons.play_arrow,
                                  ),
                                  onPressed: () {
                                    setState(() {
                                      if (_videoController!.value.isPlaying) {
                                        _videoController!.pause();
                                      } else {
                                        _videoController!.play();
                                      }
                                    });
                                  },
                                ),
                                Expanded(
                                  child: VideoProgressIndicator(
                                    _videoController!,
                                    allowScrubbing: true,
                                    colors: VideoProgressColors(
                                      playedColor: Theme.of(context).colorScheme.primary,
                                      bufferedColor: Colors.grey[300]!,
                                      backgroundColor: Colors.grey[600]!,
                                    ),
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: 24),
                          ] else if (_broadcast != null && _videoController == null) ...[
                            Card(
                              child: Padding(
                                padding: const EdgeInsets.all(16),
                                child: Column(
                                  children: [
                                    const CircularProgressIndicator(),
                                    const SizedBox(height: 16),
                                    Text(
                                      'Loading video...',
                                      style: Theme.of(context).textTheme.bodyMedium,
                                    ),
                                  ],
                                ),
                              ),
                            ),
                            const SizedBox(height: 24),
                          ],
                          
                          // Transcript
                          if (_broadcast?.transcript != null && _broadcast!.transcript!.isNotEmpty) ...[
                            Text(
                              'Transcript',
                              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                            const SizedBox(height: 12),
                            Card(
                              child: Padding(
                                padding: const EdgeInsets.all(16),
                                child: Container(
                                  constraints: const BoxConstraints(maxHeight: 400),
                                  child: SingleChildScrollView(
                                    child: Text(
                                      _broadcast!.transcript!,
                                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                                        height: 1.6,
                                      ),
                                    ),
                                  ),
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

