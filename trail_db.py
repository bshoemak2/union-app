import sqlite3
from datetime import datetime, timedelta
import re
import random
import os
import logging

MAX_STORIES_PER_DAY = 3
MAX_STORY_WORDS = 20000
ADMIN_USERNAME = "admin"

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

def init_db():
    db_path = os.environ.get("DB_PATH", "/tmp/union_app.db")  # Use /tmp for Render
    try:
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
            logging.info(f"Database initialized at {db_path}")
    except sqlite3.Error as e:
        logging.error(f"Database init failed: {e}")

def register_user(username, email, avatar_path=None):
    db_path = os.environ.get("DB_PATH", "/tmp/union_app.db")
    with sqlite3.connect(db_path) as conn:
        c = conn.cursor()
        if not re.match(r"^[a-zA-Z0-9_]+$", username):
            return "Username must be alphanumeric / Nombre de usuario debe ser alfanumérico"
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            return "Invalid email format / Formato de correo inválido"
        try:
            c.execute("INSERT INTO users (username, subscribed, avatar_path, email) VALUES (?, 0, ?, ?)", 
                      (username, avatar_path, email))
            conn.commit()
            return f"Welcome, {username}! / ¡Bienvenido, {username}!"
        except sqlite3.IntegrityError:
            return "Username or email already taken / Nombre de usuario o correo ya tomados"

def subscribe_user(username):
    db_path = os.environ.get("DB_PATH", "/tmp/union_app.db")
    try:
        with sqlite3.connect(db_path) as conn:
            c = conn.cursor()
            c.execute("UPDATE users SET subscribed = 1 WHERE username = ?", (username,))
            conn.commit()
            logging.info(f"User {username} subscribed")
            return f"{username}, you're now subscribed / {username}, ahora estás suscrito"
    except sqlite3.Error as e:
        logging.error(f"Subscribe user failed: {e}")
        return "Database error / Error de base de datos"

def submit_story(username, title, story, image_path=None, story_id=None, draft=False, location=None):
    db_path = os.environ.get("DB_PATH", "/tmp/union_app.db")
    try:
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
                logging.info(f"Story saved to {db_path}")
                return "Draft saved successfully / Borrador guardado con éxito" if draft else "Story submitted successfully / Historia enviada con éxito"
            return "You need to subscribe first / Necesitas suscribirte primero"
    except sqlite3.Error as e:
        logging.error(f"Submit story failed: {e}")
        return "Database error / Error de base de datos"

def view_stories():
    db_path = os.environ.get("DB_PATH", "/tmp/union_app.db")
    try:
        with sqlite3.connect(db_path) as conn:
            c = conn.cursor()
            c.execute("SELECT s.id, s.title, s.story, s.cheers, u.username, s.user_id, s.image_path, s.location FROM stories s LEFT JOIN users u ON s.user_id = u.id WHERE s.draft = 0 ORDER BY s.id DESC")
            return c.fetchall()
    except sqlite3.Error as e:
        logging.error(f"View stories failed: {e}")
        return []

def cheer_story(username, story_id):
    db_path = os.environ.get("DB_PATH", "/tmp/union_app.db")
    try:
        with sqlite3.connect(db_path) as conn:
            c = conn.cursor()
            c.execute("UPDATE stories SET cheers = cheers + 1 WHERE id = ?", (story_id,))
            conn.commit()
            return f"Cheered story #{story_id} / Aplaudida historia #{story_id}"
    except sqlite3.Error as e:
        logging.error(f"Cheer story failed: {e}")
        return "Database error / Error de base de datos"

def view_archived_stories():
    db_path = os.environ.get("DB_PATH", "/tmp/union_app.db")
    try:
        with sqlite3.connect(db_path) as conn:
            c = conn.cursor()
            c.execute("SELECT a.id, a.title, a.story, a.cheers, a.month, a.image_path, u.username, a.location FROM archived_stories a JOIN users u ON a.user_id = u.id ORDER BY a.archived_at DESC")
            return c.fetchall()
    except sqlite3.Error as e:
        logging.error(f"View archived stories failed: {e}")
        return []

