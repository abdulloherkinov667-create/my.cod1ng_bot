import asyncio
import logging
import os
import shutil
import uuid
import time
import sqlite3
from datetime import datetime
from typing import Optional

import instaloader
from moviepy import VideoFileClip
from yt_dlp import YoutubeDL

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

# Sizning fayllaringizdan import
from buttons.defould import start_button, user_button, send_confirmation_buttons
from create import insert_user, users_table, create_user_pdf, get_all_users, check_blocked_users
from buttons.inline import xabar_yubor
from stets import SendImg

API_TOKEN = "8301002449:AAFzKdU48I4Q0nuTxDnY9725MITFVA7w9ok"

# Bot va dispatcher
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

ADMIN_ID = [8327989068]

# Cookies fayli (agar kerak bo'lsa)
COOKIES_FILE = "cookies.txt"

# Yuklab olish papkasi
DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)


# ===================== STATES =====================
class InstagramStates(StatesGroup):
    waiting_for_link = State()


# ===================== YORDAMCHI FUNKSIYALAR =====================
def has_cookies():
    """Cookies fayli mavjudligini tekshirish"""
    return os.path.exists(COOKIES_FILE)


def split_video(file_path, max_size_mb=49):
    """Videoni qismlarga bo'lish"""
    parts = []
    try:
        video = VideoFileClip(file_path)
        duration = video.duration
        video.close()
        
        # Har bir qism uchun vaqtni hisoblash
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        num_parts = int(file_size_mb / max_size_mb) + 1
        part_duration = duration / num_parts
        
        for i in range(num_parts):
            start_time = i * part_duration
            end_time = (i + 1) * part_duration if i < num_parts - 1 else duration
            
            part_file = f"{file_path}_part{i+1}.mp4"
            
            video = VideoFileClip(file_path)
            subclip = video.subclipped(start_time, end_time)
            subclip.write_videofile(part_file, logger=None)
            subclip.close()
            video.close()
            
            parts.append(part_file)
            
        return parts
    except Exception as e:
        return [file_path]


def cleanup_old_files():
    """Eski yuklab olingan fayllarni tozalash (10 daqiqadan eski)"""
    try:
        now = time.time()
        for folder in os.listdir(DOWNLOAD_FOLDER):
            folder_path = os.path.join(DOWNLOAD_FOLDER, folder)
            if os.path.isdir(folder_path):
                if now - os.path.getctime(folder_path) > 600:  # 10 daqiqa
                    shutil.rmtree(folder_path, ignore_errors=True)
    except Exception:
        pass


# ===================== BOT KOMANDALARI =====================
@dp.message(CommandStart())
async def start_command(message: types.Message):
    await users_table()
    insert_user(
        first_name=message.from_user.first_name,
        username=message.from_user.username,
        language_code=message.from_user.language_code,
        is_bot=message.from_user.is_bot,
        chat_id=message.chat.id,
        created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )

    if message.from_user.id in ADMIN_ID:
        text = (
            f"👑 <b>Admin paneliga xush kelibsiz!</b>\n\n"
            f"Salom, <b>{message.from_user.first_name}</b>.\n\n"
            "🧰 Paneldan kerakli bo'limni tanlang."
        )
        await message.answer(text, reply_markup=user_button(), parse_mode="HTML")
    else:
        text = """
👋 Botga xush kelibsiz!

😊 Botdan foydalanishni boshlash uchun pastda joylashgan tugmalardan birini tanlang.

👇 Davom etish uchun pastdagi tugmani bosing.

✨ Shundan so‘ng sizga keyingi qadamlar ko‘rsatib beriladi.
        """
        await message.answer(text, parse_mode="HTML", reply_markup=start_button())


# ===================== VIDEO YUKLASH =====================
@dp.message(F.text == "🎬 Video yuklash")
async def start_video_download(message: types.Message, state: FSMContext):
    await state.set_state(InstagramStates.waiting_for_link)
    await message.answer("📸 Instagram video yoki reel linkini yuboring:")


