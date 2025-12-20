from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.filters import Command
import logging
import os
import services.bot.keyboards as kb
from scripts.excel_exporter import ExcelExporter
from services.bot.handlers.common import handle_network_errors, safe_edit_message

logger = logging.getLogger(__name__)
router = Router()

@router.message(Command("export"))
@handle_network_errors
async def export_command_handler(message: Message):
    """Команда экспорта данных"""
    await message.answer(
        "📄 **Экспорт данных в Excel**\n\nВыберите тип экспорта:",
        parse_mode="Markdown",
        reply_markup=kb.export_menu
    )

@router.callback_query(F.data == "export_menu")
@handle_network_errors
async def export_menu_handler(callback: CallbackQuery):
    """Показывает меню экспорта"""
    await safe_edit_message(callback, "📄 **Экспорт данных в Excel**\n\nВыберите тип экспорта:", parse_mode="Markdown", reply_markup=kb.export_menu)

@router.callback_query(F.data == "export_browse")
@handle_network_errors
async def export_browse_handler(callback: CallbackQuery):
    """Экспорт квартир для просмотра пользователя"""
    await callback.answer("⏳ Создаем Excel файл...", show_alert=True)
    
    try:
        user_id = callback.from_user.id
        
        await safe_edit_message(callback, "⏳ **Создание Excel файла с квартирами для просмотра...**\n\nПожалуйста, подождите.", parse_mode="Markdown")
        
        file_path = await ExcelExporter.export_browse_apartments_to_excel(user_id)
        
        document = FSInputFile(file_path)
        
        await callback.message.answer_document(
            document=document,
            caption="🏠 **Квартиры для просмотра**\n\nВ файле содержатся все доступные вам квартиры (исключены ваши дизлайки).",
            parse_mode="Markdown"
        )
        
        os.remove(file_path)
        await safe_edit_message(callback, "✅ **Файл с квартирами для просмотра отправлен!**\n\nВыберите другой тип экспорта:", parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Error in export_browse_handler: {e}")
        await safe_edit_message(callback, f"❌ **Ошибка при создании файла:**\n{str(e)}", parse_mode="Markdown", reply_markup=kb.export_menu)

@router.callback_query(F.data == "export_liked")
@handle_network_errors
async def export_liked_handler(callback: CallbackQuery):
    """Экспорт лайкнутых пользователем квартир"""
    await callback.answer("⏳ Создаем Excel файл...", show_alert=True)
    
    try:
        user_id = callback.from_user.id
        
        await safe_edit_message(callback, "⏳ **Создание Excel файла с вашими лайками...**\n\nПожалуйста, подождите.", parse_mode="Markdown")
        
        file_path = await ExcelExporter.export_user_liked_apartments_to_excel(user_id)
        
        document = FSInputFile(file_path)
        
        await callback.message.answer_document(
            document=document,
            caption="❤️ **Ваши лайкнутые квартиры**\n\nВ файле содержатся все квартиры, которые вы добавили в избранное.",
            parse_mode="Markdown"
        )
        
        os.remove(file_path)
        await safe_edit_message(callback, "✅ **Файл с вашими лайками отправлен!**\n\nВыберите другой тип экспорта:", parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Error in export_liked_handler: {e}")
        await safe_edit_message(callback, f"❌ **Ошибка при создании файла:**\n{str(e)}", parse_mode="Markdown", reply_markup=kb.export_menu)

@router.callback_query(F.data == "export_all")
@handle_network_errors
async def export_all_handler(callback: CallbackQuery):
    """Экспорт всех объявлений"""
    await callback.answer("⏳ Создаем Excel файл...", show_alert=True)
    
    try:
        # Показываем сообщение о процессе
        await safe_edit_message(callback, "⏳ **Создание Excel файла...**\n\nПожалуйста, подождите. Это может занять некоторое время.", parse_mode="Markdown")
        
        # Создаем Excel файл
        file_path = await ExcelExporter.export_apartments_to_excel()  # Экспортируем все данные
        
        # Отправляем файл
        document = FSInputFile(file_path)
        
        await callback.message.answer_document(
            document=document,
            caption="📋 **Все объявления о квартирах**\n\nВ файле содержатся активные объявления с подробной информацией.",
            parse_mode="Markdown"
        )
        
        # Удаляем временный файл
        os.remove(file_path)
        
        # Возвращаемся в меню экспорта
        await safe_edit_message(callback, "✅ **Файл успешно создан и отправлен!**\n\nВыберите другой тип экспорта или вернитесь в главное меню:", parse_mode="Markdown", reply_markup=kb.export_menu)
        
    except Exception as e:
        logger.error(f"Error in export_all_handler: {e}")
        await safe_edit_message(callback, f"❌ **Ошибка при создании файла:**\n{str(e)}", parse_mode="Markdown", reply_markup=kb.export_menu)

@router.callback_query(F.data == "export_stats")
@handle_network_errors
async def export_stats_handler(callback: CallbackQuery):
    """Экспорт статистики"""
    await callback.answer("⏳ Создаем статистику...", show_alert=True)
    
    try:
        await safe_edit_message(callback, "⏳ **Создание статистического отчета...**\n\nПожалуйста, подождите.", parse_mode="Markdown")
        
        file_path = await ExcelExporter.export_statistics_to_excel()
        
        document = FSInputFile(file_path)
        
        await callback.message.answer_document(
            document=document,
            caption="📊 **Статистический отчет**\n\nВ файле содержится общая статистика и топ дешевых квартир.",
            parse_mode="Markdown"
        )
        
        os.remove(file_path)
        
        await safe_edit_message(callback, "✅ **Статистика отправлена!**\n\nВыберите другой тип экспорта:", parse_mode="Markdown", reply_markup=kb.export_menu)
        
    except Exception as e:
        logger.error(f"Error in export_stats_handler: {e}")
        await safe_edit_message(callback, f"❌ **Ошибка при создании статистики:**\n{str(e)}", parse_mode="Markdown", reply_markup=kb.export_menu)
