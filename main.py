import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import (
    FSInputFile,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.dispatcher.middleware.base import BaseMiddleware

from buttons.defould import user_button, start_button, yoq_button
from create import insert_user, users_table, create_user_pdf, get_all_users, check_blocked_users
from yuklash import register_video_handlers
from shikoyat import register_complaint_handlers

API_TOKEN = "8301002449:AAFzKdU48I4Q0nuTxDnY9725MITFVA7w9ok"
ADMIN_IDS = [8377358077]
RESTRICTED_USERS = [6411347321]

# ──── Middleware ────────────────────────────────────────────
class RestrictedUserMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        if isinstance(event, types.Message):
            user_id = event.from_user.id
            if user_id in RESTRICTED_USERS:
                await event.answer("⛔ Sangaa bunday huquq yo'q")
                return
        elif isinstance(event, types.CallbackQuery):
            user_id = event.from_user.id
            if user_id in RESTRICTED_USERS:
                await event.answer("⛔ Sangaa bunday huquq yo'q", show_alert=True)
                return
        
        return await handler(event, data)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()
dp.message.middleware(RestrictedUserMiddleware())
dp.callback_query.middleware(RestrictedUserMiddleware())
register_video_handlers(dp)
register_complaint_handlers(dp, bot)

class SendImg(StatesGroup):
    image = State()
    about = State()
    confirm = State()
    

def xabar_yubor() -> InlineKeyboardMarkup:
    """Xabar turi tanlash (inline)"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🖼 Rasm bilan", callback_data="img")],
            [InlineKeyboardButton(text="📝 Faqat matn", callback_data="text_msg")],
        ]
    )


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

    if message.from_user.id in ADMIN_IDS:
        await message.answer(
            "👑 *Admin panelga xush kelibsiz!*\n\n"
            "⚙️ Kerakli bo'limni tanlang 👇\n\n"
            "📊 Statistikalar\n"
            "📨 Xabar yuborish\n"
            "👥 Foydalanuvchilar ro'yxati",
            reply_markup=user_button(),
            parse_mode="Markdown",
        )
    else:
        await message.answer(
            "Salom! 👋 @my\\_cod1ngbot ga xush kelibsiz\n\n"
            "😊 Bu yerda sizni oddiy, lekin foydali bir narsa kutmoqda.\n"
            "🧐 Faqat bir qadamni bosish kifoya…\n"
            "👇 Pastdagi tugmani bosing va o'zingiz kashf eting.",
            reply_markup=start_button(),
            parse_mode="Markdown",
        )


@dp.message(F.text == "Kino ko'rish 🎥")
async def kino_korish(message: types.Message):
    await message.answer(
        "Uzr 🙏 Ushbu funksiya hozircha to'liq ishga tushmagan.\n"
        "Hozirda uni yaxshilash ustida ishlayapmiz va yaqin orada foydalanish mumkin bo'ladi."
    )


@dp.message(F.text == "Yordam 💬")
async def yordam(message: types.Message):
    await message.answer(
        "ℹ️ *Yordam bo'limi*\n\n"
        "Bu bot orqali siz:\n"
        "• Shikoyat yuborishingiz mumkin\n"
        "• Kino ko'rishingiz mumkin (tez kunda)\n\n"
        "Muammo bo'lsa @admin ga yozing.",
        parse_mode="Markdown",
    )


def admin_only(func):
    """Admin tekshiruv dekoratori"""
    async def wrapper(message: types.Message, *args, **kwargs):
        if message.from_user.id not in ADMIN_IDS:
            await message.answer("⛔ Sizda bu buyruqdan foydalanish huquqi yo'q.")
            return
        return await func(message, *args, **kwargs)
    return wrapper


@dp.message(F.text == "Userlarni PDF korsh 👥")
async def show_users(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    await check_blocked_users(bot)
    pdf_file = create_user_pdf()
    await message.answer_document(
        FSInputFile(pdf_file),
        caption="👥 *Foydalanuvchilar ro'yxati tayyor!*",
        parse_mode="Markdown",
    )


@dp.message(F.text == "👥 User soni ko'rish")
async def user_count(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    users = get_all_users()
    count = len(users)
    await message.answer(
        f"👥 *Foydalanuvchilar soni*\n\n"
        f"📊 Jami userlar: *{count} ta*\n\n"
        f"🚀 Bot faol ishlamoqda",
        parse_mode="Markdown",
    )


@dp.message(F.text == "Xabar yuborish 📨")
async def xabar_yuborish_boshlash(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    await message.answer(
        "📨 *Xabar yuborish bo'limi*\n\n"
        "👇 Xabar turini tanlang",
        reply_markup=xabar_yubor(),
        parse_mode="Markdown",
    )


# ---- Rasm yuborish ----

@dp.callback_query(F.data == "img")
async def rasm_bosildi(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Ruxsat yo'q", show_alert=True)
        return
    await callback.message.answer("🖼 *Rasmni yuboring*", parse_mode="Markdown")
    await callback.answer()
    await state.set_state(SendImg.image)


@dp.message(SendImg.image, F.photo)
async def rasm_qabul(message: types.Message, state: FSMContext):
    await state.update_data(photo=message.photo[-1].file_id)
    await message.answer("📝 *Rasm uchun izoh kiriting:*", parse_mode="Markdown")
    await state.set_state(SendImg.about)


@dp.message(SendImg.about)
async def caption_qabul(message: types.Message, state: FSMContext):
    await state.update_data(about=message.text)
    data = await state.get_data()

    await message.answer_photo(
        photo=data["photo"],
        caption=f"📝 *Ko'rinishi:*\n\n{data['about']}",
        parse_mode="Markdown",
    )
    await message.answer(
        "📨 *Barcha foydalanuvchilarga yuborilsinmi?*",
        reply_markup=yoq_button(),
        parse_mode="Markdown",
    )
    await state.set_state(SendImg.confirm)


@dp.message(SendImg.confirm, F.text == "Xa ✅")
async def yubor(message: types.Message, state: FSMContext):
    data = await state.get_data()
    users = get_all_users()
    count = 0

    for user in users:
        try:
            await bot.send_photo(
                chat_id=user[3],
                photo=data["photo"],
                caption=data["about"],
            )
            count += 1
        except Exception:
            continue

    await message.answer(
        f"✅ *Yuborildi!*\n\n📨 {count} ta foydalanuvchiga yetkazildi",
        parse_mode="Markdown",
        reply_markup=user_button(),
    )
    await state.clear()


@dp.message(SendImg.confirm, F.text == "Yo'q ❌")
async def bekor(message: types.Message, state: FSMContext):
    await message.answer(
        "❌ *Yuborish bekor qilindi*",
        parse_mode="Markdown",
        reply_markup=user_button(),
    )
    await state.clear()


# ---- Matn xabar yuborish ----

class SendText(StatesGroup):
    text = State()
    confirm = State()


@dp.callback_query(F.data == "text_msg")
async def text_msg_start(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Ruxsat yo'q", show_alert=True)
        return
    await callback.message.answer("✏️ *Yuboriladigan matnni kiriting:*", parse_mode="Markdown")
    await callback.answer()
    await state.set_state(SendText.text)


@dp.message(SendText.text)
async def text_msg_preview(message: types.Message, state: FSMContext):
    await state.update_data(text=message.text)
    await message.answer(
        f"📋 *Ko'rinishi:*\n\n{message.text}\n\n"
        "📨 *Barcha foydalanuvchilarga yuborilsinmi?*",
        reply_markup=yoq_button(),
        parse_mode="Markdown",
    )
    await state.set_state(SendText.confirm)


@dp.message(SendText.confirm, F.text == "Xa ✅")
async def text_yubor(message: types.Message, state: FSMContext):
    data = await state.get_data()
    users = get_all_users()
    count = 0

    for user in users:
        try:
            await bot.send_message(chat_id=user[3], text=data["text"])
            count += 1
        except Exception:
            continue

    await message.answer(
        f"✅ *Yuborildi!*\n\n📨 {count} ta foydalanuvchiga yetkazildi",
        parse_mode="Markdown",
        reply_markup=user_button(),
    )
    await state.clear()
print("Bot ishga tush")

@dp.message(SendText.confirm, F.text == "Yo'q ❌")
async def text_bekor(message: types.Message, state: FSMContext):
    await message.answer(
        "❌ *Yuborish bekor qilindi*",
        parse_mode="Markdown",
        reply_markup=user_button(),
    )
    await state.clear()


# ===================== RUN =====================

async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    os.makedirs("downloads", exist_ok=True)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())