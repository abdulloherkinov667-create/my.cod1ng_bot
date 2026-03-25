import telebot
import instaloader
import os
import shutil
import uuid
import logging
import threading
import time
from telebot import types
from moviepy import VideoFileClip
from datetime import datetime

# Sizning fayllaringizdan import
from buttons.defould import start_button, user_button, send_confirmation_buttons
from create import insert_user, users_table, create_user_pdf, get_all_users, get_users_count, check_blocked_users

# Bot token
API_TOKEN = "8301002449:AAFzKdU48I4Q0nuTxDnY9725MITFVA7w9ok"
bot = telebot.TeleBot(API_TOKEN)

ADMIN_ID = [6411347321, 8327989068]

# Instaloader konfiguratsiyasi
loader = instaloader.Instaloader(
    download_comments=False,
    download_geotags=False,
    download_pictures=False,
    download_video_thumbnails=False,
    save_metadata=False
)

# ===================== START KOMANDASI =====================
@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    username = message.from_user.username
    chat_id = message.chat.id
    
    # Foydalanuvchini ma'lumotlar bazasiga qo'shish
    insert_user(
        first_name=first_name,
        username=username,
        language_code=message.from_user.language_code,
        is_bot=message.from_user.is_bot,
        chat_id=chat_id,
        created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    
    if user_id in ADMIN_ID:
        text = (
            f"👑 <b>Admin paneliga xush kelibsiz!</b>\n\n"
            f"Salom, <b>{first_name}</b>.\n\n"
            "🧰 Paneldan kerakli bo'limni tanlang."
        )
        bot.send_message(chat_id, text, reply_markup=user_button(), parse_mode="HTML")
    else:
        text = """
👋 Botga xush kelibsiz!

😊 Botdan foydalanishni boshlash uchun pastda joylashgan tugmalardan birini tanlang.

👇 Davom etish uchun pastdagi tugmani bosing.

✨ Shundan so‘ng sizga keyingi qadamlar ko‘rsatib beriladi.
        """
        bot.send_message(chat_id, text, reply_markup=start_button(), parse_mode="HTML")


# ===================== VIDEO YUKLASH =====================
@bot.message_handler(func=lambda message: message.text == "🎬 Video yuklash")
def start_video_download(message):
    msg = bot.send_message(message.chat.id, "📥 Instagram video linkini yuboring:")
    bot.register_next_step_handler(msg, get_instagram_video)


def get_instagram_video(message):
    url = message.text.strip()
    
    # URL validatsiyasi
    if not url.startswith(('https://www.instagram.com/', 'https://instagram.com/')):
        bot.send_message(message.chat.id, "❌ Noto'g'ri link! Iltimos, Instagram video linkini yuboring.")
        return
    
    try:
        # Shortcode ni olish
        if '/p/' in url:
            shortcode = url.split('/p/')[1].split('/')[0]
        elif '/reel/' in url:
            shortcode = url.split('/reel/')[1].split('/')[0]
        else:
            bot.send_message(message.chat.id, "❌ Link noto'g'ri formatda!")
            return
        
        folder_name = shortcode
        
        # Yuklab olish jarayoni haqida xabar
        loading_msg = bot.send_message(message.chat.id, "⏳ Video yuklanmoqda, iltimos kuting...")
        
        try:
            # Postni yuklab olish
            post = instaloader.Post.from_shortcode(loader.context, shortcode)
            loader.download_post(post, target=folder_name)
            
            # Video faylni topish
            video_file = None
            if os.path.exists(folder_name):
                for file in os.listdir(folder_name):
                    if file.endswith(".mp4"):
                        video_file = os.path.join(folder_name, file)
                        break
            
            if video_file and os.path.exists(video_file):
                # Audio olish uchun inline keyboard
                markup = types.InlineKeyboardMarkup()
                btn = types.InlineKeyboardButton(
                    text="🎵 Audioni yuklab olish", 
                    callback_data=f"get_audio|{video_file}|{folder_name}"
                )
                markup.add(btn)
                
                # Videoni yuborish
                with open(video_file, 'rb') as video:
                    bot.send_video(
                        message.chat.id, 
                        video, 
                        caption="✅ Video tayyor!",
                        reply_markup=markup
                    )
                
                # Yuklab olish papkasini keyinroq tozalash
                def cleanup():
                    time.sleep(5)
                    if os.path.exists(folder_name):
                        shutil.rmtree(folder_name, ignore_errors=True)
                
                threading.Thread(target=cleanup).start()
                
            else:
                bot.send_message(message.chat.id, "❌ Video topilmadi!")
                if os.path.exists(folder_name):
                    shutil.rmtree(folder_name, ignore_errors=True)
                
        except Exception as e:
            # Xatolikni o'zbek tilida chiqarish
            bot.send_message(message.chat.id, "❌ Xatolik yuz berdi!")
            if os.path.exists(folder_name):
                shutil.rmtree(folder_name, ignore_errors=True)
                
        finally:
            bot.delete_message(message.chat.id, loading_msg.message_id)
            
    except Exception as e:
        bot.send_message(message.chat.id, "❌ Xatolik yuz berdi!")


# ===================== AUDIO OLISH =====================
@bot.callback_query_handler(func=lambda call: call.data.startswith("get_audio|"))
def get_audio(callback):
    try:
        data_parts = callback.data.split("|")
        if len(data_parts) < 3:
            bot.answer_callback_query(callback.id, "Xatolik yuz berdi!")
            return
            
        video_file = data_parts[1]
        folder_name = data_parts[2]
        
        loading_msg = bot.send_message(callback.message.chat.id, "🎵 Audio yuklanmoqda, iltimos kuting...")
        
        try:
            # Videodan audio ajratish
            video = VideoFileClip(video_file)
            audio = video.audio
            
            if audio is not None:
                audio_name = f"{uuid.uuid4()}.mp3"
                audio.write_audiofile(audio_name, logger=None)
                video.close()
                
                # Audioni yuborish
                with open(audio_name, 'rb') as audio_file:
                    bot.send_audio(
                        callback.message.chat.id, 
                        audio_file,
                        caption="🎵 Audio tayyor!"
                    )
                    
                os.remove(audio_name)
                bot.answer_callback_query(callback.id, "✅ Audio tayyor!")
            else:
                bot.send_message(callback.message.chat.id, "❌ Bu videoda audio yo'q!")
                bot.answer_callback_query(callback.id, "Audio topilmadi")
                
        except Exception as e:
            bot.send_message(callback.message.chat.id, "❌ Xatolik yuz berdi!")
            bot.answer_callback_query(callback.id, "Xatolik yuz berdi")
        finally:
            bot.delete_message(callback.message.chat.id, loading_msg.message_id)
            
            # Papkani tozalash
            if os.path.exists(folder_name):
                shutil.rmtree(folder_name, ignore_errors=True)
                
    except Exception as e:
        bot.answer_callback_query(callback.id, "Xatolik yuz berdi!")


# ===================== ADMIN: USERLARNI PDF KO'RISH =====================
@bot.message_handler(func=lambda message: message.text == "Userlarni PDF korsh 👥" and message.from_user.id in ADMIN_ID)
def show_users_pdf(message):
    loading_msg = bot.send_message(message.chat.id, "⏳ PDF tayyorlanmoqda...")
    try:
        # Bloklangan userlarni tekshirish
        check_blocked_users()
        
        # PDF yaratish
        pdf_file = create_user_pdf()
        
        # PDFni yuborish
        with open(pdf_file, 'rb') as pdf:
            bot.send_document(
                message.chat.id, 
                pdf, 
                caption=f"👥 Foydalanuvchilar ro'yxati\n\n📊 Jami: {get_users_count()} ta foydalanuvchi"
            )
        
        # PDF faylni o'chirish
        os.remove(pdf_file)
        
    except Exception as e:
        bot.send_message(message.chat.id, "❌ Xatolik yuz berdi!")
    finally:
        bot.delete_message(message.chat.id, loading_msg.message_id)


# ===================== ADMIN: USERLARNI SONI =====================
@bot.message_handler(func=lambda message: message.text == "Userlarni soni 👥" and message.from_user.id in ADMIN_ID)
def show_users_count(message):
    try:
        count = get_users_count()
        bot.send_message(
            message.chat.id, 
            f"👥 <b>Foydalanuvchilar soni:</b> <code>{count}</code>",
            parse_mode="HTML"
        )
    except Exception as e:
        bot.send_message(message.chat.id, "❌ Xatolik yuz berdi!")


# ===================== ADMIN: XABAR YUBORISH =====================
@bot.message_handler(func=lambda message: message.text == "Xabar yuborish 📨" and message.from_user.id in ADMIN_ID)
def xabar_yuborish_boshlash(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn1 = types.InlineKeyboardButton("📝 Matn", callback_data="send_text")
    btn2 = types.InlineKeyboardButton("🖼 Rasm", callback_data="send_photo")
    btn3 = types.InlineKeyboardButton("🎬 Video", callback_data="send_video")
    markup.add(btn1, btn2, btn3)
    
    bot.send_message(message.chat.id, """
📢 Xabar yuborish bo‘limi

✉️ Foydalanuvchilarga yuboriladigan xabar turini tanlang.

👇 Davom etish uchun xabar turini tanlang.
    """, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data in ["send_text", "send_photo", "send_video"])
def choose_message_type(callback):
    if callback.data == "send_text":
        msg = bot.send_message(callback.message.chat.id, "📝 Yubormoqchi bo'lgan matningizni yozing:")
        bot.register_next_step_handler(msg, send_text_to_users)
        
    elif callback.data == "send_photo":
        msg = bot.send_message(callback.message.chat.id, "🖼 Yubormoqchi bo'lgan rasmingizni yuboring:")
        bot.register_next_step_handler(msg, get_photo_for_users)
        
    elif callback.data == "send_video":
        msg = bot.send_message(callback.message.chat.id, "🎬 Yubormoqchi bo'lgan videongizni yuboring:")
        bot.register_next_step_handler(msg, get_video_for_users)
    
    bot.answer_callback_query(callback.id)
    bot.delete_message(callback.message.chat.id, callback.message.message_id)


def send_text_to_users(message):
    text = message.text
    markup = types.InlineKeyboardMarkup()
    btn_yes = types.InlineKeyboardButton("✅ Ha", callback_data=f"confirm_text|{text}")
    btn_no = types.InlineKeyboardButton("❌ Yo'q", callback_data="cancel_send")
    markup.add(btn_yes, btn_no)
    
    bot.send_message(message.chat.id, f"📨 Yuboriladigan matn:\n\n{text}\n\nYuborilsinmi?", reply_markup=markup)


def get_photo_for_users(message):
    if message.photo:
        photo_id = message.photo[-1].file_id
        caption = message.caption if message.caption else ""
        
        markup = types.InlineKeyboardMarkup()
        btn_yes = types.InlineKeyboardButton("✅ Ha", callback_data=f"confirm_photo|{photo_id}|{caption}")
        btn_no = types.InlineKeyboardButton("❌ Yo'q", callback_data="cancel_send")
        markup.add(btn_yes, btn_no)
        
        bot.send_photo(message.chat.id, photo_id, caption="📨 Yuboriladigan rasm\n\nYuborilsinmi?", reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "❌ Iltimos, rasm yuboring!")
        msg = bot.send_message(message.chat.id, "🖼 Yubormoqchi bo'lgan rasmingizni yuboring:")
        bot.register_next_step_handler(msg, get_photo_for_users)


def get_video_for_users(message):
    if message.video:
        video_id = message.video.file_id
        caption = message.caption if message.caption else ""
        
        markup = types.InlineKeyboardMarkup()
        btn_yes = types.InlineKeyboardButton("✅ Ha", callback_data=f"confirm_video|{video_id}|{caption}")
        btn_no = types.InlineKeyboardButton("❌ Yo'q", callback_data="cancel_send")
        markup.add(btn_yes, btn_no)
        
        bot.send_video(message.chat.id, video_id, caption="📨 Yuboriladigan video\n\nYuborilsinmi?", reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "❌ Iltimos, video yuboring!")
        msg = bot.send_message(message.chat.id, "🎬 Yubormoqchi bo'lgan videongizni yuboring:")
        bot.register_next_step_handler(msg, get_video_for_users)


@bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_"))
def confirm_send_message(callback):
    data_parts = callback.data.split("|")
    msg_type = data_parts[0].replace("confirm_", "")
    content = data_parts[1] if len(data_parts) > 1 else None
    caption = data_parts[2] if len(data_parts) > 2 else ""
    
    loading_msg = bot.send_message(callback.message.chat.id, "⏳ Xabarlar yuborilmoqda...")
    
    users = get_all_users()
    count = 0
    
    for user in users:
        try:
            if msg_type == "text":
                bot.send_message(user[3], content)  # user[3] = chat_id
            elif msg_type == "photo":
                bot.send_photo(user[3], content, caption=caption)
            elif msg_type == "video":
                bot.send_video(user[3], content, caption=caption)
            count += 1
            time.sleep(0.1)
        except Exception:
            continue
    
    bot.delete_message(callback.message.chat.id, loading_msg.message_id)
    bot.send_message(callback.message.chat.id, f"✅ {count} ta foydalanuvchiga yuborildi.")
    bot.answer_callback_query(callback.id)
    bot.delete_message(callback.message.chat.id, callback.message.message_id)


@bot.callback_query_handler(func=lambda call: call.data == "cancel_send")
def cancel_send(callback):
    bot.send_message(callback.message.chat.id, "❌ Bekor qilindi.")
    bot.answer_callback_query(callback.id)
    bot.delete_message(callback.message.chat.id, callback.message.message_id)


# ===================== BOSHQA XABARLAR =====================
@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    bot.send_message(message.chat.id, "⚠️ Iltimos, tugmalardan foydalaning!")


# ===================== BOTNI ISHGA TUSHIRISH =====================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("🤖 Bot ishga tushdi...")
    print("👑 Admin ID lar:", ADMIN_ID)
    print("-" * 50)
    bot.polling(none_stop=True)