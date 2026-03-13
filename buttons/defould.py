from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
import asyncio
import logging
import instaloader
import re
import os

from aiogram import Bot, Dispatcher, types, F


def start_button():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎬 Video yuklash")]
        ],
        resize_keyboard=True
    )
# def start_button():
#     return ReplyKeyboardMarkup(
#         keyboard=[
#             [KeyboardButton(text="Bosish")]
#         ],
#         resize_keyboard=True
#     )
    
    
def user_button():
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="Userlarni PDF korsh 👥"),
                KeyboardButton(text="Userlarni soni 👥")
            ],
            [
                KeyboardButton(text="Xabar yuborish 📨")
            ]
        ],
        resize_keyboard=True
    )
    
    
def yoq_button():
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="Xa ✅"),
                KeyboardButton(text="Yo‘q ❌")
            ]
        ],
        resize_keyboard=True
    )
    
    
def send_confirmation_buttons():
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="Xa ✅"), types.KeyboardButton(text="Yo‘q ❌")]
        ],
        resize_keyboard=True
    )
    return keyboard
