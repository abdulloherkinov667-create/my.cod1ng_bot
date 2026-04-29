import os
import uuid
import json
import asyncio
import logging
from datetime import datetime

from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, FSInputFile

from yt_dlp import YoutubeDL

# ─────────────────────────────────────────────
#  SOZLAMALAR
# ─────────────────────────────────────────────
ADMIN_IDS = [6411347321, 8327989068]
COMPLAINTS_FILE = "complaints.json"


# ─────────────────────────────────────────────
#  HOLATLAR (States)
# ─────────────────────────────────────────────
class VideoStates(StatesGroup):
    waiting_for_link = State()


class ComplaintStates(StatesGroup):
    waiting_for_name    = State()
    waiting_for_phone   = State()
    waiting_for_message = State()


# ─────────────────────────────────────────────
#  KLAVIATURALAR
# ─────────────────────────────────────────────
def start_button():
    """Oddiy foydalanuvchi uchun asosiy menyu."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="🎬 Video Yuklash"),
                KeyboardButton(text="🎥 Kino Ko'rish"),
            ],
            [
                KeyboardButton(text="📝 Shikoyat Qilish"),
                KeyboardButton(text="📋 Shikoyatlar Tarixi"),
            ],
        ],
        resize_keyboard=True,
    )


def user_button():
    """Admin uchun kengaytirilgan menyu."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="👥 Foydalanuvchilar (PDF)"),
                KeyboardButton(text="👥 Foydalanuvchilar Soni"),
            ],
            [
                KeyboardButton(text="📨 Xabar Yuborish"),
                KeyboardButton(text="🎬 Video Yuklash"),
            ],
            [
                KeyboardButton(text="📝 Shikoyat Qilish"),
                KeyboardButton(text="📋 Shikoyatlar Tarixi"),
            ],
        ],
        resize_keyboard=True,
    )


def yoq_button():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="✅ Ha"), KeyboardButton(text="❌ Yo'q")]],
        resize_keyboard=True,
    )


def send_confirmation_buttons():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="✅ Ha"), KeyboardButton(text="❌ Yo'q")]],
        resize_keyboard=True,
    )


def cancel_button():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Bekor Qilish")]],
        resize_keyboard=True,
    )


