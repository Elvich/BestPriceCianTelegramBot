from aiogram import Router, F 
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup
import Kb

router = Router()

@router.message(CommandStart())
async def command_start_handler(message: Message, state: FSMContext):
    await message.answer(text=f"""Привет, {message.from_user.full_name}!\n
Я бот, который поможет тебе найти лучшие предложения на Циан по Москве.""", reply_markup=Kb.section)
    