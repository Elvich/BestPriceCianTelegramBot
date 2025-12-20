from aiogram import Router, F
from aiogram.types import CallbackQuery
import logging
import services.bot.keyboards as kb
from core.database.apartment_service import ApartmentService
from core.database.notification_service import NotificationService
from core.database.reaction_service import ReactionService
from services.bot.handlers.common import handle_network_errors, safe_edit_message

logger = logging.getLogger(__name__)
router = Router()

async def browse_apartments_helper(callback: CallbackQuery, index: int = 0):
    """Помощник для просмотра квартир в режиме плеера"""
    try:
        user_id = callback.from_user.id
        
        # Получаем все квартиры, исключая дизлайкнутые пользователем
        apartments = await ApartmentService.get_apartments(
            limit=50,  # Берем больше квартир для просмотра
            only_active=True,
            only_production=True,
            exclude_disliked_for_user=user_id
        )
        
        if not apartments:
            await safe_edit_message(
                callback, 
                "❌ Квартиры не найдены. Возможно, база данных пуста.",
                reply_markup=kb.back_to_menu
            )
            return
        
        # Проверяем, что индекс в пределах списка
        if index < 0 or index >= len(apartments):
            index = 0
        
        apartment = apartments[index]
        
        # Получаем текущую реакцию пользователя
        current_reaction = await ReactionService.get_user_reaction(user_id, apartment.id)
        
        # Формируем информацию о квартире
        price_str = f"{apartment.price:,} ₽" if apartment.price else "цена не указана"
        price_per_sqm_str = f" ({apartment.price_per_sqm:,} ₽/м²)" if apartment.price_per_sqm else ""
        
        metro_info = []
        for metro in apartment.metro_stations[:2]:
            metro_info.append(f"{metro.station_name} {metro.travel_time}")
        metro_str = f"\n🚇 {', '.join(metro_info)}" if metro_info else ""
        
        address_str = f"\n📍 {apartment.address}" if apartment.address else ""
        
        apartment_info = f"**{price_str}**{price_per_sqm_str}"
        apartment_info += f"\n{apartment.title}"
        apartment_info += metro_str
        apartment_info += address_str
        apartment_info += f"\n\n🔗 [Открыть на Cian]({apartment.url})"
        
        # Информация о позиции в списке
        position_info = f"📋 **Квартира {index + 1} из {len(apartments)}**\n\n"
        
        text = position_info + apartment_info
        
        # Создаем клавиатуру плеера
        keyboard = kb.create_apartment_browser_keyboard(
            current_index=index,
            total_count=len(apartments),
            apartment_id=apartment.id,
            current_reaction=current_reaction,
            list_context="all"
        )
        
        await safe_edit_message(
            callback,
            text,
            parse_mode="Markdown",
            reply_markup=keyboard,
            disable_web_page_preview=True
        )
        
    except Exception as e:
        logger.error(f"Error in browse_apartments_helper: {e}")
        await safe_edit_message(
            callback,
            f"❌ Ошибка при загрузке квартир: {str(e)}",
            reply_markup=kb.back_to_menu
        )

