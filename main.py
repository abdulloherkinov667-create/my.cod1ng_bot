import asyncio
import logging
import os
import re
import shutil
import uuid
import json
from datetime import datetime
from moviepy import VideoFileClip
from yt_dlp import YoutubeDL
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import FSInputFile
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.client.session.aiohttp import AiohttpSession

from buttons.defould import start_button, user_button, send_confirmation_buttons
from create import insert_user, users_table, create_user_pdf, get_all_users, check_blocked_users
from buttons.inline import xabar_yubor
from stets import SendImg

API_TOKEN = "8301002449:AAFzKdU48I4Q0nuTxDnY9725MITFVA7w9ok"

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

ADMIN_ID = [6411347321, 8327989068]

# FSM states for Instagram download
class InstagramStates(StatesGroup):
    waiting_for_link = State()

# Cookies file path (create cookies.txt from browser)
COOKIES_FILE = "cookies.txt"

# Function to check if cookies file exists
def has_cookies():
    return os.path.exists(COOKIES_FILE)

# Function to split video into parts
def split_video(video_path, max_size_mb=49):
    """Split video into parts smaller than max_size_mb"""
    file_size = os.path.getsize(video_path) / (1024 * 1024)
    if file_size <= max_size_mb:
        return [video_path]
    
    # Calculate number of parts needed
    num_parts = int(file_size / max_size_mb) + 1
    parts = []
    
    try:
        video = VideoFileClip(video_path)
        duration = video.duration
        part_duration = duration / num_parts
        
        for i in range(num_parts):
            start_time = i * part_duration
            end_time = min((i + 1) * part_duration, duration)
            
            part_video = video.subclipped(start_time, end_time)
            part_filename = f"{video_path}_part{i+1}.mp4"
            part_video.write_videofile(part_filename, codec='libx264', audio_codec='aac', logger=None)
            part_video.close()
            parts.append(part_filename)
        
        video.close()
        return parts
    except Exception as e:
        print(f"Error splitting video: {e}")
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

@dp.message(F.text == "🎬 Video yuklash")
async def start_video_download(message: types.Message, state: FSMContext):
    await state.set_state(InstagramStates.waiting_for_link)
    await message.answer("📸 Instagram video linkini yuboring:")

