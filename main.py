import asyncio
import logging
import os
import re
import shutil
import instaloader

from yt_dlp import YoutubeDL
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import FSInputFile
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.client.session.aiohttp import AiohttpSession
from buttons.defould import start_button

# ---------- Helper ----------
class YTDLPLogger:
    def __init__(self):
        self.last_error = None
        self.lines = []

    def debug(self, msg: str):
        self.lines.append(msg)

    def warning(self, msg: str):
        self.lines.append(msg)

    def error(self, msg: str):
        self.last_error = msg
        self.lines.append(msg)


def _has_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None


from buttons.defould import user_button, send_confirmation_buttons
from create import insert_user, users_table, create_user_pdf, get_all_users, check_blocked_users
from buttons.inline import xabar_yubor
from stets import SendImg



API_TOKEN = "8301002449:AAFzKdU48I4Q0nuTxDnY9725MITFVA7w9ok"

PROXY_URL = None

try:
    session = AiohttpSession(proxy=PROXY_URL) if PROXY_URL else AiohttpSession()
except Exception:
    session = AiohttpSession()

bot = Bot(token=API_TOKEN, session=session)
dp = Dispatcher()

ADMIN_ID = [6411347321, 8327989068]
DOWNLOAD_DIR = "downloads"
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)


# ---------- Video yuklash ----------
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

✨ Shundan so'ng sizga keyingi qadamlar ko'rsatib beriladi.
            """
        )
        await message.answer(text, parse_mode="HTML", reply_markup=start_button())


@dp.message(F.text == "🎬 Video yuklash")
async def vd_yukla_buyruq(message: types.Message, state: FSMContext):
    await state.set_state(VideoState.waiting_for_link)
    await message.answer("""
    🎬 Video yuklash bo'limiga xush kelibsiz!

📥 Kerakli videoni olish uchun havolani yuboring.

🚫 Videolar hech qanday watermark (Instagram belgisi)siz yuklab beriladi.  
🚫 Hech qanday reklamalarsiz, toza holatda taqdim etiladi.

⚡ Tezkor va qulay yuklab olish xizmati siz uchun!

🔗 Instagram yoki YouTube havolasini yuboring 👇
                         """)


@dp.message(VideoState.waiting_for_link)
async def vd_yuklash(message: types.Message, state: FSMContext):
    url = message.text
    
    # Check for Instagram link
    instagram_match = re.search(r"instagram\.com/(?:p|reels|reel|tv)/([a-zA-Z0-9_-]+)", url)
    # Check for YouTube link
    youtube_match = re.search(r"(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]+)", url)
    
    # Determine platform
    if instagram_match:
        match = instagram_match
        is_instagram = True
    elif youtube_match:
        match = youtube_match
        is_instagram = False
    else:
        await message.answer("❌ Noto'g'ri havola. Iltimos, YouTube yoki Instagram video linkini yuboring.")
        return

    wait_msg = await message.answer("⏳ Yuklanmoqda... Iltimos, biroz sabr qiling.")
    shortcode = match.group(1)
    target_dir = os.path.join(DOWNLOAD_DIR, shortcode)
    os.makedirs(target_dir, exist_ok=True)

    loop = asyncio.get_running_loop()
    last_progress = {"percent": 0}

    async def _edit_status(text: str):
        try:
            await wait_msg.edit_text(text)
        except Exception:
            pass

    def _progress_hook(d):
        status = d.get("status")
        if status == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            downloaded = d.get("downloaded_bytes", 0)
            if total:
                percent = int(downloaded / total * 100)
            else:
                percent = None

            if percent is not None:
                if percent - last_progress["percent"] < 3:
                    return
                last_progress["percent"] = percent
                text = f"⏳ Yuklanmoqda: {percent}% ({downloaded/1024/1024:.1f}/{total/1024/1024:.1f} MB)"
            else:
                text = f"⏳ Yuklanmoqda: {downloaded/1024/1024:.1f} MB ..."
                
            loop.call_soon_threadsafe(lambda: loop.create_task(_edit_status(text)))

        elif status == "finished":
            loop.call_soon_threadsafe(
                lambda: loop.create_task(_edit_status("✅ Yuklandi, tayyorlanmoqda..."))
            )

    logger = YTDLPLogger()

    ydl_opts = {
        "outtmpl": os.path.join(target_dir, "%(id)s.%(ext)s"),
        "format": "bestvideo+bestaudio/best" if _has_ffmpeg() else "best",
        "progress_hooks": [_progress_hook],
        "logger": logger,
        "quiet": True,
        "no_warnings": True,
        "restrictfilenames": True,
        "noplaylist": True,
        "overwrites": True,
    }

    video_sent = False
    ydl_logger = YTDLPLogger()

    try:
        def _download() -> str:
            if is_instagram:
                # Download Instagram video using instaloader
                try:
                    loader = instaloader.Instaloader(
                        download_videos=True,
                        save_metadata=False,
                        compress_json=False
                    )
                    post = instaloader.Post.from_shortcode(loader.context, shortcode)
                    loader.download_post(post, target=target_dir)
                    
                    # Find the downloaded video file
                    for fil in os.listdir(target_dir):
                        if fil.lower().endswith((".mp4", ".mkv")):
                            return os.path.join(target_dir, fil)
                except Exception as ig_err:
                    logging.warning(f"Instaloader failed, trying yt_dlp: {ig_err}")
                    # Fallback to yt_dlp for Instagram
                    with YoutubeDL({**ydl_opts, "logger": ydl_logger}) as ydl:
                        info = ydl.extract_info(url, download=True)
                        return ydl.prepare_filename(info)
            else:
                # Download YouTube video using yt_dlp
                with YoutubeDL({**ydl_opts, "logger": ydl_logger}) as ydl:
                    info = ydl.extract_info(url, download=True)
                    return ydl.prepare_filename(info)
            
            return None

        downloaded_file = await asyncio.to_thread(_download)
        video_path = downloaded_file if downloaded_file and os.path.exists(downloaded_file) else None

        # fallback: look for any downloaded video in the target folder
        if not video_path and os.path.exists(target_dir):
            for fil in os.listdir(target_dir):
                if fil.lower().endswith((".mp4", ".mkv", ".mov")):
                    candidate = os.path.join(target_dir, fil)
                    if os.path.getsize(candidate) > 0:
                        video_path = candidate
                        break

        if video_path:
            await message.answer_video(
                FSInputFile(video_path),
                caption=(
                    """
                    ✅ Video muvaffaqiyatli yuklandi!

