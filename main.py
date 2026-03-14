import asyncio
import logging
import os
import instaloader
import re

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import FSInputFile
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.client.session.aiohttp import AiohttpSession

# Tugmalar va bazaga oid funksiyalar (Sizning fayllaringizdan)
from buttons.defould import user_button, send_confirmation_buttons
from create import insert_user, users_table, create_user_pdf, get_all_users
from buttons.inline import xabar_yubor
from stets import SendImg

# --- KONFIGURATSIYA ---
PROXY_URL = 'http://proxy.server:3128'
session = AiohttpSession(proxy=PROXY_URL)

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

ADMIN_ID = [6411347321]
API_TOKEN = "8301002449:AAEUdfgageMiEIX-qfIAWc73owqOzkRHqtE"

bot = Bot(token=API_TOKEN, session=session)
dp = Dispatcher()

# Instaloader sozlamalari
loader = instaloader.Instaloader(
    dirname_pattern=DOWNLOAD_DIR,
    download_videos=True,
    download_video_thumbnails=False,
    download_comments=False,
    save_metadata=False,
    compress_json=False,
    post_metadata_txt_pattern="" # Ortiqcha matnli fayllar yaratmasligi uchun
)

class VideoState(StatesGroup):
    waiting_for_link = State()

# --- YUKLASH FUNKSIYASI ---
def download_instagram(shortcode):
    """Instagramdan post yoki reelni yuklab beruvchi funksiya"""
    # Avval papkani tozalash (eski fayllar bilan adashib ketmaslik uchun)
    for f in os.listdir(DOWNLOAD_DIR):
        if not f.startswith("."): # Yashirin fayllarga tegmaslik
            os.remove(os.path.join(DOWNLOAD_DIR, f))
            
    post = instaloader.Post.from_shortcode(loader.context, shortcode)
    loader.download_post(post, target=DOWNLOAD_DIR)
    return True

# --- HANDLERLAR ---

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
        text = (
            f"👑 <b>Admin panelga xush kelibsiz!</b>\n\n"
            f"Salom, <b>{message.from_user.first_name}</b>.\n"
            "Kerakli bo‘limni tanlang 👇"
        )
        await message.answer(text, reply_markup=user_button(), parse_mode="HTML")
    else:
        text = (
            "👋 <b>Botga xush kelibsiz!</b>\n\n"
            "📥 Instagramdan video yuklash uchun <b>/vd_yuklash_boshlash</b> buyrug'ini bosing."
        )
        await message.answer(text, parse_mode="HTML")

@dp.message(F.text == "/vd_yuklash_boshlash")
async def vd_yukla_buyruq(message: types.Message, state: FSMContext):
    await state.set_state(VideoState.waiting_for_link)
    await message.answer("📥 Instagram Reels yoki Post linkini yuboring:")

@dp.message(VideoState.waiting_for_link)
async def vd_yuklash(message: types.Message, state: FSMContext):
    url = message.text
    
    # Instagram linkidan shortcodeni aniqlash (Regex bilan)
    regex = r"(?:https?://)?(?:www\.)?instagram\.com/(?:p|reels|reel)/([^/?#&]+)"
    match = re.search(regex, url)
    
    if not match:
        await message.answer("❌ Iltimos, to'g'ri Instagram link yuboring (Reels yoki Post).")
        return

    shortcode = match.group(1)
    status_msg = await message.answer("⌛ Video tahlil qilinmoqda va yuklanmoqda...")

    try:
        # Yuklash jarayonini async ichida bloklamasdan ishga tushirish
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, download_instagram, shortcode)

        files_found = False
        # Yuklangan fayllarni yuborish
        for file in os.listdir(DOWNLOAD_DIR):
            path = os.path.join(DOWNLOAD_DIR, file)
            
            if file.endswith(".mp4"):
                await message.answer_video(
                    FSInputFile(path),
                    caption="✅ Video muvaffaqiyatli yuklandi!\n\n@my_codingbot"
                )
                files_found = True
            elif file.endswith(".jpg") and not files_found:
                # Agar video bo'lmasa rasm yuborish (Postlar uchun)
                await message.answer_photo(FSInputFile(path), caption="✅ Rasm yuklandi!")
                files_found = True

            # Faylni yuborgandan keyin o'chirish (Xotirani tozalash)
            if os.path.exists(path):
                os.remove(path)

        if not files_found:
            await message.answer("⚠️ Video topilmadi. Profil yopiq bo'lishi mumkin.")

    except Exception as e:
        logging.error(f"Yuklashda xatolik: {e}")
        await message.answer("⚠️ Xatolik yuz berdi. Linkni tekshiring yoki keyinroq urinib ko'ring.")

    finally:
        await status_msg.delete()
        await state.clear()

# --- ADMIN PANEL FUNKSIYALARI ---

@dp.message(F.text == "Userlarni PDF korsh 👥")
async def show_users(message: types.Message):
    if message.from_user.id in ADMIN_ID:
        pdf_file = create_user_pdf()
        await message.answer_document(FSInputFile(pdf_file), caption="📄 Foydalanuvchilar ro'yxati")

@dp.message(F.text == "Xabar yuborish 📨")
async def xabar_yuborish_boshlash(message: types.Message):
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

async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot to'xtatildi")