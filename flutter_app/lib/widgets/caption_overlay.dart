import 'dart:async';
import 'package:flutter/material.dart';
import 'package:video_player/video_player.dart';
import '../utils/srt_parser.dart';
import '../services/api_service.dart';
import '../services/logger_service.dart';

class CaptionOverlay extends StatefulWidget {
  final VideoPlayerController videoController;
  final int broadcastId;
  final bool captionsEnabled;
  final VoidCallback onToggleCaptions;
  
  const CaptionOverlay({
    super.key,
    required this.videoController,
    required this.broadcastId,
    required this.captionsEnabled,
    required this.onToggleCaptions,
  });
  
  @override
  State<CaptionOverlay> createState() => _CaptionOverlayState();
}

class _CaptionOverlayState extends State<CaptionOverlay> {
  List<SrtEntry> _captions = [];
  SrtEntry? _currentCaption;
  bool _isLoading = true;
  String? _error;
  Timer? _positionTimer;
  
  @override
  void initState() {
    super.initState();
    _loadCaptions();
    _setupPositionListener();
  }
  
  @override
  void dispose() {
    _positionTimer?.cancel();
    super.dispose();
  }
  
  Future<void> _loadCaptions() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });
    
    try {
      LoggerService().logInfo('CaptionOverlay', 'Load Captions', details: 'Broadcast ID: ${widget.broadcastId}');
      final srtContent = await ApiService.getBroadcastSrt(widget.broadcastId, screenContext: 'CaptionOverlay');
      final captions = SrtParser.parseSrt(srtContent);
      
      if (mounted) {
        setState(() {
          _captions = captions;
          _isLoading = false;
        });
        LoggerService().logInfo('CaptionOverlay', 'Captions Loaded', details: 'Count: ${captions.length}');
      }
    } catch (e) {
      LoggerService().logError('CaptionOverlay', 'Load Captions', e);
      if (mounted) {
        setState(() {
          _error = e.toString();
          _isLoading = false;
        });
      }
    }
  }
  
  void _setupPositionListener() {
    _positionTimer = Timer.periodic(const Duration(milliseconds: 100), (timer) {
      if (!mounted || _captions.isEmpty || !widget.captionsEnabled) {
        if (mounted && _currentCaption != null) {
          setState(() {
            _currentCaption = null;
          });
        }
        return;
      }
      
      if (!widget.videoController.value.isInitialized) {
        return;
      }
      
      final position = widget.videoController.value.position;
      
      // Subtract a small preview offset (0.2 seconds) to show captions slightly early
      final previewOffset = const Duration(milliseconds: 200);
      final adjustedTime = position - previewOffset;
      final currentSeconds = adjustedTime.inMilliseconds / 1000.0;
      
      // Find the caption entry that should be displayed at this time
      SrtEntry? activeCaption;
      
      // First try exact match
      for (final caption in _captions) {
        if (currentSeconds >= caption.start && currentSeconds < caption.end) {
          activeCaption = caption;
          break;
        }
      }
      
      // If no exact match, check if we're close to a caption (for smoother transitions)
      if (activeCaption == null) {
        for (final caption in _captions) {
          final timeToStart = (currentSeconds - caption.start).abs();
          final timeToEnd = (currentSeconds - caption.end).abs();
          // Show caption if we're within 0.2s of start or end
          if (timeToStart < 0.2 || timeToEnd < 0.2) {
            activeCaption = caption;
            break;
          }
        }
      }
      
      if (mounted && _currentCaption != activeCaption) {
        setState(() {
          _currentCaption = activeCaption;
        });
      }
    });
  }
  
  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        // Caption display
        if (widget.captionsEnabled && !_isLoading && _error == null && _currentCaption != null)
          Positioned(
            bottom: 64,
            left: 0,
            right: 0,
            child: Center(
              child: Container(
                margin: const EdgeInsets.symmetric(horizontal: 16),
                padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
                decoration: BoxDecoration(
                  color: Colors.black.withOpacity(0.75),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  _currentCaption!.text,
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 18,
                    fontWeight: FontWeight.w500,
                    height: 1.4,
                  ),
                ),
              ),
            ),
          ),
        // Toggle button - ensure it's always clickable
        Positioned(
          top: 8,
          right: 8,
          child: GestureDetector(
            onTap: widget.onToggleCaptions,
            behavior: HitTestBehavior.opaque,
            child: Material(
              color: Colors.black.withOpacity(0.75),
              borderRadius: BorderRadius.circular(8),
              child: InkWell(
                onTap: widget.onToggleCaptions,
                borderRadius: BorderRadius.circular(8),
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Text(
                        'CC',
                        style: TextStyle(
                          color: Colors.white,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const SizedBox(width: 4),
                      Text(
                        widget.captionsEnabled ? 'ON' : 'OFF',
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 12,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
      ],
    );
  }
}

