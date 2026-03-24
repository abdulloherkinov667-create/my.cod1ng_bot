import asyncio
import logging
import os
import re
import shutil
import telebot
import instaloader
import os
from telebot import types
from moviepy import VideoFileClip
import uuid
import shutil

from yt_dlp import YoutubeDL
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import FSInputFile
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.client.session.aiohttp import AiohttpSession
from buttons.defould import start_button


from buttons.defould import user_button, send_confirmation_buttons
from create import insert_user, users_table, create_user_pdf, get_all_users, check_blocked_users
from buttons.inline import xabar_yubor
from stets import SendImg



API_TOKEN = "8054850246:AAFrie9TuamBBWYrEOzpu1E3jxuh1jFUPnw"


bot = Bot(token=API_TOKEN)
dp = Dispatcher()

ADMIN_ID = [6411347321, 8327989068]

bot = telebot.TeleBot(API_TOKEN)

loader = instaloader.Instaloader(
    download_comments=False,
    download_geotags=False,
    download_pictures=False,
    download_video_thumbnails=False,
    save_metadata=False
)

video_file = None
folder_name = None



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
        text = (
            """
            👋 Botga xush kelibsiz!

😊 Botdan foydalanishni boshlash uchun pastda joylashgan tugmalardan birini tanlang.

👇 Davom etish uchun pastdagi tugmani bosing.

✨ Shundan so‘ng sizga keyingi qadamlar ko‘rsatib beriladi.
            """
        )
        await message.answer(text, parse_mode="HTML", reply_markup=start_button())



bot.message_handler(F.text == '🎬 Video yuklash')
def start(message):
    bot.send_message(message.chat.id, "intagram linkini yuboring")


@bot.message_handler(func=lambda message: True)
def get_instagram_video(message):
    global video_file, folder_name
    url = message.text.strip()

    try:
        shortcode = url.split("/")[-2]
        folder_name = shortcode
    except IndexError:
        bot.reply_to(message, "link notogri")
        return

    loader_message = bot.send_message(message.chat.id, "video yuklanyapti...")

    try:
        post = instaloader.Post.from_shortcode(loader.context, shortcode)
        loader.download_post(post, target=shortcode)

        for file in os.listdir(shortcode):
            if file.endswith(".mp4"):
                video_file = os.path.join(shortcode, file)
                break

        if video_file:
            with open(video_file, "rb") as video:
                markup = types.InlineKeyboardMarkup()
                btn1 = types.InlineKeyboardButton("audioni yuklab olish", callback_data="get_audio")
                markup.add(btn1)
                bot.send_video(message.chat.id, video, reply_markup=markup)
            bot.delete_message(message.chat.id, loader_message.message_id)
        else:
            bot.delete_message(message.chat.id, loader_message.message_id)
            bot.reply_to(message, "video topilmadi")

    except Exception as e:
        bot.delete_message(message.chat.id, loader_message.message_id)
        bot.reply_to(message, f"xatoli: {e}")


@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    global video_file, folder_name
    if call.data == "get_audio":
        try:
            bot.send_message(call.message.chat.id, "audio yuklanyapti...")

            video = VideoFileClip(video_file)
            audio = video.audio
            audio_name = f"{uuid.uuid4()}.mp3"
            audio.write_audiofile(audio_name)
            video.close()

            with open(audio_name, "rb") as audio_:
                bot.send_audio(call.message.chat.id, audio_)
            os.remove(audio_name)

        except Exception as e:
            bot.reply_to(call.message, f"audio yuklashda xatolik: {e}")
        finally:
            if os.path.exists(folder_name):
                shutil.rmtree(folder_name, ignore_errors=True)

@dp.message(F.text == "Userlarni PDF korsh 👥")
async def show_users(message: types.Message):
    if message.from_user.id in ADMIN_ID:
        await check_blocked_users(bot)
        pdf_file = create_user_pdf()
        await message.answer_document(FSInputFile(pdf_file), caption="""
👥 Foydalanuvchilar ro‘yxatini
                                      """)


@dp.message(F.text == "Xabar yuborish 📨")
async def xabar_yuborish_boshlash(message: types.Message):
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
    await message.answer(f"✅ {count} ta foydalanuvchiga yuborildi.", reply_markup=types.ReplyKeyboardRemove())
    await state.clear()


@dp.message(SendImg.confirm, F.text == "Yo‘q ❌")
async def bekor(message: types.Message, state: FSMContext):
    await message.answer("❌ Bekor qilindi.", reply_markup=types.ReplyKeyboardRemove())
    await state.clear()


async def main():
    logging.basicConfig(level=logging.INFO)

    try:
        await bot.delete_webhook(drop_pending_updates=True)
    except Exception:
        pass

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
