[Русский 🇷🇺](SECURITY.md) / [English 🇺🇸](SECURITY-en.md)

# 🔐 Security and Configuration Guide

## 📋 Overview

The project uses a modern approach to configuration management with environment variables to ensure security of sensitive data.

## 🔧 Environment Setup

### 1. Creating .env file

Copy the `.env.example` file to `.env`:

```bash
# From project root folder:
cp config/.env.example config/.env

# Or from config folder:
cd config
cp .env.example .env
```

### 2. Filling environment variables

Edit the `.env` file:

```env
# Telegram Bot Configuration
BOT_TOKEN=your_actual_bot_token_here

# Database Configuration  
DATABASE_URL=sqlite+aiosqlite:///dp.sqlite

# Parser Configuration
PARSER_DELAY=3
PARSER_DEEP_DELAY=2

# API Configuration
REQUEST_TIMEOUT=30
MAX_RETRIES=3
```

### 3. Installing dependencies

```bash
pip install -r requirements.txt
```

## 🛡️ Security Principles

### ✅ What's done right:

1. **Environment variables**: Sensitive data (tokens, passwords) stored in `.env` file
2. **Git exclusion**: `.env` file added to `.gitignore`
3. **Configuration example**: `.env.example` contains template without real data
4. **Validation**: Configuration is validated at application startup
5. **Centralized management**: All configuration in one place

### 🚫 What NOT to do:

- ❌ Don't commit `.env` file to repository
- ❌ Don't store tokens and passwords in code
- ❌ Don't use real data in `.env.example`
- ❌ Don't send tokens in logs or error messages

## 📁 Configuration Structure

```
config/
├── __init__.py        # Package initialization
├── Config.py          # Configuration management class  
├── .env               # Real variables (NOT in Git)
├── .env.example       # Variables template (in Git)
├── SECURITY.md        # Security guide
└── check_config.py    # Configuration diagnostics
```

## 🔍 Usage in Code

### Configuration import:

```python
from config import config

# Getting bot token
bot_token = config.get_bot_token()

# Getting other settings
delay = config.PARSER_DELAY
db_url = config.DATABASE_URL
```

### Validation at startup:

```python
# Check critical settings
config.validate()

# Print current configuration (without secrets)
config.print_config()
```

## 🚀 Application Launch

```bash
# Start the bot
cd Bot
python Bot.py

# Start the parser
python Test.py
```

## 🔧 Variable Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `BOT_TOKEN` | Telegram bot token | *required* |
| `DATABASE_URL` | Database URL | `sqlite+aiosqlite:///dp.sqlite` |
| `PARSER_DELAY` | Delay between pages (sec) | `3` |
| `PARSER_DEEP_DELAY` | Deep parsing delay (sec) | `2` |
| `REQUEST_TIMEOUT` | HTTP request timeout (sec) | `30` |
| `MAX_RETRIES` | Maximum retry attempts | `3` |

## 🎯 For Production

### Additional security measures:

1. **Token rotation**: Regularly update Bot Token
2. **Access restriction**: Use file access permissions
3. **Monitoring**: Track suspicious activity
4. **Backup**: Securely store configuration backups

### Environment variables in production:

```bash
# Set variables directly (without .env file)
export BOT_TOKEN="your_production_token"
export DATABASE_URL="postgresql://user:pass@host:port/db"
```

## ❓ Troubleshooting

### Error "BOT_TOKEN not set":
1. Check that `.env` file exists
2. Make sure `BOT_TOKEN` is specified in `.env`
3. Verify token correctness

### dotenv import error:
```bash
pip install python-dotenv
```

### Import path issues:
- Make sure `Config.py` is accessible from all modules
- Check correct `sys.path.append()`