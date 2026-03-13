from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def userkorish_button():
   keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Userlarni PDF korsh 👥", callback_data="stats")]
        ]
    )
   
   
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def xabar_yubor():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Rasm yuborish 🖼️", callback_data="img")
            ],
            [
                InlineKeyboardButton(text="Video yuborish 🎥", callback_data="videos")
            ], 
            [
                InlineKeyboardButton(text="Matn yuborish 💬", callback_data="texts")
            ]
        ]
    )
    return keyboard 


    
def yuborilmasin_sorov():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text='Xa ✅', callback_data='yes')
            ],
            [
                InlineKeyboardButton(text="Yo‘q ❌", callback_data='net')
            ]
        ]
    ) 