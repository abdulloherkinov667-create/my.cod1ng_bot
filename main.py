import asyncio
import logging
import os
import shutil
import uuid
from typing import Optional

import instaloader
from moviepy import VideoFileClip
from yt_dlp import YoutubeDL

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.client.session.aiohttp import AiohttpSession

from buttons.defould import start_button, user_button, send_confirmation_buttons
from create import insert_user, users_table, create_user_pdf, get_all_users, check_blocked_users
from buttons.inline import xabar_yubor
from stets import SendImg

API_TOKEN = "8301002449:AAFzKdU48I4Q0nuTxDnY9725MITFVA7w9ok"

# Bot va dispatcher
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

ADMIN_ID = [6411347321, 8327989068]

# Instaloader konfiguratsiyasi
loader = instaloader.Instaloader(
    download_comments=False,
    download_geotags=False,
    download_pictures=False,
    download_video_thumbnails=False,
    save_metadata=False
)


# States
class VideoStates(StatesGroup):
    waiting_for_url = State()


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
        text = """
👋 Botga xush kelibsiz!

😊 Botdan foydalanishni boshlash uchun pastda joylashgan tugmalardan birini tanlang.

👇 Davom etish uchun pastdagi tugmani bosing.

✨ Shundan so‘ng sizga keyingi qadamlar ko‘rsatib beriladi.
        """
        await message.answer(text, parse_mode="HTML", reply_markup=start_button())


@dp.message(F.text == "🎬 Video yuklash")
async def start_video_download(message: types.Message, state: FSMContext):
    await state.set_state(VideoStates.waiting_for_url)
    await message.answer("📥 Instagram video linkini yuboring:")


@dp.message(VideoStates.waiting_for_url)
async def get_instagram_video(message: types.Message, state: FSMContext):
    url = message.text.strip()
    
    # URL validatsiyasi
    if not url.startswith(('https://www.instagram.com/', 'https://instagram.com/')):
        await message.answer("❌ Noto'g'ri link! Iltimos, Instagram video linkini yuboring.")
        return
    
    try:
        # Shortcode ni olish
        if '/p/' in url:
            shortcode = url.split('/p/')[1].split('/')[0]
        elif '/reel/' in url:
            shortcode = url.split('/reel/')[1].split('/')[0]
        else:
            await message.answer("❌ Link noto'g'ri formatda!")
            return
        
        folder_name = shortcode
        
        # Yuklab olish jarayoni haqida xabar
        loading_msg = await message.answer("⏳ Video yuklanmoqda, iltimos kuting...")
        
        try:
            # Postni yuklab olish
            post = instaloader.Post.from_shortcode(loader.context, shortcode)
            loader.download_post(post, target=folder_name)
            
            # Video faylni topish
            video_file = None
            for file in os.listdir(folder_name):
                if file.endswith(".mp4"):
                    video_file = os.path.join(folder_name, file)
                    break
            
            if video_file and os.path.exists(video_file):
                # Audio olish uchun inline keyboard
                markup = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="🎵 Audioni yuklab olish", callback_data=f"get_audio:{video_file}:{folder_name}")]
                    ]
                )
                
                # Videoni yuborish
                with open(video_file, 'rb') as video:
                    await message.answer_video(
                        video=types.BufferedInputFile(video.read(), filename=f"instagram_{shortcode}.mp4"),
                        caption="✅ Video tayyor!",
                        reply_markup=markup
                    )
                
                # Yuklab olish papkasini keyinroq tozalash uchun saqlaymiz
                # (callback orqali tozalanadi)
                
            else:
                await message.answer("❌ Video topilmadi!")
                
            # Yuklanish papkasini tozalash (video yuborilgandan keyin)
            if os.path.exists(folder_name):
                shutil.rmtree(folder_name, ignore_errors=True)
                
        except Exception as e:
            await message.answer(f"❌ Xatolik: {str(e)}")
            if os.path.exists(folder_name):
                shutil.rmtree(folder_name, ignore_errors=True)
                
        finally:
            await loading_msg.delete()
            
    except Exception as e:
        await message.answer(f"❌ Xatolik yuz berdi: {str(e)}")
    
    await state.clear()


@dp.callback_query(F.data.startswith("get_audio:"))
async def get_audio(callback: types.CallbackQuery):
    data_parts = callback.data.split(":", 2)
    if len(data_parts) < 3:
        await callback.answer("Xatolik yuz berdi!")
        return
        
    video_file = data_parts[1]
    folder_name = data_parts[2]
    
    loading_msg = await callback.message.answer("🎵 Audio yuklanmoqda, iltimos kuting...")
    
    try:
        # Videodan audio ajratish
        video = VideoFileClip(video_file)
        audio = video.audio
        
        if audio is not None:
            audio_name = f"{uuid.uuid4()}.mp3"
            audio.write_audiofile(audio_name, logger=None)
            video.close()
            
            # Audioni yuborish
            with open(audio_name, 'rb') as audio_file:
                await callback.message.answer_audio(
                    audio=types.BufferedInputFile(audio_file.read(), filename=audio_name),
                    caption="🎵 Audio tayyor!"
                )
                
            os.remove(audio_name)
        else:
            await callback.message.answer("❌ Bu videoda audio yo'q!")
            
    except Exception as e:
        await callback.message.answer(f"❌ Audio yuklashda xatolik: {str(e)}")
    finally:
        await loading_msg.delete()
        
        # Papkani tozalash
        if os.path.exists(folder_name):
            shutil.rmtree(folder_name, ignore_errors=True)
    
    await callback.answer()


