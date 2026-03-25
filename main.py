import asyncio
import logging
import os
import shutil
import uuid
from moviepy import VideoFileClip
from yt_dlp import YoutubeDL
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import FSInputFile
from aiogram.fsm.context import FSMContext

# Sizning tugmalaringiz va bazangiz (create.py va boshqalar bor deb hisoblaymiz)
from buttons.defould import start_button, user_button, send_confirmation_buttons
from create import insert_user, users_table, create_user_pdf, get_all_users, check_blocked_users
from buttons.inline import xabar_yubor
from stets import SendImg

API_TOKEN = "8301002449:AAFzKdU48I4Q0nuTxDnY9725MITFVA7w9ok"

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

ADMIN_ID = [6411347321, 8327989068]

# Instagram linkini aniqlash uchun regex
INSTAGRAM_URL_PATTERN = r'(https?://(?:www\.)?instagram\.com/(?:p|reel|reels|tv)/[\w-]+)'

@dp.message(CommandStart())
async def start_command(message: types.Message):
    await users_table()
    insert_user(
        first_name=message.from_user.first_name,
        username=message.from_user.username,
        language_code=message.from_user.language_code,
        is_bot=message.from_user.is_bot,
        chat_id=message.chat.id,
        created_at=message.date,
    )
    if message.from_user.id in ADMIN_ID:
        await message.answer("👑 Admin panelga xush kelibsiz!", reply_markup=user_button())
    else:
        await message.answer("👋 Xush kelibsiz! Instagram linkini yuboring, men yuklab beraman.", reply_markup=start_button())

# ASOSIY FUNKSIYA: Link kelishi bilan ishlaydi
@dp.message(F.text.regexp(INSTAGRAM_URL_PATTERN))
async def auto_download_instagram(message: types.Message):
    url = message.text.strip()
    status_msg = await message.answer("⏳ Video tahlil qilinmoqda...")
    
    unique_id = str(uuid.uuid4())[:8]
    folder = f"downloads/{unique_id}"
    os.makedirs(folder, exist_ok=True)
    
    # Instagram bloklarini aylanib o'tish uchun maxsus sozlamalar
    ydl_opts = {
        'format': 'best',
        'outtmpl': f'{folder}/%(title)s.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.instagram.com/',
        },
        'nocheckcertificate': True,
        'ignoreerrors': False,
        'geo_bypass': True,
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            # Video ma'lumotlarini olish va yuklash
            info = await asyncio.to_thread(ydl.extract_info, url, download=True)
            video_path = ydl.prepare_filename(info)
            
            if os.path.exists(video_path):
                await status_msg.edit_text("📤 Video botga yuklanmoqda...")
                await message.answer_video(
                    video=FSInputFile(video_path),
                    caption=f"✅ Muvaffaqiyatli yuklandi!\n\n🔗 @{(await bot.get_me()).username}"
                )
                await status_msg.delete()
            else:
                raise Exception("Fayl topilmadi")

    except Exception as e:
        logging.error(f"Xatolik: {e}")
        await status_msg.edit_text("❌ Kechirasiz, videoni yuklab bo'lmadi.\nBu profil yopiq yoki link noto'g'ri bo'lishi mumkin.")
    
    finally:
        # Tozalash
        if os.path.exists(folder):
            shutil.rmtree(folder)

# --- ADMIN FUNKSIYALARI (Teginilmadi) ---

@dp.message(F.text == "Userlarni PDF korsh 👥")
async def show_users(message: types.Message):
    if message.from_user.id in ADMIN_ID:
        await check_blocked_users(bot)
        pdf_file = create_user_pdf()
        await message.answer_document(FSInputFile(pdf_file), caption="👥 Foydalanuvchilar ro‘yxati")

@dp.message(F.text == "Xabar yuborish 📨")
async def xabar_yuborish_boshlash(message: types.Message):
    await message.answer("📢 Xabar turini tanlang.", reply_markup=xabar_yubor())

@dp.callback_query(F.data == "img")
async def rasm_bosildi(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("🖼 Rasmni yuboring.")
    await state.set_state(SendImg.image)

@dp.message(SendImg.image, F.photo)
async def rasm_qabul(message: types.Message, state: FSMContext):
    await state.update_data(photo=message.photo[-1].file_id)
    await message.answer("📝 Izoh (caption) kiriting:")
    await state.set_state(SendImg.about)

@dp.message(SendImg.about)
async def caption_qabul(message: types.Message, state: FSMContext):
    await state.update_data(about=message.text)
    data = await state.get_data()
    await message.answer_photo(photo=data["photo"], caption=data["about"])
    await message.answer("📨 Barcha userlarga yuborilsinmi?", reply_markup=send_confirmation_buttons())
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
    await message.answer(f"✅ {count} ta foydalanuvchiga yuborildi.")
    await state.clear()

@dp.message(SendImg.confirm, F.text == "Yo‘q ❌")
async def bekor(message: types.Message, state: FSMContext):
    await message.answer("❌ Bekor qilindi.")
    await state.clear()

async def main():
    logging.basicConfig(level=logging.INFO)
    os.makedirs("downloads", exist_ok=True)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())