# 🏠 BestPriceCianTelegramBot

Телеграм бот для отслеживания квартир ниже рынка Циан / Telegram bot for tracking apartments below the Cian market

## 🚀 Быстрый старт

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
python3 manage_db.py

# Или инициализация напрямую
python3 DB/init_db.py
```

### 5. Запуск

#### 🚀 Быстрый запуск (рекомендуется)
```bash
# Запуск бота (с автоматической активацией виртуального окружения)
./start_bot.sh

# Запуск парсера
./run_parser.sh

# Поиск квартир (до 15 млн по умолчанию)
./search_apartments.sh
./search_apartments.sh 10000000  # до 10 млн
```

#### 🔧 Ручной запуск
```bash
# Активация виртуального окружения
source .venv/bin/activate

# Запуск бота
cd Bot && python Bot.py

# Запуск парсера с сохранением в БД
python test_final.py

# Управление базой данных
python manage_db.py stats
python manage_db.py search --max-price 10000000
```

## 🔐 Безопасность

Проект использует современный подход к управлению конфигурацией:
- ✅ Чувствительные данные в переменных окружения
- ✅ Файл `.env` исключен из Git
- ✅ Автоматическая валидация настроек
- ✅ Централизованное управление конфигурацией

Подробнее в [SECURITY.md](config/SECURITY.md)

## 📁 Структура проекта

```
├── Bot/                    # Telegram бот
│   ├── Bot.py             # Точка входа
│   ├── Router.py          # Обработчики команд
│   ├── Kb.py              # Клавиатуры
│   └── States.py          # Состояния FSM
├── config/                 # Конфигурация и безопасность
│   ├── __init__.py        # Инициализация пакета
│   ├── Config.py          # Управление конфигурацией
│   ├── .env               # Переменные окружения (НЕ в Git)
│   ├── .env.example       # Шаблон конфигурации
│   ├── SECURITY.md        # Руководство по безопасности
│   └── check_config.py    # Диагностика настроек
├── DB/                     # База данных и фильтрация  
│   ├── Models.py          # SQLAlchemy модели (единая БД)
│   ├── ApartmentService.py # Объединенный сервис (staging + production)
│   ├── FilterService.py   # Система многоступенчатой фильтрации
│   ├── Request.py         # Модели поисковых запросов
│   └── init_db.py         # Инициализация единой БД
│   └── Request.py         # Запросы к БД (устарело)
├── Parser.py               # Парсер Cian.ru 
├── FileSaver.py           # Сохранение в БД/CSV с поддержкой staging
├── ExcelExporter.py       # Экспорт данных в Excel
├── manage_db.py           # Основные операции с БД
├── apartment_manager.py   # Унифицированный CLI для фильтрации
├── demo.py               # Демонстрация полного цикла
└── ARCHITECTURE.md       # Документация архитектуры
```

## ⚙️ Конфигурация

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `BOT_TOKEN` | Токен Telegram бота | *обязательно* |
| `DATABASE_URL` | URL базы данных | `sqlite+aiosqlite:///dp.sqlite` |
| `PARSER_DELAY` | Задержка между страницами (сек) | `3` |
| `PARSER_DEEP_DELAY` | Задержка при глубоком парсинге (сек) | `2` |
| `REQUEST_TIMEOUT` | Таймаут HTTP запросов (сек) | `30` |
| `MAX_RETRIES` | Максимум повторных попыток | `3` |

## 🗄️ База данных

### Основная БД (готовые объявления)
```bash
# Статистика
python3 manage_db.py stats

# Поиск объявлений
python3 manage_db.py search --max-price 10000000
python3 manage_db.py search --metro "Полежаевская" "Беговая"
python3 manage_db.py search --min-price 5000000 --max-price 15000000

# Список станций метро
python3 manage_db.py metro

# Недавно добавленные объявления
python3 manage_db.py recent --days 7
```

### Унифицированное управление (staging + production)
```bash
# Общая статистика единой БД
python3 apartment_manager.py stats

# Запуск фильтрации  
python3 apartment_manager.py filter --config premium --verbose
python3 apartment_manager.py filter --limit 100

# Поиск в staging области
python3 apartment_manager.py search --staging --status pending
python3 apartment_manager.py search --staging --status approved --limit 5

# Поиск готовых квартир
python3 apartment_manager.py search --production --limit 10

# Логи фильтрации конкретного объявления
python3 apartment_manager.py logs 123456789

# Полный демо цикл
python3 demo.py full

# Очистка старых записей
python3 manage_staging.py cleanup --days 30

# Экспорт данных
python3 manage_staging.py export --filename staging_data.csv
```

### Система фильтрации
```bash
# Запуск фильтрации с конфигурацией по умолчанию
python3 filter_apartments.py run

# Премиум фильтрация
python3 filter_apartments.py run --config premium --limit 100 --verbose

# Пользовательская конфигурация
python3 filter_apartments.py run --config custom

# Просмотр ожидающих обработки
python3 filter_apartments.py preview --limit 20

# Статистика фильтрации
python3 filter_apartments.py stats
```

## 🏗️ Новая архитектура с фильтрацией

### Двухэтапная обработка данных
```
Парсер → Staging БД → Фильтры → Production БД → Telegram бот
```

**Staging БД** - временное хранилище всех спарсенных объявлений
**Фильтры** - система проверки объявлений на соответствие критериям
**Production БД** - только проверенные и подходящие объявления

### Демонстрация новой системы
```bash
# Полная демонстрация архитектуры
python3 demo_filter_system.py
```

### Конфигурации фильтров

**По умолчанию:**
- Цена до 25 млн ₽
- До метро максимум 15 минут
- Исключаются студии и коммунальные квартиры

**Премиум:**
- Цена от 15 до 50 млн ₽
- До метро максимум 10 минут  
- Только избранные станции метро
- Площадь от 60 м²

**Пользовательская:**
- Интерактивная настройка через CLI

### Типы фильтров

1. **PriceFilter** - фильтрация по цене и цене за м²
2. **MetroFilter** - фильтрация по станциям метро и расстоянию
3. **CharacteristicsFilter** - площадь, количество комнат, этаж
4. **QualityFilter** - качество описания, ключевые слова
5. **DuplicateFilter** - исключение дубликатов

Подробная документация: [DB/README.md](DB/README.md)
