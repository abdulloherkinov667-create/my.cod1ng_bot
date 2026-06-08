import os

import MySQLdb
import dj_database_url
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError


def get_db_config():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL environment variable is not set")

    config = dj_database_url.parse(database_url, engine="mysql")
    if not config.get("NAME"):
        raise RuntimeError("DATABASE_URL is invalid or missing the database name")

    return config


def get_db_connection():
    config = get_db_config()
    return MySQLdb.connect(
        host=config.get("HOST", "localhost") or "localhost",
        port=int(config.get("PORT") or 3306),
        user=config.get("USER", ""),
        passwd=config.get("PASSWORD", ""),
        db=config.get("NAME"),
        charset="utf8mb4",
        use_unicode=True,
        autocommit=False,
    )

async def users_table():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users(
            id INT AUTO_INCREMENT PRIMARY KEY,
            first_name VARCHAR(255),
            username VARCHAR(255),
            language_code VARCHAR(20),
            is_bot BOOLEAN,
            chat_id BIGINT UNIQUE,
            is_blocked TINYINT DEFAULT 0,
            created_at DATETIME
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    try:
        cursor.execute("CREATE INDEX idx_chat_id ON users(chat_id)")
    except MySQLdb.OperationalError as e:
        # Index already exists, ignore the error
        if "Duplicate key name" not in str(e):
            raise
    conn.commit()
    conn.close()



# ----------------------- USER FUNCTIONS -----------------------
def insert_user(first_name, username, language_code, is_bot, chat_id, created_at):
    try:
        conn = get_db_connection()
        curr = conn.cursor()
        query = (
            "INSERT IGNORE INTO users(first_name, username, language_code, is_bot, chat_id, created_at) "
            "VALUES (%s, %s, %s, %s, %s, %s)"
        )
        curr.execute(query, (first_name, username, language_code, is_bot, chat_id, created_at))
        conn.commit()
        return True
    except Exception as e:
        print(e)
        return False
    finally:
        conn.close()
        
        
        
        
        
        
#------------------------ USERLARNI BAZADAN OLISH -----------------------
def get_all_users():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, first_name, username, chat_id, created_at, is_blocked
        FROM users
    """)
    users = cursor.fetchall()
    conn.close()
    return users


#------------------------ BLOKED USERLARNI TEKSHIRISH -----------------------
async def check_blocked_users(bot):
    users = get_all_users()
    conn = get_db_connection()
    cursor = conn.cursor()
    for user in users:
        chat_id = user[3]
        try:
            # Test message yuborish
            await bot.send_chat_action(chat_id=chat_id, action="typing")
            # Agar muvaffaqiyatli bo'lsa, bloklanmagan
            cursor.execute("UPDATE users SET is_blocked = %s WHERE chat_id = %s", (0, chat_id))
        except (TelegramBadRequest, TelegramForbiddenError):
            # Bloklangan
            cursor.execute("UPDATE users SET is_blocked = %s WHERE chat_id = %s", (1, chat_id))
        except Exception:
            # Boshqa xato, ehtimol bloklangan
            cursor.execute("UPDATE users SET is_blocked = %s WHERE chat_id = %s", (1, chat_id))
    conn.commit()
    conn.close()
        
        
#------------------------ USERLARNI PDF GA O'TKAZISH -----------------------      
def create_user_pdf():
    file_name = "userlar_royxati.pdf"

    pdf = SimpleDocTemplate(
        file_name,
        pagesize=A4,
        rightMargin=30,
        leftMargin=30,
        topMargin=30,
        bottomMargin=30
    )

    users = get_all_users()

    # Jadval sarlavhalari
    data = [
        ["ID", "Ismi", "Username", "Chat ID", "Royxtdn otgn vqt", "Bloklangan"]
    ]

    # Userlarni qo‘shish
    for user in users:
        blocked_status = "Ha" if user[5] else "Yo'q"
        data.append([
            str(user[0]),
            user[1],
            f"@{user[2]}" if user[2] else "-",
            str(user[3]),
            str(user[4]),
            blocked_status
        ])

    # Jadval yaratish
    table = Table(
        data,
        colWidths=[30, 80, 80, 100, 100, 60]
    )

    # Jadval stili 
    style = [
        ('GRID', (0, 0), (-1, -1), 1, colors.black),   
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),  
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),  
        ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
    ]

    # Bloklangan userlar uchun ko'k rang
    for i, user in enumerate(users, start=1):
        if user[5]:  # is_blocked
            style.append(('BACKGROUND', (0, i), (-1, i), colors.lightblue))

    table.setStyle(TableStyle(style))

    pdf.build([table])
    return file_name


def setup_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS movies (code VARCHAR(255) PRIMARY KEY, file_id TEXT) "
        "ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"
    )
    conn.commit()
    conn.close()

