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


def cleanup_uid(uid: str):
    for f in glob.glob(os.path.join(DOWNLOAD_DIR, f"{uid}*")):
        try:
            os.remove(f)
        except Exception:
            pass


def find_files(uid: str) -> list[str]:
    return glob.glob(os.path.join(DOWNLOAD_DIR, f"{uid}*"))


def file_type(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    if ext in VIDEO_EXTS:
        return "video"
    if ext in IMAGE_EXTS:
        return "image"
    return "other"


async def run_ydl(opts: dict, url: str):
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, lambda: YoutubeDL(opts).download([url]))


async def smart_download(url: str, uid: str) -> list[str]:
    """
    URL dan video yuklab oladi.
    Faqat video bo'lsa yuklaydi, rasm yuklamaydi.
    """
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    tmpl = os.path.join(DOWNLOAD_DIR, f"{uid}.%(ext)s")

    noplaylist = not any(d in url for d in ["instagram.com", "tiktok.com"])

    base_opts = {
        "outtmpl": tmpl,
        "quiet": True,
        "no_warnings": True,
        "noplaylist": noplaylist,
        "socket_timeout": 30,
        "retries": 5,
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        },
    }

    # --- 1. Info olish: bu URL video o'z ichidami? ---
    has_video = False
    try:
        loop = asyncio.get_event_loop()
        info_opts = {**base_opts, "skip_download": True}
        info = await loop.run_in_executor(
            None,
            lambda: YoutubeDL(info_opts).extract_info(url, download=False),
        )
        if info:
            vcodec = info.get("vcodec", "none")
            entries = info.get("entries")  # playlist/album/carousel
            if entries:
                for e in entries:
                    if e and e.get("vcodec", "none") not in (None, "none"):
                        has_video = True
                        break
            else:
                has_video = vcodec not in (None, "none")
    except Exception as e:
        logger.warning(f"Info extraction xato: {e}")
        has_video = True  # info ololmadik — video deb sinab ko'ramiz

    # --- 2. Video yuklab olish ---
    if has_video:
        video_opts = {
            **base_opts,
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "merge_output_format": "mp4",
        }
        try:
            await run_ydl(video_opts, url)
            files = [f for f in find_files(uid) if file_type(f) == "video"]
            if files:
                return files
        except Exception as e:
            logger.warning(f"Video yuklash xato: {e}")

        # Fallback: har qanday format
        any_opts = {**base_opts, "format": "best"}
        try:
            await run_ydl(any_opts, url)
            files = [f for f in find_files(uid) if file_type(f) == "video"]
            if files:
                return files
        except Exception as e:
            logger.warning(f"Fallback yuklash xato: {e}")

    # Video yo'q bo'lsa, hech narsa yuklamaymiz
    return []


async def send_files(message: types.Message, files: list[str]):
    caption = "✅ Yuklandi! Yana havola yuboring yoki /cancel bosing."
    videos = [f for f in files if file_type(f) == "video"]
    images = [f for f in files if file_type(f) == "image"]

    for path in videos:
        size_mb = os.path.getsize(path) / 1024 / 1024
        if size_mb > 49:
            await message.answer(
                f"⚠️ Video {size_mb:.1f} MB — Telegram 50 MB dan katta faylni qabul qilmaydi."
            )
            continue
        await message.answer_video(FSInputFile(path), caption=caption)
        caption = None

    if images:
        if len(images) == 1:
            await message.answer_photo(
                FSInputFile(images[0]),
                caption=caption or "✅ Rasm yuklandi!"
            )
        else:
            media = [
                InputMediaPhoto(
                    media=FSInputFile(p),
                    caption=(caption or "✅ Rasmlar yuklandi!") if i == 0 else None,
                )
                for i, p in enumerate(images[:10])
            ]
            await message.answer_media_group(media)


def register_video_handlers(dp: Dispatcher):

    @dp.message(F.text == "🎬 Video yuklash")
    async def start_video_download(message: types.Message, state: FSMContext):
        await state.set_state(VideoStates.waiting_for_link)
        await message.answer(
            "🎬 <b>Video Yuklash</b>\n\n"
            "Havola tashlang — video yuklab beraman!\n\n"
            "📸 Instagram · 🎵 TikTok · ▶️ YouTube\n"
            "📌 Pinterest · 🐦 Twitter/X · 📘 Facebook\n\n"
            "❌ Bekor qilish: /cancel",
            parse_mode="HTML",
        )

    @dp.message(VideoStates.waiting_for_link)
    async def handle_link(message: types.Message, state: FSMContext):
        url = (message.text or "").strip()

        if url in MAIN_KEYBOARD_BUTTONS:
            await state.clear()
            await message.answer("⚙️ Rejim bekor qilindi. Tugmani qayta bosing.")
            return

        if url == "/cancel":
            await state.clear()
            await message.answer("❌ Bekor qilindi. 🎬 Video yuklash tugmasini bosing.")
            return

        if not (url.startswith("http://") or url.startswith("https://")):
            await message.answer(
                "❌ <b>Noto'g'ri havola!</b>\n\n"
                "To'liq URL yuboring.\n"
                "<i>Masalan: https://www.instagram.com/p/ABC123/</i>",
                parse_mode="HTML",
            )
            return

        if not any(d in url for d in SUPPORTED_DOMAINS):
            await message.answer(
                "⚠️ <b>Qo'llab-quvvatlanmaydigan platforma!</b>\n\n"
                "Instagram · TikTok · YouTube · Pinterest · Twitter/X · Facebook",
                parse_mode="HTML",
            )
            return

        uid = str(uuid.uuid4())
        status = await message.answer("⏳ <b>Yuklanmoqda...</b>", parse_mode="HTML")

        try:
            files = await smart_download(url, uid)
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

            await send_files(message, files)

        except Exception as e:
            logger.error(f"Xato: {e}", exc_info=True)
            try:
                await status.delete()
            except Exception:
                pass
            await message.answer("❌ Kutilmagan xato yuz berdi. Qayta urinib ko'ring.")
        finally:
            cleanup_uid(uid)
            for f in glob.glob(os.path.join(DOWNLOAD_DIR, f"{uid}_img*")):
                try:
                    os.remove(f)
                except Exception:
                    pass

    @dp.message(F.text == "/cancel")
    async def cancel_video(message: types.Message, state: FSMContext):
        await state.clear()
        await message.answer("❌ Bekor qilindi. 🎬 Video yuklash tugmasini bosing.")