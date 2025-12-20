"""
CLI утилита для управления системой уведомлений
"""

import asyncio
import sys
import argparse
import os
from datetime import datetime

# Добавляем путь к родительской директории
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database.notification_service import NotificationService
from core.database.models import async_session, User, UserNotification
from sqlalchemy import select, func


async def show_notification_stats():
    """Показывает статистику системы уведомлений"""
    print("📊 Статистика системы уведомлений:")
    print("=" * 50)
    
    stats = await NotificationService.get_notification_stats()
    
    print(f"📨 Всего уведомлений: {stats['total_notifications']}")
    print(f"✅ Отправлено: {stats['sent_notifications']}")
    print(f"👀 Прочитано: {stats['read_notifications']}")
    print(f"⏳ В очереди: {stats['pending_notifications']}")
    print(f"🆕 Новых квартир: {stats['new_apartments']}")
    
    # Дополнительная статистика
    async with async_session() as session:
        # Количество активных пользователей
        users_query = select(func.count(User.id)).where(User.is_active == True)
        users_result = await session.execute(users_query)
        active_users = users_result.scalar() or 0
        
        # Последние уведомления
        recent_notifications_query = select(UserNotification).order_by(
            UserNotification.created_at.desc()
        ).limit(3)
        recent_result = await session.execute(recent_notifications_query)
        recent_notifications = recent_result.scalars().all()
        
        print(f"👥 Активных пользователей: {active_users}")
        
        if recent_notifications:
            print(f"\n📋 Последние уведомления:")
            for notif in recent_notifications:
                status = "✅ отправлено" if notif.is_sent else "⏳ в очереди"
                read_status = " (прочитано)" if notif.is_read else ""
                print(f"   • {notif.created_at.strftime('%d.%m %H:%M')} - {notif.apartment_count} квартир - {status}{read_status}")


async def test_notifications(test_user_id: int):
    """Тестирует систему уведомлений"""
    print(f"🧪 Тестирование уведомлений для пользователя {test_user_id}")
    
    # Создаем тестовое уведомление
    created = await NotificationService.create_notifications_for_new_apartments(3)
    
    if created > 0:
        print(f"✅ Создано {created} тестовых уведомлений")
    else:
        print("❌ Не удалось создать тестовые уведомления")


async def cleanup_notifications(days: int = 30):
    """Очищает старые уведомления"""
    print(f"🧹 Очистка уведомлений старше {days} дней...")
    
    deleted = await NotificationService.cleanup_old_notifications(days)
    print(f"✅ Удалено {deleted} старых уведомлений")


async def show_user_notifications(telegram_id: int):
    """Показывает уведомления конкретного пользователя"""
    print(f"👤 Уведомления для пользователя {telegram_id}:")
    print("=" * 50)
    
    async with async_session() as session:
        query = select(UserNotification).where(
            UserNotification.telegram_id == telegram_id
        ).order_by(UserNotification.created_at.desc())
        
        result = await session.execute(query)
        notifications = result.scalars().all()
        
        if not notifications:
            print("❌ Уведомления не найдены")
            return
        
        for i, notif in enumerate(notifications, 1):
            status_emoji = "✅" if notif.is_sent else "⏳"
            read_emoji = "👁️" if notif.is_read else "📬"
            
            print(f"{i}. {status_emoji} {read_emoji} {notif.created_at.strftime('%d.%m.%Y %H:%M')}")
            print(f"   {notif.apartment_count} квартир")
            if notif.sent_at:
                print(f"   Отправлено: {notif.sent_at.strftime('%d.%m.%Y %H:%M')}")
            if notif.read_at:
                print(f"   Прочитано: {notif.read_at.strftime('%d.%m.%Y %H:%M')}")
            print()


async def show_new_apartments_for_user(telegram_id: int):
    """Показывает новые квартиры для пользователя"""
    print(f"🆕 Новые квартиры для пользователя {telegram_id}:")
    print("=" * 50)
    
    apartments = await NotificationService.get_new_apartments_for_user(telegram_id, limit=10)
    
    if not apartments:
        print("❌ Новых квартир не найдено")
        return
    
    for i, apt in enumerate(apartments, 1):
        price_str = f"{apt.price:,} ₽" if apt.price else "цена не указана"
        print(f"{i}. {price_str}")
        print(f"   {apt.title}")
        print(f"   ID: {apt.cian_id}")
        print(f"   Одобрено: {apt.approved_at.strftime('%d.%m.%Y %H:%M') if apt.approved_at else 'N/A'}")
        print()


async def mark_user_notifications_read(telegram_id: int):
    """Отмечает все уведомления пользователя как прочитанные"""
    print(f"📖 Отмечаю уведомления как прочитанные для пользователя {telegram_id}...")
    
    marked = await NotificationService.mark_notifications_read(telegram_id)
    print(f"✅ Отмечено {marked} уведомлений как прочитанные")


def main():
    parser = argparse.ArgumentParser(description='Управление системой уведомлений')
    
    subparsers = parser.add_subparsers(dest='command', help='Доступные команды')
    
    # Команда статистики
    subparsers.add_parser('stats', help='Показать статистику уведомлений')
    
    # Команда тестирования
    test_parser = subparsers.add_parser('test', help='Тестировать уведомления')
    test_parser.add_argument('user_id', type=int, help='ID тестового пользователя')
    
    # Команда очистки
    cleanup_parser = subparsers.add_parser('cleanup', help='Очистить старые уведомления')
    cleanup_parser.add_argument('--days', type=int, default=30, help='Возраст в днях')
    
    # Команда просмотра уведомлений пользователя
    user_parser = subparsers.add_parser('user', help='Уведомления пользователя')
    user_parser.add_argument('telegram_id', type=int, help='Telegram ID пользователя')
    
    # Команда просмотра новых квартир для пользователя
    new_parser = subparsers.add_parser('new', help='Новые квартиры для пользователя')
    new_parser.add_argument('telegram_id', type=int, help='Telegram ID пользователя')
    
    # Команда отметки как прочитанное
    read_parser = subparsers.add_parser('mark-read', help='Отметить уведомления как прочитанные')
    read_parser.add_argument('telegram_id', type=int, help='Telegram ID пользователя')
    
    args = parser.parse_args()
    
    if args.command == 'stats':
        asyncio.run(show_notification_stats())
        
    elif args.command == 'test':
        asyncio.run(test_notifications(args.user_id))
        
    elif args.command == 'cleanup':
        asyncio.run(cleanup_notifications(args.days))
        
    elif args.command == 'user':
        asyncio.run(show_user_notifications(args.telegram_id))
        
    elif args.command == 'new':
        asyncio.run(show_new_apartments_for_user(args.telegram_id))
        
    elif args.command == 'mark-read':
        asyncio.run(mark_user_notifications_read(args.telegram_id))
        
    else:
        parser.print_help()


if __name__ == "__main__":
    main()