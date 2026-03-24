import asyncio
import logging
import os
import shutil
import instaloader
import uuid
from moviepy import VideoFileClip # Yangi versiya uchun to'g'ri import

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

# Sizning shaxsiy modullaringiz (Teginilmagan)
from buttons.defould import start_button, user_button, send_confirmation_buttons
from create import insert_user, users_table, create_user_pdf, get_all_users, check_blocked_users
from buttons.inline import xabar_yubor
from stets import SendImg

API_TOKEN = "8054850246:AAGlgGkJ0VpGarnaf7wXrx1H_WPCh_R59wA"
ADMIN_ID = [6411347321, 8327989068]

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Instagram loader sozlamalari
loader = instaloader.Instaloader(
    download_comments=False,
    download_geotags=False,
    download_pictures=False,
    download_video_thumbnails=False,
    save_metadata=False,
    compress_json=False
)

# --- PROGRESS BAR FUNKSIYASI ---
async def update_progress(message: types.Message):
    progress_chars = ["⬜", "⬜", "⬜", "⬜", "⬜", "⬜", "⬜", "⬜", "⬜", "⬜"]
    for i in range(len(progress_chars)):
        progress_chars[i] = "🟩"
        percent = (i + 1) * 10
        bar = "".join(progress_chars)
        try:
            await message.edit_text(f"📥 Yuklanmoqda: {percent}%\n{bar}")
            await asyncio.sleep(0.5) # Yuklash tezligini simulyatsiya qilish
        except:
            pass

# --- START KOMANDASI (Admin tekshiruvi bilan) ---
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
        text = "👋 Botga xush kelibsiz!\n\n😊 Botdan foydalanishni boshlash uchun pastdagi tugmani bosing."
        await message.answer(text, parse_mode="HTML", reply_markup=start_button())

# --- INSTAGRAM VIDEO YUKLASH (INSTALOADER) ---

@dp.message(F.text == '🎬 Video yuklash')
async def ask_link(message: types.Message):
    await message.answer("🔗 Instagram video linkini yuboring:")

@dp.message(F.text.contains("instagram.com"))
async def get_instagram_video(message: types.Message):
    url = message.text.strip()
    
    try:
        # Linkdan shortcode olish (https://www.instagram.com/reels/C4-xyz/ -> C4-xyz)
        shortcode = url.split("/")[-2] if url.endswith('/') else url.split("/")[-1]
        if "?" in shortcode: shortcode = shortcode.split("?")[0]
    except Exception:
        await message.reply("❌ Link noto'g'ri!")
        return

    loader_msg = await message.answer("⏳ Yuklash boshlandi: 0%\n⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜")
    
    # Progress bar-ni alohida ishga tushiramiz
    progress_task = asyncio.create_task(update_progress(loader_msg))

    try:
        target_dir = f"temp_{uuid.uuid4().hex[:8]}"
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
        
        # Instaloader yuklash (Sinxron funksiyani asinxron kutish)
        loop = asyncio.get_event_loop()
        post = await loop.run_in_executor(None, lambda: instaloader.Post.from_shortcode(loader.context, shortcode))
        await loop.run_in_executor(None, lambda: loader.download_post(post, target=target_dir))

        video_path = None
        for file in os.listdir(target_dir):
            if file.endswith(".mp4"):
                video_path = os.path.join(target_dir, file)
                break

        await progress_task # Progress tugashini kutish

        if video_path:
            await loader_msg.edit_text("✅ Yuklash tugadi! Video yuborilmoqda...")
            
            markup = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🎵 Audioni yuklab olish", callback_data=f"audio_{target_dir}")]
            ])
            
            video = FSInputFile(video_path)
            await message.answer_video(video, caption="✨ @sizning_botingiz orqali yuklab olindi", reply_markup=markup)
            await loader_msg.delete()
        else:
            await loader_msg.edit_text("❌ Video topilmadi yoki xatolik yuz berdi.")
            shutil.rmtree(target_dir, ignore_errors=True)

    except Exception as e:
        await loader_msg.edit_text(f"⚠️ Xatolik: {str(e)}")
        if 'target_dir' in locals(): shutil.rmtree(target_dir, ignore_errors=True)

@dp.callback_query(F.data.startswith("audio_"))
async def get_audio_callback(call: types.CallbackQuery):
    target_dir = call.data.split("_")[1]
    video_path = None
    
    if os.path.exists(target_dir):
        for file in os.listdir(target_dir):
            if file.endswith(".mp4"):
                video_path = os.path.join(target_dir, file)
                break

    if video_path:
        status_msg = await call.message.answer("🎵 Audio ajratib olinmoqda...")
        try:
            audio_name = f"{uuid.uuid4()}.mp3"
            video_clip = VideoFileClip(video_path)
            video_clip.audio.write_audiofile(audio_name, verbose=False, logger=None)
            video_clip.close()

            audio_file = FSInputFile(audio_name)
            await call.message.answer_audio(audio_file, caption="🎵 Videodagi audio")
            os.remove(audio_name)
            await status_msg.delete()
        except Exception as e:
            await call.message.answer(f"❌ Audio xatosi: {e}")
        finally:
            shutil.rmtree(target_dir, ignore_errors=True)
    else:
        await call.answer("📁 Fayl serverdan o'chib ketgan.", show_alert=True)

# --- ADMIN PANEL FUNKSIYALARI (Teginilmagan) ---

@dp.message(F.text == "Userlarni PDF korsh 👥")
async def show_users(message: types.Message):
    if message.from_user.id in ADMIN_ID:
        await check_blocked_users(bot) 
        pdf_file = create_user_pdf()
        await message.answer_document(FSInputFile(pdf_file), caption="👥 Foydalanuvchilar ro‘yxati")

@dp.message(F.text == "Xabar yuborish 📨")
async def xabar_yuborish_boshlash(message: types.Message):
    if message.from_user.id in ADMIN_ID:
        await message.answer("📢 Xabar turini tanlang:", reply_markup=xabar_yubor())

@dp.callback_query(F.data == "img")
async def rasm_bosildi(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("🖼 Rasmni yuboring va unga izoh qo'shishingiz mumkin:")
    await state.set_state(SendImg.image)
    await callback.answer()

@dp.message(SendImg.image, F.photo)
async def rasm_qabul(message: types.Message, state: FSMContext):
    await state.update_data(photo=message.photo[-1].file_id)
    await message.answer("✏️ Endi rasm uchun matn (caption) kiriting:")
    await state.set_state(SendImg.about)

@dp.message(SendImg.about)
async def caption_qabul(message: types.Message, state: FSMContext):
    await state.update_data(about=message.text)
    data = await state.get_data()
    await message.answer_photo(photo=data["photo"], caption=data["about"], parse_mode="HTML")
    await message.answer("📨 Barcha foydalanuvchilarga yuborilsinmi?", reply_markup=send_confirmation_buttons())
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
            await asyncio.sleep(0.05) 
        except:
            continue
    await message.answer(f"✅ {count} ta foydalanuvchiga yuborildi.", reply_markup=user_button())
    await state.clear()

@dp.message(SendImg.confirm, F.text == "Yo‘q ❌")
async def bekor(message: types.Message, state: FSMContext):
    await message.answer("❌ Bekor qilindi.", reply_markup=user_button())
    await state.clear()

# --- ISHGA TUSHIRISH ---

async def main():
    logging.basicConfig(level=logging.INFO)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass