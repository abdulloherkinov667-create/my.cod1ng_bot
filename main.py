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
from aiogram.fsm.context import FSMContext

from buttons.defould import start_button, user_button, send_confirmation_buttons
from create import insert_user, users_table, create_user_pdf, get_all_users, check_blocked_users
from buttons.inline import xabar_yubor
from stets import SendImg

API_TOKEN = "TOKENINGNI_QOY"
ADMIN_ID = [6411347321, 8327989068]

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# --- INSTAGRAM LOADER ---
loader = instaloader.Instaloader(
    download_comments=False,
    download_geotags=False,
    download_pictures=False,
    download_video_thumbnails=False,
    save_metadata=False,
    compress_json=False
)

# --- PROGRESS BAR ---
async def update_progress(msg):
    bar = ["⬜"] * 10
    for i in range(10):
        bar[i] = "🟩"
        try:
            await msg.edit_text(f"📥 Yuklanmoqda: {(i+1)*10}%\n{''.join(bar)}")
            await asyncio.sleep(0.4)
        except:
            pass

# --- START ---
@dp.message(CommandStart())
async def start(message: types.Message):
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

# --- VIDEO TUGMA ---
@dp.message(F.text == "🎬 Video yuklash")
async def ask_link(message: types.Message):
    await message.answer("🔗 Instagram video linkini yuboring:")

# --- VIDEO YUKLASH (FULL FIX) ---
@dp.message(F.text.contains("instagram.com"))
async def download_video(message: types.Message):
    url = message.text.strip()

    try:
        shortcode = url.split("/")[-2] if url.endswith("/") else url.split("/")[-1]
        if "?" in shortcode:
            shortcode = shortcode.split("?")[0]
    except:
        await message.answer("❌ Link xato")
        return

    msg = await message.answer("⏳ Yuklanmoqda: 0%\n⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜")
    progress = asyncio.create_task(update_progress(msg))

    try:
        folder = f"temp_{uuid.uuid4().hex[:6]}"
        os.makedirs(folder, exist_ok=True)

        loop = asyncio.get_event_loop()
        post = await loop.run_in_executor(None, lambda: instaloader.Post.from_shortcode(loader.context, shortcode))
        await loop.run_in_executor(None, lambda: loader.download_post(post, target=folder))

        await progress

        # 🔥 VIDEO QIDIRISH (ENG MUHIM FIX)
        video_path = None
        for root, dirs, files in os.walk(folder):
            for f in files:
                if f.endswith(".mp4"):
                    video_path = os.path.join(root, f)
                    break

        if not video_path:
            await msg.edit_text("❌ Video topilmadi")
            shutil.rmtree(folder, ignore_errors=True)
            return

        await msg.edit_text("📤 Video yuborilmoqda...")

        video = FSInputFile(video_path)

        await message.answer_video(
            video=video,
            caption="✅ Video yuklandi"
        )

        await msg.delete()
        shutil.rmtree(folder, ignore_errors=True)

    except Exception as e:
        await msg.edit_text(f"⚠️ Xatolik: {e}")
        shutil.rmtree(folder, ignore_errors=True)

# --- ADMIN ---
@dp.message(F.text == "Userlarni PDF korsh 👥")
async def show_users(message: types.Message):
    if message.from_user.id in ADMIN_ID:
        await check_blocked_users(bot)
        pdf = create_user_pdf()
        await message.answer_document(FSInputFile(pdf))

@dp.message(F.text == "Xabar yuborish 📨")
async def send_msg(message: types.Message):
    if message.from_user.id in ADMIN_ID:
        await message.answer("📢 Tanlang:", reply_markup=xabar_yubor())

# --- RUN ---
async def main():
    logging.basicConfig(level=logging.INFO)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())