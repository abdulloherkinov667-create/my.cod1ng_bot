import os
import uuid
from yt_dlp import YoutubeDL

from aiogram import Dispatcher, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import FSInputFile

class InstagramStates(StatesGroup):
    waiting_for_reel = State()


def register_video_handlers(dp: Dispatcher):
    @dp.message(F.text == "🎬 Video yuklash")
    async def start_video_download(message: types.Message, state: FSMContext):
        await state.set_state(InstagramStates.waiting_for_reel)
        await message.answer(
            "🎬 VIDEO YUKLASH MODEMI\n\n"
            "📎 Iltimos, Instagram video linkini yuboring.\n"
            "🔁 Bu holat to‘xtamaguncha video linklarini qabul qiladi.\n"
            "❌ Agar bekor qilmoqchi bo‘lsangiz /cancel buyrug‘ini bosing.\n\n"
            "⏳ Video avtomatik yuklab olinadi"
        )

    @dp.message(InstagramStates.waiting_for_reel)
    async def download_reel(message: types.Message, state: FSMContext):
        url = message.text.strip()

        if url == "🎬 Video yuklash":
            await message.answer("📌 Siz hozir video yuklash rejimidasiz. Iltimos, Instagram video linkini yuboring yoki /cancel buyrug‘ini bosing.")
            return

        main_keyboard_buttons = [
            "Userlarni PDF korsh 👥",
            "Userlarni soni 👥",
            "Xabar yuborish 📨",
            "👥 User soni ko‘rish"
        ]

        if url in main_keyboard_buttons:
            await state.clear()
            await message.answer("⚙️ Oldingi video yuklash rejimi bekor qilindi. Iltimos, yangi tugmani qayta bosing.")
            return

        if not (url.startswith("http://") or url.startswith("https://")):
            await message.answer("❌ Iltimos, amaldagi URL yuboring. Masalan: https://www.instagram.com/reel/...")
            return

        if "instagram.com" not in url:
            await message.answer("❌ Faqat Instagram manzilni qabul qilamiz (instagram.com).")
            return

        if not any(k in url for k in ["/reel/", "/p/", "/tv/", "/stories/"]):
            await message.answer("⚠️ Mumkin bo‘lgan Instagram video linkini yuboring (reel/p/tv).")
            return

        os.makedirs("downloads", exist_ok=True)
        filename = os.path.join("downloads", f"{uuid.uuid4()}.mp4")
        ydl_opts = {
            'outtmpl': filename,
            'format': 'mp4',
            'quiet': True,
            'noplaylist': True
        }

        try:
            await message.answer("⏳ Video yuklanmoqda...")
            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            await message.answer_video(FSInputFile(filename))

        except Exception:
            await message.answer("⚠️ Video yuklab bo‘lmadi, boshqa link yuboring.")

        finally:
            if os.path.exists(filename):
                os.remove(filename)

    @dp.message(F.text == "/cancel")
    async def cancel_video_upload(message: types.Message, state: FSMContext):
        await state.clear()
        await message.answer("❌ Video yuklash rejimi bekor qilindi. Qayta boshlash uchun 🎬 Video yuklash tugmasini bosib, link yuboring.")
