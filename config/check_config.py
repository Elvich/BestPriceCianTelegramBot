#!/usr/bin/env python3
"""
Скрипт для проверки конфигурации и валидации настроек.
Запустите этот скрипт для диагностики проблем с конфигурацией.
"""

import sys
from pathlib import Path

def check_env_file():
    """Проверка наличия и содержимого .env файла."""
    print("🔍 Проверка .env файла...")

    env_path = Path("config/.env")
    env_example_path = Path("config/.env.example")

    if not env_path.exists():
        print("❌ Файл .env не найден!")
        if env_example_path.exists():
            print("💡 Файл .env.example найден. Скопируйте его в .env:")
            print("   cp .env.example .env")
        return False
    
    print("✅ Файл .env найден")
    
    # Проверяем основные переменные
    with open(env_path, 'r') as f:
        content = f.read()
        
    required_vars = ['BOT_TOKEN', 'DATABASE_URL']
    missing_vars = []
    
    for var in required_vars:
        if f"{var}=" not in content:
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Отсутствуют переменные: {', '.join(missing_vars)}")
        return False
    
    print("✅ Все обязательные переменные присутствуют")
    return True

def check_config_import():
    """Проверка импорта конфигурации."""
    print("\n🔍 Проверка импорта конфигурации...")
    
    try:
        from config import config
        print("✅ Модуль config импортирован успешно")
        
        # Проверяем валидацию
        config.validate()
        print("✅ Валидация конфигурации прошла успешно")
        
        # Выводим конфигурацию
        print("\n📋 Текущая конфигурация:")
        config.print_config()
        
        return True
        
    except ImportError as e:
        print(f"❌ Ошибка импорта: {e}")
        return False
    except ValueError as e:
        print(f"❌ Ошибка валидации: {e}")
        return False
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        return False

def check_dependencies():
    """Проверка зависимостей."""
    print("\n🔍 Проверка зависимостей...")
    
    try:
        import dotenv
        print("✅ python-dotenv установлен")
    except ImportError:
        print("❌ python-dotenv не установлен")
        print("💡 Установите: pip3 install python-dotenv")
        return False
    
    # Проверяем другие критические зависимости
    dependencies = [
        ('requests', 'requests'),
        ('bs4', 'beautifulsoup4'),
        ('aiogram', 'aiogram'),
        ('sqlalchemy', 'sqlalchemy'),
        ('tqdm', 'tqdm')
    ]
    
    missing = []
    for module, package in dependencies:
        try:
            __import__(module)
            print(f"✅ {package} установлен")
        except ImportError:
            missing.append(package)
            print(f"❌ {package} не установлен")
    
    if missing:
        print(f"\n💡 Установите недостающие пакеты:")
        print(f"   pip3 install {' '.join(missing)}")
        return False
    
    return True

def main():
    """Основная функция проверки."""
    print("🔐 Диагностика конфигурации BestPriceCianTelegramBot")
    print("=" * 60)
    
    # Проверяем рабочую директорию
    #if not Path("Config.py").exists():
    #    print("❌ Запустите скрипт из папки config или корневой директории проекта")
    #    sys.exit(1)
    
    checks = [
        check_env_file,
        check_dependencies,
        check_config_import
    ]
    
    all_passed = True
    for check in checks:
        if not check():
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 Все проверки прошли успешно!")
        print("✅ Конфигурация готова к использованию")
    else:
        print("❌ Обнаружены проблемы с конфигурацией")
        print("💡 Исправьте указанные выше ошибки")
        sys.exit(1)

if __name__ == "__main__":
    main()