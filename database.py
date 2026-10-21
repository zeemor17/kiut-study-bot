import sqlite3
from datetime import datetime

DB_PATH = "bot_database.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Foydalanuvchilar jadvali
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        full_name TEXT,
        group_name TEXT DEFAULT 'Aniqlanmagan',
        first_seen TEXT,
        last_seen TEXT
    )
    """)

    # Harakatlar / Darslar jurnali
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        action TEXT,
        summary TEXT,
        created_at TEXT
    )
    """)

    # Flashcardlar jadvali (Savol-javoblar doimiy saqlanadi)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS flashcards (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        question TEXT,
        answer TEXT,
        created_at TEXT
    )
    """)

    conn.commit()
    conn.close()

def save_or_update_user(user_id: int, username: str, full_name: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()

    clean_username = username if username else ""
    clean_full_name = full_name if full_name else ""

    if row:
        cursor.execute("""
            UPDATE users 
            SET username = ?, full_name = ?, last_seen = ?
            WHERE user_id = ?
        """, (clean_username, clean_full_name, now, user_id))
    else:
        cursor.execute("""
            INSERT INTO users (user_id, username, full_name, first_seen, last_seen)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, clean_username, clean_full_name, now, now))

    conn.commit()
    conn.close()

def log_activity(user_id: int, action: str, summary: str = ""):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        INSERT INTO logs (user_id, action, summary, created_at)
        VALUES (?, ?, ?, ?)
    """, (user_id, action, summary[:500], now))

    conn.commit()
    conn.close()

def get_statistics():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM logs WHERE action = 'photo_processed'")
    total_lessons = cursor.fetchone()[0]

    conn.close()
    return {
        "total_users": total_users,
        "total_lessons": total_lessons
    }

def get_recent_users(limit: int = 10):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT user_id, username, full_name, group_name, last_seen
        FROM users
        ORDER BY last_seen DESC
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()

    conn.close()
    return rows

def get_all_user_ids():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    rows = [r[0] for r in cursor.fetchall()]
    conn.close()
    return rows

def save_flashcards(user_id: int, cards: list) -> list:
    """Savol-javoblarni bazaga saqlaydi va ularning ID larini qaytaradi."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    saved_ids = []

    for card in cards:
        q = card.get("question", "")
        a = card.get("answer", "")
        cursor.execute("""
            INSERT INTO flashcards (user_id, question, answer, created_at)
            VALUES (?, ?, ?, ?)
        """, (user_id, q, a, now))
        saved_ids.append(cursor.lastrowid)

    conn.commit()
    conn.close()
    return saved_ids

def get_flashcard(card_id: int):
    """Bitta flashcardni ID si bo'yicha oladi."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT question, answer FROM flashcards WHERE id = ?", (card_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {"question": row[0], "answer": row[1]}
    return None

init_db()

