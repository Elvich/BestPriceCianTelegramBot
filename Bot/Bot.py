from aiogram import Bot, Dispatcher, types
import asyncio
from Router import router

async def main():
    bot = Bot(token="7434936528:AAHmoy6FfwSmrXiBM3tiiRRWXACI8EVm3fU")
    dp = Dispatcher()
    dp.include_router(router)

    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped")