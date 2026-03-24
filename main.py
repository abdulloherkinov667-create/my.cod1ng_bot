import asyncio
import logging
import os
import re
import shutil

from yt_dlp import YoutubeDL
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import FSInputFile
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.client.session.aiohttp import AiohttpSession
from buttons.defould import start_button

from buttons.defould import user_button, send_confirmation_buttons
from create import insert_user, users_table, create_user_pdf, get_all_users, check_blocked_users
from buttons.inline import xabar_yubor
from stets import SendImg


API_TOKEN = "8301002449:AAFzKdU48I4Q0nuTxDnY9725MITFVA7w9ok"

PROXY_URL = None

try:
    session = AiohttpSession(proxy=PROXY_URL) if PROXY_URL else AiohttpSession()
except Exception:
    session = AiohttpSession()

bot = Bot(token=API_TOKEN, session=session)
dp = Dispatcher()

ADMIN_ID = [6411347321, 8327989068]
DOWNLOAD_DIR = "downloads"
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)


# Video download states
class VideoState(StatesGroup):
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
        text = (
            """
            👋 Botga xush kelibsiz!

😊 Botdan foydalanishni boshlash uchun pastda joylashgan tugmalardan birini tanlang.

👇 Davom etish uchun pastdagi tugmani bosing.

✨ Shundan so'ng sizga keyingi qadamlar ko'rsatib beriladi.
            """
        )
        await message.answer(text, parse_mode="HTML", reply_markup=start_button())


@dp.message(F.text == "🎬 Video yuklash")
async def vd_yukla_buyruq(message: types.Message, state: FSMContext):
    await state.set_state(VideoState.waiting_for_link)
    await message.answer("""
🎬 Video Yuklash

✅ Qollab-quvvatlanadi:
📸 Instagram Reels & Posts
▶️ YouTube Videos

📝 Havolani yuboring:
""")


@dp.message(VideoState.waiting_for_link)
async def download_video(message: types.Message, state: FSMContext):
    url = message.text.strip()
    
    # Validate URL
    if "instagram.com" not in url and "youtube.com" not in url and "youtu.be" not in url:
        await message.answer("❌ Instagram yoki YouTube havolasini yuboring!")
        return
    
    status_msg = await message.answer("⏳ Video yuklanmoqda, iltimos kuting...")
    
    try:
        # Create download directory
        dl_path = os.path.join(DOWNLOAD_DIR, "temp_video")
        os.makedirs(dl_path, exist_ok=True)
        
        # Setup yt_dlp options
        ydl_opts = {
            'outtmpl': os.path.join(dl_path, '%(title)s.%(ext)s'),
            'quiet': False,
            'no_warnings': False,
            'format': 'best',
            'socket_timeout': 30,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        }
        
        # Download video function to run in thread
        def download_video_file():
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                return ydl.prepare_filename(info)
        
        # Run download in thread
        video_file = await asyncio.to_thread(download_video_file)
        
        # Validate file
        if not os.path.exists(video_file):
            raise FileNotFoundError(f"Video file not found")
        
        file_size = os.path.getsize(video_file)
        if file_size == 0:
            raise ValueError("Downloaded file is empty")
        
        # Update status
        await status_msg.edit_text("📤 Video yuborilmoqda...")
        
        # Send video
        with open(video_file, 'rb') as f:
            await message.answer_video(
                video=f,
                caption="✅ Tayyor!\n\n🎉 Video muvaffaqiyatli yuklandi!"
            )
        
        await status_msg.delete()
        
    except Exception as e:
        error_msg = str(e)[:100]
        logging.error(f"Video download error: {error_msg}")
        await status_msg.edit_text(f"❌ Xato: {error_msg}")
    
    finally:
        # Cleanup
        try:
            shutil.rmtree(os.path.join(DOWNLOAD_DIR, "temp_video"), ignore_errors=True)
        except:
            pass
        
        await state.clear()


@dp.message(F.text == "Userlarni PDF korsh 👥")
async def show_users(message: types.Message):
    if message.from_user.id in ADMIN_ID:
        await check_blocked_users(bot)
        pdf_file = create_user_pdf()
        await message.answer_document(FSInputFile(pdf_file), caption="""
👥 Foydalanuvchilar ro'yxatini
                                      """)


@dp.message(F.text == "Xabar yuborish 📨")
async def xabar_yuborish_boshlash(message: types.Message):
    await message.answer("""
                         📢 Xabar yuborish bo'limi

✉️ Foydalanuvchilarga yuboriladigan xabar turini tanlang.

📝 Siz quyidagi formatlardan birini tanlashingiz mumkin:

• Matn (text)
• Rasm (photo)
• Video

⚙️ Tanlagan turga qarab keyingi bosqichlar ko'rsatib beriladi.

👇 Davom etish uchun xabar turini tanlang.
                         """, reply_markup=xabar_yubor())


@dp.callback_query(F.data == "img")
async def rasm_bosildi(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("""
                                  🖼 Rasm yuborish

📸 Iltimos, foydalanuvchilarga yubormoqchi bo'lgan rasmingizni yuboring.

✏️ Rasm bilan birga izoh (caption) ham qo'shishingiz mumkin.

⚡ Yuborilgan rasm barcha tanlangan foydalanuvchilarga yetkaziladi.

👇 Endi rasmni yuboring.
                                  """)
    await state.set_state(SendImg.image)
    await callback.answer()


@dp.message(SendImg.image, F.photo)
async def rasm_qabul(message: types.Message, state: FSMContext):
    await state.update_data(photo=message.photo[-1].file_id)
    await message.answer("""
                         ✏️ Rasm uchun izoh qo'shish

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


@dp.message(SendImg.confirm, F.text == "Yo'q ❌")
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
