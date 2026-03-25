import asyncio
import logging
import os
import shutil
import uuid
from yt_dlp import YoutubeDL

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import FSInputFile
from aiogram.fsm.context import FSMContext

# Sizning mavjud fayllar
from buttons.defould import start_button, user_button, send_confirmation_buttons
from create import insert_user, users_table, create_user_pdf, get_all_users, check_blocked_users
from buttons.inline import xabar_yubor
from stets import SendImg

API_TOKEN = "TOKENINGNI_OZING_QOY"

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

ADMIN_ID = [6411347321, 8327989068]

INSTAGRAM_URL_PATTERN = r'(https?://(?:www\.)?instagram\.com/[^\s]+)'

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
            "👑 *Admin panelga xush kelibsiz!*\n\n"
            "⚙️ Kerakli bo‘limni tanlang 👇",
            reply_markup=user_button(),
            parse_mode="Markdown"
        )
    else:
        await message.answer(
            "👋 *Salom! Xush kelibsiz!*\n\n"
            "🎬 Instagram video yoki reel yuklab olish uchun:\n"
            "1️⃣ Pastdagi tugmani bosing\n"
            "2️⃣ Link yuboring\n\n"
            "🚀 Qolganini men bajaraman 😉",
            reply_markup=start_button(),
            parse_mode="Markdown"
        )

# ================= VIDEO YUKLASH =================
@dp.message(F.text.regexp(INSTAGRAM_URL_PATTERN))
async def download_instagram(message: types.Message):
    url = message.text.strip()
    msg = await message.answer(
        "⏳ *Video yuklab olinmoqda...*\n\n"
        "📥 Iltimos, biroz kuting...",
        parse_mode="Markdown"
    )

    folder = f"downloads/{uuid.uuid4().hex[:6]}"
    os.makedirs(folder, exist_ok=True)

    ydl_opts = {
        'format': 'mp4',
        'outtmpl': f'{folder}/%(title)s.%(ext)s',
        'quiet': True,
        'nocheckcertificate': True,
        'ignoreerrors': False,
        'geo_bypass': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0',
        },
    }

    try:
        def load_video():
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                return ydl.prepare_filename(info)

        video_path = await asyncio.to_thread(load_video)

        if os.path.exists(video_path):
            await msg.edit_text(
                "📤 *Video tayyor!*\n\n"
                "🚀 Sizga yuborilmoqda...",
                parse_mode="Markdown"
            )

            await message.answer_video(
                video=FSInputFile(video_path),
                caption=
                "✅ *Muvaffaqiyatli yuklandi!*\n\n"
                "🎬 Video tayyor 👌\n"
                "📲 Yana yuklash uchun link yuboring",
                parse_mode="Markdown"
            )

            await msg.delete()
        else:
            raise Exception("Video topilmadi")

    except Exception as e:
        logging.error(e)
        await msg.edit_text(
            "❌ *Xatolik yuz berdi!*\n\n"
            "🔒 Video yuklab bo‘lmadi.\n"
            "Sababi:\n"
            "• Profil yopiq bo‘lishi mumkin\n"
            "• Link noto‘g‘ri bo‘lishi mumkin\n\n"
            "🔁 Qayta urinib ko‘ring",
            parse_mode="Markdown"
        )

    finally:
        if os.path.exists(folder):
            shutil.rmtree(folder)

# ================= ADMIN (TEGINILMADI) =================

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
        except:
            continue

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