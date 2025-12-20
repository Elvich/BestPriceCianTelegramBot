
# Используем официальный образ Python
FROM python:3.11-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Копируем файл зависимостей
COPY requirements.txt .

# Устанавливаем зависимости Python
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код приложения
COPY core /app/core
COPY services/bot /app/services/bot
COPY scripts /app/scripts
RUN touch /app/services/__init__.py

# Устанавливаем переменную окружения PYTHONPATH
ENV PYTHONPATH=/app

# Создаем директорию для логов внутри контейнера
RUN mkdir -p /app/services/bot/logs

# Команда запуска
CMD ["python", "-m", "services.bot.main"]