@dp.message(F.text == "Userlarni PDF korsh 👥")
async def show_users(message: types.Message):
    if message.from_user.id in ADMIN_ID:
        loading_msg = await message.answer("⏳ PDF tayyorlanmoqda...")
        try:
            await check_blocked_users(bot)
            pdf_file = create_user_pdf()
            await message.answer_document(
                FSInputFile(pdf_file), 
                caption="👥 Foydalanuvchilar ro‘yxati"
            )
        except Exception as e:
            await message.answer(f"❌ Xatolik: {str(e)}")
        finally:
            await loading_msg.delete()
    else:
        await message.answer("⛔ Bu buyruq faqat adminlar uchun!")


@dp.message(F.text == "Xabar yuborish 📨")
async def xabar_yuborish_boshlash(message: types.Message):
    if message.from_user.id in ADMIN_ID:
        await message.answer("""
📢 Xabar yuborish bo‘limi

✉️ Foydalanuvchilarga yuboriladigan xabar turini tanlang.

📝 Siz quyidagi formatlardan birini tanlashingiz mumkin:

• Matn (text)
• Rasm (photo)
• Video

⚙️ Tanlagan turga qarab keyingi bosqichlar ko‘rsatib beriladi.

👇 Davom etish uchun xabar turini tanlang.
        """, reply_markup=xabar_yubor())
    else:
        await message.answer("⛔ Bu buyruq faqat adminlar uchun!")


@dp.callback_query(F.data == "img")
async def rasm_bosildi(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("""
🖼 Rasm yuborish

📸 Iltimos, foydalanuvchilarga yubormoqchi bo‘lgan rasmingizni yuboring.

✏️ Rasm bilan birga izoh (caption) ham qo‘shishingiz mumkin.

⚡ Yuborilgan rasm barcha tanlangan foydalanuvchilarga yetkaziladi.

👇 Endi rasmni yuboring.
    """)
    await state.set_state(SendImg.image)
    await callback.answer()


@dp.message(SendImg.image, F.photo)
async def rasm_qabul(message: types.Message, state: FSMContext):
    await state.update_data(photo=message.photo[-1].file_id)
    await message.answer("""
✏️ Rasm uchun izoh qo‘shish

📝 Endi yuborilgan rasm uchun matn (caption) kiriting.
    """)
    await state.set_state(SendImg.about)


@dp.message(SendImg.about, F.text)
async def caption_qabul(message: types.Message, state: FSMContext):
    await state.update_data(about=message.text)
    data = await state.get_data()
    await message.answer_photo(
        photo=data["photo"], 
        caption=data["about"], 
        parse_mode="HTML"
    )
    await message.answer("📨 Yuborilsinmi?", reply_markup=send_confirmation_buttons())
    await state.set_state(SendImg.confirm)


@dp.message(SendImg.confirm, F.text == "Xa ✅")
async def yubor(message: types.Message, state: FSMContext):
    data = await state.get_data()
    users = get_all_users()
    count = 0
    
    loading_msg = await message.answer("⏳ Xabarlar yuborilmoqda...")
    
    for user in users:
        try:
            await bot.send_photo(
                chat_id=user[3],  # chat_id
                photo=data["photo"], 
                caption=data["about"]
            )
            count += 1
            await asyncio.sleep(0.1)  # Rate limit uchun
        except Exception:
            continue
    
    await loading_msg.delete()
    await message.answer(f"✅ {count} ta foydalanuvchiga yuborildi.", reply_markup=types.ReplyKeyboardRemove())
    await state.clear()


@dp.message(SendImg.confirm, F.text == "Yo‘q ❌")
async def bekor(message: types.Message, state: FSMContext):
    await message.answer("❌ Bekor qilindi.", reply_markup=types.ReplyKeyboardRemove())
    await state.clear()


# Matn xabar yuborish uchun (agar kerak bo'lsa)
@dp.callback_query(F.data == "text")
async def text_xabar_boshlash(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("📝 Yubormoqchi bo'lgan matningizni yozing:")
    await state.set_state(SendImg.text_message)
    await callback.answer()


@dp.message(SendImg.text_message, F.text)
async def text_xabar_qabul(message: types.Message, state: FSMContext):
    await state.update_data(text_message=message.text)
    await message.answer(f"📨 Yuboriladigan matn:\n\n{message.text}\n\nYuborilsinmi?", 
                        reply_markup=send_confirmation_buttons())
    await state.set_state(SendImg.confirm_text)


@dp.message(SendImg.confirm_text, F.text == "Xa ✅")
async def text_xabar_yubor(message: types.Message, state: FSMContext):
    data = await state.get_data()
    users = get_all_users()
    count = 0
    
    loading_msg = await message.answer("⏳ Xabarlar yuborilmoqda...")
    
    for user in users:
        try:
            await bot.send_message(
                chat_id=user[3],
                text=data["text_message"]
            )
            count += 1
            await asyncio.sleep(0.1)
        except Exception:
            continue
    
    await loading_msg.delete()
    await message.answer(f"✅ {count} ta foydalanuvchiga yuborildi.", reply_markup=types.ReplyKeyboardRemove())
    await state.clear()


@dp.message(SendImg.confirm_text, F.text == "Yo‘q ❌")
async def text_xabar_bekor(message: types.Message, state: FSMContext):
    await message.answer("❌ Bekor qilindi.", reply_markup=types.ReplyKeyboardRemove())
    await state.clear()


async def main():
    logging.basicConfig(level=logging.INFO)
    
    try:
        await bot.delete_webhook(drop_pending_updates=True)
    except Exception as e:
        logging.error(f"Webhook delete error: {e}")
    
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())