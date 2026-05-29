import sqlite3

# =========================
# CREATE CONNECTION
# =========================

conn = sqlite3.connect(
    "study_assistant.db",
    check_same_thread=False
)

cursor = conn.cursor()

# =========================
# CREATE TABLE
# =========================

cursor.execute("""
CREATE TABLE IF NOT EXISTS notes (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    filename TEXT,

    extracted_text TEXT,

    summary TEXT,

    quiz TEXT

)
""")
# =========================
# USERS TABLE
# =========================

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    username TEXT UNIQUE,

    password TEXT

)
""")

conn.commit()

conn.commit()