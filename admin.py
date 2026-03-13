
from aiogram import Bot, Dispatcher, Router, types, F
from aiogram.filters import CommandStart
from aiogram.types import FSInputFile
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from buttons.defould import start_button, user_button
from buttons.inline import userkorish_button
from create import creat_user_pdf


dp = Router()


ADMIN_ID = "6411347321, 8327989068"
    
    

@dp.message(CommandStart())
async def admin_start(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer(f"""
        ✨ Admin panelga xush kelibsiz! hurmatli {message.from_user.first_name}!
                             """, reply_markup=userkorish_button())
    else:
        await message.answer("❌ Siz admin emassiz!")
        
        
@dp.message(F.text == "Userlarni ko'rish 👥")
async def show_users(message: types.Message):
    if message.from_user.id == int(ADMIN_ID):
        pdf_file = creat_user_pdf()
        await message.answer_document(
            FSInputFile(pdf_file),
            caption="📄 Foydalanuvchilar ro'yxati"
        )
    else:
        await message.answer("❌ Siz admin emassiz!")
