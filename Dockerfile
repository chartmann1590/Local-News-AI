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

FROM debian:bookworm-slim AS flutterbuild
WORKDIR /build

# Install dependencies for Flutter and Android SDK
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    unzip \
    xz-utils \
    zip \
    libglu1-mesa \
    ca-certificates \
    openjdk-17-jdk \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Install Flutter SDK
RUN curl -fSL https://storage.googleapis.com/flutter_infra_release/releases/stable/linux/flutter_linux_3.24.5-stable.tar.xz -o flutter.tar.xz \
    && tar xf flutter.tar.xz \
    && rm flutter.tar.xz

# Add Flutter to PATH
ENV PATH="/build/flutter/bin:${PATH}"

# Install Android SDK Command Line Tools
ENV ANDROID_HOME=/opt/android-sdk
ENV PATH="${PATH}:${ANDROID_HOME}/cmdline-tools/latest/bin:${ANDROID_HOME}/platform-tools"

RUN mkdir -p ${ANDROID_HOME}/cmdline-tools && \
    cd ${ANDROID_HOME}/cmdline-tools && \
    curl -fSL https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip -o cmdline-tools.zip && \
    unzip cmdline-tools.zip && \
    mv cmdline-tools latest && \
    rm cmdline-tools.zip && \
    yes | sdkmanager --licenses || true && \
    sdkmanager "platform-tools" "platforms;android-34" "platforms;android-33" "build-tools;34.0.0" "ndk;25.1.8937393"

# Configure git safe directory
RUN git config --global --add safe.directory /build/flutter

# Set environment variables for Flutter
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ENV PATH="${PATH}:${JAVA_HOME}/bin"

# Accept Android licenses via flutter
RUN flutter doctor --android-licenses || true

# Verify Flutter installation
RUN flutter --version && flutter doctor -v

# Copy Flutter app
COPY flutter_app /build/flutter_app

# Build APK
WORKDIR /build/flutter_app
# Clean any previous build artifacts
RUN flutter clean || true
RUN flutter pub get
# Set environment to avoid Windows path issues
ENV FLUTTER_ROOT=/build/flutter
RUN flutter build apk --release

# Copy built APK to a location we can extract it from
RUN mkdir -p /build/apk && \
    cp /build/flutter_app/build/app/outputs/flutter-apk/app-release.apk /build/apk/news-ai-app.apk

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
       tzdata \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY app /app/app
# Copy built React app into static directory
COPY --from=webbuild /web/dist /app/app/static
# Copy built APK from Flutter build stage
COPY --from=flutterbuild /build/apk/news-ai-app.apk /app/app/static/news-ai-app.apk

# SQLite data path
RUN mkdir -p /data
VOLUME ["/data"]

EXPOSE 8000

ENV TZ=${TZ:-America/New_York}

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
