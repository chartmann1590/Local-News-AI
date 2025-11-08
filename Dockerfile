# This Dockerfile uses BuildKit cache mounts (--mount=type=cache) to persist
# Flutter and Gradle dependencies between builds, avoiding network downloads.
# BuildKit is enabled by default in Docker 20.10+ and Docker Compose 2.0+
# If you encounter issues, ensure BuildKit is enabled:
#   export DOCKER_BUILDKIT=1
#   docker compose build
FROM node:20-alpine AS webbuild
WORKDIR /web
COPY web/package.json /web/package.json
COPY web/package-lock.json /web/package-lock.json
RUN npm ci --no-audit --no-fund || npm install --no-audit --no-fund
COPY web /web
# Generate required PNG icons for PWA install (Chrome needs PNG)
RUN apk add --no-cache imagemagick librsvg \
 && convert -background none -density 256x256 -resize 192x192 /web/public/icons/icon-192.svg /web/public/icons/icon-192.png \
 && convert -background none -density 512x512 -resize 512x512 /web/public/icons/icon-512.svg /web/public/icons/icon-512.png \
 && convert -background none -density 512x512 -resize 512x512 /web/public/icons/icon-maskable.svg /web/public/icons/icon-maskable.png
RUN npm run build

# APK should be pre-built locally before building Docker image
# Build the APK with: cd flutter_app && flutter build apk --release
# The APK will be copied from flutter_app/build/app/outputs/flutter-apk/

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_VIRTUALENVS_CREATE=false

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential \
       curl \
       ca-certificates \
       libxml2 \
       libxml2-dev \
       libxslt1.1 \
       libxslt1-dev \
       libjpeg62-turbo \
       ffmpeg \
       imagemagick \
       tzdata \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY app /app/app
# Copy built React app into static directory
COPY --from=webbuild /web/dist /app/app/static
# Copy pre-built APK from flutter_app/build/app/outputs/flutter-apk/
# APK should be built locally first: cd flutter_app && flutter build apk --release
# Create directory and copy APK files (COPY will fail if directory doesn't exist, handled in RUN)
RUN mkdir -p /app/app/static/apk-source
# Use a shell glob pattern - copy the directory contents
COPY flutter_app/build/app/outputs/flutter-apk/ /app/app/static/apk-source/
RUN APK_FOUND="" && \
    APK_FILE="" && \
    if [ -f /app/app/static/apk-source/app-arm64-v8a-release.apk ]; then \
        APK_FILE="/app/app/static/apk-source/app-arm64-v8a-release.apk"; \
    elif [ -f /app/app/static/apk-source/app-armeabi-v7a-release.apk ]; then \
        APK_FILE="/app/app/static/apk-source/app-armeabi-v7a-release.apk"; \
    elif [ -f /app/app/static/apk-source/app-release.apk ]; then \
        APK_FILE="/app/app/static/apk-source/app-release.apk"; \
    fi && \
    if [ -n "$APK_FILE" ] && [ -f "$APK_FILE" ]; then \
        APK_SIZE=$(stat -c%s "$APK_FILE" 2>/dev/null || echo 0) && \
        if [ "$APK_SIZE" -gt 1000000 ]; then \
            cp "$APK_FILE" /app/app/static/news-ai-app.apk && \
            echo "✓ Pre-built APK copied successfully: $(basename $APK_FILE) (size: ${APK_SIZE} bytes)" && \
            APK_FOUND="yes"; \
        else \
            echo "⚠ APK file too small (${APK_SIZE} bytes): $(basename $APK_FILE)"; \
        fi; \
    fi && \
    rm -rf /app/app/static/apk-source 2>/dev/null || true && \
    if [ -z "$APK_FOUND" ]; then \
        echo "⚠ No valid pre-built APK found. Build it first with: cd flutter_app && flutter build apk --release"; \
        echo "⚠ Creating empty placeholder file"; \
        touch /app/app/static/news-ai-app.apk || true; \
    fi

# Generate a royalty-free ambient background music MP3 (procedurally, no network)
# Soft triad sine tones mixed and encoded to MP3 for ~90 seconds
RUN set -eux; \
    if [ ! -f /app/app/static/bgm.mp3 ]; then \
      ffmpeg -hide_banner -loglevel error \
        -f lavfi -i sine=frequency=261.63:duration=90:sample_rate=48000 \
        -f lavfi -i sine=frequency=329.63:duration=90:sample_rate=48000 \
        -f lavfi -i sine=frequency=392.00:duration=90:sample_rate=48000 \
        -filter_complex "amix=inputs=3:normalize=0, volume=0.08, aformat=sample_fmts=s16:sample_rates=44100:channel_layouts=stereo" \
        -c:a libmp3lame -q:a 5 /app/app/static/bgm.mp3 || true; \
    fi

# SQLite data path
RUN mkdir -p /data
VOLUME ["/data"]

EXPOSE 8000

ENV TZ=${TZ:-America/New_York}

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