# ─────────────────────────────────────────────
#  YORDAMCHI: shikoyatlar fayli
# ─────────────────────────────────────────────
def _load_complaints() -> list:
    if not os.path.exists(COMPLAINTS_FILE):
        return []
    with open(COMPLAINTS_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []


def _save_complaint(data: dict):
    complaints = _load_complaints()
    complaints.append(data)
    with open(COMPLAINTS_FILE, "w", encoding="utf-8") as f:
        json.dump(complaints, f, ensure_ascii=False, indent=2)


# ─────────────────────────────────────────────
#  VIDEO YUKLASH HANDLERLARI
# ─────────────────────────────────────────────
SUPPORTED_DOMAINS = [
    "instagram.com", "tiktok.com", "youtube.com", "youtu.be",
    "pinterest.com", "pin.it", "vimeo.com", "twitter.com",
    "x.com", "facebook.com", "fb.watch",
]

MAIN_BUTTONS = {
    "🎬 Video Yuklash", "🎥 Kino Ko'rish", "📝 Shikoyat Qilish",
    "📋 Shikoyatlar Tarixi", "👥 Foydalanuvchilar (PDF)",
    "👥 Foydalanuvchilar Soni", "📨 Xabar Yuborish",
    "❌ Bekor Qilish", "✅ Ha", "❌ Yo'q",
    # eski nomlar ham qo'llab-quvvatlansin
    "Kino ko'rish 🎥", "🎬 Video yuklash", "Shikoyat qilish 📝",
    "Userlarni PDF korsh 👥", "Userlarni soni 👥",
    "Xabar yuborish 📨", "👥 User soni ko'rish",
}


def register_video_handlers(dp: Dispatcher):

    # ── Video yuklash rejimiga kirish ──────────────────────────────────────
    @dp.message(F.text.in_({"🎬 Video Yuklash", "🎬 Video yuklash"}))
    async def start_video_download(message: types.Message, state: FSMContext):
        await state.set_state(VideoStates.waiting_for_link)
        await message.answer(
            "🎬 <b>Video Yuklash Rejimi</b>\n\n"
            "Quyidagi platformalardan video havolasini yuboring:\n\n"
            "• 📸 <b>Instagram</b> — Reels, Post, Stories\n"
            "• 🎵 <b>TikTok</b> — Har qanday video\n"
            "• ▶️ <b>YouTube</b> — Video & Shorts\n"
            "• 📌 <b>Pinterest</b> — Video pinlar\n"
            "• 🐦 <b>Twitter / X</b> — Video tweetlar\n"
            "• 📘 <b>Facebook</b> — Video postlar\n\n"
            "📎 Havolani yuboring — video avtomatik yuklanadi.\n"
            "❌ Bekor qilish uchun <b>/cancel</b> yoki pastdagi tugmani bosing.",
            parse_mode="HTML",
            reply_markup=cancel_button(),
        )

    # ── Havola qabul qilish va yuklash ─────────────────────────────────────
    @dp.message(VideoStates.waiting_for_link)
    async def download_video(message: types.Message, state: FSMContext):
        url = message.text.strip() if message.text else ""

        # Tugma bosilgan bo'lsa — rejimdan chiq
        if url in MAIN_BUTTONS or url == "❌ Bekor Qilish":
            await state.clear()
            await message.answer(
                "✅ Video yuklash rejimi yakunlandi.\n"
                "Bosh menyuga qaytdingiz.",
                reply_markup=start_button(),
            )
            return

        # URL tekshiruvi
        if not (url.startswith("http://") or url.startswith("https://")):
            await message.answer(
                "❌ <b>Noto'g'ri havola!</b>\n\n"
                "Iltimos, to'liq URL manzilini yuboring.\n"
                "<i>Masalan: https://www.tiktok.com/@user/video/...</i>",
                parse_mode="HTML",
            )
            return

        domain_ok = any(d in url for d in SUPPORTED_DOMAINS)
        if not domain_ok:
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
            "cookiesfrombrowser": None,
        }

        status_msg = await message.answer("⏳ <b>Video yuklanmoqda...</b>\nIltimos, biroz kuting.", parse_mode="HTML")

        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: YoutubeDL(ydl_opts).download([url]),
            )

            # Ba'zan yt-dlp fayl nomiga qo'shimcha qo'shishi mumkin
            actual_file = filename
            if not os.path.exists(actual_file):
                # .mp4 bilan tugaydigan eng yangi faylni qidirish
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
                caption="✅ <b>Video muvaffaqiyatli yuklandi!</b>\n\nBoshqa havola yuboring yoki /cancel bosing.",
                parse_mode="HTML",
            )

        except Exception as e:
            logging.warning(f"Video yuklashda xato: {e}")
            await status_msg.delete()
            await message.answer(
                "❌ <b>Video yuklab bo'lmadi.</b>\n\n"
                "Sabablari:\n"
                "• Havola noto'g'ri yoki o'chirilgan\n"
                "• Video yopiq/shaxsiy akkauntda\n"
                "• Platforma cheklovlari\n\n"
                "Boshqa havola yuboring yoki /cancel bosing.",
                parse_mode="HTML",
            )
        finally:
            for f in [filename, actual_file if 'actual_file' in dir() else ""]:
                if f and os.path.exists(f):
                    try:
                        os.remove(f)
                    except Exception:
                        pass

    # ── /cancel buyrug'i ────────────────────────────────────────────────────
    @dp.message(F.text == "/cancel")
    async def cancel_video(message: types.Message, state: FSMContext):
        await state.clear()
        await message.answer(
            "✅ Amal bekor qilindi. Bosh menyuga qaytdingiz.",
            reply_markup=start_button(),
        )


