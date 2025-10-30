
# Project Overview

This is a full-stack news aggregation application that provides localized news and weather. It features AI-powered article rewrites, text-to-speech, and an interactive chat feature. The application is containerized using Docker and consists of a Python backend, a React-based web frontend, and a Flutter mobile app.

## Technologies

*   **Backend:** Python, FastAPI, SQLAlchemy, APScheduler
*   **Frontend (Web):** React, Vite, Tailwind CSS
*   **Frontend (Mobile):** Flutter
*   **AI:** Ollama
*   **TTS:** OpenTTS (Piper)
*   **Database:** SQLite
*   **Deployment:** Docker, Docker Compose, Nginx

## Architecture

The application is composed of several services orchestrated by Docker Compose:

*   `app`: The main Python backend service.
*   `tts`: The Text-to-Speech service.
*   `nginx`: An Nginx reverse proxy for SSL.

The backend serves a React-based web frontend and also provides a REST API for the Flutter mobile app.

# Building and Running

## Prerequisites

*   Docker and Docker Compose
*   Ollama installed and running on the host machine.

## Running the Application

1.  **Build and start the containers:**
    ```bash
    docker compose up --build -d
    ```

2.  **Access the application:**
    *   Web app: [http://localhost:18080](http://localhost:18080)
    *   Web app (HTTPS): [https://localhost:18443](https://localhost:18443)

## Development

### Backend

The backend code is located in the `app` directory. To install dependencies:

```bash
pip install -r requirements.txt
```

To run the backend development server:

```bash
uvicorn app.main:app --reload
```

### Web Frontend

The web frontend code is in the `web` directory. To install dependencies and run the development server:

```bash
cd web
npm install
npm run dev
```

### Mobile App

The Flutter mobile app code is in the `flutter_app` directory. See `docs/mobile-app.md` for instructions on how to build and run the app.

# Development Conventions

*   **Backend:** The Python code follows standard FastAPI conventions. It uses SQLAlchemy for database interactions and Pydantic for data validation.
*   **Frontend:** The web frontend uses React with functional components and hooks. Styling is done with Tailwind CSS.
*   **Mobile:** The mobile app is built with Flutter and uses the Provider package for state management.
