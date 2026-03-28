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

from yt_dlp import YoutubeDL  

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
            "👑 *Admin panelga xush kelibsiz!*\n\n"
            "⚙️ Kerakli bo‘limni tanlang 👇\n\n"
            "📊 Statistikalar\n"
            "📨 Xabar yuborish\n"
            "👥 Foydalanuvchilar ro‘yxati",
            reply_markup=user_button(),
            parse_mode="Markdown"
        )
    else:
        await message.answer(
            "👋 *Salom! Xush kelibsiz!*\n\n"
            "🎬 Instagram REELS videolarni yuklab beruvchi botga xush kelibsiz!\n\n"
            "👇 Pastdagi tugmalardan birini tanlang va davom eting",
            reply_markup=start_button(),
            parse_mode="Markdown"
        )

# ================= VIDEO YUKLASH =================

@dp.message(F.text == "🎬 Video yuklash")
async def start_video_download(message: types.Message, state: FSMContext):
    await state.set_state(InstagramStates.waiting_for_reel)
    await message.answer(
        "🎬 *REELS YUKLASH XIZMATI*\n\n"
        "📎 Instagram reels linkini yuboring:\n"
        "━━━━━━━━━━━━━━━\n"
        "✅ Faqat REELS ishlaydi\n"
        "🚫 Post / Story qo‘llab-quvvatlanmaydi\n"
        "━━━━━━━━━━━━━━━\n\n"
        "⚡ Video tez va avtomatik yuklab beriladi",
        parse_mode="Markdown"
    )

@dp.message(InstagramStates.waiting_for_reel)
async def download_reel(message: types.Message, state: FSMContext):
    url = message.text.strip()

    if not ("instagram.com" in url and "/reel/" in url):
        await message.answer(
            "❌ *Noto‘g‘ri link!*\n\n"
            "📎 Iltimos, faqat Instagram REELS link yuboring.\n"
            "🔗 Masalan: instagram.com/reel/...",
            parse_mode="Markdown"
        )
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
        await message.answer("⏳ *Video yuklanmoqda...*\n\n📥 Iltimos biroz kuting", parse_mode="Markdown")

        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        video = FSInputFile(filename)

        await message.answer_video(
            video,
            caption="🎬 *Yuklab olindi!*\n\n"
                    "🤖 Bot: @my_cod1ngbot\n"
                    "⚡ Tez va oson yuklab berildi",
            parse_mode="Markdown"
        )

    except Exception:
        await message.answer(
            "⚠️ *Yuklashda muammo yuz berdi*\n\n"
            "🔁 Boshqa reels link yuborib ko‘ring",
            parse_mode="Markdown"
        )

    finally:
        if os.path.exists(filename):
            os.remove(filename)

# ================= ADMIN =================

@dp.message(F.text == "Userlarni PDF korsh 👥")
async def show_users(message: types.Message):
    if message.from_user.id in ADMIN_ID:
        await check_blocked_users(bot)
        pdf_file = create_user_pdf()
        await message.answer_document(
            FSInputFile(pdf_file),
            caption="👥 *Foydalanuvchilar ro‘yxati tayyor!*",
            parse_mode="Markdown"
        )

@dp.message(F.text == "Xabar yuborish 📨")
async def xabar_yuborish_boshlash(message: types.Message):
    await message.answer(
        "📨 *Xabar yuborish bo‘limi*\n\n"
        "👇 Xabar turini tanlang",
        reply_markup=xabar_yubor(),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == "img")
async def rasm_bosildi(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("🖼 *Rasmni yuboring*", parse_mode="Markdown")
    await state.set_state(SendImg.image)

@dp.message(SendImg.image, F.photo)
async def rasm_qabul(message: types.Message, state: FSMContext):
    await state.update_data(photo=message.photo[-1].file_id)
    await message.answer("📝 *Rasm uchun izoh kiriting:*", parse_mode="Markdown")
    await state.set_state(SendImg.about)

@dp.message(SendImg.about)
async def caption_qabul(message: types.Message, state: FSMContext):
    await state.update_data(about=message.text)
    data = await state.get_data()

    await message.answer_photo(
        photo=data["photo"],
        caption=f"📝 *Ko‘rinishi:*\n\n{data['about']}",
        parse_mode="Markdown"
    )

    await message.answer(
        "📨 *Barcha foydalanuvchilarga yuborilsinmi?*",
        reply_markup=send_confirmation_buttons(),
        parse_mode="Markdown"
    )

    await state.set_state(SendImg.confirm)

@dp.message(SendImg.confirm, F.text == "Xa ✅")
async def yubor(message: types.Message, state: FSMContext):
    data = await state.get_data()
    users = get_all_users()
    count = 0

    for user in users:
        try:
            await bot.send_photo(
                chat_id=user[3],
                photo=data["photo"],
                caption=data["about"]
            )
            count += 1
        except:
            continue

    await message.answer(
        f"✅ *Yuborildi!*\n\n📨 {count} ta foydalanuvchiga yetkazildi",
        parse_mode="Markdown"
    )

    await state.clear()

@dp.message(SendImg.confirm, F.text == "Yo‘q ❌")
async def bekor(message: types.Message, state: FSMContext):
    await message.answer("❌ *Yuborish bekor qilindi*", parse_mode="Markdown")
    await state.clear()

@dp.message(F.text == "👥 User soni ko‘rish")
async def user_count(message: types.Message):
    if message.from_user.id in ADMIN_ID:
        users = get_all_users()
        count = len(users)

        await message.answer(
            f"👥 *Foydalanuvchilar soni*\n\n"
            f"📊 Jami userlar: *{count} ta*\n\n"
            f"🚀 Bot faol ishlamoqda",
            parse_mode="Markdown"
        )

# ================= RUN =================
async def main():
    logging.basicConfig(level=logging.INFO)
    os.makedirs("downloads", exist_ok=True)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())