async def browse_apartments_list_helper(callback: CallbackQuery, index: int, list_context: str):
    """Универсальная функция для просмотра списков квартир в режиме плеера"""
    try:
        user_id = callback.from_user.id
        
        # Получаем квартиры в зависимости от контекста
        if list_context == "all":
            apartments = await ApartmentService.get_apartments(
                limit=50,
                only_active=True,
                only_production=True,
                exclude_disliked_for_user=user_id
            )
            title_prefix = "🏠 Просмотр квартир"
        elif list_context == "liked":
            apartments = await ReactionService.get_user_liked_apartments(user_id, limit=50)
            title_prefix = "❤️ Ваши лайки"
        elif list_context == "disliked":
            apartments = await ReactionService.get_user_disliked_apartments(user_id, limit=50)
            title_prefix = "👎 Скрытые квартиры"
        elif list_context == "new":
            apartments = await NotificationService.get_new_apartments_for_user(user_id, limit=50)
            title_prefix = "🆕 Новые квартиры"
        elif list_context == "views_100":
            apartments = await ApartmentService.get_apartments(
                limit=50,
                only_active=True,
                only_production=True,
                exclude_disliked_for_user=user_id,
                min_views=100
            )
            title_prefix = ">100 просмотров"
        elif list_context == "views_200":
            apartments = await ApartmentService.get_apartments(
                limit=50,
                only_active=True,
                only_production=True,
                exclude_disliked_for_user=user_id,
                min_views=200
            )
            title_prefix = ">200 просмотров"
        else:
            apartments = []
            title_prefix = "📋 Квартиры"
        
        if not apartments:
            empty_messages = {
                "all": "❌ Квартиры не найдены. Возможно, база данных пуста.",
                "liked": "❤️ У вас пока нет лайкнутых квартир.\nИспользуйте кнопку ❤️ при просмотре квартир.",
                "disliked": "👎 У вас пока нет скрытых квартир.\nИспользуйте кнопку 👎 при просмотре квартир.",
                "new": "🆕 Новых квартир для вас пока нет.",
                "views_100": "Квартир с >100 просмотров пока нет.",
                "views_200": "Квартир с >200 просмотров пока нет."
            }
            
            await safe_edit_message(
                callback, 
                empty_messages.get(list_context, "❌ Квартиры не найдены."),
                reply_markup=kb.back_to_menu
            )
            return
        
        # Проверяем, что индекс в пределах списка
        if index < 0 or index >= len(apartments):
            index = 0
        
        apartment = apartments[index]
        
        # Получаем текущую реакцию пользователя
        current_reaction = await ReactionService.get_user_reaction(user_id, apartment.id)
        
        # Формируем информацию о квартире
        price_str = f"{apartment.price:,} ₽" if apartment.price else "цена не указана"
        price_per_sqm_str = f" ({apartment.price_per_sqm:,} ₽/м²)" if apartment.price_per_sqm else ""
        
        metro_info = []
        for metro in apartment.metro_stations[:2]:
            metro_info.append(f"{metro.station_name} {metro.travel_time}")
        metro_str = f"\n🚇 {', '.join(metro_info)}" if metro_info else ""
        
        address_str = f"\n📍 {apartment.address}" if apartment.address else ""
        
        apartment_info = f"**{price_str}**{price_per_sqm_str}"
        apartment_info += f"\n{apartment.title}"
        apartment_info += metro_str
        apartment_info += address_str
        apartment_info += f"\n\n🔗 [Открыть на Cian]({apartment.url})"
        
        # Информация о позиции в списке
        position_info = f"📋 **{title_prefix} - {index + 1} из {len(apartments)}**\n\n"
        
        text = position_info + apartment_info
        
        # Создаем клавиатуру плеера
        keyboard = kb.create_apartment_browser_keyboard(
            current_index=index,
            total_count=len(apartments),
            apartment_id=apartment.id,
            current_reaction=current_reaction,
            list_context=list_context
        )
        
        await safe_edit_message(
            callback,
            text,
            parse_mode="Markdown",
            reply_markup=keyboard,
            disable_web_page_preview=True
        )
        
    except Exception as e:
        logger.error(f"Error in browse_apartments_list_helper: {e}")
        await safe_edit_message(
            callback,
            f"❌ Ошибка при загрузке квартир: {str(e)}",
            reply_markup=kb.back_to_menu
        )


@router.callback_query(F.data == "browse_all")
@handle_network_errors
async def browse_all_handler(callback: CallbackQuery):
    """Просмотр всех квартир"""
    await browse_apartments_helper(callback, index=0)
    await callback.answer()

