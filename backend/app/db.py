import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).resolve().parent.parent / "app.db"

def now_iso():
    return datetime.utcnow().isoformat()

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS candidates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT,
        target_role TEXT,
        cv_filename TEXT,
        cv_text TEXT,
        created_at TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        candidate_id INTEGER,
        status TEXT,
        started_at TEXT,
        ended_at TEXT,
        stop_reason TEXT,
        total_questions INTEGER,
        avg_accuracy REAL,
        avg_ai_risk REAL,
        FOREIGN KEY(candidate_id) REFERENCES candidates(id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS turns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id INTEGER,
        q_index INTEGER,
        question TEXT,
        answer TEXT,
        accuracy REAL,
        ai_risk REAL,
        asked_at TEXT,
        answered_at TEXT,
        FOREIGN KEY(session_id) REFERENCES sessions(id)
    )
    """)

    conn.commit()
    conn.close()