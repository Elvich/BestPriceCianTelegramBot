from aiogram import Bot, Dispatcher, types
import asyncio
from Router import router
from Config import bot_token

async def main():
    bot = Bot(bot_token)
    dp = Dispatcher()
    dp.include_router(router)

    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped")