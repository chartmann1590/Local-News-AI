import 'dart:async';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:audioplayers/audioplayers.dart';
import '../services/api_service.dart';
import '../services/logger_service.dart';

class AudioPlayerWidget extends StatefulWidget {
  final String fetchUrl;
  final String? voice;
  
  const AudioPlayerWidget({
    super.key,
    required this.fetchUrl,
    this.voice,
  });
  
  @override
  State<AudioPlayerWidget> createState() => _AudioPlayerWidgetState();
}

class _AudioPlayerWidgetState extends State<AudioPlayerWidget> {
  final AudioPlayer _audioPlayer = AudioPlayer();
  bool _isPlaying = false;
  bool _isLoading = false;
  bool _hasError = false;
  Duration _duration = Duration.zero;
  Duration _position = Duration.zero;
  String? _localFilePath;
  
  @override
  void initState() {
    super.initState();
    LoggerService().logInfo('AudioPlayerWidget', 'Widget Initialized', details: 'URL: ${widget.fetchUrl}');
    _audioPlayer.onPlayerStateChanged.listen((state) {
      if (mounted) {
        setState(() {
          _isPlaying = state == PlayerState.playing;
        });
      }
    });
    
    _audioPlayer.onDurationChanged.listen((duration) {
      if (mounted) {
        setState(() {
          _duration = duration;
        });
      }
    });
    
    _audioPlayer.onPositionChanged.listen((position) {
      if (mounted) {
        setState(() {
          _position = position;
        });
      }
    });
    
    _audioPlayer.onPlayerComplete.listen((_) {
      if (mounted) {
        setState(() {
          _isPlaying = false;
          _position = Duration.zero;
        });
      }
    });
  }
  
  Future<void> _loadAndPlay() async {
    LoggerService().logInfo('AudioPlayerWidget', 'Load Audio', details: 'URL: ${widget.fetchUrl}');
    setState(() {
      _isLoading = true;
      _hasError = false;
    });
    
    try {
      List<int> audioBytes;
      
      if (widget.fetchUrl.contains('tts/article/')) {
        final parts = widget.fetchUrl.split('/');
        final articleIdStr = parts.last.split('?').first;
        final articleId = int.parse(articleIdStr);
        LoggerService().logInfo('AudioPlayerWidget', 'Fetching Article TTS', details: 'Article ID: $articleId');
        audioBytes = await ApiService.getTtsArticle(articleId, voice: widget.voice);
      } else if (widget.fetchUrl.contains('tts/weather')) {
        LoggerService().logInfo('AudioPlayerWidget', 'Fetching Weather TTS');
        audioBytes = await ApiService.getTtsWeather(voice: widget.voice);
      } else {
        final error = Exception('Unknown audio URL: ${widget.fetchUrl}');
        LoggerService().logError('AudioPlayerWidget', 'Load Audio', error);
        throw error;
      }
      
      LoggerService().logInfo('AudioPlayerWidget', 'Audio Loaded', details: 'Size: ${audioBytes.length} bytes');
      
      // Save to temporary file
      final tempDir = Directory.systemTemp;
      final file = File('${tempDir.path}/audio_${DateTime.now().millisecondsSinceEpoch}.wav');
      await file.writeAsBytes(audioBytes);
      
      LoggerService().logInfo('AudioPlayerWidget', 'Audio File Saved', details: 'Path: ${file.path}');
      
      setState(() {
        _localFilePath = file.path;
        _isLoading = false;
      });
      
      await _audioPlayer.play(DeviceFileSource(_localFilePath!));
      LoggerService().logInfo('AudioPlayerWidget', 'Audio Playing');
    } catch (e) {
      LoggerService().logError('AudioPlayerWidget', 'Load Audio', e);
      setState(() {
        _isLoading = false;
        _hasError = true;
      });
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to load audio: ${e.toString()}'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }
  
  Future<void> _togglePlay() async {
    if (_isLoading) {
      LoggerService().logWarning('AudioPlayerWidget', 'Toggle Play', details: 'Still loading');
      return;
    }
    
    LoggerService().logInfo('AudioPlayerWidget', 'Toggle Play', details: 'Is Playing: $_isPlaying, Has File: ${_localFilePath != null}');
    
    if (_localFilePath == null) {
      await _loadAndPlay();
      return;
    }
    
    if (_isPlaying) {
      LoggerService().logInfo('AudioPlayerWidget', 'Pause Audio');
      await _audioPlayer.pause();
    } else {
      LoggerService().logInfo('AudioPlayerWidget', 'Resume Audio');
      await _audioPlayer.resume();
    }
  }
  
  Future<void> _seek(Duration position) async {
    await _audioPlayer.seek(position);
  }
  
  String _formatDuration(Duration duration) {
    String twoDigits(int n) => n.toString().padLeft(2, '0');
    final minutes = twoDigits(duration.inMinutes.remainder(60));
    final seconds = twoDigits(duration.inSeconds.remainder(60));
    return '$minutes:$seconds';
  }
  
  @override
  void dispose() {
    _audioPlayer.dispose();
    super.dispose();
  }
  
  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Theme.of(context).cardColor,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: Theme.of(context).dividerColor,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              IconButton(
                icon: Icon(_isPlaying ? Icons.pause : Icons.play_arrow),
                onPressed: _togglePlay,
                disabledColor: Colors.grey,
              ),
              Expanded(
                child: Slider(
                  value: _duration.inMilliseconds > 0
                      ? _position.inMilliseconds.toDouble()
                      : 0.0,
                  max: _duration.inMilliseconds > 0
                      ? _duration.inMilliseconds.toDouble()
                      : 1.0,
                  onChanged: (value) {
                    _seek(Duration(milliseconds: value.toInt()));
                  },
                ),
              ),
              Text(
                '${_formatDuration(_position)} / ${_formatDuration(_duration)}',
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ],
          ),
          if (_isLoading)
            const LinearProgressIndicator(),
          if (_hasError)
            Text(
              'Error loading audio',
              style: TextStyle(
                color: Colors.red,
                fontSize: 12,
              ),
            ),
        ],
      ),
    );
  }
}

