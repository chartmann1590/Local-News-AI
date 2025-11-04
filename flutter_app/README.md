# News AI Flutter Android App

A fully-featured Flutter Android application that integrates with the News AI web backend, providing access to local news articles, weather reports, TTS audio playback, and interactive comments.

## Features

- 📰 **News Screen**: Browse paginated news articles with images, previews, and full content
- ☀️ **Weather Screen**: AI-generated weather reports, 5-day forecasts, and interactive radar maps
- 🎤 **Text-to-Speech**: Listen to articles and weather reports with audio playback
- 💬 **Comments**: Interactive chat with AI about articles
- 🌓 **Dark/Light Mode**: Full theme support matching the web app
- ⚙️ **Server Configuration**: Configure and test server connection from the app
- 🎨 **Material Design 3**: Modern, responsive UI with smooth animations

## Setup

### Prerequisites

- Flutter SDK (3.0.0 or later)
- Android Studio or VS Code with Flutter extensions
- Android SDK (API level 21+)

### Installation

1. Navigate to the Flutter app directory:
   ```bash
   cd flutter_app
   ```

2. Install dependencies:
   ```bash
   flutter pub get
   ```

3. Run the app:
   ```bash
   flutter run
   ```

### Building for Release

```bash
flutter build apk --release
```

For app bundle:
```bash
flutter build appbundle --release
```

## Configuration

On first launch, the app will prompt you to configure the server connection:

1. Enter your News AI server IP address (e.g., `192.168.1.100` or `localhost`)
2. Enter the server port (default: `8000`)
3. Click "Test Connection" to verify connectivity
4. Click "Save Configuration" to proceed

You can change the server configuration later from the Settings screen.

## Project Structure

```
lib/
├── main.dart                 # App entry point
├── screens/                  # Screen widgets
│   ├── splash_screen.dart
│   ├── server_config_screen.dart
│   ├── news_screen.dart
│   ├── article_detail_screen.dart
│   ├── weather_screen.dart
│   └── settings_screen.dart
├── models/                   # Data models
│   ├── article.dart
│   ├── weather.dart
│   ├── chat_message.dart
│   └── server_config.dart
├── services/                 # Business logic
│   ├── api_service.dart
│   ├── storage_service.dart
│   └── theme_service.dart
├── widgets/                  # Reusable widgets
│   ├── audio_player_widget.dart
│   ├── article_card.dart
│   └── chat_widget.dart
└── utils/
    └── constants.dart
```

## API Integration

The app communicates with the News AI backend using the following endpoints:

- `GET /health` or `GET /api/config` - Health check
- `GET /api/articles` - Fetch articles with pagination
- `GET /api/weather` - Get weather report
- `GET /api/articles/{id}/chat` - Get article chat history
- `POST /api/articles/{id}/chat` - Send chat message
- `DELETE /api/articles/{id}/chat` - Clear chat history
- `GET /api/tts/article/{id}` - Get article TTS audio
- `GET /api/tts/weather` - Get weather TTS audio
- `GET /api/tts/settings` - Get TTS settings
- `POST /api/tts/settings` - Update TTS settings
- `GET /api/settings` - Get app settings
- `POST /api/settings` - Update app settings
- `POST /api/location` - Update location

## Dependencies

- `provider` - State management
- `http` & `dio` - HTTP client
- `shared_preferences` - Local storage
- `audioplayers` - Audio playback
- `webview_flutter` - Radar map display
- `url_launcher` - Open external URLs
- `intl` - Date formatting
- `flutter_html` - HTML rendering

## License

This app is part of the News AI project.







