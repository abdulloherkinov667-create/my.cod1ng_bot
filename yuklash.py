import asyncio
from email.mime import message
import logging
import os
import shutil
import uuid
import instaloader
from moviepy import VideoFileClip

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# Mavjud fayllar
from buttons.defould import start_button, user_button, send_confirmation_buttons
from create import insert_user, users_table, create_user_pdf, get_all_users, check_blocked_users
from buttons.inline import xabar_yubor
from stets import SendImg

from yt_dlp import YoutubeDL  
class InstagramStates(StatesGroup):
    waiting_for_reel = State()
    
    
dp = Dispatcher()


@dp.message(F.text == "🎬 Video yuklash")
async def start_video_download(message: types.Message, state: FSMContext):
    await state.set_state(InstagramStates.waiting_for_reel)
    await message.answer(
        "🎬 VIDEO YUKLASH MODEMI\n\n"
        "📎 Iltimos, Instagram video linkini yuboring.\n"
        "🔁 Bu holat to‘xtamaguncha video linklarni qabul qiladi.\n"
        "❌ Agar bekor qilmoqchi bo‘lsangiz /cancel buyrug‘ini bosing.\n\n"
        "⏳ Video avtomatik yuklab olinadi"
    )

@dp.message(InstagramStates.waiting_for_reel)
async def download_reel(message: types.Message, state: FSMContext):
    url = message.text.strip()

    if url == "🎬 Video yuklash":
        await message.answer("📌 Siz hozir video yuklash rejimidasiz. Iltimos, Instagram video linkini yuboring yoki /cancel buyrug‘ini bosing.")
        return

    main_keyboard_buttons = [
        "Userlarni PDF korsh 👥",
        "Userlarni soni 👥",
        "Xabar yuborish 📨",
        "👥 User soni ko‘rish"
    ]

    if url in main_keyboard_buttons:
        await state.clear()
        await message.answer("⚙️ Oldingi video yuklash rejimi bekor qilindi. Iltimos, yangi tugmani qayta bosing.")
        return

    if not (url.startswith("http://") or url.startswith("https://")):
        await message.answer("❌ Iltimos, amaldagi URL yuboring. Masalan: https://www.instagram.com/reel/...")
        return

    if "instagram.com" not in url:
        await message.answer("❌ Faqat Instagram manzilni qabul qilamiz (instagram.com).")
        return

    if not any(k in url for k in ["/reel/", "/p/", "/tv/", "/stories/"]):
        await message.answer("⚠️ Mumkin bo‘lgan Instagram video linkini yuboring (reel/p/tv).")
        return
    

    file_id = str(uuid.uuid4())
    filename = f"{file_id}.mp4"
    ydl_opts = {
        'outtmpl': filename,
        'format': 'mp4',
        'quiet': True,
        'noplaylist': True
    }

    try:
        await message.answer("⏳ Video yuklanmoqda...")
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        video = FSInputFile(filename)
        await message.answer_video(video)

    except Exception:
        await message.answer("⚠️ Video yuklab bo‘lmadi, boshqa link yuboring.")

    finally:
        if os.path.exists(filename):
            os.remove(filename)

@dp.message(F.text == "/cancel")
async def cancel_video_upload(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Video yuklash rejimi bekor qilindi. Qayta boshlash uchun 🎬 Video yuklash tugmasini bosib, link yuboring.")