@router.callback_query(F.data == "back_to_browse_menu")
@handle_network_errors
async def back_to_browse_menu_handler(callback: CallbackQuery):
    """Возврат в меню просмотра"""
    await safe_edit_message(
        callback, 
        "🔍 **Выберите режим просмотра:**", 
        reply_markup=kb.browse_menu,
        parse_mode="Markdown"
    )

@router.callback_query(F.data.in_({"browse_views_100", "browse_views_200"}))
@handle_network_errors
async def browse_views_handler(callback: CallbackQuery):
    """Просмотр популярных квартир"""
    min_views = 100 if "100" in callback.data else 200
    context = f"views_{min_views}"
    await browse_apartments_list_helper(callback, index=0, list_context=context)
    await callback.answer()

@router.callback_query(F.data == "browse")
@handle_network_errors
async def browse_apartments_handler(callback: CallbackQuery):
    """Меню просмотра квартир"""
    await safe_edit_message(
        callback, 
        "🔍 **Выберите режим просмотра:**", 
        reply_markup=kb.browse_menu,
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "my_likes")
@handle_network_errors  
async def my_likes_handler(callback: CallbackQuery):
    """Показать лайкнутые квартиры в плеере"""
    await browse_apartments_list_helper(callback, index=0, list_context="liked")
    await callback.answer()

@router.callback_query(F.data == "my_dislikes")
@handle_network_errors
async def my_dislikes_handler(callback: CallbackQuery):
    """Показать дизлайкнутые квартиры в плеере"""
    await browse_apartments_list_helper(callback, index=0, list_context="disliked")
    await callback.answer()

@router.callback_query(F.data.startswith("browse_prev_"))
@handle_network_errors
async def browse_previous_handler(callback: CallbackQuery):
    """Переход к предыдущей квартире в плеере"""
    try:
        # Извлекаем данные из callback_data
        parts = callback.data.split('_')
        current_index = int(parts[2])
        # Join the rest as context (e.g. "views_100")
        list_context = "_".join(parts[3:]) if len(parts) > 3 else "all"
        new_index = current_index - 1
        
        if new_index >= 0:
            if list_context == "all":
                await browse_apartments_helper(callback, index=new_index)
            else:
                await browse_apartments_list_helper(callback, index=new_index, list_context=list_context)
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in browse_previous_handler: {e}")
        await callback.answer("❌ Ошибка при переходе")

@router.callback_query(F.data.startswith("browse_next_"))
@handle_network_errors
async def browse_next_handler(callback: CallbackQuery):
    """Переход к следующей квартире в плеере"""
    try:
        # Извлекаем данные из callback_data
        parts = callback.data.split('_')
        current_index = int(parts[2])
        # Join the rest as context (e.g. "views_100")
        list_context = "_".join(parts[3:]) if len(parts) > 3 else "all"
        new_index = current_index + 1
        
        # Функции сами проверят границы
        if list_context == "all":
            await browse_apartments_helper(callback, index=new_index)
        else:
            await browse_apartments_list_helper(callback, index=new_index, list_context=list_context)
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in browse_next_handler: {e}")
        await callback.answer("❌ Ошибка при переходе")

