import re
import os
import instaloader

from unittest import loader
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import FSInputFile
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from buttons.defould import start_button
from main import VideoState



dp = Dispatcher()
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)



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