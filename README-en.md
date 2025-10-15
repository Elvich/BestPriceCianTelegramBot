[Русский 🇷🇺](README.md) / [English 🇺🇸](README-en.md)

# 🏠 BestPriceCianTelegramBot

Telegram bot for tracking apartments below market price on Cian 

### 1. Clone and Install
```bash
git clone https://github.com/Elvich/BestPriceCianTelegramBot.git
cd BestPriceCianTelegramBot
pip3 install -r requirements.txt
```

### 2. Configuration Setup
```bash
# Copy configuration template
cp config/.env.example config/.env

# Edit the .env file and specify your BOT_TOKEN
nano config/.env
```

### 3. Configuration Check
```bash
python3 check_config.py
```

### 4. Database Initialization
```bash
# Create unified DB tables (only on first run)
python3 scripts/manage_db.py

# Or initialize directly
python3 DB/init_db.py
```

### 5. Launch
```bash
# Start the bot
python3 bot.py

# Start the parser
python3 auto_parser.py
```


## 🔐 Security

- ✅ Sensitive data in environment variables
- ✅ `.env` file excluded from Git
- ✅ Automatic configuration validation
- ✅ Centralized configuration management

More details in [SECURITY](config/SECURITY-en.md) |