import asyncio
import logging
import os
import re
import shutil
import uuid
from moviepy import VideoFileClip
from yt_dlp import YoutubeDL
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import FSInputFile
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

# Tugmalar va database funksiyalari (Sizning fayllaringizdan)
from buttons.defould import start_button, user_button, send_confirmation_buttons
from create import insert_user, users_table, create_user_pdf, get_all_users, check_blocked_users
from buttons.inline import xabar_yubor
from stets import SendImg

API_TOKEN = "8301002449:AAFzKdU48I4Q0nuTxDnY9725MITFVA7w9ok"

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

ADMIN_ID = [6411347321, 8327989068]
INSTAGRAM_PATTERN = r'(https?://)?(www\.)?(instagram\.com|instagr\.am)/(p|reels|reel|tv)/[\w-]+'

class InstagramStates(StatesGroup):
    waiting_for_link = State()

def has_cookies():
    return os.path.exists("cookies.txt")

# Videoni qismlarga bo'lish funksiyasi
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
            part_video = video.subclipped(start_time, end_time)
            part_video.write_videofile(part_filename, codec='libx264', audio_codec='aac', logger=None)
            parts.append(part_filename)
        video.close()
        return parts
    except:
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
        await message.answer("👑 Admin panelga xush kelibsiz!", reply_markup=user_button())
    else:
        await message.answer("👋 Xush kelibsiz! Instagram link yuboring yoki menyudan foydalaning.", reply_markup=start_button())

@dp.message(F.text == "🎬 Video yuklash")
async def start_video_download(message: types.Message, state: FSMContext):
    await state.set_state(InstagramStates.waiting_for_link)
    await message.answer("📸 Instagram linkini yuboring:")

# Instagram linki kelganda (Xoh holatda bo'lsin, xoh menyudan kelgan bo'lsin)
@dp.message(F.text.regexp(INSTAGRAM_PATTERN))
async def handle_instagram_link(message: types.Message, state: FSMContext):
    url = message.text.strip()
    loading_msg = await message.answer("📥 Yuklanmoqda...")
    
    unique_id = str(uuid.uuid4())[:8]
    download_folder = f"downloads/{unique_id}"
    os.makedirs(download_folder, exist_ok=True)

    ydl_opts = {
        'format': 'best',
        'outtmpl': f'{download_folder}/video.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        'cookiefile': 'cookies.txt' if has_cookies() else None,
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = await asyncio.to_thread(ydl.extract_info, url, download=True)
            video_file = ydl.prepare_filename(info)

        if os.path.exists(video_file):
            file_size_mb = os.path.getsize(video_file) / (1024 * 1024)
            
            if file_size_mb <= 49:
                await message.answer_video(video=FSInputFile(video_file), caption="✅ Tayyor!")
            else:
                parts = split_video(video_file)
                for part in parts:
                    await message.answer_video(video=FSInputFile(part))
                    if part != video_file: os.remove(part)
            
            await loading_msg.delete()
    except:
        await loading_msg.edit_text("⚠️ Videoni yuklab bo'lmadi. Linkni tekshiring.")
    
    finally:
        shutil.rmtree(download_folder, ignore_errors=True)
        await state.clear()

# --- ADMIN QISMI (O'zgarishsiz) ---

@dp.message(F.text == "Userlarni PDF korsh 👥")
async def show_users(message: types.Message):
    if message.from_user.id in ADMIN_ID:
        await check_blocked_users(bot)
        pdf_file = create_user_pdf()
        await message.answer_document(FSInputFile(pdf_file), caption="👥 Foydalanuvchilar ro‘yxati")

@dp.message(F.text == "Xabar yuborish 📨")
async def xabar_yuborish_boshlash(message: types.Message):
    if message.from_user.id in ADMIN_ID:
        await message.answer("Xabar turini tanlang:", reply_markup=xabar_yubor())

@dp.callback_query(F.data == "img")
async def rasm_bosildi(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("📸 Rasm yuboring:")
    await state.set_state(SendImg.image)

@dp.message(SendImg.image, F.photo)
async def rasm_qabul(message: types.Message, state: FSMContext):
    await state.update_data(photo=message.photo[-1].file_id)
    await message.answer("📝 Izoh kiriting:")
    await state.set_state(SendImg.about)

@dp.message(SendImg.about)
async def caption_qabul(message: types.Message, state: FSMContext):
    await state.update_data(about=message.text)
    data = await state.get_data()
    await message.answer_photo(photo=data["photo"], caption=data["about"])
    await message.answer("📨 Yuborilsinmi?", reply_markup=send_confirmation_buttons())
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
    await message.answer(f"✅ {count} ta foydalanuvchiga yuborildi.", reply_markup=user_button())
    await state.clear()

@dp.message(SendImg.confirm, F.text == "Yo‘q ❌")
async def bekor(message: types.Message, state: FSMContext):
    await message.answer("❌ Bekor qilindi.", reply_markup=user_button())
    await state.clear()

async def main():
    logging.basicConfig(level=logging.INFO)
    os.makedirs("downloads", exist_ok=True)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())