# ─────────────────────────────────────────────
#  SHIKOYAT HANDLERLARI
# ─────────────────────────────────────────────
def register_complaint_handlers(dp: Dispatcher, bot: Bot):

    # ── Shikoyat qilish — boshlash ─────────────────────────────────────────
    @dp.message(F.text.in_({"📝 Shikoyat Qilish", "Shikoyat qilish 📝"}))
    async def start_complaint(message: types.Message, state: FSMContext):
        await state.set_state(ComplaintStates.waiting_for_name)
        await message.answer(
            "📝 <b>Shikoyat Qilish</b>\n\n"
            "Shikoyatingizni qabul qilishimiz uchun bir necha savol beramiz.\n\n"
            "1️⃣ <b>Ismingizni kiriting:</b>\n"
            "<i>(To'liq ism va familiya)</i>",
            parse_mode="HTML",
            reply_markup=cancel_button(),
        )

    # ── Ism qabul qilish ───────────────────────────────────────────────────
    @dp.message(ComplaintStates.waiting_for_name)
    async def complaint_get_name(message: types.Message, state: FSMContext):
        text = message.text.strip()

        if text == "❌ Bekor Qilish":
            await state.clear()
            await message.answer("✅ Shikoyat bekor qilindi.", reply_markup=start_button())
            return

        if len(text) < 2:
            await message.answer("⚠️ Iltimos, to'liq ismingizni kiriting.")
            return

        await state.update_data(name=text)
        await state.set_state(ComplaintStates.waiting_for_phone)
        await message.answer(
            f"✅ Rahmat, <b>{text}</b>!\n\n"
            "2️⃣ <b>Telefon raqamingizni kiriting:</b>\n"
            "<i>Masalan: +998901234567</i>",
            parse_mode="HTML",
        )

    # ── Telefon qabul qilish ───────────────────────────────────────────────
    @dp.message(ComplaintStates.waiting_for_phone)
    async def complaint_get_phone(message: types.Message, state: FSMContext):
        text = message.text.strip()

        if text == "❌ Bekor Qilish":
            await state.clear()
            await message.answer("✅ Shikoyat bekor qilindi.", reply_markup=start_button())
            return

        # Raqam tekshiruvi (oddiy)
        digits = text.replace("+", "").replace(" ", "").replace("-", "")
        if not digits.isdigit() or len(digits) < 9:
            await message.answer(
                "❌ Noto'g'ri telefon raqami.\n"
                "Iltimos, to'g'ri raqam kiriting.\n"
                "<i>Masalan: +998901234567</i>",
                parse_mode="HTML",
            )
            return

        await state.update_data(phone=text)
        await state.set_state(ComplaintStates.waiting_for_message)
        await message.answer(
            "3️⃣ <b>Shikoyatingizni yozing:</b>\n\n"
            "<i>Muammoni batafsil izohlang — biz tezda ko'rib chiqamiz.</i>",
            parse_mode="HTML",
        )

    # ── Shikoyat matni qabul qilish ─────────────────────────────────────────
    @dp.message(ComplaintStates.waiting_for_message)
    async def complaint_get_message(message: types.Message, state: FSMContext):
        text = message.text.strip()

        if text == "❌ Bekor Qilish":
            await state.clear()
            await message.answer("✅ Shikoyat bekor qilindi.", reply_markup=start_button())
            return

        if len(text) < 10:
            await message.answer("⚠️ Shikoyat juda qisqa. Iltimos, batafsilroq yozing (kamida 10 belgi).")
            return

        data = await state.get_data()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        complaint = {
            "id": len(_load_complaints()) + 1,
            "date": now,
            "user_id": message.from_user.id,
            "username": message.from_user.username or "—",
            "name": data["name"],
            "phone": data["phone"],
            "message": text,
        }

        _save_complaint(complaint)
        await state.clear()

        # Foydalanuvchiga javob
        await message.answer(
            "✅ <b>Shikoyatingiz qabul qilindi!</b>\n\n"
            "📋 Shikoyat tafsilotlari:\n"
            f"👤 Ism: {complaint['name']}\n"
            f"📞 Tel: {complaint['phone']}\n"
            f"🕐 Vaqt: {now}\n\n"
            "Shikoyatingiz ko'rib chiqiladi va siz bilan bog'laniladi. Rahmat! 🙏",
            parse_mode="HTML",
            reply_markup=start_button(),
        )

        # Adminlarga yuborish
        admin_text = (
            "🚨 <b>YANGI SHIKOYAT!</b>\n"
            f"{'─' * 30}\n"
            f"🔢 ID: #{complaint['id']}\n"
            f"🕐 Vaqt: {now}\n"
            f"👤 Ism: {complaint['name']}\n"
            f"📞 Telefon: {complaint['phone']}\n"
            f"🆔 Telegram ID: <code>{complaint['user_id']}</code>\n"
            f"👤 Username: @{complaint['username']}\n"
            f"{'─' * 30}\n"
            f"📝 <b>Shikoyat:</b>\n{text}"
        )

        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(admin_id, admin_text, parse_mode="HTML")
            except Exception as e:
                logging.warning(f"Admin {admin_id} ga xabar yuborib bo'lmadi: {e}")


# ─────────────────────────────────────────────
#  SHIKOYATLAR TARIXI HANDLERI
# ─────────────────────────────────────────────
def register_history_handler(dp: Dispatcher):

    @dp.message(F.text == "📋 Shikoyatlar Tarixi")
    async def show_complaints_history(message: types.Message):
        # Faqat adminlar ko'rishi mumkin
        if message.from_user.id not in ADMIN_IDS:
            await message.answer(
                "🔒 <b>Ruxsat yo'q!</b>\n\n"
                "Shikoyatlar tarixini faqat adminlar ko'rishi mumkin.",
                parse_mode="HTML",
            )
            return

        complaints = _load_complaints()

        if not complaints:
            await message.answer(
                "📋 <b>Shikoyatlar Tarixi</b>\n\n"
                "Hozircha hech qanday shikoyat yo'q.",
                parse_mode="HTML",
            )
            return

        # Oxirgi 10 ta shikoyatni ko'rsatish
        recent = complaints[-10:][::-1]
        lines = [f"📋 <b>Shikoyatlar Tarixi</b> (Jami: {len(complaints)} ta)\n{'─'*30}"]

        for c in recent:
            lines.append(
                f"\n🔢 <b>#{c['id']}</b> | 🕐 {c['date']}\n"
                f"👤 {c['name']} | 📞 {c['phone']}\n"
                f"📝 {c['message'][:120]}{'...' if len(c['message']) > 120 else ''}"
            )

        if len(complaints) > 10:
            lines.append(f"\n<i>... va yana {len(complaints) - 10} ta shikoyat</i>")

        await message.answer("\n".join(lines), parse_mode="HTML")


# ─────────────────────────────────────────────
#  BARCHA HANDLERLARNI RO'YXATDAN O'TKAZISH
# ─────────────────────────────────────────────
def register_all_handlers(dp: Dispatcher, bot: Bot):
    register_video_handlers(dp)
    register_complaint_handlers(dp, bot)
    register_history_handler(dp)