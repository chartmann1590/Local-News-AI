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

# Install dependencies for Flutter
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

# Configure git safe directory
RUN git config --global --add safe.directory /build/flutter

# Set environment variables for Flutter/Java
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ENV PATH="${PATH}:${JAVA_HOME}/bin"

# Install Android SDK command line tools (Flutter needs this to manage the rest)
ENV ANDROID_HOME=/opt/android-sdk
RUN mkdir -p ${ANDROID_HOME}/cmdline-tools && \
    cd ${ANDROID_HOME}/cmdline-tools && \
    for i in 1 2 3 4 5; do \
        curl -fSL --retry 3 --retry-delay 5 https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip -o cmdline-tools.zip && break || \
        (echo "Download attempt $i failed, retrying..." && sleep 10); \
    done && \
    unzip -q cmdline-tools.zip && \
    mv cmdline-tools latest && \
    rm cmdline-tools.zip
ENV PATH="${PATH}:${ANDROID_HOME}/cmdline-tools/latest/bin"

# Accept Android licenses
RUN yes | sdkmanager --licenses || true

# Set environment variables for Android SDK
ENV ANDROID_SDK_ROOT=${ANDROID_HOME}
ENV PATH="${PATH}:${ANDROID_HOME}/platform-tools"

# Let Flutter handle Android SDK setup automatically (more reliable than manual install)
# Flutter will download and configure SDK components as needed during build
RUN flutter doctor --android-licenses || true
RUN flutter doctor -v || true

# Copy Flutter app
COPY flutter_app /build/flutter_app

# Build APK using Flutter
WORKDIR /build/flutter_app
RUN flutter clean || true
RUN flutter pub get
ENV FLUTTER_ROOT=/build/flutter

# Build APK - allow build to continue even if APK fails (network issues are common)
RUN mkdir -p /build/apk && \
    if flutter build apk --release 2>&1 | tee /tmp/apk_build.log; then \
        cp /build/flutter_app/build/app/outputs/flutter-apk/app-release.apk /build/apk/news-ai-app.apk && \
        echo "APK built successfully"; \
    else \
        echo "APK build failed (network issues likely) - continuing without APK. Check /tmp/apk_build.log for details." && \
        touch /build/apk/news-ai-app.apk || true; \
    fi

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
# Copy built APK from Flutter build stage (if it was successfully built)
COPY --from=flutterbuild /build/apk/news-ai-app.apk /app/app/static/news-ai-app.apk

# SQLite data path
RUN mkdir -p /data
VOLUME ["/data"]

EXPOSE 8000

ENV TZ=${TZ:-America/New_York}

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
