import asyncio
import logging
import os
import re
import shutil
import uuid
from datetime import datetime
from moviepy import VideoFileClip
from yt_dlp import YoutubeDL
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import FSInputFile, BufferedInputFile
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

# O'zingizning fayllaringizdan importlar
from buttons.defould import start_button, user_button, send_confirmation_buttons
from create import insert_user, users_table, create_user_pdf, get_all_users, check_blocked_users
from buttons.inline import xabar_yubor
from stets import SendImg

API_TOKEN = "8301002449:AAFzKdU48I4Q0nuTxDnY9725MITFVA7w9ok"

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

ADMIN_ID = [6411347321, 8327989068]

class InstagramStates(StatesGroup):
    waiting_for_link = State()

COOKIES_FILE = "cookies.txt"

def has_cookies():
    return os.path.exists(COOKIES_FILE)

# --- VIDEO SPLIT FUNKSIYASI ---
def split_video(video_path, max_size_mb=45):
    file_size = os.path.getsize(video_path) / (1024 * 1024)
    if file_size <= max_size_mb:
        return [video_path]
    
    parts = []
    try:
        video = VideoFileClip(video_path)
        duration = video.duration
        num_parts = int(file_size / max_size_mb) + 1
        part_duration = duration / num_parts
        
        for i in range(num_parts):
            start_time = i * part_duration
            end_time = min((i + 1) * part_duration, duration)
            part_filename = f"{video_path}_part{i+1}.mp4"
            
            # Subclip va yozish
            part_video = video.subclipped(start_time, end_time)
            part_video.write_videofile(part_filename, codec='libx264', audio_codec='aac', logger=None)
            part_video.close()
            parts.append(part_filename)
        
        video.close()
        return parts
    except Exception as e:
        logging.error(f"Split xatolik: {e}")
        return [video_path]

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
        await message.answer(f"👑 Admin panelga xush kelibsiz, {message.from_user.first_name}!", reply_markup=user_button())
    else:
        await message.answer("👋 Botga xush kelibsiz! Video yuklash uchun tugmani bosing.", reply_markup=start_button())


@dp.message(F.text == "🎬 Video yuklash")
async def start_video_download(message: types.Message, state: FSMContext):
    await state.set_state(InstagramStates.waiting_for_link)
    await message.answer("📸 Instagram video yoki reel linkini yuboring:")


@dp.message(InstagramStates.waiting_for_link)
async def download_instagram_video(message: types.Message, state: FSMContext):
    url = message.text.strip()

    if "instagram.com" not in url and "instagr.am" not in url:
        await message.answer("❌ Bu Instagram linki emas!")
        return

    loading_msg = await message.answer("📥 Yuklanmoqda... (Instagram biroz vaqt olishi mumkin)")

    unique_id = str(uuid.uuid4())[:8]
    download_folder = f"downloads/{unique_id}"
    os.makedirs(download_folder, exist_ok=True)

    ydl_opts = {
        'format': 'best',
        'outtmpl': f'{download_folder}/%(title)s.%(ext)s',  # 🔥 FIX
        'quiet': True,
        'no_warnings': True,
        'retries': 10,
        'user_agent': 'Mozilla/5.0',
    }

    if has_cookies():
        ydl_opts['cookiefile'] = COOKIES_FILE

    try:
        # 🔥 ENG ASOSIY FIX (extract_info o‘rniga download)
        with YoutubeDL(ydl_opts) as ydl:
            await asyncio.to_thread(ydl.download, [url])

        # 🔥 FILE TOPISH (MUHIM)
        files = os.listdir(download_folder)
        video_file = None

        for f in files:
            if f.endswith(('.mp4', '.mkv', '.webm', '.mov')):
                video_file = os.path.join(download_folder, f)
                break

        if video_file and os.path.exists(video_file):
            file_size_mb = os.path.getsize(video_file) / (1024 * 1024)

            markup = types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="🎵 Audio (MP3)", callback_data=f"audio_{unique_id}")]
            ])

            if file_size_mb <= 49:
                await message.answer_video(
                    video=FSInputFile(video_file),
                    caption=f"✅ Yuklandi! @{bot.username}",
                    reply_markup=markup
                )
            else:
                await message.answer("⚠️ Video katta, qismlarga bo'linmoqda...")

                parts = split_video(video_file)
                for p in parts:
                    await message.answer_video(video=FSInputFile(p))
                    if p != video_file:
                        os.remove(p)

            await loading_msg.delete()

        else:
            await loading_msg.edit_text("❌ Video yuklab bo'lmadi.")

    except Exception as e:
        logging.error(f"Xatolik: {e}")
        await loading_msg.edit_text(f"❌ Xatolik: {str(e)[:100]}")

    await state.clear()

# --- ADMIN FUNKSIYALARI ---

@dp.message(F.text == "Userlarni PDF korsh 👥")
async def show_users(message: types.Message):
    if message.from_user.id in ADMIN_ID:
        wait = await message.answer("⏳ Tayyorlanmoqda...")
        await check_blocked_users(bot)
        pdf_path = create_user_pdf()
        await message.answer_document(FSInputFile(pdf_path), caption="👥 Foydalanuvchilar ro'yxati")
        await wait.delete()

@dp.message(F.text == "Xabar yuborish 📨")
async def xabar_yuborish_boshlash(message: types.Message):
    if message.from_user.id in ADMIN_ID:
        await message.answer("Xabar turini tanlang:", reply_markup=xabar_yubor())

@dp.callback_query(F.data == "img")
async def rasm_bosildi(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("🖼 Rasmni yuboring:")
    await state.set_state(SendImg.image)

@dp.message(SendImg.image, F.photo)
async def rasm_qabul(message: types.Message, state: FSMContext):
    await state.update_data(photo=message.photo[-1].file_id)
    await message.answer("📝 Rasm uchun matn kiriting:")
    await state.set_state(SendImg.about)

@dp.message(SendImg.about)
async def caption_qabul(message: types.Message, state: FSMContext):
    await state.update_data(about=message.text)
    data = await state.get_data()
    await message.answer_photo(photo=data["photo"], caption=data["about"])
    await message.answer("📨 Barchaga yuborilsinmi?", reply_markup=send_confirmation_buttons())
    await state.set_state(SendImg.confirm)

@dp.message(SendImg.confirm, F.text == "Xa ✅")
async def yubor(message: types.Message, state: FSMContext):
    data = await state.get_data()
    users = get_all_users()
    s_count, f_count = 0, 0
    
    msg = await message.answer("🚀 Yuborilmoqda...")
    for user in users:
        try:
            await bot.send_photo(chat_id=user[3], photo=data["photo"], caption=data["about"])
            s_count += 1
            await asyncio.sleep(0.05) # Spam blokdan qochish
        except:
            f_count += 1
            
    await msg.edit_text(f"✅ Tugadi.\nMuvaffaqiyatli: {s_count}\nO'chib ketgan: {f_count}", reply_markup=user_button())
    await state.clear()

@dp.message(SendImg.confirm, F.text == "Yo‘q ❌")
async def bekor(message: types.Message, state: FSMContext):
    await message.answer("❌ Bekor qilindi.", reply_markup=user_button())
    await state.clear()

# --- BOTNI ISHGA TUSHIRISH ---
async def main():
    logging.basicConfig(level=logging.INFO)
    if not os.path.exists("downloads"):
        os.makedirs("downloads")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot to'xtatildi")