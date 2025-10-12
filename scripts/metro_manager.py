#!/usr/bin/env python3
"""
Утилита для управления конфигурацией станций метро
"""
import sys
import os

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.metro_config import (
    get_blocked_stations, 
    get_preferred_stations,
    is_station_blocked,
    is_station_preferred,
    get_station_priority
)

def show_current_config():
    """Показывает текущую конфигурацию станций"""
    print("🚇 Текущая конфигурация станций метро")
    print("="*60)
    
    blocked = get_blocked_stations()
    preferred = get_preferred_stations()
    
    print(f"\n🚫 Заблокированные станции ({len(blocked)}):")
    for i, station in enumerate(blocked, 1):
        print(f"   {i:2}. {station}")
    
    print(f"\n⭐ Предпочитаемые станции ({len(preferred)}):")
    for i, station in enumerate(preferred, 1):
        print(f"   {i:2}. {station}")

def check_station(station_name: str):
    """Проверяет статус конкретной станции"""
    print(f"\n🔍 Проверка станции: '{station_name}'")
    print("-" * 50)
    
    priority = get_station_priority(station_name)
    
    if priority == 0:
        print("❌ Заблокирована (не будет использоваться)")
    elif priority == 2:
        print("⭐ Предпочитаемая (приоритетная)")
    else:
        print("📍 Обычная (нейтральная)")
    
    # Проверяем частичные совпадения
    blocked = get_blocked_stations()
    preferred = get_preferred_stations()
    
    blocked_matches = [b for b in blocked if station_name.lower() in b.lower() or b.lower() in station_name.lower()]
    preferred_matches = [p for p in preferred if station_name.lower() in p.lower() or p.lower() in station_name.lower()]
    
    if blocked_matches:
        print(f"🚫 Совпадения с заблокированными: {', '.join(blocked_matches)}")
    
    if preferred_matches:
        print(f"⭐ Совпадения с предпочитаемыми: {', '.join(preferred_matches)}")

def add_station_to_blocked(station_name: str):
    """Добавляет станцию в бан-лист (инструкция)"""
    print(f"\n➕ Чтобы добавить '{station_name}' в бан-лист:")
    print("="*60)
    print("1. Откройте файл: config/metro_config.py")
    print("2. Найдите список BLOCKED_METRO_STATIONS")
    print("3. Добавьте строку:")
    print(f"   '{station_name}',")
    print("4. Сохраните файл")
    print("\n💡 Изменения вступят в силу при следующей фильтрации")

def add_station_to_preferred(station_name: str):
    """Добавляет станцию в whitelist (инструкция)"""
    print(f"\n⭐ Чтобы добавить '{station_name}' в предпочитаемые:")
    print("="*60)
    print("1. Откройте файл: config/metro_config.py")
    print("2. Найдите список PREFERRED_METRO_STATIONS")
    print("3. Добавьте строку:")
    print(f"   '{station_name}',")
    print("4. Сохраните файл")
    print("\n💡 Изменения вступят в силу при следующей фильтрации")

def main():
    if len(sys.argv) == 1:
        print("🚇 Утилита управления станциями метро")
        print("="*50)
        print("Использование:")
        print("  python metro_manager.py show                    - показать конфигурацию")
        print("  python metro_manager.py check <станция>         - проверить статус станции")
        print("  python metro_manager.py block <станция>         - инструкция добавления в бан-лист")
        print("  python metro_manager.py prefer <станция>        - инструкция добавления в whitelist")
        print("\nПримеры:")
        print("  python metro_manager.py check 'Красносельская'")
        print("  python metro_manager.py block 'Новая станция'")
        return
    
    command = sys.argv[1].lower()
    
    if command == 'show':
        show_current_config()
    
    elif command == 'check':
        if len(sys.argv) < 3:
            print("❌ Укажите название станции для проверки")
            return
        station_name = sys.argv[2]
        check_station(station_name)
    
    elif command == 'block':
        if len(sys.argv) < 3:
            print("❌ Укажите название станции для блокировки")
            return
        station_name = sys.argv[2]
        add_station_to_blocked(station_name)
    
    elif command == 'prefer':
        if len(sys.argv) < 3:
            print("❌ Укажите название станции для предпочтений")
            return
        station_name = sys.argv[2]
        add_station_to_preferred(station_name)
    
    else:
        print(f"❌ Неизвестная команда: {command}")
        print("Используйте: show, check, block, prefer")

if __name__ == '__main__':
    main()