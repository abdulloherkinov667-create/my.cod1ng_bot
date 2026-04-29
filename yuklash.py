import os
import uuid
import asyncio

from yt_dlp import YoutubeDL

from aiogram import Dispatcher, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import FSInputFile


# ─────────────────────────────────────────────
#  HOLATLAR
# ─────────────────────────────────────────────
class VideoStates(StatesGroup):
    waiting_for_link = State()


# ─────────────────────────────────────────────
#  QO'LLAB-QUVVATLANADIGAN PLATFORMALAR
# ─────────────────────────────────────────────
SUPPORTED_DOMAINS = [
    "instagram.com",
    "tiktok.com",
    "youtube.com",
    "youtu.be",
    "pinterest.com",
    "pin.it",
    "twitter.com",
    "x.com",
    "facebook.com",
    "fb.watch",
    "vimeo.com",
]

# Tugmalar bosilganda rejimdan chiqish uchun
MAIN_KEYBOARD_BUTTONS = [
    "Userlarni PDF korsh 👥",
    "Userlarni soni 👥",
    "Xabar yuborish 📨",
    "👥 User soni ko'rish",
    "Kino ko'rish 🎥",
    "Shikoyat qilish 📝",
    "🎬 Video yuklash",
]


# ─────────────────────────────────────────────
#  HANDLERLAR
# ─────────────────────────────────────────────
def register_video_handlers(dp: Dispatcher):

    @dp.message(F.text == "🎬 Video yuklash")
    async def start_video_download(message: types.Message, state: FSMContext):
        await state.set_state(VideoStates.waiting_for_link)
        await message.answer(
            "🎬 <b>Video Yuklash</b>\n\n"
            "Quyidagi platformalardan video havolasini yuboring:\n\n"
            "📸 Instagram · 🎵 TikTok · ▶️ YouTube\n"
            "📌 Pinterest · 🐦 Twitter/X · 📘 Facebook\n\n"
            "📎 Havolani yuboring — video avtomatik yuklanadi\n"
            "❌ Bekor qilish: /cancel",
            parse_mode="HTML",
        )

    @dp.message(VideoStates.waiting_for_link)
    async def download_video(message: types.Message, state: FSMContext):
        url = message.text.strip() if message.text else ""

        # Tugma bosilgan bo'lsa — rejimdan chiq
        if url in MAIN_KEYBOARD_BUTTONS:
            await state.clear()
            await message.answer(
                "⚙️ Video yuklash rejimi bekor qilindi.\n"
                "Iltimos, tanlangan tugmani qayta bosing."
            )
            return

        # URL formatini tekshirish
        if not (url.startswith("http://") or url.startswith("https://")):
            await message.answer(
                "❌ <b>Noto'g'ri havola!</b>\n\n"
                "To'liq URL manzilini yuboring.\n"
                "<i>Masalan: https://www.tiktok.com/@user/video/...</i>",
                parse_mode="HTML",
            )
            return

        # Platforma tekshiruvi
        if not any(domain in url for domain in SUPPORTED_DOMAINS):
            await message.answer(
                "⚠️ <b>Qo'llab-quvvatlanmaydigan platforma!</b>\n\n"
                "Faqat quyidagilardan video yuklash mumkin:\n"
                "Instagram · TikTok · YouTube · Pinterest · Twitter/X · Facebook",
                parse_mode="HTML",
            )
            return

        # Yuklash
        os.makedirs("downloads", exist_ok=True)
        filename = os.path.join("downloads", f"{uuid.uuid4()}.mp4")

        ydl_opts = {
            "outtmpl": filename,
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "merge_output_format": "mp4",
            "quiet": True,
            "noplaylist": True,
        }

        status_msg = await message.answer("⏳ Video yuklanmoqda, kuting...")

        actual_file = filename
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: YoutubeDL(ydl_opts).download([url]),
            )

            # yt-dlp ba'zan fayl nomiga qo'shimcha belgi qo'shadi — eng yangi .mp4 ni topamiz
            if not os.path.exists(actual_file):
                candidates = [
                    os.path.join("downloads", f)
                    for f in os.listdir("downloads")
                    if f.endswith(".mp4")
                ]
                if candidates:
                    actual_file = max(candidates, key=os.path.getmtime)

            await status_msg.delete()
            await message.answer_video(
                FSInputFile(actual_file),
                caption="✅ Video yuklandi! Boshqa havola yuboring yoki /cancel bosing.",
            )

        except Exception:
            await status_msg.delete()
            await message.answer(
                "❌ <b>Video yuklab bo'lmadi.</b>\n\n"
                "Mumkin sabablar:\n"
                "• Havola noto'g'ri yoki eskirgan\n"
                "• Video yopiq/shaxsiy akkauntda\n"
                "• Platforma cheklovlari\n\n"
                "Boshqa havola yuboring yoki /cancel bosing.",
                parse_mode="HTML",
            )

        finally:
            for f in set([filename, actual_file]):
                if f and os.path.exists(f):
                    try:
                        os.remove(f)
                    except Exception:
                        pass

    @dp.message(F.text == "/cancel")
    async def cancel_video_upload(message: types.Message, state: FSMContext):
        await state.clear()
        await message.answer(
            "❌ Video yuklash rejimi bekor qilindi.\n"
            "Qayta boshlash uchun 🎬 Video yuklash tugmasini bosing."
        )