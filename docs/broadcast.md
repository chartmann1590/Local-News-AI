# Broadcast Feature

## Overview

The broadcast feature generates professional news videos with AI-narrated articles, weather reports, and synchronized captions. The system uses a **segment-by-segment approach** to ensure perfect synchronization between audio, video, and captions.

## Key Features

### Segment-by-Segment Generation (NEW)

Each broadcast segment is created individually to guarantee perfect alignment:

1. **Generate TTS Audio** → Get actual duration
2. **Create Video Slide** → Use exact duration from audio
3. **Generate Word-Level Captions** → Align to actual audio timing
4. **Validate Segment** → Confirm complete before moving to next
5. **Compile All Segments** → Concatenate into final broadcast

### Benefits

- ✅ **Perfect Audio/Video Sync**: Video duration exactly matches actual audio
- ✅ **Word-Level Caption Timing**: Captions show 4 words at a time, precisely synced
- ✅ **No Estimated Durations**: All timing based on actual TTS output
- ✅ **Validated Segments**: Each segment confirmed before compilation
- ✅ **Graceful Failure Handling**: Failed segments skipped (no silent gaps)

## How It Works

### Broadcast Structure

Each broadcast contains the following segments:

1. **Intro**: Welcome message with location
2. **Articles**: 1-10 news stories with AI summaries
3. **Weather**: Local forecast and conditions
4. **Ending**: Thank you message

### Generation Process

```
Step 1-4: Preparation
├─ Gather recent articles (10 max, 48 hours)
├─ Get latest weather report
├─ Download article images
└─ Create intro/ending slides

Step 5: Create Intro Segment
├─ Generate TTS audio (e.g., 5.2 seconds)
├─ Create video slide (exactly 5.2 seconds)
├─ Generate captions (5.2s word-level timing)
└─ ✓ Validated and saved

Step 6: Create Article Segments
├─ For each article:
│  ├─ Generate TTS audio (e.g., 15.7 seconds)
│  ├─ Create video slide (exactly 15.7 seconds)
│  ├─ Generate captions (15.7s word-level timing)
│  └─ ✓ Validated and saved
└─ Repeat for all articles

Step 7: Create Weather Segment
├─ Generate TTS audio (e.g., 22.1 seconds)
├─ Create video slide (exactly 22.1 seconds)
├─ Generate captions (22.1s word-level timing)
└─ ✓ Validated and saved

Step 8: Create Ending Segment
├─ Generate TTS audio (e.g., 4.8 seconds)
├─ Create video slide (exactly 4.8 seconds)
├─ Generate captions (4.8s word-level timing)
└─ ✓ Validated and saved

Step 9: Compile All Segments
├─ Concatenate all segment videos
├─ Adjust caption timings for final positions
├─ Generate final SRT file
└─ ✓ Broadcast complete!
```

## Configuration

### Visual Effects

- **Transition Duration**: `BROADCAST_TRANSITION_DURATION` (seconds, default `0.5`)
  - Smooth crossfades between slides
- **Ken Burns Effect**: `BROADCAST_KEN_BURNS` (`1`/`true` to enable, default enabled)
  - Subtle slow zoom on article images
- **Ken Burns Zoom**: `BROADCAST_KEN_BURNS_ZOOM` (fractional, default `0.03` = 3% zoom)

### Audio Configuration

- **Background Music Path**: `BROADCAST_BGM_PATH` (file path)
  - Default locations: `/data/broadcasts/bgm.mp3` or `app/broadcasts/bgm.mp3`
- **Background Music Volume**: `BROADCAST_BGM_VOLUME` (0.0–1.0, default `0.12`)
- **Audio Fade**: `BROADCAST_AUDIO_FADE` (seconds, default `0.5`)

### TTS Settings

Configure via Settings → Text-to-Speech in the web UI:

- **Base URL**: Default `http://tts:5500` (OpenTTS service)
- **Voice**: Select from available voices
- **Speed**: 0.5 - 2.0 (default 1.0)

## Usage

### Web Interface

1. Navigate to the **Broadcast** tab
2. Click **"Generate New Broadcast"**
3. Monitor progress through the steps
4. Play the generated video with captions

### API

```bash
# Generate a new broadcast
POST /api/broadcasts/generate

# List all broadcasts
GET /api/broadcasts

# Get broadcast video
GET /api/broadcasts/{id}/video

# Get broadcast captions (SRT)
GET /api/broadcasts/{id}/srt

# Get broadcast transcript
GET /api/broadcasts/{id}
```

## Output Files

Broadcasts are stored in `data/broadcasts/`:

```
data/broadcasts/
├── broadcast_1234567890.mp4  # Final video with embedded audio
├── broadcast_1234567890.srt  # Caption file with word-level timing
├── intro_slide.png           # Reusable intro slide
├── ending_slide.png          # Reusable ending slide
└── temp_1234567890/          # Temporary segment files (cleaned up)
    ├── intro_intro_video.mp4
    ├── article_94_video.mp4
    ├── article_95_video.mp4
    ├── weather_weather_video.mp4
    └── ending_ending_video.mp4
```

## Technical Details

### Segment Video Files

Each segment is a complete video file with:
- Image slide (article image, weather slide, or intro/ending graphic)
- Embedded audio (TTS narration)
- Exact duration matching audio length
- Title overlays for articles

### Caption Format

SRT captions with:
- Word-level timing precision
- 4 words per caption entry
- Properly adjusted offsets in final file
- Compatible with all video players

### Image Handling

- Automatic format conversion (PNG/JPEG/RGBA/Palette)
- Resizing to 1280x720 (16:9 aspect ratio)
- White background for transparent images
- Fallback placeholders if download fails

## Troubleshooting

### Broadcast Generation Fails

1. **Check TTS Service**: `docker compose ps` - ensure `tts` service is running
2. **Verify TTS Settings**: Enable TTS in Settings → Text-to-Speech
3. **Check Disk Space**: Ensure sufficient space in `data/broadcasts/`
4. **Review Logs**: `docker compose logs app` for detailed errors

### Audio/Video/Captions Not Aligned

The new segment-by-segment approach ensures perfect alignment. If you experience issues:

1. **Regenerate Broadcast**: Old broadcasts may use previous approach
2. **Check Segment Logs**: Look for "CRITICAL: Failed to generate TTS" errors
3. **Verify TTS Connection**: Test TTS service connectivity

### No Audio in Broadcast

1. **Enable TTS**: Settings → Text-to-Speech → Enable
2. **Check TTS Service**: `docker compose logs tts`
3. **Test TTS**: Use "Preview" button in TTS settings
4. **Review Segment Errors**: Check logs for failed audio generation

## Background Music (Optional)

To add background music to broadcasts:

1. **Add Music File**:
   ```bash
   # Place royalty-free music in data directory
   cp your-music.mp3 data/broadcasts/bgm.mp3
   ```

2. **Configure Volume** (optional):
   ```bash
   # In docker-compose.yml or .env
   BROADCAST_BGM_VOLUME=0.12  # 12% volume (0.0-1.0)
   ```

3. **Regenerate Broadcast**: Music will be mixed under narration

**Note**: Ensure you have rights to use any background music.

## Performance

- **Generation Time**: ~2-5 minutes for 10 articles (depends on TTS speed)
- **Video Size**: ~5-15 MB per minute of broadcast
- **Disk Usage**: Temp files cleaned up after successful compilation
- **Concurrent Generations**: Only one broadcast can be generated at a time

## Future Enhancements

Potential improvements being considered:

- Multiple voice selection for different segments
- Customizable video templates and themes
- Live broadcast streaming
- Multi-language support
- Advanced caption styling options
