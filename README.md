# 🏠 BestPriceCianTelegramBot

Телеграм бот для отслеживания квартир ниже рынка Циан

### 1. Клонирование и установка
```bash
git clone https://github.com/Elvich/BestPriceCianTelegramBot.git
cd BestPriceCianTelegramBot
pip3 install -r config/requirements.txt
```

### 2. Настройка конфигурации
```bash
# Скопируйте шаблон конфигурации
cp config/.env.example config/.env
```

```bash
# Отредактируйте .env файл и укажите BOT_TOKEN
nano config/.env
```

### 3. Проверка конфигурации
```bash
python3 check_config.py
```

### 4. Инициализация базы данных
```bash
# Инициализация БД
python3 DB/init_db.py
```

### 5. Запуск 
```bash
# Запуск бота
python3 bot.py

# Запуск парсера
python3 auto_parser.py
```