@dp.message(InstagramStates.waiting_for_link)
async def download_instagram_video(message: types.Message, state: FSMContext):
    url = message.text.strip()
    
    # Instagram link validation
    instagram_pattern = r'(https?://)?(www\.)?(instagram\.com|instagr\.am)/.*'
    if not re.match(instagram_pattern, url):
        await message.answer("❌ Noto'g'ri link! Iltimos, Instagram linkini yuboring.")
        return
    
    loading_msg = await message.answer("📥 Video yuklanmoqda, iltimos kuting...")
    
    try:
        # Generate unique filename
        unique_id = str(uuid.uuid4())[:8]
        output_template = f"downloads/{unique_id}_%(title)s.%(ext)s"
        
        # Create downloads directory if not exists
        os.makedirs("downloads", exist_ok=True)
        
        # yt-dlp options with better Instagram support
        ydl_opts = {
            'format': 'best[ext=mp4]/best',
            'outtmpl': output_template,
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'headers': {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-us,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
            },
            'retries': 10,
            'fragment_retries': 10,
            'extract_flat': 'in_playlist',
            'prefer_insecure': False,
        }
        
        # Add cookies if available
        if has_cookies():
            ydl_opts['cookiefile'] = COOKIES_FILE
        
        video_file = None
        
        with YoutubeDL(ydl_opts) as ydl:
            try:
                # Download video
                ydl.download([url])
                
                # Find the actual downloaded file
                downloaded_files = [f for f in os.listdir('downloads') if f.startswith(unique_id)]
                if downloaded_files:
                    video_file = os.path.join('downloads', downloaded_files[0])
                
                if video_file and os.path.exists(video_file):
                    # Check file size
                    file_size_mb = os.path.getsize(video_file) / (1024 * 1024)
                    
                    # Create inline keyboard for audio download
                    markup = types.InlineKeyboardMarkup(inline_keyboard=[
                        [types.InlineKeyboardButton(text="🎵 Audio yuklab olish", callback_data=f"audio_{video_file}")]
                    ])
                    
                    if file_size_mb <= 50:
                        # Send video directly
                        with open(video_file, 'rb') as video:
                            await message.answer_video(
                                video=types.BufferedInputFile(video.read(), filename=os.path.basename(video_file)),
                                caption=f"✅ Video muvaffaqiyatli yuklandi!\n📊 Hajmi: {file_size_mb:.1f}MB",
                                reply_markup=markup
                            )
                    else:
                        # Video is too large, split it
                        await message.answer(f"⚠️ Video hajmi {file_size_mb:.1f}MB (Telegram cheklovi: 50MB).\n🔄 Videoni qismlarga bo'lib yuboryapman...")
                        
                        # Split video into parts
                        video_parts = split_video(video_file)
                        
                        if len(video_parts) == 1:
                            # Couldn't split, just send as is
                            with open(video_file, 'rb') as video:
                                await message.answer_video(
                                    video=types.BufferedInputFile(video.read(), filename=os.path.basename(video_file)),
                                    caption=f"⚠️ Video hajmi katta ({file_size_mb:.1f}MB). Telegram cheklovi tufayli yuborib bo'lmadi.",
                                    reply_markup=markup
                                )
                        else:
                            # Send each part
                            for i, part_path in enumerate(video_parts, 1):
                                part_size = os.path.getsize(part_path) / (1024 * 1024)
                                with open(part_path, 'rb') as part:
                                    await message.answer_video(
                                        video=types.BufferedInputFile(part.read(), filename=f"video_part_{i}.mp4"),
                                        caption=f"📹 {i}/{len(video_parts)} qism | Hajmi: {part_size:.1f}MB"
                                    )
                                # Clean up part file
                                os.remove(part_path)
                            
                            # Send audio option for the full video
                            await message.answer(
                                "🎵 Videodan audio ajratib olishni xohlaysizmi?",
                                reply_markup=markup
                            )
                    
                    await loading_msg.delete()
                    await state.clear()
                else:
                    await loading_msg.delete()
                    await message.answer("❌ Video topilmadi. Iltimos, boshqa linkni sinab ko'ring.")
                    
            except Exception as e:
                error_msg = str(e)
                if "login required" in error_msg.lower() or "rate-limit" in error_msg.lower():
                    await loading_msg.delete()
                    await message.answer(
                        "⚠️ Instagram cheklovlari tufayli video yuklab bo'lmadi.\n\n"
                        "🔧 Yechimlar:\n"
                        "1. Bir necha daqiqadan so'ng qayta urinib ko'ring\n"
                        "2. Boshqa Instagram linkini sinab ko'ring\n"
                        "3. Agar muammo takrorlansa, admin bilan bog'laning\n\n"
                        "📞 Admin: @your_admin_username"
                    )
                else:
                    raise e
                
    except Exception as e:
        await loading_msg.delete()
        error_message = str(e)
        
        # Check for specific errors
        if "rate-limit" in error_message.lower():
            await message.answer(
                "⚠️ Instagram so'rovlar chekloviga uchradi.\n"
                "Iltimos, 5-10 daqiqadan so'ng qayta urinib ko'ring."
            )
        elif "login required" in error_message.lower():
            await message.answer(
                "⚠️ Instagram autentifikatsiya talab qilmoqda.\n"
                "Bu vaqtinchalik muammo. Iltimos, keyinroq qayta urinib ko'ring."
            )
        else:
            await message.answer(f"❌ Xatolik: {error_message[:200]}\nIltimos, keyinroq qayta urinib ko'ring.")
        
        await state.clear()
    
    finally:
        # Clean up downloaded files
        try:
            if os.path.exists('downloads'):
                for file in os.listdir('downloads'):
                    if file.startswith(unique_id):
                        file_path = os.path.join('downloads', file)
                        if os.path.exists(file_path):
                            os.remove(file_path)
        except Exception as e:
            print(f"Cleanup error: {e}")

