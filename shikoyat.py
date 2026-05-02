import sqlite3
from aiogram import Dispatcher, types, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
# from main import ADMIN_IDS  <-- Buni o'chiring, xato berishi mumkin
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

# Admin ID ni shu yerga o'zini yozib qo'ying
ADMIN_IDS = [6411347321] 

class ComplaintStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_phone = State()
    waiting_for_text = State()

def init_db():
    conn = sqlite3.connect("shikoyat_baza.db")
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS complaints 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                       user_id INTEGER, 
                       name TEXT, 
                       phone TEXT, 
                       text TEXT)''')
    conn.commit()
    conn.close()

def get_phone_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📞 Telefon raqamni yuborish", request_contact=True)]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def register_complaint_handlers(dp: Dispatcher, bot: Bot):
    init_db()

    @dp.message(F.text == "Shikoyat qilish 📝")
    async def start_complaint(message: types.Message, state: FSMContext):
        await state.set_state(ComplaintStates.waiting_for_name)
        await message.answer(
            "<b>Ismingizni kiriting:</b>",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardRemove()
        )

    @dp.message(ComplaintStates.waiting_for_name)
    async def get_name(message: types.Message, state: FSMContext):
        await state.update_data(name=message.text)
        await state.set_state(ComplaintStates.waiting_for_phone)
        await message.answer("""
        📌 Eslatma: Telefon raqamingiz talab qilinadi. 
        ✍️ Iltimos, shikoyatingizni aniq va asosli tarzda yozing. 

        🔍 Murojaatingiz operatorlar tomonidan ko'rib chiqiladi va zarurat tug'ilganda siz bilan bog'lanishlari mumkin. 
        👤 Iltimos, telefon raqamingizni yuboring.
        """, reply_markup=get_phone_kb())

    @dp.message(ComplaintStates.waiting_for_phone)
    async def get_phone(message: types.Message, state: FSMContext):
        if message.contact:
            phone = message.contact.phone_number
        else:
            phone = message.text

        await state.update_data(phone=phone)
        await state.set_state(ComplaintStates.waiting_for_text)
        await message.answer(
            "<b>Shikoyatingiz mazmunini yozing:</b>",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardRemove()
        )

    @dp.message(ComplaintStates.waiting_for_text)
    async def get_text(message: types.Message, state: FSMContext):
        data = await state.get_data()
        user_id = message.from_user.id
        name = data['name']
        phone = data['phone']
        text = message.text

        conn = sqlite3.connect("shikoyat_baza.db")
        cursor = conn.cursor()
        cursor.execute("INSERT INTO complaints (user_id, name, phone, text) VALUES (?, ?, ?, ?)",
                        (user_id, name, phone, text))
        conn.commit()
        conn.close()

        await message.answer("✅ Shikoyatingiz qabul qilindi!")

        admin_msg = (
            f"📢 <b>Yangi shikoyat</b>\n"
            f"━━━━━━━━━━━━━━━\n\n"
            f"👤 <b>Ism:</b> {name}\n"
            f"📞 <b>Telefon:</b> {phone}\n\n"
            f"📝 <b>Shikoyat matni:</b>\n"
            f"{text}\n\n"
            f"━━━━━━━━━━━━━━━"
        )
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(admin_id, admin_msg, parse_mode="HTML")
            except Exception:
                pass

        await state.clear()

    @dp.message(F.text == "Mening shikoyatlarim 📋")
    async def show_user_complaints(message: types.Message):
        conn = sqlite3.connect("shikoyat_baza.db")
        cursor = conn.cursor()
        cursor.execute("SELECT text FROM complaints WHERE user_id = ?", (message.from_user.id,))
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            await message.answer("Sizda hali shikoyatlar yo'q.")
            return

        txt = "📋 <b>Siz yuborgan shikoyatlar:</b>\n\n"
        for i, row in enumerate(rows, 1):
            txt += f"{i}. {row[0]}\n"
        await message.answer(txt, parse_mode="HTML")

    @dp.message(F.text == "Shikoyatlar ro‘yxati 📝")
    async def show_all_complaints(message: types.Message):
        if message.from_user.id not in ADMIN_IDS:
            return

        conn = sqlite3.connect("shikoyat_baza.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id, user_id, name, phone, text FROM complaints")
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            await message.answer("Hozircha bazada shikoyat yo'q.")
            return

        txt = "📂 <b>Barcha shikoyatlar:</b>\n\n"
        for row in rows:
            txt += f"🆔 <b>ID:</b> {row[0]}\n👤 <b>User ID:</b> {row[1]}\n👨‍💼 <b>Ism:</b> {row[2]}\n📞 <b>Telefon:</b> {row[3]}\n📝 <b>Shikoyat:</b> {row[4]}\n━━━━━━━━━━━━━━━━━\n\n"
        await message.answer(txt, parse_mode="HTML")