@router.callback_query(F.data.startswith("reaction_"))
@handle_network_errors
async def reaction_handler(callback: CallbackQuery):
    """Обработчик кнопок лайка/дизлайка"""
    user_id = callback.from_user.id
    
    # Парсим callback_data: "reaction_like_123_context_index" или "reaction_dislike_123"
    try:
        parts = callback.data.split('_')
        reaction_type = parts[1]  # 'like' или 'dislike'
        apartment_id = int(parts[2])
        
        # Если есть контекст и индекс (длина > 3)
        if len(parts) > 3:
            # Индекс всегда последний
            current_index = int(parts[-1])
            # Контекст - все между id и index
            list_context = "_".join(parts[3:-1])
            # Если контекст пустой (например reaction_like_123_0), значит "all" - хотя такой формат не генерируем
            if not list_context:
                list_context = "all"
        else:
            list_context = "all"
            current_index = 0
    except (IndexError, ValueError):
        await callback.answer("❌ Ошибка в данных", show_alert=True)
        return
    
    try:
        # Получаем текущую реакцию пользователя
        current_reaction = await ReactionService.get_user_reaction(user_id, apartment_id)
        
        # Логика противоположных реакций
        if current_reaction and current_reaction != reaction_type:
            # Если есть противоположная реакция, убираем её и ставим новую
            await ReactionService.remove_reaction(user_id, apartment_id)
            result = await ReactionService.toggle_reaction(user_id, apartment_id, reaction_type)
            
            if reaction_type == 'like':
                message = "❤️ Убрали дизлайк и поставили лайк!"
            else:
                message = "👎 Убрали лайк и поставили дизлайк!"
        else:
            # Обычное переключение реакции
            result = await ReactionService.toggle_reaction(user_id, apartment_id, reaction_type)
            
            # Формируем ответ пользователю
            if result['action'] == 'added':
                if reaction_type == 'like':
                    message = "❤️ Квартира добавлена в избранное!"
                else:
                    message = "👎 Квартира скрыта из результатов поиска"
            elif result['action'] == 'removed':
                if reaction_type == 'like':
                    message = "💔 Квартира удалена из избранного"
                else:
                    message = "✅ Квартира снова будет показываться"
            else:
                message = "✅ Реакция обновлена"
        
        await callback.answer(message, show_alert=True)
        
        # Обновляем плеер с актуальными данными
        if list_context == "all":
            await browse_apartments_helper(callback, index=current_index)
        else:
            await browse_apartments_list_helper(callback, index=current_index, list_context=list_context)
            
    except Exception as e:
        logger.error(f"Error in reaction_handler: {e}")
        await callback.answer("❌ Ошибка при обработке реакции", show_alert=True)

@router.callback_query(F.data.startswith("back_to_list_"))
@handle_network_errors
async def back_to_list_handler(callback: CallbackQuery):
    """Возврат к списку (из плеера обратно к обзору списка)"""
    try:
        parts = callback.data.split('_')
        list_context = "_".join(parts[3:])
        
        if list_context == "liked":
            await my_likes_handler(callback)
        elif list_context == "disliked":
            await my_dislikes_handler(callback)
        elif list_context == "new":
            # Avoid circular dependency in recent_callback_handler logic by re-using list helper/handler
            # But recent_callback_handler is in stats.py.
            # We can use browse_apartments_list_helper here directly.
            await browse_apartments_list_helper(callback, index=0, list_context="new")
        elif list_context.startswith("views_"):
            await browse_apartments_list_helper(callback, index=0, list_context=list_context)
            
    except Exception as e:
        logger.error(f"Error in back_to_list_handler: {e}")
        await safe_edit_message(callback, "❌ Ошибка при возврате к списку", reply_markup=kb.back_to_menu)

@router.callback_query(F.data.startswith("remove_reaction_"))
@handle_network_errors
async def remove_reaction_handler(callback: CallbackQuery):
    """Удаление реакции из списка лайков/дизлайков"""
    user_id = callback.from_user.id
    
    try:
        apartment_id = int(callback.data.split('_')[2])
        await ReactionService.remove_reaction(user_id, apartment_id)
        
        await callback.answer("✅ Реакция удалена", show_alert=True)
        
        # Обновляем список, так как элемент удален
        # Однако мы не знаем контекст (лайки или дизлайки), 
        # но кнопка эта используется в меню 'my_likes' или 'my_dislikes'? 
        # В коде роутера это не очевидно, но обычно при удалении реакции мы хотим обновить текущий список.
        # Пока просто ответим, пользователю придется переоткрыть список.
        
    except Exception as e:
        logger.error(f"Error in remove_reaction_handler: {e}")
        await callback.answer("❌ Ошибка при удалении реакции", show_alert=True)
