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

# Foydalanuvchilarni saqlash uchun (vaqtinchalik)
users_data = {}


# Start komandasi
@bot.message_handler(commands=['start'])
def start_command(message):
    # Foydalanuvchini ro'yxatga olish
    user_id = message.from_user.id
    users_data[user_id] = {
        'first_name': message.from_user.first_name,
        'username': message.from_user.username,
        'chat_id': message.chat.id
    }
    
    if user_id in ADMIN_ID:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        btn1 = types.KeyboardButton("Userlarni PDF korsh 👥")
        btn2 = types.KeyboardButton("Xabar yuborish 📨")
        markup.add(btn1, btn2)
        
        text = (
            f"👑 <b>Admin paneliga xush kelibsiz!</b>\n\n"
            f"Salom, <b>{message.from_user.first_name}</b>.\n\n"
            "🧰 Paneldan kerakli bo'limni tanlang."
        )
        bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode="HTML")
    else:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        btn1 = types.KeyboardButton("🎬 Video yuklash")
        markup.add(btn1)
        
        text = """
👋 Botga xush kelibsiz!

😊 Botdan foydalanishni boshlash uchun pastda joylashgan tugmalardan birini tanlang.

👇 Davom etish uchun pastdagi tugmani bosing.

✨ Shundan so‘ng sizga keyingi qadamlar ko‘rsatib beriladi.
        """
        bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode="HTML")


# Video yuklash tugmasi
@bot.message_handler(func=lambda message: message.text == "🎬 Video yuklash")
def start_video_download(message):
    msg = bot.send_message(message.chat.id, "📥 Instagram video linkini yuboring:")
    bot.register_next_step_handler(msg, get_instagram_video)


# Instagram videoni yuklab olish
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
            bot.send_message(message.chat.id, f"❌ Xatolik: {str(e)}")
            if os.path.exists(folder_name):
                shutil.rmtree(folder_name, ignore_errors=True)
                
        finally:
            bot.delete_message(message.chat.id, loading_msg.message_id)
            
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Xatolik yuz berdi: {str(e)}")


# Callback query handler (audio olish uchun)
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
            bot.send_message(callback.message.chat.id, f"❌ Audio yuklashda xatolik: {str(e)}")
            bot.answer_callback_query(callback.id, "Xatolik yuz berdi")
        finally:
            bot.delete_message(callback.message.chat.id, loading_msg.message_id)
            
            # Papkani tozalash
            if os.path.exists(folder_name):
                shutil.rmtree(folder_name, ignore_errors=True)
                
    except Exception as e:
        bot.answer_callback_query(callback.id, f"Xatolik: {str(e)}")


# Admin: Userlarni PDF ko'rish
@bot.message_handler(func=lambda message: message.text == "Userlarni PDF korsh 👥" and message.from_user.id in ADMIN_ID)
def show_users(message):
    loading_msg = bot.send_message(message.chat.id, "⏳ PDF tayyorlanmoqda...")
    try:
        # PDF yaratish funksiyasini chaqirish
        # pdf_file = create_user_pdf()
        # with open(pdf_file, 'rb') as pdf:
        #     bot.send_document(message.chat.id, pdf, caption="👥 Foydalanuvchilar ro‘yxati")
        # os.remove(pdf_file)
        
        # Vaqtinchalik PDF o'rniga userlar sonini ko'rsatish
        user_count = len(users_data)
        bot.send_message(message.chat.id, f"👥 Jami foydalanuvchilar soni: {user_count}")
        
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Xatolik: {str(e)}")
    finally:
        bot.delete_message(message.chat.id, loading_msg.message_id)


# Admin: Xabar yuborish bo'limi
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


# Admin: Xabar turini tanlash
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


# Matn xabar yuborish
def send_text_to_users(message):
    text = message.text
    markup = types.InlineKeyboardMarkup()
    btn_yes = types.InlineKeyboardButton("✅ Ha", callback_data=f"confirm_text|{text}")
    btn_no = types.InlineKeyboardButton("❌ Yo'q", callback_data="cancel_send")
    markup.add(btn_yes, btn_no)
    
    bot.send_message(message.chat.id, f"📨 Yuboriladigan matn:\n\n{text}\n\nYuborilsinmi?", reply_markup=markup)


# Rasm xabar yuborish
def get_photo_for_users(message):
    if message.photo:
        photo_id = message.photo[-1].file_id
        markup = types.InlineKeyboardMarkup()
        btn_yes = types.InlineKeyboardButton("✅ Ha", callback_data=f"confirm_photo|{photo_id}")
        btn_no = types.InlineKeyboardButton("❌ Yo'q", callback_data="cancel_send")
        markup.add(btn_yes, btn_no)
        
        bot.send_photo(message.chat.id, photo_id, caption="📨 Yuboriladigan rasm\n\nYuborilsinmi?", reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "❌ Iltimos, rasm yuboring!")
        msg = bot.send_message(message.chat.id, "🖼 Yubormoqchi bo'lgan rasmingizni yuboring:")
        bot.register_next_step_handler(msg, get_photo_for_users)


# Video xabar yuborish
def get_video_for_users(message):
    if message.video:
        video_id = message.video.file_id
        markup = types.InlineKeyboardMarkup()
        btn_yes = types.InlineKeyboardButton("✅ Ha", callback_data=f"confirm_video|{video_id}")
        btn_no = types.InlineKeyboardButton("❌ Yo'q", callback_data="cancel_send")
        markup.add(btn_yes, btn_no)
        
        bot.send_video(message.chat.id, video_id, caption="📨 Yuboriladigan video\n\nYuborilsinmi?", reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "❌ Iltimos, video yuboring!")
        msg = bot.send_message(message.chat.id, "🎬 Yubormoqchi bo'lgan videongizni yuboring:")
        bot.register_next_step_handler(msg, get_video_for_users)


# Xabarni tasdiqlash
@bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_"))
def confirm_send_message(callback):
    data_parts = callback.data.split("|")
    msg_type = data_parts[0].replace("confirm_", "")
    content = data_parts[1] if len(data_parts) > 1 else None
    
    loading_msg = bot.send_message(callback.message.chat.id, "⏳ Xabarlar yuborilmoqda...")
    
    count = 0
    for user_id, user_data in users_data.items():
        try:
            if msg_type == "text":
                bot.send_message(user_data['chat_id'], content)
            elif msg_type == "photo":
                bot.send_photo(user_data['chat_id'], content)
            elif msg_type == "video":
                bot.send_video(user_data['chat_id'], content)
            count += 1
            time.sleep(0.1)  # Rate limit uchun
        except Exception:
            continue
    
    bot.delete_message(callback.message.chat.id, loading_msg.message_id)
    bot.send_message(callback.message.chat.id, f"✅ {count} ta foydalanuvchiga yuborildi.")
    bot.answer_callback_query(callback.id)
    bot.delete_message(callback.message.chat.id, callback.message.message_id)


# Bekor qilish
@bot.callback_query_handler(func=lambda call: call.data == "cancel_send")
def cancel_send(callback):
    bot.send_message(callback.message.chat.id, "❌ Bekor qilindi.")
    bot.answer_callback_query(callback.id)
    bot.delete_message(callback.message.chat.id, callback.message.message_id)


# Barcha xatolarni ushlash
@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    bot.send_message(message.chat.id, "⚠️ Iltimos, tugmalardan foydalaning!")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Bot ishga tushdi...")
    bot.polling(none_stop=True)