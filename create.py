import sqlite3
from tkinter import Canvas
import aiosqlite
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors



dp = sqlite3.connect("users.db")
cursor = dp.cursor()

async def users_table():
    async with aiosqlite.connect("users.db") as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users(
                id INTEGER PRIMARY KEY,
                first_name TEXT,
                username TEXT,
                language_code TEXT,
                is_bot BOOLEAN,
                chat_id INTEGER UNIQUE,
                is_blocked INTEGER DEFAULT 0,
                created_at DATETIME
            )
        """)
        await db.commit()



# ----------------------- USER FUNCTIONS -----------------------
def insert_user(first_name, username, language_code, is_bot, chat_id, created_at):
    try:
        conn = sqlite3.connect('users.db')
        curr = conn.cursor()
        query = "INSERT OR IGNORE INTO users(first_name, username, language_code, is_bot, chat_id, created_at) VALUES (?, ?, ?, ?, ?, ?)"
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
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, first_name, username, chat_id, created_at
        FROM users
    """)
    users = cursor.fetchall()
    conn.close()
    return users
        
        
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
        ["ID", "Ismi", "Username", "Chat ID", "Royxtdn otgn vqt"]
    ]

    # Userlarni qo‘shish
    for user in users:
        data.append([
            str(user[0]),
            user[1],
            f"@{user[2]}" if user[2] else "-",
            str(user[3]),
            str(user[4])
        ])

    # Jadval yaratish
    table = Table(
        data,
        colWidths=[40, 100, 100, 120, 120]
    )

    # Jadval stili 
    table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 1, colors.black),   
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),  
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),  
        ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
    ]))

    pdf.build([table])
    return file_name

