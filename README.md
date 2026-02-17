# 🏠 BestPriceCianTelegramBot

Telegram bot for tracking Cian apartment listings priced below market value.

## 🚀 Features

- **Multi-stage Parsing**: Fast listing collection followed by deep detail extraction.
- **Advanced Scoring**: Evaluates apartments based on:
  - Price discount relative to market median (by metro, rooms, and type).
  - Proximity to metro stations.
  - Floor preference (avoiding first/last floors).
  - Living area quality.
  - Market interest (daily views).
- **Interactive Telegram UI**:
  - Carousel-style apartment browsing.
  - Like/Dislike system to filter your feed.
  - Sorting by Score or Views.
  - Favorites management.
- **Developer Tools**: Real-time market statistics and source management.

## 🛠 Project Structure

```text
BestPriceCianTelegramBot/
├── src/
│   ├── core/              # Database models and schema
│   ├── bot/               # Telegram bot implementation
│   │   ├── bot.py         # Main bot script
│   │   └── keyboards.py   # UI components
│   ├── parser/            # Cian scrapers
│   │   ├── listing_parser.py
│   │   ├── detail_parser.py
│   │   └── run_parsers.py # Orchestrator
│   └── scoring/           # Scoring algorithms
├── scripts/               # Management utilities
├── config/                # Environment templates
├── data/                  # Runtime data (cookies, etc.)
└── requirements.txt       # Dependencies
```

## ⚙️ Setup Instructions

### 1. Installation
```bash
git clone https://github.com/Elvich/BestPriceCianTelegramBot.git
cd BestPriceCianTelegramBot
pip install -r requirements.txt
```

### 2. Configuration
Create a `.env` file from the example:
```bash
cp config/.env.example .env
```
Edit `.env` and provide your `TELEGRAM_BOT_TOKEN` and `DATABASE_URL`.

### 3. Database Initialization
Ensure PostgreSQL is running and your database exists, then run the schema:
```bash
psql -d YOUR_DB_NAME -f src/core/schema.sql
```

## 🐳 Docker Deployment 

Using Docker Compose is the most reliable way to run the bot and parser continuously on a server.

### 1. Requirements
- Docker and Docker Compose installed on your server.

### 2. Configure Environment
Create a `.env` file from the Docker template:
```bash
cp config/.env.example .env
```
Edit the `.env` file with your **Bot Token** and **Postgres credentials**.

### 3. Launch Services
Run the following command to build and start the database, bot, and parser in the background:
```bash
docker compose up -d --build
```

### 4. Monitor
Check the logs to ensure everything is running correctly:
```bash
docker compose logs -f
```

## Manual Execution (Alternative)

### Run the Parser
```bash
python run_parsers.py --all-sources --pages 3 --update-limit 25 --loop --interval 60
```

## 🍪 Cookies
For better resilience against CAPTCHAs, place your Cian `cookies.txt` (header format) into the `data/` directory.