@dp.callback_query(F.data.startswith("audio_"))
async def extract_audio(callback: types.CallbackQuery):
    video_file = callback.data.replace("audio_", "")
    
    if not os.path.exists(video_file):
        await callback.answer("❌ Video fayl topilmadi!", show_alert=True)
        return
    
    await callback.answer("🎵 Audio yuklanmoqda...")
    audio_msg = await callback.message.answer("🎵 Audio yuklanmoqda, iltimos kuting...")
    
    try:
        # Extract audio from video
        video_clip = VideoFileClip(video_file)
        audio = video_clip.audio
        
        if audio is not None:
            audio_filename = f"audio_{uuid.uuid4()}.mp3"
            audio.write_audiofile(audio_filename, logger=None, verbose=False)
            video_clip.close()
            
            # Send audio (no size limit check for audio)
            with open(audio_filename, 'rb') as audio_file:
                await callback.message.answer_audio(
                    audio=types.BufferedInputFile(audio_file.read(), filename=audio_filename),
                    caption="🎵 Audio muvaffaqiyatli yuklandi!"
                )
            
            # Clean up audio file
            os.remove(audio_filename)
            await audio_msg.delete()
        else:
            await callback.message.answer("❌ Bu videoda audio topilmadi.")
            
    except Exception as e:
        await callback.message.answer(f"❌ Audio yuklashda xatolik: {str(e)}")
    finally:
        # Clean up video file
        try:
            if os.path.exists(video_file):
                os.remove(video_file)
        except:
            pass

@dp.message(F.text == "Userlarni PDF korsh 👥")
async def show_users(message: types.Message):
    if message.from_user.id in ADMIN_ID:
        await check_blocked_users(bot)
        pdf_file = create_user_pdf()
        await message.answer_document(
            FSInputFile(pdf_file), 
            caption="👥 Foydalanuvchilar ro‘yxati"
        )

@dp.message(F.text == "Xabar yuborish 📨")
async def xabar_yuborish_boshlash(message: types.Message):
    await message.answer("""
📢 Xabar yuborish bo‘limi

✉️ Foydalanuvchilarga yuboriladigan xabar turini tanlang.

📝 Siz quyidagi formatlardan birini tanlashingiz mumkin:

• Matn (text)
• Rasm (photo)
• Video

⚙️ Tanlagan turga qarab keyingi bosqichlar ko‘rsatib beriladi.

👇 Davom etish uchun xabar turini tanlang.
""", reply_markup=xabar_yubor())

@dp.callback_query(F.data == "img")
async def rasm_bosildi(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("""
🖼 Rasm yuborish

📸 Iltimos, foydalanuvchilarga yubormoqchi bo‘lgan rasmingizni yuboring.

✏️ Rasm bilan birga izoh (caption) ham qo‘shishingiz mumkin.

⚡ Yuborilgan rasm barcha tanlangan foydalanuvchilarga yetkaziladi.

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
            await bot.send_photo(chat_id=user[3], photo=data["photo"], caption=data["about"])
            count += 1
        except:
            continue
    await message.answer(f"✅ {count} ta foydalanuvchiga yuborildi.", reply_markup=types.ReplyKeyboardRemove())
    await state.clear()

@dp.message(SendImg.confirm, F.text == "Yo‘q ❌")
async def bekor(message: types.Message, state: FSMContext):
    await message.answer("❌ Bekor qilindi.", reply_markup=types.ReplyKeyboardRemove())
    await state.clear()

async def main():
    logging.basicConfig(level=logging.INFO)
    
    # Create downloads directory
    os.makedirs("downloads", exist_ok=True)
    
    try:
        await bot.delete_webhook(drop_pending_updates=True)
    except Exception:
        pass
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())