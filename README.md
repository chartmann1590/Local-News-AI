# 📰 News AI: Your Personal Local News Aggregator

**News AI** is a self-hosted, Dockerized application that delivers localized news and weather with AI-powered article summaries. It's designed to be a private, cost-effective, and highly customizable news source.

## ✨ Features

*   **📍 Automatic Location Detection:** Get news and weather relevant to your current location, with a manual override option.
*   **🤖 AI-Powered Summaries:** Uses a local Ollama instance to rewrite and summarize news articles.
*   **🌦️ Weather Reports:** Includes a 5-day forecast, weather icons, and an embedded radar map.
*   **🗣️ Text-to-Speech:** Listen to articles and weather reports with offline TTS (OpenTTS/Piper).
*   **💬 AI Comments:** Engage in a conversation with the AI about each article.
*   **⭐ Article Bookmarking:** Save your favorite articles for later reading.
*   **🔍 Search and Filtering:** Easily find articles with keyword search and source filtering.
*   **📱 Mobile & Web Apps:** Access your news via a web interface (PWA) or a native Android app built with Flutter.
*   **🎨 Light/Dark Mode:** Choose your preferred theme.
*   **⚙️ Highly Configurable:** Customize schedules, news sources, and AI models.

## 🛠️ Technologies

*   **Backend:** Python, FastAPI, SQLAlchemy, APScheduler
*   **Frontend (Web):** React, Vite, Tailwind CSS
*   **Frontend (Mobile):** Flutter
*   **AI:** Ollama
*   **TTS:** OpenTTS (Piper)
*   **Database:** SQLite
*   **Deployment:** Docker, Docker Compose, Nginx

## 🚀 Getting Started

### Prerequisites

*   [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/)
*   [Ollama](https://ollama.ai/) installed and running on the host machine.

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/news-ai.git
    cd news-ai
    ```

2.  **Build and start the containers:**
    ```bash
    docker compose up --build -d
    ```

3.  **Access the application:**
    *   Web app: [http://localhost:18080](http://localhost:18080)
    *   Web app (HTTPS): [https://localhost:18443](https://localhost:18443)

## 📖 Documentation

For more detailed information, please refer to the documentation in the `docs` directory:

*   [**`docs/README.md`**](./docs/README.md): Documentation overview and index.
*   [**`docs/setup.md`**](./docs/setup.md): Detailed setup and configuration instructions.
*   [**`docs/mobile-app.md`**](./docs/mobile-app.md): Mobile app setup and usage guide.
*   [**`docs/api.md`**](./docs/api.md): API reference.
*   [**`docs/architecture.md`**](./docs/architecture.md): Application architecture.
*   [**`docs/configuration.md`**](./docs/configuration.md): Environment variables and in-app settings.
*   [**`docs/customization.md`**](./docs/customization.md): How to customize the application.
*   [**`docs/deployment.md`**](./docs/deployment.md): Deployment tips.
*   [**`docs/maintenance.md`**](./docs/maintenance.md): Maintenance and data management.
*   [**`docs/troubleshooting.md`**](./docs/troubleshooting.md): Troubleshooting common issues.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a pull request or open an issue.

## 📝 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.