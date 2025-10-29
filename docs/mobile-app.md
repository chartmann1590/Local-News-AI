# News AI Mobile App Documentation

## Overview

The News AI mobile app is a Flutter-based Android application that provides full-featured access to the News AI web backend. It offers a native mobile experience with offline caching, push notifications (optional), and optimized performance for mobile devices.

## Features

### Core Features

- **📰 News Feed**: Browse paginated news articles with images, previews, and full content
  - Auto-refresh every 30 seconds
  - Pull-to-refresh support
  - Pagination controls (10 articles per page)
  - Article detail view with full content
  - Source attribution and bylines

- **☀️ Weather Reports**: AI-generated weather reports with forecasts and radar
  - AI-generated weather summaries
  - 5-day forecast with weather icons
  - Interactive radar map (embedded WebView)
  - Auto-refresh every 30 seconds

- **🎤 Text-to-Speech**: Listen to articles and weather reports
  - Audio playback for articles
  - Audio playback for weather reports
  - Play/pause controls
  - Seek slider with time indicators
  - Custom voice selection
  - Speed adjustment (0.5x - 2.0x)

- **💬 AI Comments**: Interactive chat with AI about articles
  - Per-article chat context
  - Real-time messaging
  - Chat history management
  - Rate limiting awareness

- **🌓 Theme Support**: Full dark/light mode support
  - System theme detection
  - Manual theme selection
  - Persistent theme preferences
  - Material Design 3 components

- **⚙️ Server Configuration**: Flexible server connection management
  - First-time setup wizard
  - Server address and port configuration
  - Connection testing
  - Settings accessible from app

### Technical Features

- **Offline Logging**: Comprehensive logging system for debugging
- **Error Handling**: Graceful error handling with user-friendly messages
- **State Management**: Provider-based state management
- **Local Storage**: Persistent settings using SharedPreferences
- **Network Resiliency**: Connection timeout handling and retry logic

## Installation

### Prerequisites

- Android device or emulator (API level 21+)
- Flutter SDK 3.0.0 or later
- Android Studio or VS Code with Flutter extensions
- News AI backend server running and accessible

### Building from Source

1. **Clone the repository** (if not already cloned):
   ```bash
   git clone <repository-url>
   cd News-AI
   ```

2. **Navigate to Flutter app directory**:
   ```bash
   cd flutter_app
   ```

3. **Install dependencies**:
   ```bash
   flutter pub get
   ```

4. **Run the app** (development):
   ```bash
   flutter run
   ```

5. **Build release APK**:
   ```bash
   flutter build apk --release
   ```
   The APK will be located at: `build/app/outputs/flutter-apk/app-release.apk`

6. **Build app bundle** (for Play Store):
   ```bash
   flutter build appbundle --release
   ```
   The bundle will be located at: `build/app/outputs/bundle/release/app-release.aab`

### Installing Pre-built APK

1. Download `news-ai-app.apk` from the `app/static/` directory
2. Transfer to Android device
3. Enable "Install from Unknown Sources" in Android settings
4. Install the APK

**Note**: The APK is also available via the web interface at `http://your-server:port/static/news-ai-app.apk`

## Configuration

### Initial Setup

On first launch, the app will display a splash screen, then prompt you to configure the server connection:

1. **Server Configuration Screen**:
   - Enter your News AI server IP address (e.g., `192.168.1.100` or `localhost`)
   - Enter the server port (default: `8000`)
   - Click "Test Connection" to verify connectivity
   - Click "Save Configuration" to proceed

### Server Configuration Settings

You can change the server configuration at any time from the Settings screen:

1. Navigate to **Settings** tab
2. Under **Server Configuration** section
3. Click the edit icon to modify server address
4. Click the refresh icon to test connection

### Network Requirements

- **Same Network**: The app and server must be on the same network (for local IP addresses)
- **Firewall**: Ensure the server port is accessible from your device
- **HTTPS/HTTP**: The app supports both HTTP and HTTPS connections
- **Port**: Default port is 8000, but configurable

### Configuration Best Practices

- **Local Network**: Use your server's local IP (e.g., `192.168.1.100:8000`)
- **Remote Access**: Use domain or public IP if accessing remotely
- **Test Connection**: Always test connection after configuration changes
- **Port Format**: Include port number (e.g., `:8000` is required)

## Usage Guide

### News Screen

1. **Viewing Articles**:
   - Scroll through the article list
   - Tap any article to view full details
   - Use pagination controls at bottom to navigate pages

