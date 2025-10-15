[Русский 🇷🇺](README.md) / [English 🇺🇸](README-en.md)

# 🏠 BestPriceCianTelegramBot

Телеграм бот для отслеживания квартир ниже рынка Циан

### 1. Клонирование и установка
```bash
git clone https://github.com/Elvich/BestPriceCianTelegramBot.git
cd BestPriceCianTelegramBot
pip3 install -r requirements.txt
```

### 2. Настройка конфигурации
```bash
# Скопируйте шаблон конфигурации
cp config/.env.example config/.env

# Отредактируйте .env файл и укажите ваш BOT_TOKEN
nano config/.env
```

### 3. Проверка конфигурации
```bash
python3 check_config.py
```

### 4. Инициализация базы данных
```bash
# Создание таблиц единой БД (только при первом запуске)
python3 scripts/manage_db.py

# Или инициализация напрямую
python3 DB/init_db.py
```

### 5. Зпапуск 
```bash
# Запуск бота
python3 bot.py

# Запуск парсера
python3 auto_parser.py
```


## 🔐 Безопасность

- ✅ Чувствительные данные в переменных окружения
- ✅ Файл `.env` исключен из Git
- ✅ Автоматическая валидация настроек
- ✅ Централизованное управление конфигурацией

Подробнее в [SECURITY](config/SECURITY.md) 

