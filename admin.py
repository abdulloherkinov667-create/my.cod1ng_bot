from aiogram import types, F
from aiogram.filters import CommandStart
from aiogram.types import FSInputFile

from main import dp, bot, ADMIN_ID
from create import insert_user, users_table, create_user_pdf, get_all_users
from buttons.defould import user_button, start_button, send_confirmation_buttons
from buttons.inline import xabar_yubor
from stets import SendImg


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

✨ Shundan so‘ng sizga keyingi qadamlar ko‘rsatib beriladi.
            """
        )
        await message.answer(text, parse_mode="HTML", reply_markup=start_button())


@dp.message(F.text == "Userlarni PDF korsh 👥")
async def show_users(message: types.Message):
    if message.from_user.id in ADMIN_ID:
        pdf_file = create_user_pdf()
        await message.answer_document(FSInputFile(pdf_file), caption="""
👥 Foydalanuvchilar ro‘yxatini
                                      """)


@dp.message(F.text == "Xabar yuborish 📨")
async def xabar_yuborish_boshlash(message: types.Message):
    await message.answer("""
                         📢 Xabar yuborish bo‘limi

✉️ Foydalanuvchilarga yuboriladigan xabar turini tanlang.

📝 Siz quyidagi formatlardan birini tanlashingiz mumkin:

• Matn (text)
• Rasm (photo)
• Video

⚙️ Tanlagan turga qarab keyingi bosqichlar ko‘rsatib beriladi.

👇 Davom etish uchun xabar turini tanlang.
                         """, reply_markup=xabar_yubor())


@dp.callback_query(F.data == "img")
async def rasm_bosildi(callback: types.CallbackQuery, state):
    await callback.message.answer("""warning: in the working copy of 'main.py', LF will be replaced by CRLF the next time Git touches it
                                  🖼 Rasm yuborish

📸 Iltimos, foydalanuvchilarga yubormoqchi bo‘lgan rasmingizni yuboring.

✏️ Rasm bilan birga izoh (caption) ham qo‘shishingiz mumkin.

⚡ Yuborilgan rasm barcha tanlangan foydalanuvchilarga yetkaziladi.

👇 Endi rasmni yuboring.
                                  """)
    await state.set_state(SendImg.image)
    await callback.answer()


@dp.message(SendImg.image, F.photo)
async def rasm_qabul(message: types.Message, state):
    await state.update_data(photo=message.photo[-1].file_id)
    await message.answer("""
                         ✏️ Rasm uchun izoh qo‘shish

📝 Endi yuborilgan rasm uchun matn (caption) kiriting.
                         """)
    await state.set_state(SendImg.about)


@dp.message(SendImg.about)
async def caption_qabul(message: types.Message, state):
    await state.update_data(about=message.text)
    data = await state.get_data()
    await message.answer_photo(photo=data["photo"], caption=data["about"], parse_mode="HTML")
    await message.answer("📨 Yuborilsinmi?", reply_markup=send_confirmation_buttons())
    await state.set_state(SendImg.confirm)


@dp.message(SendImg.confirm, F.text == "Xa ✅")
async def yubor(message: types.Message, state):
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
async def bekor(message: types.Message, state):
    await message.answer("❌ Bekor qilindi.", reply_markup=types.ReplyKeyboardRemove())
    await state.clear()