🎬 Video tayyor — endi uni bemalol saqlab olishingiz yoki qayta ko'rishingiz mumkin.

🚫 Hech qanday watermarksiz  
🚫 Reklamalarsiz, toza holatda

⚡ Siz uchun tezkor va qulay xizmat!

🤖 Bot: @my_cod1ngbot
                    """
                ),
            )
            video_sent = True
        else:
            raise RuntimeError("Yuklangan video topilmadi")

    except Exception as e:
        logging.exception("Videoni yuklashda xatolik: %s", e)

        info_text = ydl_logger.last_error or "Noma'lum xatolik yuz berdi."

        await message.answer(
            "⚠️ Yuklashda muammo yuz berdi. Iltimos, linkni tekshirib qayta urinib ko'ring."
        )

    finally:
        if os.path.exists(target_dir):
            shutil.rmtree(target_dir)
        try:
            await wait_msg.delete()
        except:
            pass
        await state.clear()

@dp.message(F.text == "Userlarni PDF korsh 👥")
async def show_users(message: types.Message):
    if message.from_user.id in ADMIN_ID:
        await check_blocked_users(bot)
        pdf_file = create_user_pdf()
        await message.answer_document(FSInputFile(pdf_file), caption="""
👥 Foydalanuvchilar ro'yxatini
                                      """)


@dp.message(F.text == "Xabar yuborish 📨")
async def xabar_yuborish_boshlash(message: types.Message):
    await message.answer("""
                         📢 Xabar yuborish bo'limi

✉️ Foydalanuvchilarga yuboriladigan xabar turini tanlang.

📝 Siz quyidagi formatlardan birini tanlashingiz mumkin:

• Matn (text)
• Rasm (photo)
• Video

⚙️ Tanlagan turga qarab keyingi bosqichlar ko'rsatib beriladi.

👇 Davom etish uchun xabar turini tanlang.
                         """, reply_markup=xabar_yubor())


@dp.callback_query(F.data == "img")
async def rasm_bosildi(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("""
                                  🖼 Rasm yuborish

📸 Iltimos, foydalanuvchilarga yubormoqchi bo'lgan rasmingizni yuboring.

✏️ Rasm bilan birga izoh (caption) ham qo'shishingiz mumkin.

⚡ Yuborilgan rasm barcha tanlangan foydalanuvchilarga yetkaziladi.

👇 Endi rasmni yuboring.
                                  """)
    await state.set_state(SendImg.image)
    await callback.answer()


@dp.message(SendImg.image, F.photo)
async def rasm_qabul(message: types.Message, state: FSMContext):
    await state.update_data(photo=message.photo[-1].file_id)
    await message.answer("""
                         ✏️ Rasm uchun izoh qo'shish

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


@dp.message(SendImg.confirm, F.text == "Yo'q ❌")
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
