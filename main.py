import asyncio
import logging
import os
import random
import yt_dlp

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import FSInputFile
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.client.session.aiohttp import AiohttpSession

# O'z fayllaringizdan importlar
from buttons.defould import user_button, send_confirmation_buttons
from create import insert_user, users_table, create_user_pdf, get_all_users
from buttons.inline import xabar_yubor
from stets import SendImg

# --- KONFIGURATSIYA ---
# MUHIM: Agar lokal kompyuterda ishlatayotgan bo'lsangiz PROXY shart emas.
# Serverda (VPS) ishlamasa, PROXY_URL ni kiriting.
PROXY_URL = None # Masalan: 'http://username:password@proxy_host:port'
session = AiohttpSession(proxy=PROXY_URL) if PROXY_URL else None

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

ADMIN_ID = [6411347321]
API_TOKEN = "8301002449:AAEUdfgageMiEIX-qfIAWc73owqOzkRHqtE"

bot = Bot(token=API_TOKEN, session=session)
dp = Dispatcher()

class VideoState(StatesGroup):
    waiting_for_link = State()

# --- YUKLASH FUNKSIYASI (COOKIES BILAN) ---
def download_video(url):
    """Instagramdan xatolarsiz yuklash uchun optimallashtirilgan"""
    
    # Yuklashdan oldin papkani tozalash (joy tejash uchun)
    for f in os.listdir(DOWNLOAD_DIR):
        file_path = os.path.join(DOWNLOAD_DIR, f)
        try:
            if os.path.isfile(file_path): os.remove(file_path)
        except: pass

    # Instagram bloklamasligi uchun sozlamalar
    ydl_opts = {
        'format': 'best',
        'outtmpl': f'{DOWNLOAD_DIR}/%(id)s.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        # MUHIM: Instagram bot ekanligingizni bilmasligi uchun 'user-agent'
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'add_header': [
            ('Accept', '*/*'),
            ('Accept-Language', 'en-US,en;q=0.9'),
            ('Referer', 'https://www.instagram.com/'),
        ],
        # Agar blokirovka davom etsa, brauzeringizdan 'cookies.txt' yuklab shu yerga bog'lang:
        # 'cookiefile': 'cookies.txt', 
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info)

# --- ASOSIY HANDLERLAR ---

@dp.message(CommandStart())
async def start_command(message: types.Message):
    await users_table()
    insert_user(
        first_name=message.from_user.first_name,
        username=message.from_user.username,
        language_code=message.from_user.language_code,
        is_bot=message.from_user.is_bot,
        chat_id=message.chat.id,
        created_at=message.date
    )

    if message.from_user.id in ADMIN_ID:
        text = (f"👑 <b>Admin panelga xush kelibsiz!</b>\n\n"
                f"Salom, <b>{message.from_user.first_name}</b>.\n"
                "Kerakli bo‘limni tanlang 👇")
        await message.answer(text, reply_markup=user_button(), parse_mode="HTML")
    else:
        text = ("👋 <b>Botga xush kelibsiz!</b>\n\n"
                "📥 Instagramdan video yuklash uchun link yuboring yoki quyidagi buyruqni bosing: /vd_yuklash_boshlash")
        await message.answer(text, parse_mode="HTML")

@dp.message(F.text == "/vd_yuklash_boshlash")
async def vd_yukla_buyruq(message: types.Message, state: FSMContext):
    await state.set_state(VideoState.waiting_for_link)
    await message.answer("📥 Instagram Reels yoki Post linkini yuboring:")

# Link yuborilganda avtomatik tutib olish (FSM-siz ham ishlashi uchun)
@dp.message(F.text.contains("instagram.com"))
@dp.message(VideoState.waiting_for_link)
async def vd_yuklash(message: types.Message, state: FSMContext):
    url = message.text
    
    # Oddiy validatsiya
    if "instagram.com" not in url:
        await message.answer("❌ Iltimos, faqat Instagram linkini yuboring.")
        return

    status_msg = await message.answer("⌛ Video tahlil qilinmoqda, kuting...")

    try:
        # Bloklanmaslik uchun tasodifiy kutish
        await asyncio.sleep(random.uniform(1, 3))
        
        loop = asyncio.get_event_loop()
        file_path = await loop.run_in_executor(None, download_video, url)

        if os.path.exists(file_path):
            if file_path.lower().endswith(('.mp4', '.mkv', '.mov', '.webm')):
                await message.answer_video(
                    FSInputFile(file_path),
                    caption="✅ Video yuklab berildi!\n\n@my_codingbot"
                )
            else:
                await message.answer_photo(
                    FSInputFile(file_path),
                    caption="✅ Rasm yuklab berildi!\n\n@my_codingbot"
                )
            
            os.remove(file_path) # Faylni o'chirish
        else:
            await message.answer("⚠️ Faylni yuklashda muammo bo'ldi.")

    except Exception as e:
        logging.error(f"Xatolik: {e}")
        await message.answer("❌ Kechirasiz, ushbu videoni yuklab bo'lmadi. (Profil yopiq yoki bot bloklangan bo'lishi mumkin)")

    finally:
        await status_msg.delete()
        await state.clear()

# --- ADMIN PANEL (O'z holicha qoldi) ---
# ... (Siz yuborgan admin qismlari shu yerda davom etadi)

async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        async asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot to'xtatildi")