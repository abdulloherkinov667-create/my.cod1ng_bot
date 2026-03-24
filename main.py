import asyncio
import logging
import os
import shutil
import instaloader
import uuid
from moviepy import VideoFileClip

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from buttons.defould import start_button, user_button, send_confirmation_buttons
from create import insert_user, users_table, create_user_pdf, get_all_users, check_blocked_users
from buttons.inline import xabar_yubor
from stets import SendImg

API_TOKEN = "TOKENINGNI_QOY"
ADMIN_ID = [6411347321, 8327989068]

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

loader = instaloader.Instaloader(
    download_comments=False,
    download_geotags=False,
    download_pictures=False,
    download_video_thumbnails=False,
    save_metadata=False,
    compress_json=False
)

# --- PROGRESS ---
async def update_progress(message: types.Message):
    progress_chars = ["⬜"] * 10
    for i in range(10):
        progress_chars[i] = "🟩"
        percent = (i + 1) * 10
        bar = "".join(progress_chars)
        try:
            await message.edit_text(f"📥 Yuklanmoqda: {percent}%\n{bar}")
            await asyncio.sleep(0.4)
        except:
            pass

# --- START ---
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
        await message.answer("👑 Admin panel", reply_markup=user_button())
    else:
        await message.answer("👋 Xush kelibsiz", reply_markup=start_button())

# --- VIDEO BOSHLASH ---
@dp.message(F.text == '🎬 Video yuklash')
async def ask_link(message: types.Message):
    await message.answer("🔗 Instagram link yubor:")

# --- ASOSIY FIX QISM ---
@dp.message(F.text.contains("instagram.com"))
async def get_instagram_video(message: types.Message):
    url = message.text.strip()

    try:
        shortcode = url.split("/")[-2] if url.endswith('/') else url.split("/")[-1]
        if "?" in shortcode:
            shortcode = shortcode.split("?")[0]
    except:
        await message.answer("❌ Link noto‘g‘ri")
        return

    loader_msg = await message.answer("⏳ Yuklanmoqda: 0%\n⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜")
    progress_task = asyncio.create_task(update_progress(loader_msg))

    try:
        target_dir = f"temp_{uuid.uuid4().hex[:8]}"
        os.makedirs(target_dir, exist_ok=True)

        loop = asyncio.get_event_loop()
        post = await loop.run_in_executor(None, lambda: instaloader.Post.from_shortcode(loader.context, shortcode))
        await loop.run_in_executor(None, lambda: loader.download_post(post, target=target_dir))

        await progress_task

        # 🔥 VIDEO TOPISH (FIX)
        video_path = None
        for root, dirs, files in os.walk(target_dir):
            for file in files:
                if file.endswith(".mp4"):
                    video_path = os.path.join(root, file)
                    break

        if not video_path:
            await loader_msg.edit_text("❌ Video topilmadi")
            shutil.rmtree(target_dir, ignore_errors=True)
            return

        await loader_msg.edit_text("📤 Video yuborilmoqda...")

        video = FSInputFile(video_path)

        await message.answer_video(
            video=video,
            caption="✅ Video yuklandi"
        )

        await loader_msg.delete()
        shutil.rmtree(target_dir, ignore_errors=True)

    except Exception as e:
        await loader_msg.edit_text(f"⚠️ Xatolik: {e}")
        shutil.rmtree(target_dir, ignore_errors=True)

# --- AUDIO ---
@dp.callback_query(F.data.startswith("audio_"))
async def get_audio_callback(call: types.CallbackQuery):
    await call.answer("⚠️ Bu versiyada audio o‘chirilgan")

# --- ADMIN (tegilmadi) ---
@dp.message(F.text == "Userlarni PDF korsh 👥")
async def show_users(message: types.Message):
    if message.from_user.id in ADMIN_ID:
        await check_blocked_users(bot)
        pdf_file = create_user_pdf()
        await message.answer_document(FSInputFile(pdf_file))

@dp.message(F.text == "Xabar yuborish 📨")
async def xabar_yuborish_boshlash(message: types.Message):
    if message.from_user.id in ADMIN_ID:
        await message.answer("📢 Tanlang:", reply_markup=xabar_yubor())

# --- RUN ---
async def main():
    logging.basicConfig(level=logging.INFO)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())