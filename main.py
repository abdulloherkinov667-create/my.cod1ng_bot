import asyncio
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

# Instagram loader sozlamalari
loader = instaloader.Instaloader(
    download_comments=False,
    download_geotags=False,
    download_pictures=False,
    download_video_thumbnails=False,
    save_metadata=False
)

API_TOKEN = "8301002449:AAFzKdU48I4Q0nuTxDnY9725MITFVA7w9ok"
ADMIN_ID = [6411347321, 8327989068]

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

class InstagramStates(StatesGroup):
    waiting_for_reel = State()

# ================= START =================
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
        await message.answer(
            "👑 *Admin panelga xush kelibsiz!*\n\n⚙️ Kerakli bo‘limni tanlang 👇",
            reply_markup=user_button(),
            parse_mode="Markdown"
        )
    else:
        await message.answer(
            "👋 *Salom! Xush kelibsiz!*",
            reply_markup=start_button(),
            parse_mode="Markdown"
        )

# ================= VIDEO YUKLASH QISMI =================

@dp.message(F.text == "🎬 Video yuklash")
async def start_video_download(message: types.Message, state: FSMContext):
    await state.set_state(InstagramStates.waiting_for_reel)
    await message.answer(
        "🎬 REELS YUKLASH\n\n"
        "📎 Reels linkini yuboring:\n"
        "━━━━━━━━━━━━━━━\n"
        "✅ Faqat Instagram REELS\n"
        "🚫 Post / Story ishlamaydi\n"
        "━━━━━━━━━━━━━━━\n\n"
        "⏳ Video avtomatik yuklab beriladi"
    )

@dp.message(InstagramStates.waiting_for_reel)
async def download_reel(message: types.Message, state: FSMContext):
    url = message.text.strip()

    # 🔥 TO‘G‘IRLANGAN TEKSHIRUV
    if not ("instagram.com" in url and "/reel/" in url):
        await message.answer("❌ Faqat Instagram REELS link yuboring!")
        return

    import os
    import uuid
    from yt_dlp import YoutubeDL
    from aiogram.types import FSInputFile

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
# ================= ADMIN PANEL (TEGINILMAGAN) =================

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
    await message.answer("📝 Izoh kiriting:")
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

# ================= RUN =================
async def main():
    logging.basicConfig(level=logging.INFO)
    os.makedirs("downloads", exist_ok=True)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())