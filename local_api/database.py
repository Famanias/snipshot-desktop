"""
SnipShot Desktop - Local Database

SQLite database for local mode storage.
"""

import sqlite3
import os

from config import LOCAL_STORAGE_DIR

DB_PATH = os.path.join(LOCAL_STORAGE_DIR, "snipshot_local.db")


def get_connection():
    """Get a SQLite connection with row factory enabled."""
    os.makedirs(LOCAL_STORAGE_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create tables if they don't exist."""
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS folders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            folder_id INTEGER REFERENCES folders(id) ON DELETE SET NULL,
            storage_path TEXT NOT NULL,
            public_url TEXT NOT NULL,
            filename TEXT NOT NULL,
            original_filename TEXT,
            source_language TEXT DEFAULT '',
            target_language TEXT DEFAULT '',
            file_size INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    conn.close()
