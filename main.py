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

# Holatlarni belgilash
class DownloadState(StatesGroup):
    waiting_for_link = State()

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
async def ask_for_link(message: types.Message, state: FSMContext):
    await message.answer("🔗 Instagram video linkini yuboring:")
    await state.set_state(DownloadState.waiting_for_link)

@dp.message(DownloadState.waiting_for_link)
async def process_instagram_link(message: types.Message, state: FSMContext):
    url = message.text.strip()
    
    if "instagram.com" not in url:
        await message.answer("❌ Bu haqiqiy Instagram linki emas. Iltimos qaytadan yuboring.")
        return

    loader_msg = await message.answer("⏳ Video yuklanmoqda, iltimos kuting...")
    
    try:
        # Shortcode ajratib olish
        shortcode = url.split("/")[-2] if url.endswith("/") else url.split("/")[-1]
        if "?" in shortcode: shortcode = shortcode.split("?")[0]

        # Papka yaratish (uuid bilan xavfsizroq)
        folder_name = f"downloads/{uuid.uuid4()}"
        
        # Yuklash (Sinxron funksiyani asinxron ishlatish)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: loader.download_post(instaloader.Post.from_shortcode(loader.context, shortcode), target=folder_name))

        video_file = None
        for file in os.listdir(folder_name):
            if file.endswith(".mp4"):
                video_file = os.path.join(folder_name, file)
                break

        if video_file:
            # Audio tugmasi
            markup = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🎵 Audioni yuklab olish", callback_data=f"getaudio_{video_file}")]
            ])
            
            video_input = FSInputFile(video_file)
            await bot.send_video(message.chat.id, video_input, reply_markup=markup)
            await loader_msg.delete()
        else:
            await message.answer("😔 Video topilmadi.")
            shutil.rmtree(folder_name, ignore_errors=True)
            
    except Exception as e:
        await message.answer(f"❌ Xatolik yuz berdi: {e}")
    finally:
        await state.clear()

@dp.callback_query(F.data.startswith("getaudio_"))
async def send_audio(call: types.CallbackQuery):
    video_path = call.data.split("_")[1]
    
    if not os.path.exists(video_path):
        await call.answer("Fayl muddati o'tgan yoki o'chirilgan.", show_alert=True)
        return

    wait_msg = await call.message.answer("🎵 Audio ajratib olinmoqda...")
    audio_path = f"{video_path}.mp3"

    try:
        # Audio ajratish
        video = VideoFileClip(video_path)
        video.audio.write_audiofile(audio_path, logger=None)
        video.close()

        audio_input = FSInputFile(audio_path)
        await call.message.answer_audio(audio_input)
        await wait_msg.delete()
        
    except Exception as e:
        await call.message.answer(f"Audio xatosi: {e}")
    finally:
        # Tozalash
        if os.path.exists(audio_path): os.remove(audio_path)
        folder = os.path.dirname(video_path)
        if os.path.exists(folder): shutil.rmtree(folder, ignore_errors=True)

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