import sqlite3
from datetime import datetime, timedelta
import re
import random
import shutil
import os

MAX_STORIES_PER_DAY = 3
MAX_STORY_WORDS = 20000
ADMIN_USERNAME = "admin"

def init_db():
    db_path = "/opt/render/project/src/union_app.db"  # Render writable path
    with sqlite3.connect(db_path) as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users 
                     (id INTEGER PRIMARY KEY, username TEXT UNIQUE, subscribed INTEGER DEFAULT 0, 
                      avatar_path TEXT, email TEXT UNIQUE)''')
        c.execute('''CREATE TABLE IF NOT EXISTS stories 
                     (id INTEGER PRIMARY KEY, user_id INTEGER, title TEXT, story TEXT, 
                      cheers INTEGER DEFAULT 0, submitted_at TEXT, month TEXT, image_path TEXT, 
                      draft INTEGER DEFAULT 0, location TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS comments 
                     (id INTEGER PRIMARY KEY, story_id INTEGER, user_id INTEGER, comment TEXT, created_at TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS archived_stories 
                     (id INTEGER PRIMARY KEY, user_id INTEGER, title TEXT, story TEXT, 
                      cheers INTEGER, month TEXT, image_path TEXT, archived_at TEXT, location TEXT)''')
        conn.commit()

def submit_story(username, title, story, image_path=None, story_id=None, draft=False, location=None):
    db_path = "/opt/render/project/src/union_app.db"  # Render writable path
    with sqlite3.connect(db_path) as conn:
        c = conn.cursor()
        c.execute("SELECT id, subscribed FROM users WHERE username = ?", (username,))
        user = c.fetchone()
        if not user:
            return "User not found / Usuario no encontrado"
        if user[1] == 1 or draft:
            if not re.match(r"^[a-zA-Z0-9\s.,!?]+$", title):
                return "Invalid title characters / Caracteres de título inválidos"
            if not re.match(r"^[a-zA-Z0-9\s.,!?*]+$", story):
                return "Invalid story characters / Caracteres de historia inválidos"
            if len(story.split()) > MAX_STORY_WORDS:
                return f"Story exceeds {MAX_STORY_WORDS} words / Historia excede {MAX_STORY_WORDS} palabras"
            if story_id:
                c.execute("UPDATE stories SET title = ?, story = ?, image_path = ?, submitted_at = ?, draft = ?, location = ? WHERE id = ? AND user_id = ?", 
                          (title, story, image_path, datetime.now().isoformat(), 1 if draft else 0, location, story_id, user[0]))
            else:
                if not draft:
                    c.execute("SELECT COUNT(*) FROM stories WHERE user_id = ? AND submitted_at > ? AND draft = 0", 
                              (user[0], (datetime.now() - timedelta(days=1)).isoformat()))
                    if c.fetchone()[0] >= MAX_STORIES_PER_DAY:
                        return "Story limit reached for today / Límite de historias alcanzado por hoy"
                month = datetime.now().strftime("%Y-%m") if not draft else None
                c.execute("INSERT INTO stories (user_id, title, story, cheers, submitted_at, month, image_path, draft, location) VALUES (?, ?, ?, 0, ?, ?, ?, ?, ?)", 
                          (user[0], title, story, datetime.now().isoformat(), month, image_path, 1 if draft else 0, location))
            conn.commit()
            return "Draft saved successfully / Borrador guardado con éxito" if draft else "Story submitted successfully / Historia enviada con éxito"
        return "You need to subscribe first / Necesitas suscribirte primero