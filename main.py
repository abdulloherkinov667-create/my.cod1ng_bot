import asyncio
import logging
import re
import os
import yt_dlp

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import FSInputFile
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.client.session.aiohttp import AiohttpSession

from buttons.defould import user_button, yoq_button, send_confirmation_buttons
from create import insert_user, users_table, create_user_pdf, get_all_users
from buttons.inline import xabar_yubor, yuborilmasin_sorov
from stets import SendImg



PROXY_URL = 'http://proxy.server:3128'
session = AiohttpSession(proxy=PROXY_URL)


DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


ADMIN_ID = [6411347321]
API_TOKEN = "8301002449:AAHoIQ5PFqLzG1qU-ctYab1QZFZptI6Y8dw"


bot = Bot(token=API_TOKEN, session=session)
dp = Dispatcher()


class VideoState(StatesGroup):
    waiting_for_link = State()



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
            "Siz bot administratorisiz.\n\n"
            "Kerakli bo‘limni tanlang 👇"
        )
        await message.answer(text, reply_markup=user_button(), parse_mode="HTML")
    else:
        text = (
            "👋 <b>Botga xush kelibsiz!</b>\n\n"
            "📥 <b>/vd_yuklash_boshlash</b> buyrug'ini bosing."
        )
        await message.answer(text, parse_mode="HTML")



@dp.message(lambda m: m.text == "/vd_yuklash_boshlash")
async def vd_yukla_buyruq(message: types.Message, state: FSMContext):
    await state.set_state(VideoState.waiting_for_link)
    await message.answer("📥 Instagram video linkini yuboring")



@dp.message(VideoState.waiting_for_link)
async def vd_yuklash(message: types.Message, state: FSMContext):
    url = message.text
    if "instagram.com" not in url:
        await message.answer("❌ Iltimos, to'g'ri Instagram linkini yuboring.")
        return

    status_msg = await message.answer("⌛ Video qayta ishlanmoqda...")
    
    ydl_opts = {
        'format': 'best',
        'outtmpl': f'{DOWNLOAD_DIR}/%(id)s.%(ext)s',
        'merge_output_format': 'mp4',
        'quiet': True,
        'no_warnings': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.instagram.com/',
        },

    }

    try:
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(None, lambda: download_video(url, ydl_opts))
        
        if info:
            file_path = info.get('file_path')
            video_file = FSInputFile(file_path)
            
            await message.answer_video(
                video_file, 
                caption="✅ Video tayyor!\n\n@my_codingbot",
                parse_mode="HTML"
            )
            
            if os.path.exists(file_path):
                os.remove(file_path)
        else:
            raise Exception("Ma'lumot topilmadi")

    except Exception as e:
        error_str = str(e)
        if "429" in error_str or "Too Many Requests" in error_str:
            await message.answer("⚠️ Instagram juda ko'p so'rov yuborganimiz uchun bizni vaqtincha chekladi. 10-15 daqiqa kuting.")
        elif "403" in error_str:
            await message.answer("🚫 Bu video yopiq profildan yoki ruxsat berilmagan hududdan olingan.")
        else:
            await message.answer("⚠️ Xatolik yuz berdi. Linkni tekshiring yoki keyinroq urinib ko'ring.")
        print(f"Log xatosi: {e}")
    
    finally:
        await status_msg.delete()
        await state.clear()

# Alohida yordamchi funksiya (yt-dlp uchun)
def download_video(url, opts):
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return {
            'file_path': ydl.prepare_filename(info),
            'id': info.get('id')
        }



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
        except: continue
    await message.answer(f"✅ {count} ta foydalanuvchiga yuborildi.", reply_markup=types.ReplyKeyboardRemove())
    await state.clear()



@dp.message(SendImg.confirm, F.text == "Yo‘q ❌")
async def bekor(message: types.Message, state: FSMContext):
    await message.answer("❌ Bekor qilindi.", reply_markup=types.ReplyKeyboardRemove())
    await state.clear()






async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())