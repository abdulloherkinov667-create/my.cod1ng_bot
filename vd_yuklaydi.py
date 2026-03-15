import asyncio
import logging
import os
import instaloader
import re
import shutil

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import FSInputFile
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.client.session.aiohttp import AiohttpSession

# Sizning tugmalaringiz va bazangiz (fayllar mavjudligiga ishonch hosil qiling)
from buttons.defould import user_button, send_confirmation_buttons
from create import insert_user, users_table, create_user_pdf, get_all_users
from buttons.inline import xabar_yubor
from stets import SendImg

# --- KONFIGURATSIYA ---
PROXY_URL = 'http://proxy.server:3128'
session = AiohttpSession(proxy=PROXY_URL)

ADMIN_ID = [6411347321]
API_TOKEN = "8301002449:AAGzIhcw-tEI0IKqvPPw60i3jwschEZ-z6Y"

DOWNLOAD_DIR = "downloads"
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

bot = Bot(token=API_TOKEN, session=session)
dp = Dispatcher()

# Instaloader sozlamalari (Loader obyekti shu yerda yaratiladi)
L = instaloader.Instaloader(
    dirname_pattern=os.path.join(DOWNLOAD_DIR, "{target}"),
    download_videos=True,
    download_video_thumbnails=True,
    download_comments=True,
    save_metadata=True,
    compress_json=True
)

class VideoState(StatesGroup):
    waiting_for_link = State()

# --- START KOMANDASI ---
@dp.message(CommandStart())
async def start_command(message: types.Message):
    await users_table()
    insert_user(
        first_name=message.from_user.first_name,
        username=message.from_user.username,
        language_code=message.from_user.language_code,
        is_bot=message.from_user.is_bot,
        chat_id=message.chat.id,
        created_at=message.date
    )

    if message.from_user.id in ADMIN_ID:
        text = f"👑 <b>Admin panelga xush kelibsiz!</b>\n\nSalom, <b>{message.from_user.first_name}</b>."
        await message.answer(text, reply_markup=user_button(), parse_mode="HTML")
    else:
        text = "👋 <b>Botga xush kelibsiz!</b>\n\n📥 Video yuklash uchun /vd_yuklash_boshlash buyrug'ini bosing."
        await message.answer(text, parse_mode="HTML")

# --- VIDEO YUKLASH QISMI ---
@dp.message(F.text == "/vd_yuklash_boshlash")
async def vd_yukla_buyruq(message: types.Message, state: FSMContext):
    await state.set_state(VideoState.waiting_for_link)
    await message.answer("📥 Instagram video (Reels yoki Post) linkini yuboring")

@dp.message(VideoState.waiting_for_link)
async def vd_yuklash(message: types.Message, state: FSMContext):
    url = message.text
    
    # Instagram linkini aniqlash (p/, reels/, reel/, tv/)
    match = re.search(r"instagram\.com/(?:p|reels|reel|tv)/([a-zA-Z0-9_-]+)", url)
    
    if not match:
        await message.answer("❌ Iltimos, to'g'ri Instagram video linkini yuboring.")
        return

    shortcode = match.group(1)
    wait_msg = await message.answer("⏳ Video yuklanmoqda, iltimos kuting...")
    target_dir = os.path.join(DOWNLOAD_DIR, shortcode)

    try:
        # Postni yuklab olish
        post = instaloader.Post.from_shortcode(L.context, shortcode)
        L.download_post(post, target=shortcode)
        
        video_found = False
        # Papka ichidan video faylni qidirish
        if os.path.exists(target_dir):
            for file in os.listdir(target_dir):
                if file.endswith(".mp4"):
                    video_path = os.path.join(target_dir, file)
                    video = FSInputFile(video_path)
                    await message.answer_video(
                        video, 
                        caption="📹 Video siz uchun yuklandi!\n\n🤖 Bot: @my_cod1ngbot"
                    )
                    video_found = True
                    break
        
        if not video_found:
            await message.answer("⚠️ Bu postda video topilmadi.")

    except Exception as e:
        logging.error(f"Yuklashda xato: {e}")
        await message.answer("⚠️ Xatolik yuz berdi! Video yuklab bo'lmadi.\n(Profil yopiq yoki link noto'g'ri bo'lishi mumkin)")
    
    finally:
        # Tozalash: Yuklangan papkani va ichidagilarni o'chirish
        if os.path.exists(target_dir):
            shutil.rmtree(target_dir)
        await wait_msg.delete()
        await state.clear()

# --- ADMIN FUNKSIYALARI ---
@dp.message(F.text == "Userlarni PDF korsh 👥")
async def show_users(message: types.Message):
    if message.from_user.id in ADMIN_ID:
        pdf_file = create_user_pdf()
        await message.answer_document(FSInputFile(pdf_file), caption="📄 Foydalanuvchilar ro'yxati")

@dp.message(F.text == "Xabar yuborish 📨")
async def xabar_yuborish_boshlash(message: types.Message):
    if message.from_user.id in ADMIN_ID:
        await message.answer("📨 Xabar turini tanlang:", reply_markup=xabar_yubor())

@dp.callback_query(F.data == "img")
async def rasm_bosildi(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("🖼 Rasmni yuklang.")
    await state.set_state(SendImg.image)
    await callback.answer()

@dp.message(SendImg.image, F.photo)
async def rasm_qabul(message: types.Message, state: FSMContext):
    await state.update_data(photo=message.photo[-1].file_id)
    await message.answer("✏️ Rasm uchun matn kiriting")
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
            # user[3] bu chat_id deb hisoblandi
            await bot.send_photo(chat_id=user[3], photo=data["photo"], caption=data["about"])
            count += 1
        except:
            continue
    await message.answer(f"✅ {count} ta foydalanuvchiga yuborildi.", reply_markup=user_button())
    await state.clear()

@dp.message(SendImg.confirm, F.text == "Yo‘q ❌")
async def bekor(message: types.Message, state: FSMContext):
    await message.answer("❌ Bekor qilindi.", reply_markup=user_button())
    await state.clear()

# --- ASOSIY ISHGA TUSHIRISH ---
async def main():
    logging.basicConfig(level=logging.INFO)
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())