2. **Refreshing**:
   - Pull down to refresh manually
   - Tap refresh icon in app bar
   - Auto-refreshes every 30 seconds

3. **Article Details**:
   - Tap article card to open detail view
   - View full AI-rewritten content
   - Listen to audio (if TTS enabled)
   - Chat with AI about the article

### Weather Screen

1. **Viewing Weather**:
   - Scroll to see AI-generated report
   - View 5-day forecast (scrollable horizontal list)
   - Interactive radar map at bottom

2. **Refreshing**:
   - Pull down to refresh manually
   - Tap refresh icon in app bar
   - Auto-refreshes every 30 seconds

3. **Audio Playback**:
   - TTS audio player appears if TTS is enabled
   - Play/pause weather report audio
   - Adjust playback position with slider

### Settings Screen

#### Appearance

- **Theme Selection**:
  - System (follows device theme)
  - Light mode
  - Dark mode
  - Changes apply immediately

#### Location

- **Update Location**:
  - Enter city, state, or ZIP code
  - Click "Update Location" button
  - Location updates server-side configuration

#### Text-to-Speech

- **Enable TTS**: Toggle to enable/disable TTS features
- **TTS Base URL**: Server TTS endpoint (default: `http://tts:5500`)
- **Voice Selection**: Choose voice from available voices (optional)
- **Speed Control**: Adjust playback speed (0.5x to 2.0x)

#### Weather Units

- **Fahrenheit (°F)**: US temperature format
- **Celsius (°C)**: Metric temperature format

#### Logs

- **Email Logs**: Export app logs via email
  - Useful for debugging connection issues
  - Logs include API calls, errors, and screen navigation

### Server Configuration

- **Server Address**: View current server configuration
- **Test Connection**: Verify server connectivity
- **Edit Configuration**: Modify server IP and port

## Project Structure

```
flutter_app/
├── android/              # Android-specific files
│   ├── app/
│   │   ├── build.gradle # App build configuration
│   │   └── src/
│   └── build.gradle     # Project build configuration
├── lib/
│   ├── main.dart        # App entry point
│   ├── screens/         # Screen widgets
│   │   ├── splash_screen.dart
│   │   ├── server_config_screen.dart
│   │   ├── news_screen.dart
│   │   ├── article_detail_screen.dart
│   │   ├── weather_screen.dart
│   │   └── settings_screen.dart
│   ├── models/          # Data models
│   │   ├── article.dart
│   │   ├── weather.dart
│   │   ├── chat_message.dart
│   │   └── server_config.dart
│   ├── services/        # Business logic
│   │   ├── api_service.dart
│   │   ├── storage_service.dart
│   │   ├── theme_service.dart
│   │   └── logger_service.dart
│   ├── widgets/         # Reusable widgets
│   │   ├── audio_player_widget.dart
│   │   ├── article_card.dart
│   │   └── chat_widget.dart
│   └── utils/
│       └── constants.dart
├── pubspec.yaml         # Dependencies
└── README.md           # Flutter app README
```

## API Integration

The app communicates with the News AI backend using RESTful API endpoints:

### Health & Configuration

- `GET /health` - Health check endpoint
- `GET /api/config` - Server configuration

### Articles

- `GET /api/articles?page=1&limit=10` - Fetch articles with pagination
- `GET /api/articles/{id}/chat` - Get article chat history
- `POST /api/articles/{id}/chat` - Send chat message
- `DELETE /api/articles/{id}/chat` - Clear chat history

### Weather

- `GET /api/weather` - Get weather report and forecast

### Text-to-Speech

- `GET /api/tts/article/{id}?voice={voice}` - Get article TTS audio
- `GET /api/tts/weather?voice={voice}` - Get weather TTS audio
- `GET /api/tts/settings` - Get TTS settings
- `POST /api/tts/settings` - Update TTS settings

### Settings

- `GET /api/settings` - Get app settings
- `POST /api/settings` - Update app settings
- `POST /api/location` - Update location

### Error Handling

- **Connection Timeouts**: 10 seconds for regular requests, 3 minutes for TTS
- **Rate Limiting**: Shows user-friendly message when rate limited (429)
- **Network Errors**: Displays error message with retry option
- **Server Errors**: Shows HTTP status codes and error messages

## Dependencies

### Core Dependencies

