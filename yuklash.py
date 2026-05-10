import os
import uuid
import asyncio
import glob
import logging
from yt_dlp import YoutubeDL

from aiogram import Dispatcher, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import FSInputFile, InputMediaPhoto

logger = logging.getLogger(__name__)


class VideoStates(StatesGroup):
    waiting_for_link = State()


SUPPORTED_DOMAINS = [
    "instagram.com", "tiktok.com",
    "youtube.com", "youtu.be",
    "pinterest.com", "pin.it",
    "twitter.com", "x.com",
    "facebook.com", "fb.watch",
    "vimeo.com",
]

MAIN_KEYBOARD_BUTTONS = [
    "Userlarni PDF korsh 👥",
    "Userlarni soni 👥",
    "Xabar yuborish 📨",
    "👥 User soni ko'rish",
    "Kino ko'rish 🎥",
    "Shikoyat qilish 📝",
    "🎬 Video yuklash",
]

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
VIDEO_EXTS = {".mp4", ".mkv", ".webm", ".mov", ".avi"}
DOWNLOAD_DIR = "downloads"


# ── Yordamchi funksiyalar ──────────────────────────────────────────────────────

def file_type(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    if ext in VIDEO_EXTS:  return "video"
    if ext in IMAGE_EXTS:  return "image"
    return "other"


def find_files(uid: str) -> list[str]:
    return glob.glob(os.path.join(DOWNLOAD_DIR, f"{uid}*"))


def cleanup(uid: str):
    for f in find_files(uid):
        try: os.remove(f)
        except Exception: pass


# ── Asosiy yuklash ─────────────────────────────────────────────────────────────

async def download(url: str, uid: str) -> list[str]:
    """
    Bir marta yuklab, natijani qaytaradi.
    extract_info + download — ikki qadam yo'q, faqat bitta download().
    """
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    # Instagram/TikTok carousel uchun noplaylist=False
    is_multi = any(d in url for d in ["instagram.com", "tiktok.com"])

    base = {
        "outtmpl": os.path.join(DOWNLOAD_DIR, f"{uid}.%(autonumber)s.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
        "noplaylist": not is_multi,
        "socket_timeout": 30,
        "retries": 3,
        "fragment_retries": 3,
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        },
    }

    loop = asyncio.get_event_loop()

    # ── 1-urinish: mp4 video ──────────────────────────────────────────────────
    opts1 = {
        **base,
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "merge_output_format": "mp4",
    }
    try:
        await loop.run_in_executor(None, lambda: YoutubeDL(opts1).download([url]))
        files = [f for f in find_files(uid) if file_type(f) == "video"]
        if files:
            return files
    except Exception as e:
        logger.warning(f"1-urinish xato: {e}")

    # ── 2-urinish: har qanday format (rasm ham) ───────────────────────────────
    opts2 = {**base, "format": "best"}
    try:
        await loop.run_in_executor(None, lambda: YoutubeDL(opts2).download([url]))
        files = [f for f in find_files(uid) if file_type(f) in ("video", "image")]
        if files:
            return files
    except Exception as e:
        logger.warning(f"2-urinish xato: {e}")

    # ── 3-urinish: thumbnail (faqat rasm postlar uchun) ──────────────────────
    opts3 = {
        **base,
        "outtmpl": os.path.join(DOWNLOAD_DIR, f"{uid}.thumb.%(ext)s"),
        "skip_download": True,
        "writethumbnail": True,
        "postprocessors": [{"key": "FFmpegThumbnailsConvertor", "format": "jpg"}],
    }
    try:
        await loop.run_in_executor(None, lambda: YoutubeDL(opts3).download([url]))
        files = [f for f in find_files(uid) if file_type(f) == "image"]
        if files:
            return files
    except Exception as e:
        logger.warning(f"3-urinish xato: {e}")

    return []


# ── Yuborish ───────────────────────────────────────────────────────────────────

async def send_media(message: types.Message, files: list[str]):
    videos = [f for f in files if file_type(f) == "video"]
    images = [f for f in files if file_type(f) == "image"]
    caption = "✅ Yuklandi! Yana havola yuboring yoki /cancel bosing."

    for path in videos:
        mb = os.path.getsize(path) / 1024 / 1024
        if mb > 49:
            await message.answer(f"⚠️ Video {mb:.1f} MB — Telegram 50 MB dan katta faylni qabul qilmaydi.")
            continue
        await message.answer_video(FSInputFile(path), caption=caption)
        caption = None

    if images and not videos:
        if len(images) == 1:
            await message.answer_photo(FSInputFile(images[0]), caption=caption)
        else:
            group = [
                InputMediaPhoto(
                    media=FSInputFile(p),
                    caption=caption if i == 0 else None,
                )
                for i, p in enumerate(images[:10])
            ]
            await message.answer_media_group(group)


# ── Handler'lar ────────────────────────────────────────────────────────────────

RESTRICTED_USERS = [8377358077]

def register_video_handlers(dp: Dispatcher):

    @dp.message(F.text == "🎬 Video yuklash")
    async def start(message: types.Message, state: FSMContext):
        if message.from_user.id in RESTRICTED_USERS:
            await message.answer("⛔ Sangaa bunday huquq yo'q")
            return
        await state.set_state(VideoStates.waiting_for_link)
        await message.answer(
            "🎬 <b>Video / Rasm Yuklash</b>\n\n"
            "Havola tashlang — yuklab beraman!\n\n"
            "📸 Instagram · 🎵 TikTok · ▶️ YouTube\n"
            "📌 Pinterest · 🐦 Twitter/X · 📘 Facebook\n\n"
            "❌ Bekor qilish: /cancel",
            parse_mode="HTML",
        )

    @dp.message(VideoStates.waiting_for_link)
    async def handle_link(message: types.Message, state: FSMContext):
        url = (message.text or "").strip()

        # Tugma bosildi
        if url in MAIN_KEYBOARD_BUTTONS:
            await state.clear()
            await message.answer("⚙️ Rejim bekor qilindi. Tugmani qayta bosing.")
            return

        # /cancel
        if url.lower() == "/cancel":
            await state.clear()
            await message.answer("❌ Bekor qilindi.")
            return

        # URL tekshiruvi
        if not url.startswith(("http://", "https://")):
            await message.answer(
                "❌ <b>Noto'g'ri havola!</b>\n"
                "<i>Masalan: https://www.tiktok.com/@user/video/...</i>",
                parse_mode="HTML",
            )
            return

        # Platforma tekshiruvi
        if not any(d in url for d in SUPPORTED_DOMAINS):
            await message.answer(
                "⚠️ <b>Qo'llab-quvvatlanmaydigan platforma!</b>\n\n"
                "Instagram · TikTok · YouTube · Pinterest · Twitter/X · Facebook",
                parse_mode="HTML",
            )
            return

        uid = str(uuid.uuid4())
        status = await message.answer("⏳ Yuklanmoqda...", parse_mode="HTML")

        try:
            files = await download(url, uid)
            await status.delete()

            if not files:
                await message.answer(
                    "❌ <b>Yuklab bo'lmadi.</b>\n\n"
                    "• Havola noto'g'ri yoki eskirgan\n"
                    "• Yopiq / shaxsiy akkaunt\n"
                    "• Platforma cheklovlari\n\n"
                    "Boshqa havola yuboring yoki /cancel bosing.",
                    parse_mode="HTML",
                )
                return

            await send_media(message, files)

        except Exception as e:
            logger.error(f"Xato: {e}", exc_info=True)
            try: await status.delete()
            except Exception: pass
            await message.answer("❌ Xato yuz berdi. Qayta urinib ko'ring.")

        finally:
            cleanup(uid)

    @dp.message(F.text == "/cancel")
    async def cancel(message: types.Message, state: FSMContext):
        await state.clear()
        await message.answer("❌ Bekor qilindi. 🎬 Video yuklash tugmasini bosing.")