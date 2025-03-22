from flask import Flask, render_template, request, redirect, url_for, jsonify, session
import folium
from trail_db import init_db, view_stories, submit_story, get_prize_pool, get_leaderboard, get_random_story_snippet, subscribe_user, get_existing_users
from trail_security import validate_username, validate_title, validate_story
from trail_payments import PaymentHandler
import os
import logging

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "your-secret-key-here")  # Set in Render env vars
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

# Stripe handler uses env var set in Render - replace placeholder with your key in Render env vars
stripe_handler = PaymentHandler(os.environ.get("STRIPE_SECRET_KEY"))

@app.route('/')
def home():
    prize_pool = get_prize_pool()
    winners_share = prize_pool * (2/3)
    quote = get_random_story_snippet() or "Kindness is the sunshine that brightens the world."
    return render_template('home.html', prize_pool=prize_pool, winners_share=winners_share, quote=quote)

@app.route('/stories')
def stories():
    stories = view_stories()
    return render_template('stories.html', stories=stories)

@app.route('/submit', methods=['GET', 'POST'])
def submit():
    if 'username' not in session:
        return redirect(url_for('home'))
    if request.method == 'POST':
        title = request.form['title']
        story = request.form['story']
        location = request.form.get('location', '')
        logging.debug(f"Submit attempt: title='{title}', story='{story[:50]}...', location='{location}'")
        if validate_title(title) and validate_story(story):
            submit_story(session['username'], title, story, location=location)
            logging.info(f"Story submitted by {session['username']}: {title}")
            return redirect(url_for('stories'))
        else:
            logging.error(f"Validation failed: title_valid={validate_title(title)}, story_valid={validate_story(story)}")
            return render_template('submit.html', error="Invalid input")
    return render_template('submit.html')

@app.route('/map')
def map():
    m = folium.Map(location=[20, 0], zoom_start=2, tiles="OpenStreetMap")
    stories = view_stories()
    for story in stories:
        _, title, _, _, username, _, _, location = story
        if location:
            loc_key = location.lower().strip()
            coords = {
                "usa": (37.0902, -95.7129), "canada": (56.1304, -106.3468), "uk": (55.3781, -3.4360),
                "france": (46.6034, 1.8883), "brazil": (-14.2350, -51.9253), "australia": (-25.2744, 133.7751)
            }.get(loc_key, (random.uniform(-90, 90), random.uniform(-180, 180)))
            folium.Marker(coords, popup=f"{title} by {username or 'Anonymous'}").add_to(m)
    map_html = m._repr_html_()
    return render_template('map.html', map_html=map_html)

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username', '').strip()
    logging.debug(f"Login attempt with username: {username}")
    if not username:
        logging.error("No username provided")
        prize_pool = get_prize_pool()
        winners_share = prize_pool * (2/3)
        quote = get_random_story_snippet() or "Kindness is the sunshine that brightens the world."
        return render_template('home.html', error="Please enter a username / Ingresa un nombre de usuario", 
                               prize_pool=prize_pool, winners_share=winners_share, quote=quote)
    if not validate_username(username):
        logging.error(f"Invalid username format: {username}")
        prize_pool = get_prize_pool()
        winners_share = prize_pool * (2/3)
        quote = get_random_story_snippet() or "Kindness is the sunshine that brightens the world."
        return render_template('home.html', error="Invalid username format / Formato de nombre de usuario inválido", 
                               prize_pool=prize_pool, winners_share=winners_share, quote=quote)
    existing_users = get_existing_users()
    logging.debug(f"Existing users: {existing_users}")
    if username in existing_users:
        session['username'] = username
        logging.info(f"User logged in: {username}")
    else:
        from trail_db import register_user
        result = register_user(username, f"{username}@example.com")
        if "Welcome" in result or "Bienvenido" in result:
            session['username'] = username
            logging.info(f"New user registered and logged in: {username}")
        else:
            logging.error(f"Registration failed: {result}")
            prize_pool = get_prize_pool()
            winners_share = prize_pool * (2/3)
            quote = get_random_story_snippet() or "Kindness is the sunshine that brightens the world."
            return render_template('home.html', error=result, prize_pool=prize_pool, winners_share=winners_share, quote=quote)
    return redirect(url_for('home'))

@app.route('/subscribe', methods=['POST'])
def subscribe():
    if 'username' not in session:
        return redirect(url_for('home'))
    # Replace with your actual Price ID from Stripe
    url, error = stripe_handler.create_subscription(session['username'], price_id="price_1YourActualPriceIdHere"")
    if url:
        return redirect(url)
    return jsonify({"error": error}), 500

@app.route('/success')
def success():
    if 'username' in session:
        subscribe_user(session['username'])
    return render_template('success.html')

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)