@dp.message(InstagramStates.waiting_for_link)
async def download_instagram_video(message: types.Message, state: FSMContext):
    url = message.text.strip()
    
    # URL validatsiyasi
    if "instagram.com" not in url and "instagr.am" not in url:
        await message.answer("❌ Bu Instagram linki emas!")
        await state.clear()
        return

    loading_msg = await message.answer("📥 Yuklanmoqda...")
    unique_id = str(uuid.uuid4())[:8]
    download_folder = f"{DOWNLOAD_FOLDER}/{unique_id}"
    os.makedirs(download_folder, exist_ok=True)

    ydl_opts = {
        'format': 'best',
        'outtmpl': f'{download_folder}/video.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }
    
    if has_cookies():
        ydl_opts['cookiefile'] = COOKIES_FILE

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = await asyncio.to_thread(ydl.extract_info, url, download=True)
            filename = ydl.prepare_filename(info)

        if os.path.exists(filename):
            file_size_mb = os.path.getsize(filename) / (1024 * 1024)
            
            # Audio olish uchun inline keyboard
            markup = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🎵 Audio (MP3)", callback_data=f"audio_{unique_id}")]
            ])

            if file_size_mb <= 49:
                video_file = FSInputFile(filename)
                await message.answer_video(
                    video=video_file, 
                    caption=f"✅ Video tayyor!",
                    reply_markup=markup
                )
            else:
                await message.answer("⚠️ Video katta, qismlarga bo'linmoqda...")
                parts = split_video(filename)
                for i, p in enumerate(parts):
                    await message.answer_video(video=FSInputFile(p))
                    if p != filename:
                        os.remove(p)
            
            await loading_msg.delete()
            
            # Faylni keyinroq o'chirish uchun timer
            async def delayed_cleanup():
                await asyncio.sleep(600)  # 10 daqiqa
                if os.path.exists(download_folder):
                    shutil.rmtree(download_folder, ignore_errors=True)
            
            asyncio.create_task(delayed_cleanup())
            
        else:
            await loading_msg.edit_text("❌ Video topilmadi!")
            if os.path.exists(download_folder):
                shutil.rmtree(download_folder, ignore_errors=True)

    except Exception as e:
        logging.error(f"Video yuklash xatoligi: {e}")
        await loading_msg.edit_text("❌ Xatolik yuz berdi!")
        if os.path.exists(download_folder):
            shutil.rmtree(download_folder, ignore_errors=True)
    
    await state.clear()


# ===================== AUDIO OLISH =====================
@dp.callback_query(lambda c: c.data and c.data.startswith("audio_"))
async def get_audio(callback: types.CallbackQuery):
    unique_id = callback.data.split("_")[1]
    download_folder = f"{DOWNLOAD_FOLDER}/{unique_id}"
    
    loading_msg = await callback.message.answer("🎵 Audio yuklanmoqda...")
    
    try:
        # Video faylni topish
        video_file = None
        if os.path.exists(download_folder):
            for file in os.listdir(download_folder):
                if file.endswith(('.mp4', '.mkv', '.avi', '.mov')):
                    video_file = os.path.join(download_folder, file)
                    break
        
        if video_file and os.path.exists(video_file):
            # Videodan audio ajratish
            video = VideoFileClip(video_file)
            audio = video.audio
            
            if audio is not None:
                audio_name = f"{download_folder}/audio_{unique_id}.mp3"
                audio.write_audiofile(audio_name, logger=None)
                video.close()
                
                # Audioni yuborish
                audio_file = FSInputFile(audio_name)
                await callback.message.answer_audio(
                    audio=audio_file,
                    caption="🎵 Audio tayyor!"
                )
                
                await loading_msg.delete()
                await callback.answer("✅ Audio tayyor!")
            else:
                await loading_msg.edit_text("❌ Bu videoda audio yo'q!")
                await callback.answer("Audio topilmadi")
        else:
            await loading_msg.edit_text("❌ Video fayl topilmadi!")
            await callback.answer("Xatolik yuz berdi")
            
    except Exception as e:
        logging.error(f"Audio yuklash xatoligi: {e}")
        await loading_msg.edit_text("❌ Xatolik yuz berdi!")
        await callback.answer("Xatolik yuz berdi")


