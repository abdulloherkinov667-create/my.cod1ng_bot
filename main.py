import asyncio
import logging
import os
import shutil

from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession

API_TOKEN = "8301002449:AAFzKdU48I4Q0nuTxDnY9725MITFVA7w9ok"
PROXY_URL = None

try:
    session = AiohttpSession(proxy=PROXY_URL) if PROXY_URL else AiohttpSession()
except Exception:
    session = AiohttpSession()

bot = Bot(token=API_TOKEN, session=session)
dp = Dispatcher()

ADMIN_ID = [6411347321]
DOWNLOAD_DIR = "downloads"
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# import handler modules after dp is initialized
import video_yuk
import admin


async def main():
    logging.basicConfig(level=logging.INFO)

    try:
        await bot.delete_webhook(drop_pending_updates=True)
    except Exception:
        pass

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
