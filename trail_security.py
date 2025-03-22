import tkinter as tk
import tkinter.ttk as ttk
import random
import re

def validate_username(username):
    return bool(re.match(r"^[a-zA-Z0-9_]+$", username))

def validate_email(email):
    return bool(re.match(r"[^@]+@[^@]+\.[^@]+", email))

def validate_title(title):
    return bool(re.match(r"^[a-zA-Z0-9\s.,!?]+$", title))

def validate_story(story):
    from trail_db import MAX_STORY_WORDS
    if not re.match(r"^[a-zA-Z0-9\s.,!?*]+$", story):
        return False
    return len(story.split()) <= MAX_STORY_WORDS

def validate_comment(comment):
    return bool(re.match(r"^[a-zA-Z0-9\s.,!?]+$", comment))

def captcha_test(app):
    captcha_window = tk.Toplevel(app.root)
    captcha_window.title(app.translations["captcha"][app.language])
    captcha_window.geometry("200x200")
    captcha_window.configure(bg="#D2B48C" if not app.is_dark_mode else "#4A2F1A")
    
    canvas = tk.Canvas(captcha_window, width=150, height=100, 
                       bg="#D2B48C" if not app.is_dark_mode else "#4A2F1A")
    canvas.pack(pady=10)
    correct_x, correct_y = random.randint(20, 80), random.randint(20, 60)
    canvas.create_rectangle(correct_x, correct_y, correct_x + 20, correct_y + 20, fill="#8B4513", tags="wagon")
    for _ in range(3):
        x, y = random.randint(20, 120), random.randint(20, 80)
        if (x, y) != (correct_x, correct_y):
            canvas.create_rectangle(x, y, x + 20, y + 20, fill="#A9A9A9")
    
    tk.Label(captcha_window, text=app.translations["click_wagon"][app.language], font=("Courier", 10), 
             bg="#D2B48C" if not app.is_dark_mode else "#4A2F1A", 
             fg="#4A2F1A" if not app.is_dark_mode else "#D2B48C").pack()

    def check_click(event):
        if canvas.coords("wagon")[0] <= event.x <= canvas.coords("wagon")[2] and canvas.coords("wagon")[1] <= event.y <= canvas.coords("wagon")[3]:
            captcha_window.destroy()
            app.register_after_captcha()
        else:
            app.show_telegraph("Telegraph Dispatch / Despacho Telegráfico", 
                              "Wrong choice - Try again / Elección incorrecta - Intenta de nuevo")
            captcha_window.destroy()
            captcha_test(app)

    canvas.bind("<Button-1>", check_click)