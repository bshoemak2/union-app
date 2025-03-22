import sqlite3
from datetime import datetime, timedelta
import re
import random
import shutil
import os

# Security settings
MAX_STORIES_PER_DAY = 3
MAX_STORY_WORDS = 20000
ADMIN_USERNAME = "admin"

def init_db():
    """Initialize the database with required tables, adding location column if missing."""
    with sqlite3.connect("union_app.db") as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users 
                     (id INTEGER PRIMARY KEY, username TEXT UNIQUE, subscribed INTEGER DEFAULT 0, 
                      avatar_path TEXT, email TEXT UNIQUE)''')
        c.execute('''CREATE TABLE IF NOT EXISTS stories 
                     (id INTEGER PRIMARY KEY, user_id INTEGER, title TEXT, story TEXT, 
                      cheers INTEGER DEFAULT 0, submitted_at TEXT, month TEXT, image_path TEXT, 
                      draft INTEGER DEFAULT 0)''')  # Initial schema
        c.execute('''CREATE TABLE IF NOT EXISTS comments 
                     (id INTEGER PRIMARY KEY, story_id INTEGER, user_id INTEGER, comment TEXT, created_at TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS archived_stories 
                     (id INTEGER PRIMARY KEY, user_id INTEGER, title TEXT, story TEXT, 
                      cheers INTEGER, month TEXT, image_path TEXT, archived_at TEXT)''')
        # Add location column if it doesn’t exist
        c.execute("PRAGMA table_info(stories)")
        if "location" not in [col[1] for col in c.fetchall()]:
            c.execute("ALTER TABLE stories ADD COLUMN location TEXT")
        c.execute("PRAGMA table_info(archived_stories)")
        if "location" not in [col[1] for col in c.fetchall()]:
            c.execute("ALTER TABLE archived_stories ADD COLUMN location TEXT")
        conn.commit()

def register_user(username, email, avatar_path=None):
    """Register a new user without email verification."""
    with sqlite3.connect("union_app.db") as conn:
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
    """Mark a user as subscribed."""
    with sqlite3.connect("union_app.db") as conn:
        c = conn.cursor()
        c.execute("UPDATE users SET subscribed = 1 WHERE username = ?", (username,))
        conn.commit()
        return f"{username}, you're now subscribed / {username}, ahora estás suscrito"

def submit_story(username, title, story, image_path=None, story_id=None, draft=False, location=None):
    """Submit or save a story (draft or final) with optional location."""
    with sqlite3.connect("union_app.db") as conn:
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
                if image_path and not draft:
                    story_id = c.lastrowid
                    new_path = f"story_images/story_{story_id}.jpg"
                    os.makedirs("story_images", exist_ok=True)
                    shutil.copy(image_path, new_path)
                    c.execute("UPDATE stories SET image_path = ? WHERE id = ?", (new_path, story_id))
            conn.commit()
            return "Draft saved successfully / Borrador guardado con éxito" if draft else "Story submitted successfully / Historia enviada con éxito"
        return "You need to subscribe first / Necesitas suscribirte primero"

def delete_story(story_id, username):
    with sqlite3.connect("union_app.db") as conn:
        c = conn.cursor()
        if username != ADMIN_USERNAME:
            return "Only admin can delete stories / Solo el admin puede eliminar historias"
        c.execute("SELECT id FROM stories WHERE id = ?", (story_id,))
        if not c.fetchone():
            return "Story not found / Historia no encontrada"
        c.execute("DELETE FROM stories WHERE id = ?", (story_id,))
        c.execute("DELETE FROM comments WHERE story_id = ?", (story_id,))
        conn.commit()
        return f"Story #{story_id} deleted by admin / Historia #{story_id} eliminada por admin"

def cheer_story(username, story_id):
    with sqlite3.connect("union_app.db") as conn:
        c = conn.cursor()
        c.execute("UPDATE stories SET cheers = cheers + 1 WHERE id = ?", (story_id,))
        conn.commit()
        return f"Cheered story #{story_id} / Aplaudida historia #{story_id}"

def add_comment(username, story_id, comment):
    with sqlite3.connect("union_app.db") as conn:
        c = conn.cursor()
        user_id = get_current_user_id(username) if username else None
        if not re.match(r"^[a-zA-Z0-9\s.,!?]+$", comment):
            return "Invalid comment characters / Caracteres de comentario inválidos"
        c.execute("INSERT INTO comments (story_id, user_id, comment, created_at) VALUES (?, ?, ?, ?)", 
                  (story_id, user_id, comment, datetime.now().isoformat()))
        conn.commit()
        return "Comment posted / Comentario publicado"

def get_comments(story_id):
    with sqlite3.connect("union_app.db") as conn:
        c = conn.cursor()
        c.execute("SELECT c.comment, u.username FROM comments c LEFT JOIN users u ON c.user_id = u.id WHERE c.story_id = ?", (story_id,))
        return c.fetchall()

def view_stories():
    with sqlite3.connect("union_app.db") as conn:
        c = conn.cursor()
        c.execute("SELECT s.id, s.title, s.story, s.cheers, u.username, s.user_id, s.image_path, s.location FROM stories s LEFT JOIN users u ON s.user_id = u.id WHERE s.draft = 0 ORDER BY s.id DESC")
        return c.fetchall()

def pick_winner():
    with sqlite3.connect("union_app.db") as conn:
        c = conn.cursor()
        month = (datetime.now() - timedelta(days=30)).strftime("%Y-%m")
        c.execute("SELECT s.id, s.title, s.story, s.cheers, s.user_id, s.image_path, u.username, s.location FROM stories s JOIN users u ON s.user_id = u.id WHERE s.month = ? AND s.draft = 0 ORDER BY s.cheers DESC LIMIT 3", (month,))
        winners = c.fetchall()
        if winners:
            prize_pool = get_prize_pool()
            total_prize = prize_pool * (2/3)  # 2/3 of prize pool for top 3
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

def view_archived_stories():
    with sqlite3.connect("union_app.db") as conn:
        c = conn.cursor()
        c.execute("SELECT a.id, a.title, a.story, a.cheers, a.month, a.image_path, u.username, a.location FROM archived_stories a JOIN users u ON a.user_id = u.id ORDER BY a.archived_at DESC")
        return c.fetchall()

def get_existing_users():
    with sqlite3.connect("union_app.db") as conn:
        c = conn.cursor()
        c.execute("SELECT username FROM users")
        return [row[0] for row in c.fetchall()]

def get_user_avatar(username):
    with sqlite3.connect("union_app.db") as conn:
        c = conn.cursor()
        c.execute("SELECT avatar_path FROM users WHERE username = ?", (username,))
        result = c.fetchone()
        return result[0] if result else None

def get_user_email(username):
    with sqlite3.connect("union_app.db") as conn:
        c = conn.cursor()
        c.execute("SELECT email FROM users WHERE username = ?", (username,))
        result = c.fetchone()
        return result[0] if result else None

def get_user_story_count(username):
    with sqlite3.connect("union_app.db") as conn:
        c = conn.cursor()
        c.execute("SELECT id FROM users WHERE username = ?", (username,))
        user_id = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM stories WHERE user_id = ? AND draft = 0", (user_id,))
        return c.fetchone()[0]

def get_user_cheers_received(username):
    with sqlite3.connect("union_app.db") as conn:
        c = conn.cursor()
        c.execute("SELECT id FROM users WHERE username = ?", (username,))
        user_id = c.fetchone()[0]
        c.execute("SELECT SUM(cheers) FROM stories WHERE user_id = ? AND draft = 0", (user_id,))
        result = c.fetchone()[0]
        return result if result else 0

def get_stories_today(username):
    with sqlite3.connect("union_app.db") as conn:
        c = conn.cursor()
        c.execute("SELECT id FROM users WHERE username = ?", (username,))
        user_id = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM stories WHERE user_id = ? AND submitted_at > ? AND draft = 0", 
                  (user_id, (datetime.now() - timedelta(days=1)).isoformat()))
        return c.fetchone()[0]

def get_prize_pool():
    with sqlite3.connect("union_app.db") as conn:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM users WHERE subscribed = 1")
        sub_count = c.fetchone()[0]
        return sub_count * 3  # Total pool, 2/3 goes to winners

def get_current_user_id(username):
    with sqlite3.connect("union_app.db") as conn:
        c = conn.cursor()
        c.execute("SELECT id FROM users WHERE username = ?", (username,))
        result = c.fetchone()
        return result[0] if result else None

def get_leaderboard(limit=10):
    with sqlite3.connect("union_app.db") as conn:
        c = conn.cursor()
        c.execute("SELECT u.username, SUM(s.cheers) as total_cheers FROM stories s JOIN users u ON s.user_id = u.id WHERE s.draft = 0 GROUP BY u.id, u.username ORDER BY total_cheers DESC LIMIT ?", (limit,))
        return c.fetchall()

def get_random_story_snippet():
    with sqlite3.connect("union_app.db") as conn:
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

if __name__ == "__main__":
    init_db()
    with sqlite3.connect("union_app.db") as conn:
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO users (username, subscribed, email) VALUES (?, 1, ?)", 
                  ("admin", "admin@example.com"))
        conn.commit()