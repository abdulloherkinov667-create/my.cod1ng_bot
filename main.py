import asyncio
import logging
import os
import yt_dlp

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import FSInputFile
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from buttons.defould import user_button, yoq_button, send_confirmation_buttons
from create import insert_user, users_table, create_user_pdf, get_all_users
from buttons.inline import xabar_yubor, yuborilmasin_sorov
from stets import SendImg
from aiogram.client.session.aiohttp import AiohttpSession


# PythonAnywhere uchun proxy manzili
PROXY_URL = 'http://proxy.server:3128'
session = AiohttpSession(proxy=PROXY_URL)

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

ADMIN_ID = [6411347321]
API_TOKEN = "8301002449:AAEUdfgageMiEIX-qfIAWc73owqOzkRHqtE"

bot = Bot(token=API_TOKEN, session=session)
dp = Dispatcher()

class VideoState(StatesGroup):
    waiting_for_link = State()




@dp.message(CommandStart())
async def start_command(message: types.Message):
    await users_table()
    insert_user(
        first_name=message.from_user.first_name,
        username=message.from_user.username,
        language_code=message.from_user.language_code,
        is_bot=message.from_user.is_bot,
        chat_id=message.chat.id,
        created_at=message.date)

    if message.from_user.id in ADMIN_ID:
        await message.answer(
            f"""
🌟 <b>Assalomu alaykum hurmatli Admin!</b>

Siz botning administratorisiz.

Bot orqali quyidagi ishlarni bajarishingiz mumkin:

👥 Foydalanuvchilar ro'yxatini ko'rish
📨 Barcha foydalanuvchilarga xabar yuborish
📄 Foydalanuvchilarni PDF qilib yuklab olish

Kerakli bo'limni pastdagi tugmalar orqali tanlang.
""", reply_markup=user_button(), parse_mode="HTML")

    else:
        await message.answer(
            """
👋 <b>Assalomu alaykum!</b>

🎬 Ushbu bot orqali siz <b>Instagram videolarini juda oson yuklab olishingiz mumkin.</b>

Bot qanday ishlaydi?

1️⃣ Instagramga kiring  
2️⃣ Video yoki Reel linkini nusxa oling  
3️⃣ Shu botga yuboring  

📥 Bot sizga videoni yuklab beradi.

🚀 Boshlash uchun quyidagi buyruqni bosing:

/vd_yuklash_boshlash """, parse_mode="HTML")


@dp.message(lambda m: m.text == "/vd_yuklash_boshlash")
async def start_download(message: types.Message, state: FSMContext):

    await state.set_state(VideoState.waiting_for_link)
    await message.answer(
        """
🔗 <b>Instagram video linkini yuboring</b>

Quyidagi turdagi linklar ishlaydi:

• Post video
• Reel video

Masalan:

https://www.instagram.com/reel/xxxx

Yoki

https://www.instagram.com/p/xxxx

Linkni yuboring 👇
""", parse_mode="HTML")


@dp.message(VideoState.waiting_for_link)
async def download_video(message: types.Message, state: FSMContext):
    url = message.text

    if "instagram.com" not in url:
        await message.answer(
            """
❌ <b>Noto'g'ri link yuborildi!</b>

Iltimos faqat Instagram video linkini yuboring.

Masalan:

https://www.instagram.com/reel/xxxx
""",
            parse_mode="HTML"
        )
        return

    msg = await message.answer(
        """
⏳ <b>Video yuklanmoqda...</b>

Iltimos biroz kuting.

Bot video faylni yuklab olib sizga yubormoqda.
""", parse_mode="HTML")

    ydl_opts = {
        'format': 'mp4/best',
        'outtmpl': f'{DOWNLOAD_DIR}/%(id)s.%(ext)s',
        'quiet': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0'
        }
}
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:

            info = ydl.extract_info(url, download=True)

            file_path = ydl.prepare_filename(info)

            if not file_path.endswith(".mp4"):
                file_path = file_path.rsplit('.', 1)[0] + ".mp4"

            await message.answer_video(
            FSInputFile(file_path),
            caption="""
✅ <b>Video muvaffaqiyatli yuklab olindi!</b>

📥 Instagram videosi tayyor.

Agar yana video yuklamoqchi bo'lsangiz yangi link yuboring.

🚀 Bot: @my_codingbot
""",parse_mode="HTML")
        
        
        
        if os.path.exists(file_path):
            os.remove(file_path)


    except Exception as e:
        logging.error(e)
        await message.answer(
            """
❌ <b>Video yuklab bo'lmadi!</b>

Sabablari:

• Video yopiq profil bo'lishi mumkin
• Instagram videoni bloklagan bo'lishi mumkin
• Link noto'g'ri bo'lishi mumkin

Iltimos boshqa video link yuborib ko'ring.
""", parse_mode="HTML")
    await msg.delete()
    await state.clear()






async def main():
    logging.basicConfig(level=logging.INFO)
    print("Bot ishga tushdi...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())