# ===================== ADMIN: USERLARNI PDF KO'RISH =====================
@dp.message(F.text == "Userlarni PDF korsh 👥")
async def show_users_pdf(message: types.Message):
    if message.from_user.id not in ADMIN_ID:
        await message.answer("⛔ Bu buyruq faqat adminlar uchun!")
        return
    
    loading_msg = await message.answer("⏳ PDF tayyorlanmoqda...")
    try:
        # Bloklangan userlarni tekshirish
        await check_blocked_users(bot)
        
        # PDF yaratish
        pdf_file = create_user_pdf()
        
        # PDFni yuborish
        await message.answer_document(
            FSInputFile(pdf_file), 
            caption=f"👥 Foydalanuvchilar ro'yxati\n\n📊 Jami: {get_users_count()} ta foydalanuvchi"
        )
        
        # PDF faylni o'chirish
        os.remove(pdf_file)
        
    except Exception as e:
        logging.error(f"PDF yaratish xatoligi: {e}")
        await message.answer("❌ Xatolik yuz berdi!")
    finally:
        await loading_msg.delete()


# ===================== ADMIN: USERLARNI SONI =====================
@dp.message(F.text == "Userlarni soni 👥")
async def show_users_count(message: types.Message):
    if message.from_user.id not in ADMIN_ID:
        await message.answer("⛔ Bu buyruq faqat adminlar uchun!")
        return
    
    try:
        count = get_users_count()
        blocked_count = len([u for u in get_all_users() if u[5] == 1])
        
        text = f"""
👥 <b>Foydalanuvchilar statistikasi</b>

📊 <b>Jami foydalanuvchilar:</b> <code>{count}</code>
🚫 <b>Bloklanganlar:</b> <code>{blocked_count}</code>
✅ <b>Faollar:</b> <code>{count - blocked_count}</code>
        """
        await message.answer(text, parse_mode="HTML")
    except Exception as e:
        logging.error(f"Userlar sonini olish xatoligi: {e}")
        await message.answer("❌ Xatolik yuz berdi!")


# ===================== ADMIN: XABAR YUBORISH =====================
@dp.message(F.text == "Xabar yuborish 📨")
async def xabar_yuborish_boshlash(message: types.Message):
    if message.from_user.id not in ADMIN_ID:
        await message.answer("⛔ Bu buyruq faqat adminlar uchun!")
        return
    
    await message.answer("""
📢 Xabar yuborish bo‘limi

✉️ Foydalanuvchilarga yuboriladigan xabar turini tanlang.

👇 Davom etish uchun xabar turini tanlang.
    """, reply_markup=xabar_yubor())


