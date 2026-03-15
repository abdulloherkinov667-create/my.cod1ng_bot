import asyncio
import logging
import os
import instaloader
import re
import shutil
import uuid

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import FSInputFile
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.client.session.aiohttp import AiohttpSession

# O'zingizning fayllaringizdan importlar
# Eslatma: Bu fayllar va funksiyalar mavjudligiga ishonch hosil qiling
try:
    from buttons.defould import user_button, send_confirmation_buttons
    from create import insert_user, users_table, create_user_pdf, get_all_users
    from buttons.inline import xabar_yubor
    from stets import SendImg
except ImportError:
    logging.warning("Ba'zi modullar topilmadi, iltimos fayllaringizni tekshiring!")

# --- KONFIGURATSIYA ---
PROXY_URL = 'http://proxy.server:3128' # Agar serveringizda kerak bo'lmasa, session'ni olib tashlang
session = AiohttpSession(proxy=PROXY_URL)

ADMIN_ID = [6411347321]
API_TOKEN = "8301002449:AAETmzKpcyiwraQlZo3DvvIo7cHKs5DcoNk"

DOWNLOAD_DIR = "downloads"
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

bot = Bot(token=API_TOKEN) # session=session agar kerak bo'lsa qo'shing
dp = Dispatcher()

# Instaloader sozlamalari
loader = instaloader.Instaloader(
    download_videos=True,
    download_video_thumbnails=False,
    download_comments=False,
    save_metadata=False,
    compress_json=False,
    post_metadata_txt_pattern=""
)

# Agar bot ko'p video yuklasa, Instagram bloklamasligi uchun login qilish tavsiya etiladi:
# loader.login("Sizning_Usernamiz", "Sizning_Parolingiz") 

class VideoState(StatesGroup):
    waiting_for_link = State()

# --- HANDLERLAR ---

@dp.message(CommandStart())
async def start_command(message: types.Message):
    try:
        await users_table()
        insert_user(
            first_name=message.from_user.first_name,
            username=message.from_user.username,
            language_code=message.from_user.language_code,
            is_bot=message.from_user.is_bot,
            chat_id=message.chat.id,
            created_at=message.date
        )
    except Exception as e:
        logging.error(f"DB Error: {e}")

    if message.from_user.id in ADMIN_ID:
        text = f"👑 <b>Admin panelga xush kelibsiz!</b>\n\nSalom, <b>{message.from_user.first_name}</b>."
        await message.answer(text, reply_markup=user_button(), parse_mode="HTML")
    else:
        text = "👋 <b>Botga xush kelibsiz!</b>\n\n📥 Video yuklash uchun quyidagi tugmani bosing yoki link yuboring."
        await message.answer(text, parse_mode="HTML")

@dp.message(F.text == "/vd_yuklash_boshlash")
async def vd_yukla_buyruq(message: types.Message, state: FSMContext):
    await state.set_state(VideoState.waiting_for_link)
    await message.answer("📥 Instagram video (Reels/Post) linkini yuboring:")

@dp.message(VideoState.waiting_for_link)
@dp.message(F.text.contains("instagram.com")) # Linkni shunchaki yuborganda ham ushlab oladi
async def vd_yuklash(message: types.Message, state: FSMContext):
    url = message.text
    
    # Kengaytirilgan Regex (reels, p, tv va share linklar uchun)
    match = re.search(r"instagram\.com/(?:p|reels|reel|tv)/([a-zA-Z0-9_-]+)", url)
    
    if not match:
        await message.answer("❌ Iltimos, to'g'ri Instagram video linkini yuboring.\nMasalan: <code>https://www.instagram.com/reels/XXXXX/</code>", parse_mode="HTML")
        return

    wait_msg = await message.answer("⏳ Video tahlil qilinmoqda...")
    shortcode = match.group(1)
    
    # Har bir yuklash uchun unikal papka (muhim!)
    unique_id = str(uuid.uuid4())[:8]
    target_dir = os.path.join(DOWNLOAD_DIR, f"{shortcode}_{unique_id}")

    try:
        # Post ma'lumotlarini olish
        post = instaloader.Post.from_shortcode(loader.context, shortcode)
        
        if not post.is_video:
            await wait_msg.edit_text("⚠️ Bu postda video mavjud emas (faqat rasm).")
            return

        await wait_msg.edit_text("📥 Video yuklab olinmoqda...")
        
        # Yuklash (Faqat bitta postni o'zini papkaga yuklaydi)
        loader.dirname_pattern = target_dir
        loader.download_post(post, target=target_dir)
        
        video_file = None
        for fil in os.listdir(target_dir):
            if fil.endswith(".mp4"):
                video_file = os.path.join(target_dir, fil)
                break
        
        if video_file:
            await wait_msg.edit_text("📤 Video botga yuklanmoqda...")
            await message.answer_video(
                FSInputFile(video_file), 
                caption=f"📹 <b>Video muvaffaqiyatli yuklandi!</b>\n\n🤖 Bot: @my_cod1ngbot",
                parse_mode="HTML"
            )
        else:
            await wait_msg.edit_text("⚠️ Video fayli topilmadi.")

    except instaloader.exceptions.ProfileNotExistsException:
        await wait_msg.edit_text("❌ Profil topilmadi yoki o'chirilgan.")
    except instaloader.exceptions.PrivatePostException:
        await wait_msg.edit_text("🔒 Bu profil yopiq! Bot faqat ochiq profillardagi videolarni yuklay oladi.")
    except Exception as e:
        logging.error(f"Xatolik yuz berdi: {e}")
        await wait_msg.edit_text("⚠️ Xatolik yuz berdi! Link noto'g'ri yoki Instagram botni chekladi.")
    
    finally:
        # Tozalash
        if os.path.exists(target_dir):
            shutil.rmtree(target_dir)
        try:
            await wait_msg.delete()
        except:
            pass
        await state.clear()

# --- QOLGAN ADMIN FUNKSIYALARI ---
# (Siz yozgan admin kodlari shu yerda davom etadi...)

async def main():
    logging.basicConfig(level=logging.INFO)
    print("Bot ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot to'xtatildi")