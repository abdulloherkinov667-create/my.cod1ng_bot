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

from buttons.defould import user_button, yoq_button, send_confirmation_buttons
from create import insert_user, users_table, create_user_pdf, get_all_users
from buttons.inline import xabar_yubor, yuborilmasin_sorov
from stets import SendImg


PROXY_URL = 'http://proxy.server:3128'
session = AiohttpSession(proxy=PROXY_URL)

ADMIN_ID = [6411347321]
API_TOKEN = "8301002449:AAEUdfgageMiEIX-qfIAWc73owqOzkRHqtE"

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

bot = Bot(token=API_TOKEN, session=session)
dp = Dispatcher()

loader = instaloader.Instaloader(
    dirname_pattern=DOWNLOAD_DIR,
    download_videos=True,
    download_video_thumbnails=True,
    download_comments=True,
    save_metadata=True
)


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
    
# link tekshirish
    if "instagram.com" not  in url:
        await message.answer("❌ Iltimos, to'g'ri Instagram video linkini yuboring.")
        return
        await message.answer(" ⏳ Video yuklanmoqda, iltimos kuting...")
    
    try:
        match = re.search(r"instagram\.com/p/([a-zA-Z0-9_-]+)", url)
        shortcode = match.group(1) or match.group(2)
        post = instaloader.Post.from_shortcode(loader.context, shortcode)
        loader.download_post(post, DOWNLOAD_DIR)
        
        for fil in os.listdir(DOWNLOAD_DIR):
            if fil.endswith(".mp4"):
                video_path = os.path.join(DOWNLOAD_DIR, fil)
                await message.answer_video(FSInputFile(video_path), caption="""
                📹 Video siz uchun yuklandi!  

✅ Agar sizga yoqsa, boshqa videolarni ham ko‘rishni unutmang!  
🤖 Bot orqali yuklab olish oson: @my_cod1ngbot 
                                           """)
                os.remove(video_path)
                break
            await state.clear()
            
    except:
        await message.answer("""
        ⚠️ Xatolik yuz berdi!

😕 Video yuklab bo‘lmadi. Iltimos, quyidagilarni tekshiring:
1️⃣ Havola to‘g‘ri kiritilganmi
2️⃣ Video mavjudmi
3️⃣ Internet aloqangiz barqarormi

🔄 Qayta /vd_yuklash_boshlash komandasi orqali yana urinib ko‘ring.

🤖 Agar davomiy muammo bo‘lsa, bot orqali yordam so‘rashingiz mumkin: @my_codingpython """)
        await state.clear()


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