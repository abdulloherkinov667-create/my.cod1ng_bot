import os
import uuid
import asyncio
import glob
import logging
from yt_dlp import YoutubeDL

from aiogram import Dispatcher, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import FSInputFile, InputMediaPhoto, InputMediaVideo

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

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".webm", ".mov", ".avi"}

DOWNLOAD_DIR = "downloads"


def get_ydl_opts(output_template: str, media_type: str = "video") -> dict:
    """
    yt-dlp opsiyalarini qaytaradi.
    media_type: 'video' | 'image' | 'auto'
    """
    base = {
        "outtmpl": output_template,
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
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

    if media_type == "image":
        base["format"] = "best"
        base["writethumbnail"] = True
        base["skip_download"] = True
    else:
        # video: avval mp4, bo'lmasa eng yaxshi format
        base["format"] = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
        base["merge_output_format"] = "mp4"
        base["postprocessors"] = [
            {
                "key": "FFmpegVideoConvertor",
                "preferedformat": "mp4",
            }
        ]

    return base


def find_downloaded_files(uid: str) -> list[str]:
    """uid bo'yicha yuklangan barcha fayllarni topadi."""
    pattern = os.path.join(DOWNLOAD_DIR, f"{uid}*")
    files = glob.glob(pattern)
    # Sort: eng katta hajmdagi fayl birinchi
    files.sort(key=lambda f: os.path.getsize(f) if os.path.exists(f) else 0, reverse=True)
    return files


def classify_file(path: str) -> str:
    """Fayl turini aniqlaydi: 'video', 'image', 'unknown'"""
    ext = os.path.splitext(path)[1].lower()
    if ext in VIDEO_EXTENSIONS:
        return "video"
    if ext in IMAGE_EXTENSIONS:
        return "image"
    return "unknown"


def cleanup(uid: str):
    """Berilgan uid bilan bog'liq barcha fayllarni o'chiradi."""
    for f in find_downloaded_files(uid):
        try:
            os.remove(f)
        except Exception:
            pass


async def download_media(url: str, uid: str) -> list[str]:
    """
    URL dan media yuklab oladi.
    Avval video sifatida sinab ko'radi, 
    keyin rasm sifatida sinab ko'radi.
    Yuklangan fayl yo'llarini qaytaradi.
    """
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    output_template = os.path.join(DOWNLOAD_DIR, f"{uid}.%(ext)s")
    loop = asyncio.get_event_loop()

    # --- 1-urinish: Video ---
    ydl_opts_video = get_ydl_opts(output_template, media_type="video")
    try:
        await loop.run_in_executor(
            None,
            lambda: YoutubeDL(ydl_opts_video).download([url]),
        )
        files = [f for f in find_downloaded_files(uid) if classify_file(f) in ("video", "image")]
        if files:
            return files
    except Exception as e:
        logger.warning(f"Video yuklashda xato: {e}")

    # --- 2-urinish: Thumbnail/Rasm ---
    ydl_opts_img = get_ydl_opts(output_template, media_type="image")
    try:
        await loop.run_in_executor(
            None,
            lambda: YoutubeDL(ydl_opts_img).download([url]),
        )
        files = [f for f in find_downloaded_files(uid) if classify_file(f) in ("video", "image")]
        if files:
            return files
    except Exception as e:
        logger.warning(f"Rasm yuklashda xato: {e}")

    # --- 3-urinish: Hamma formatlar ---
    ydl_opts_any = get_ydl_opts(output_template, media_type="video")
    ydl_opts_any["format"] = "best"
    ydl_opts_any.pop("postprocessors", None)
    try:
        await loop.run_in_executor(
            None,
            lambda: YoutubeDL(ydl_opts_any).download([url]),
        )
        files = [f for f in find_downloaded_files(uid) if classify_file(f) in ("video", "image")]
        if files:
            return files
    except Exception as e:
        logger.warning(f"Fallback yuklashda xato: {e}")

    return []


async def send_media_files(message: types.Message, files: list[str]):
    """Fayllarni turga qarab yuboradi."""
    videos = [f for f in files if classify_file(f) == "video"]
    images = [f for f in files if classify_file(f) == "image"]

    caption = "✅ Yuklandi! Yana havola yuboring yoki /cancel bosing."

    # Videolar
    for path in videos:
        size_mb = os.path.getsize(path) / (1024 * 1024)
        if size_mb > 49:
            await message.answer(
                f"⚠️ Video hajmi {size_mb:.1f} MB — Telegram 50 MB dan katta fayllarni qabul qilmaydi."
            )
            continue
        await message.answer_video(FSInputFile(path), caption=caption)

    # Rasmlar (thumbnail yoki to'g'ridan-to'g'ri rasm)
    if images and not videos:
        if len(images) == 1:
            await message.answer_photo(FSInputFile(images[0]), caption=caption)
        else:
            # Ko'p rasm — album sifatida yuborish
            media_group = []
            for i, path in enumerate(images[:10]):  # Telegram max 10
                media_group.append(
                    InputMediaPhoto(
                        media=FSInputFile(path),
                        caption=caption if i == 0 else None,
                    )
                )
            await message.answer_media_group(media_group)
    elif images and videos:
        # Rasm ham, video ham bor — rasimlarni ham yuborish
        for path in images:
            await message.answer_photo(FSInputFile(path))


def register_video_handlers(dp: Dispatcher):

    @dp.message(F.text == "🎬 Video yuklash")
    async def start_video_download(message: types.Message, state: FSMContext):
        await state.set_state(VideoStates.waiting_for_link)
        await message.answer(
            "🎬 <b>Video / Rasm Yuklash</b>\n\n"
            "Quyidagi platformalardan havola yuboring:\n\n"
            "📸 <b>Instagram</b> — post, reel, story, rasm\n"
            "🎵 <b>TikTok</b> — video, foto\n"
            "▶️ <b>YouTube</b> — video, shorts\n"
            "📌 <b>Pinterest</b> — video, rasm\n"
            "🐦 <b>Twitter/X</b> — video, gif\n"
            "📘 <b>Facebook</b> — video\n\n"
            "📎 Havolani yuboring — media avtomatik yuklanadi\n"
            "❌ Bekor qilish: /cancel",
            parse_mode="HTML",
        )

    @dp.message(VideoStates.waiting_for_link)
    async def handle_link(message: types.Message, state: FSMContext):
        url = message.text.strip() if message.text else ""

        # Tugma bosilsa — rejimdan chiq
        if url in MAIN_KEYBOARD_BUTTONS:
            await state.clear()
            await message.answer(
                "⚙️ Video yuklash rejimi bekor qilindi.\n"
                "Iltimos, tanlangan tugmani qayta bosing."
            )
            return

        # /cancel
        if url == "/cancel":
            await state.clear()
            await message.answer(
                "❌ Video yuklash rejimi bekor qilindi.\n"
                "Qayta boshlash uchun 🎬 Video yuklash tugmasini bosing."
            )
            return

        # URL tekshiruvi
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
                "Faqat quyidagilardan yuklash mumkin:\n"
                "Instagram · TikTok · YouTube · Pinterest · Twitter/X · Facebook",
                parse_mode="HTML",
            )
            return

        uid = str(uuid.uuid4())
        status_msg = await message.answer("⏳ <b>Yuklanmoqda...</b> Kuting ⏳", parse_mode="HTML")

        try:
            files = await download_media(url, uid)

            await status_msg.delete()

            if not files:
                await message.answer(
                    "❌ <b>Media yuklab bo'lmadi.</b>\n\n"
                    "Mumkin sabablar:\n"
                    "• Havola noto'g'ri yoki eskirgan\n"
                    "• Video/rasm yopiq yoki shaxsiy akkauntda\n"
                    "• Platforma cheklovlari (Instagram login talab qiladi)\n"
                    "• Story yoki highlight bo'lsa — faqat ochiq akkauntlardan ishlaydi\n\n"
                    "Boshqa havola yuboring yoki /cancel bosing.",
                    parse_mode="HTML",
                )
                return

            await send_media_files(message, files)

        except Exception as e:
            logger.error(f"Xato: {e}", exc_info=True)
            try:
                await status_msg.delete()
            except Exception:
                pass
            await message.answer(
                "❌ <b>Kutilmagan xato yuz berdi.</b>\n\n"
                "Boshqa havola yuboring yoki /cancel bosing.",
                parse_mode="HTML",
            )

        finally:
            cleanup(uid)

    @dp.message(F.text == "/cancel")
    async def cancel_video(message: types.Message, state: FSMContext):
        await state.clear()
        await message.answer(
            "❌ Video yuklash rejimi bekor qilindi.\n"
            "Qayta boshlash uchun 🎬 Video yuklash tugmasini bosing."
        )