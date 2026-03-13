import asyncio
import logging
import re
import os
import yt_dlp

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import FSInputFile
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.client.session.aiohttp import AiohttpSession

# Tugmalar va bazaga oid importlar (o'zgarishsiz qoldi)
from buttons.defould import user_button, yoq_button, send_confirmation_buttons
from create import insert_user, users_table, create_user_pdf, get_all_users
from buttons.inline import xabar_yubor, yuborilmasin_sorov
from stets import SendImg

# --- 1. SOZLAMALAR VA PROXY ---
# PythonAnywhere uchun proxy manzili
PROXY_URL = 'http://proxy.server:3128'
session = AiohttpSession(proxy=PROXY_URL)

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Admin va Token ma'lumotlari
ADMIN_ID = [6411347321]
API_TOKEN = "8301002449:AAHoIQ5PFqLzG1qU-ctYab1QZFZptI6Y8dw"

bot = Bot(token=API_TOKEN, session=session)
dp = Dispatcher()

# --- 2. HOLATLAR (STATES) ---
class VideoState(StatesGroup):
    waiting_for_link = State()

# --- 3. START VA ASOSIY BUYRUQLAR ---
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
        text = (
            f"🌟 <b>Assalomu alaykum, Hurmatli Admin!</b>\n\n"
            f"👤 <b>Foydalanuvchi:</b> {message.from_user.first_name}\n"
            f"🛠 <b>Status:</b> Administrator\n\n"
            f"Pastdagi tugmalar orqali botni boshqarishingiz mumkin 👇"
        )
        await message.answer(text, reply_markup=user_button(), parse_mode="HTML")
    else:
        text = (
            "👋 <b>Assalomu alaykum! Bizning botga xush kelibsiz!</b>\n\n"
            "🎬 Men Instagram tarmog'idan videolarni yuklab beraman.\n\n"
            "🚀 Boshlash uchun 📥 <b>/vd_yuklash_boshlash</b> buyrug'ini bosing."
        )
        await message.answer(text, parse_mode="HTML")

@dp.message(lambda m: m.text == "/vd_yuklash_boshlash")
async def vd_yukla_buyruq(message: types.Message, state: FSMContext):
    await state.set_state(VideoState.waiting_for_link)
    await message.answer("🔗 <b>Iltimos, Instagram video linkini yuboring:</b>\n\n<i>(Masalan: https://www.instagram.com/p/...)</i>", parse_mode="HTML")

# --- 4. VIDEO YUKLASH QISMI (ENG MUHIM JOYI) ---
@dp.message(VideoState.waiting_for_link)
async def vd_yuklash(message: types.Message, state: FSMContext):
    url = message.text
    if "instagram.com" not in url:
        await message.answer("⚠️ <b>Xato!</b> Bu Instagram linki emas. Iltimos, qaytadan tekshirib yuboring.")
        return

    status_msg = await message.answer("⏳ <b>Iltimos, biroz kuting...</b>\n🎬 Video qayta ishlanmoqda va yuklanmoqda...")
    
    # PythonAnywhere'da ishlashi uchun yt_dlp ga ham proxy beramiz
    ydl_opts = {
        'format': 'best',
        'outtmpl': f'{DOWNLOAD_DIR}/%(id)s.%(ext)s',
        'merge_output_format': 'mp4',
        'quiet': True,
        'no_warnings': True,
        'proxy': PROXY_URL,  # MUHIM: yt_dlp ham proxy orqali chiqishi kerak
        'add_header': [
            ('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
        ] # Instagram bloklab qo'ymasligi uchun "User-Agent" qo'shildi
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Ma'lumotni yuklash
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)
            
            # Agar format mp4 bo'lmasa, mp4 qilib belgilaymiz
            if not file_path.endswith(".mp4"):
                file_path = file_path.rsplit('.', 1)[0] + ".mp4"

            # Videoni foydalanuvchiga yuborish
            video_file = FSInputFile(file_path)
            await message.answer_video(
                video_file, 
                caption="✅ <b>Video muvaffaqiyatli yuklab olindi!</b>\n\n🚀 @my_codingbot orqali yuklandi",
                parse_mode="HTML"
            )
            
            # Yuklab bo'lingach, serverda joy egallamasligi uchun o'chiramiz
            if os.path.exists(file_path):
                os.remove(file_path)

    except Exception as e:
        logging.error(f"Xatolik yuz berdi: {e}")
        await message.answer("❌ <b>Kechirasiz, xatolik yuz berdi!</b>\n\nSababi: Video yopiq profildan bo'lishi yoki Instagram bizni bloklagan bo'lishi mumkin.")
    
    finally:
        await status_msg.delete()
        await state.clear()

# --- 5. ADMIN PANEL VA XABAR YUBORISH (O'zgarishsiz qoldi) ---
@dp.message(F.text == "Userlarni PDF korsh 👥")
async def show_users(message: types.Message):
    if message.from_user.id in ADMIN_ID:
        pdf_file = create_user_pdf()
        await message.answer_document(FSInputFile(pdf_file), caption="📄 <b>Barcha foydalanuvchilar ro'yxati (PDF)</b>", parse_mode="HTML")

@dp.message(F.text == "Xabar yuborish 📨")
async def xabar_yuborish_boshlash(message: types.Message):
    await message.answer("📨 <b>Xabar turini tanlang:</b>", reply_markup=xabar_yubor(), parse_mode="HTML")

@dp.callback_query(F.data == "img")
async def rasm_bosildi(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("🖼 <b>Xabar uchun rasm yuklang:</b>", parse_mode="HTML")
    await state.set_state(SendImg.image)
    await callback.answer()

@dp.message(SendImg.image, F.photo)
async def rasm_qabul(message: types.Message, state: FSMContext):
    await state.update_data(photo=message.photo[-1].file_id)
    await message.answer("✏️ <b>Rasm osti matnini (caption) kiriting:</b>", parse_mode="HTML")
    await state.set_state(SendImg.about)

@dp.message(SendImg.about)
async def caption_qabul(message: types.Message, state: FSMContext):
    await state.update_data(about=message.text)
    data = await state.get_data()
    await message.answer_photo(photo=data["photo"], caption=data["about"], parse_mode="HTML")
    await message.answer("📨 <b>Ushbu xabar hamma foydalanuvchilarga yuborilsinmi?</b>", reply_markup=send_confirmation_buttons(), parse_mode="HTML")
    await state.set_state(SendImg.confirm)

@dp.message(SendImg.confirm, F.text == "Xa ✅")
async def yubor(message: types.Message, state: FSMContext):
    data = await state.get_data()
    users = get_all_users()
    count = 0
    for user in users:
        try:
            await bot.send_photo(chat_id=user[3], photo=data["photo"], caption=data["about"])
            count += 1
        except: continue
    await message.answer(f"✅ <b>Xabar {count} ta foydalanuvchiga yuborildi!</b>", reply_markup=types.ReplyKeyboardRemove(), parse_mode="HTML")
    await state.clear()

@dp.message(SendImg.confirm, F.text == "Yo‘q ❌")
async def bekor(message: types.Message, state: FSMContext):
    await message.answer("❌ <b>Xabar yuborish bekor qilindi.</b>", reply_markup=types.ReplyKeyboardRemove(), parse_mode="HTML")
    await state.clear()

# --- 6. ASOSIY ISHGA TUSHIRISH ---
async def main():
    logging.basicConfig(level=logging.INFO)
    print("Bot ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())