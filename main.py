import asyncio
import logging
import os
import random
import re
import yt_dlp

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import FSInputFile
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.client.session.aiohttp import AiohttpSession

# O'z fayllaringizdan importlar (Bular loyihangizda mavjud deb hisoblaymiz)
try:
    from buttons.defould import user_button, send_confirmation_buttons
    from create import insert_user, users_table, create_user_pdf, get_all_users
    from buttons.inline import xabar_yubor
    from stets import SendImg
except ImportError:
    logging.warning("Ba'zi modullar topilmadi. Fayl tuzilmangizni tekshiring!")

# --- KONFIGURATSIYA ---
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

ADMIN_ID = [6411347321]
API_TOKEN = "8301002449:AAEUdfgageMiEIX-qfIAWc73owqOzkRHqtE"

# Botni sozlash
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

class VideoState(StatesGroup):
    waiting_for_link = State()

# --- YUKLASH FUNKSIYASI (YT-DLP) ---
def download_media(url):
    """Instagramdan video yoki rasmni eng sifatli holatda yuklash"""
    # Eski fayllarni tozalash
    for f in os.listdir(DOWNLOAD_DIR):
        try:
            os.remove(os.path.join(DOWNLOAD_DIR, f))
        except: pass

    ydl_opts = {
        'format': 'best',
        'outtmpl': f'{DOWNLOAD_DIR}/%(id)s.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info)

# --- ASOSIY HANDLERLAR ---

@dp.message(CommandStart())
async def start_command(message: types.Message):
    await users_table() # Bazani yaratish
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
                "📥 Instagramdan video yuklash uchun link yuboring yoki quyidagi tugmani bosing.")
        await message.answer(text, parse_mode="HTML")

@dp.message(F.text == "/vd_yuklash_boshlash")
async def vd_yukla_buyruq(message: types.Message, state: FSMContext):
    await state.set_state(VideoState.waiting_for_link)
    await message.answer("📥 Instagram Reels yoki Post linkini yuboring:")

# --- VIDEO YUKLASH LOGIKASI ---
@dp.message(F.text.contains("instagram.com"))
async def handle_instagram_link(message: types.Message):
    url = message.text
    status_msg = await message.answer("⌛ Video tahlil qilinmoqda...")

    try:
        # Instagram bloklamasligi uchun kichik pauza
        await asyncio.sleep(random.uniform(1, 2))
        
        loop = asyncio.get_event_loop()
        file_path = await loop.run_in_executor(None, download_media, url)

        if os.path.exists(file_path):
            file_input = FSInputFile(file_path)
            
            if file_path.lower().endswith(('.mp4', '.mkv', '.mov')):
                await message.answer_video(file_input, caption="✅ Video yuklandi!\n\n@my_codingbot")
            else:
                await message.answer_photo(file_input, caption="✅ Rasm yuklandi!\n\n@my_codingbot")
            
            os.remove(file_path) # Yuborgandan keyin faylni o'chiramiz
        else:
            await message.answer("⚠️ Fayl yuklanmadi, qaytadan urinib ko'ring.")
            
    except Exception as e:
        logging.error(f"Xato: {e}")
        await message.answer("❌ Xatolik yuz berdi. Profil yopiq bo'lishi mumkin.")
    
    finally:
        await status_msg.delete()

# --- ADMIN PANEL FUNKSIYALARI ---

@dp.message(F.text == "Userlarni PDF korsh 👥")
async def show_users(message: types.Message):
    if message.from_user.id in ADMIN_ID:
        pdf_file = create_user_pdf()
        await message.answer_document(FSInputFile(pdf_file), caption="📄 Foydalanuvchilar ro'yxati")

@dp.message(F.text == "Xabar yuborish 📨")
async def xabar_yuborish_boshlash(message: types.Message):
    if message.from_user.id in ADMIN_ID:
        await message.answer("📨 Xabar turini tanlang:", reply_markup=xabar_yubor())

@dp.callback_query(F.data == "img")
async def rasm_bosildi(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("🖼 Rasmni yuklang.")
    await state.set_state(SendImg.image)
    await callback.answer()

@dp.message(SendImg.image, F.photo)
async def rasm_qabul(message: types.Message, state: FSMContext):
    await state.update_data(photo=message.photo[-1].file_id)
    await message.answer("✏️ Rasm uchun matn kiriting")
    await state.set_state(SendImg.about)

@dp.message(SendImg.about)
async def caption_qabul(message: types.Message, state: FSMContext):
    await state.update_data(about=message.text)
    data = await state.get_data()
    await message.answer_photo(photo=data["photo"], caption=data["about"], parse_mode="HTML")
    await message.answer("📨 Yuborilsinmi?", reply_markup=send_confirmation_buttons())
    await state.set_state(SendImg.confirm)

@dp.message(SendImg.confirm, F.text == "Xa ✅")
async def yubor(message: types.Message, state: FSMContext):
    data = await state.get_data()
    users = get_all_users()
    count = 0
    for user in users:
        try:
            # user[3] odatda chat_id bo'ladi, bazangizga qarab tekshiring
            await bot.send_photo(chat_id=user[3], photo=data["photo"], caption=data["about"])
            count += 1
            await asyncio.sleep(0.05) # Telegram spam cheklovi uchun
        except:
            continue
    await message.answer(f"✅ {count} ta foydalanuvchiga yuborildi.", reply_markup=user_button())
    await state.clear()

@dp.message(SendImg.confirm, F.text == "Yo‘q ❌")
async def bekor(message: types.Message, state: FSMContext):
    await message.answer("❌ Bekor qilindi.", reply_markup=user_button())
    await state.clear()

# --- RUN BOT ---
async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot to'xtatildi")