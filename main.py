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
        # yt-dlp options for Instagram
        ydl_opts = {
            'format': 'best[ext=mp4]/best',
            'outtmpl': f'{message.chat.id}_%(title)s.%(ext)s',
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        }
        
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_file = ydl.prepare_filename(info)
            
            if os.path.exists(video_file):
                # Create inline keyboard for audio download
                markup = types.InlineKeyboardMarkup(inline_keyboard=[
                    [types.InlineKeyboardButton(text="🎵 Audio yuklab olish", callback_data=f"audio_{video_file}")]
                ])
                
                # Send video
                with open(video_file, 'rb') as video:
                    await message.answer_video(
                        video=types.BufferedInputFile(video.read(), filename=os.path.basename(video_file)),
                        caption="✅ Video muvaffaqiyatli yuklandi!",
                        reply_markup=markup
                    )
                
                await loading_msg.delete()
                await state.clear()
            else:
                await loading_msg.delete()
                await message.answer("❌ Video topilmadi. Iltimos, boshqa linkni sinab ko'ring.")
                
    except Exception as e:
        await loading_msg.delete()
        await message.answer(f"❌ Xatolik yuz berdi: {str(e)}\nIltimos, keyinroq qayta urinib ko'ring.")
        await state.clear()
    
    finally:
        # Clean up downloaded files
        for file in os.listdir('.'):
            if file.startswith(str(message.chat.id)) and file.endswith(('.mp4', '.webm', '.mkv')):
                try:
                    os.remove(file)
                except:
                    pass

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
            audio_filename = f"{uuid.uuid4()}.mp3"
            audio.write_audiofile(audio_filename, logger=None)
            video_clip.close()
            
            # Send audio
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
    
    try:
        await bot.delete_webhook(drop_pending_updates=True)
    except Exception:
        pass
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())