- `flutter` - Flutter SDK
- `provider` (^6.1.1) - State management
- `http` (^1.1.0) - HTTP client
- `dio` (^5.4.0) - Advanced HTTP client
- `shared_preferences` (^2.2.2) - Local storage
- `audioplayers` (^5.2.1) - Audio playback
- `webview_flutter` (^4.4.2) - WebView for radar
- `url_launcher` (^6.2.2) - URL launching
- `intl` (^0.18.1) - Date formatting
- `flutter_html` (^3.0.0-beta.2) - HTML rendering
- `path_provider` (^2.1.1) - File system paths

### Development Dependencies

- `flutter_test` - Testing framework
- `flutter_lints` (^3.0.1) - Linting rules

## Logging

The app includes comprehensive logging for debugging:

- **Screen Navigation**: Logs all screen transitions
- **API Calls**: Logs all HTTP requests and responses
- **Errors**: Detailed error logging with stack traces
- **User Actions**: Logs user interactions (taps, settings changes)
- **Performance**: Logs timing information for API calls

### Accessing Logs

1. Navigate to **Settings** screen
2. Scroll to **Logs** section
3. Tap **Email Logs** button
4. Choose email app to send logs

Logs are stored locally and include timestamps, screen context, and detailed error information.

## Troubleshooting

### Connection Issues

**Problem**: Cannot connect to server

**Solutions**:
1. Verify server is running: `docker compose ps`
2. Check server IP address in Settings
3. Ensure device and server are on same network
4. Test connection using "Test Connection" button
5. Check firewall settings on server
6. Verify server port is correct (default: 8000)

### App Crashes

**Problem**: App crashes on launch

**Solutions**:
1. Check logs using "Email Logs" feature
2. Verify Flutter version: `flutter --version`
3. Clean build: `flutter clean && flutter pub get`
4. Rebuild app: `flutter build apk --release`

### TTS Not Working

**Problem**: Audio playback fails

**Solutions**:
1. Verify TTS is enabled in Settings
2. Check TTS Base URL is correct
3. Ensure server TTS service is running
4. Check network connectivity
5. Try different voice or default voice

### Articles Not Loading

**Problem**: News feed is empty

**Solutions**:
1. Check server connection
2. Verify backend has articles in database
3. Try pull-to-refresh
4. Check logs for API errors
5. Verify server API endpoints are accessible

### Weather Not Loading

**Problem**: Weather screen shows error

**Solutions**:
1. Verify location is set correctly
2. Check server weather service
3. Test connection to server
4. Check logs for specific error messages
5. Ensure backend has location configured

## Development

### Running in Development Mode

```bash
cd flutter_app
flutter run
```

### Debugging

- Use Flutter DevTools for performance profiling
- Check logs via "Email Logs" feature
- Enable verbose logging in code
- Use breakpoints in IDE

### Code Style

- Follow Flutter linting rules
- Use `flutter analyze` to check code
- Follow Material Design guidelines
- Maintain consistent naming conventions

## Building for Release

### APK Build

```bash
flutter build apk --release
```

Output: `build/app/outputs/flutter-apk/app-release.apk`

### App Bundle Build (Play Store)

```bash
flutter build appbundle --release
```

Output: `build/app/outputs/bundle/release/app-release.aab`

### Signing

For production releases, configure signing in `android/app/build.gradle`:

```gradle
signingConfigs {
    release {
        keyAlias keystoreProperties['keyAlias']
        keyPassword keystoreProperties['keyPassword']
        storeFile keystoreProperties['storeFile']
        storePassword keystoreProperties['storePassword']
    }
}
```

## Version Information

- **App Version**: 1.0.0+1
- **Minimum SDK**: 21 (Android 5.0)
- **Target SDK**: 34 (Android 14)
- **Flutter Version**: 3.0.0+

## Limitations

- **Android Only**: Currently only supports Android platform
- **Network Required**: Requires network connection to backend server
- **Server Dependency**: Cannot function without backend server
- **No Offline Mode**: Content is not cached offline (future feature)

## Future Enhancements

Potential features for future releases:

- iOS support
- Offline article caching
- Push notifications for new articles
- Widget support for home screen
- Better error recovery
- Article bookmarks/favorites
- Share functionality
- Search functionality

## Security Considerations

- **HTTP vs HTTPS**: Use HTTPS for production deployments
- **Server Authentication**: Currently no authentication (ensure server is on private network)
- **Data Storage**: Local storage contains only configuration (no sensitive data)
- **Network Security**: Ensure server is properly secured

## Support

For issues or questions:

1. Check this documentation
2. Review main project documentation
3. Check app logs via "Email Logs" feature
4. Review server logs
5. Check Flutter/Android compatibility

---

**Last Updated**: 2024
**Documentation Version**: 1.0