@dp.callback_query(F.data == "img")
async def rasm_bosildi(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("""
🖼 Rasm yuborish

📸 Iltimos, foydalanuvchilarga yubormoqchi bo‘lgan rasmingizni yuboring.

✏️ Rasm bilan birga izoh (caption) ham qo‘shishingiz mumkin.

👇 Endi rasmni yuboring.
    """)
    await state.set_state(SendImg.image)
    await callback.answer()


@dp.message(SendImg.image, F.photo)
async def rasm_qabul(message: types.Message, state: FSMContext):
    await state.update_data(photo=message.photo[-1].file_id)
    await message.answer("""
✏️ Rasm uchun izoh qo‘shish

📝 Endi yuborilgan rasm uchun matn (caption) kiriting.
    """)
    await state.set_state(SendImg.about)


@dp.message(SendImg.about, F.text)
async def caption_qabul(message: types.Message, state: FSMContext):
    await state.update_data(about=message.text)
    data = await state.get_data()
    await message.answer_photo(
        photo=data["photo"], 
        caption=data["about"], 
        parse_mode="HTML"
    )
    await message.answer("📨 Yuborilsinmi?", reply_markup=send_confirmation_buttons())
    await state.set_state(SendImg.confirm)


@dp.message(SendImg.confirm, F.text == "Xa ✅")
async def yubor(message: types.Message, state: FSMContext):
    data = await state.get_data()
    users = get_all_users()
    count = 0
    
    loading_msg = await message.answer("⏳ Xabarlar yuborilmoqda...")
    
    for user in users:
        try:
            await bot.send_photo(
                chat_id=user[3],
                photo=data["photo"], 
                caption=data["about"]
            )
            count += 1
            await asyncio.sleep(0.1)
        except Exception:
            continue
    
    await loading_msg.delete()
    await message.answer(f"✅ {count} ta foydalanuvchiga yuborildi.", reply_markup=types.ReplyKeyboardRemove())
    await state.clear()


@dp.message(SendImg.confirm, F.text == "Yo‘q ❌")
async def bekor(message: types.Message, state: FSMContext):
    await message.answer("❌ Bekor qilindi.", reply_markup=types.ReplyKeyboardRemove())
    await state.clear()


@dp.callback_query(F.data == "text")
async def text_xabar_boshlash(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("📝 Yubormoqchi bo'lgan matningizni yozing:")
    await state.set_state(SendImg.text_message)
    await callback.answer()


@dp.message(SendImg.text_message, F.text)
async def text_xabar_qabul(message: types.Message, state: FSMContext):
    await state.update_data(text_message=message.text)
    await message.answer(f"📨 Yuboriladigan matn:\n\n{message.text}\n\nYuborilsinmi?", 
                        reply_markup=send_confirmation_buttons())
    await state.set_state(SendImg.confirm_text)


@dp.message(SendImg.confirm_text, F.text == "Xa ✅")
async def text_xabar_yubor(message: types.Message, state: FSMContext):
    data = await state.get_data()
    users = get_all_users()
    count = 0
    
    loading_msg = await message.answer("⏳ Xabarlar yuborilmoqda...")
    
    for user in users:
        try:
            await bot.send_message(
                chat_id=user[3],
                text=data["text_message"]
            )
            count += 1
            await asyncio.sleep(0.1)
        except Exception:
            continue
    
    await loading_msg.delete()
    await message.answer(f"✅ {count} ta foydalanuvchiga yuborildi.", reply_markup=types.ReplyKeyboardRemove())
    await state.clear()


@dp.message(SendImg.confirm_text, F.text == "Yo‘q ❌")
async def text_xabar_bekor(message: types.Message, state: FSMContext):
    await message.answer("❌ Bekor qilindi.", reply_markup=types.ReplyKeyboardRemove())
    await state.clear()


@dp.callback_query(F.data == "video")
async def video_xabar_boshlash(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("🎬 Yubormoqchi bo'lgan videongizni yuboring:")
    await state.set_state(SendImg.video_message)
    await callback.answer()


@dp.message(SendImg.video_message, F.video)
async def video_xabar_qabul(message: types.Message, state: FSMContext):
    await state.update_data(video=message.video.file_id, caption=message.caption or "")
    await message.answer(f"📨 Yuboriladigan video\n\nYuborilsinmi?", 
                        reply_markup=send_confirmation_buttons())
    await state.set_state(SendImg.confirm_video)


@dp.message(SendImg.confirm_video, F.text == "Xa ✅")
async def video_xabar_yubor(message: types.Message, state: FSMContext):
    data = await state.get_data()
    users = get_all_users()
    count = 0
    
    loading_msg = await message.answer("⏳ Xabarlar yuborilmoqda...")
    
    for user in users:
        try:
            await bot.send_video(
                chat_id=user[3],
                video=data["video"],
                caption=data.get("caption", "")
            )
            count += 1
            await asyncio.sleep(0.1)
        except Exception:
            continue
    
    await loading_msg.delete()
    await message.answer(f"✅ {count} ta foydalanuvchiga yuborildi.", reply_markup=types.ReplyKeyboardRemove())
    await state.clear()


@dp.message(SendImg.confirm_video, F.text == "Yo‘q ❌")
async def video_xabar_bekor(message: types.Message, state: FSMContext):
    await message.answer("❌ Bekor qilindi.", reply_markup=types.ReplyKeyboardRemove())
    await state.clear()


# ===================== XATOLIKLARNI USHLASH =====================
@dp.errors()
async def errors_handler(update: types.Update, exception: Exception):
    logging.error(f"Xatolik: {exception}")
    return True


# ===================== BOTNI ISHGA TUSHIRISH =====================
async def main():
    logging.basicConfig(level=logging.INFO)
    
    # Eski fayllarni tozalash
    cleanup_old_files()
    
    try:
        await bot.delete_webhook(drop_pending_updates=True)
    except Exception:
        pass
    
    print("🤖 Bot ishga tushdi...")
    print("👑 Admin ID lar:", ADMIN_ID)
    print("-" * 50)
    
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())