def pick_winner():
    db_path = os.environ.get("DB_PATH", "/tmp/union_app.db")
    try:
        with sqlite3.connect(db_path) as conn:
            c = conn.cursor()
            month = (datetime.now() - timedelta(days=30)).strftime("%Y-%m")
            c.execute("SELECT s.id, s.title, s.story, s.cheers, s.user_id, s.image_path, u.username, s.location FROM stories s JOIN users u ON s.user_id = u.id WHERE s.month = ? AND s.draft = 0 ORDER BY s.cheers DESC LIMIT 3", (month,))
            winners = c.fetchall()
            if winners:
                prize_pool = get_prize_pool()
                total_prize = prize_pool * (2/3)
                payouts = [total_prize * 0.5, total_prize * 0.3, total_prize * 0.2]
                result = []
                for i, (story_id, title, story, cheers, user_id, image_path, username, location) in enumerate(winners):
                    c.execute("SELECT COUNT(*) FROM archived_stories WHERE id = ? AND month = ?", (story_id, month))
                    if c.fetchone()[0] == 0:
                        c.execute("INSERT INTO archived_stories (id, user_id, title, story, cheers, month, image_path, archived_at, location) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", 
                                  (story_id, user_id, title, story, cheers, month, image_path, datetime.now().isoformat(), location))
                    result.append(f"#{i+1}: {username} with '{title}' ({cheers} cheers) - ${payouts[i]:.2f} / #{i+1}: {username} con '{title}' ({cheers} aplausos) - ${payouts[i]:.2f}")
                conn.commit()
                return "\n".join(result)
            return "No stories last month / No hay historias del último mes"
    except sqlite3.Error as e:
        logging.error(f"Pick winner failed: {e}")
        return "Database error / Error de base de datos"

def get_prize_pool():
    db_path = os.environ.get("DB_PATH", "/tmp/union_app.db")
    try:
        with sqlite3.connect(db_path) as conn:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM users WHERE subscribed = 1")
            sub_count = c.fetchone()[0]
            return sub_count * 3
    except sqlite3.Error as e:
        logging.error(f"Get prize pool failed: {e}")
        return 0

def get_existing_users():
    db_path = os.environ.get("DB_PATH", "/tmp/union_app.db")
    try:
        with sqlite3.connect(db_path) as conn:
            c = conn.cursor()
            c.execute("SELECT username FROM users")
            return [row[0] for row in c.fetchall()]
    except sqlite3.Error as e:
        logging.error(f"Get existing users failed: {e}")
        return []

def get_user_email(username):
    db_path = os.environ.get("DB_PATH", "/tmp/union_app.db")
    try:
        with sqlite3.connect(db_path) as conn:
            c = conn.cursor()
            c.execute("SELECT email FROM users WHERE username = ?", (username,))
            result = c.fetchone()
            return result[0] if result else None
    except sqlite3.Error as e:
        logging.error(f"Get user email failed: {e}")
        return None

def get_leaderboard(limit=10):
    db_path = os.environ.get("DB_PATH", "/tmp/union_app.db")
    try:
        with sqlite3.connect(db_path) as conn:
            c = conn.cursor()
            c.execute("SELECT u.username, SUM(s.cheers) as total_cheers FROM stories s JOIN users u ON s.user_id = u.id WHERE s.draft = 0 GROUP BY u.id, u.username ORDER BY total_cheers DESC LIMIT ?", (limit,))
            return c.fetchall()
    except sqlite3.Error as e:
        logging.error(f"Get leaderboard failed: {e}")
        return []

def get_random_story_snippet():
    db_path = os.environ.get("DB_PATH", "/tmp/union_app.db")
    try:
        with sqlite3.connect(db_path) as conn:
            c = conn.cursor()
            c.execute("SELECT story FROM stories WHERE draft = 0 ORDER BY RANDOM() LIMIT 1")
            result = c.fetchone()
            if result:
                story = result[0]
                words = story.split()
                if len(words) > 10:
                    start = random.randint(0, len(words) - 10)
                    return " ".join(words[start:start + 10])
                return story
            return None
    except sqlite3.Error as e:
        logging.error(f"Get random story snippet failed: {e}")
        return None