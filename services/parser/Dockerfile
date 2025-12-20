
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

# Копируем код приложения (core и services/parser)
# Мы копируем весь контекст, но .dockerignore (который мы создадим) должен исключить лишнее
COPY core /app/core
COPY services/parser /app/services/parser
# Создаем пустой init для services, если его нет, чтобы работали импорты
RUN touch /app/services/__init__.py

# Устанавливаем переменную окружения PYTHONPATH
ENV PYTHONPATH=/app

# Команда запуска
CMD ["python", "-m", "services.parser.main"]
