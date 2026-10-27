# app.py
# Flask + MongoDB (PyMongo) backend for the Movie Max website.
# Simple, student-friendly: plain Flask routes, no ORM.

import os
import re       # simple pattern-matching validation (name, email, phone, seats)
import random
from datetime import date, datetime, timedelta
from functools import wraps                          # ADMIN: used by the admin_required guard

from flask import (Flask, render_template, request, redirect, url_for, session,jsonify, flash)                    # ADMIN: flash = one-time success message
from bson.objectid import ObjectId
from bson.errors import InvalidId
from pymongo.errors import DuplicateKeyError
from werkzeug.security import generate_password_hash, check_password_hash

from database.mongodb import users, bookings   # MongoDB collections
from movies import movies                       # the list of 8 movies
from utils.email_utils import send_booking_email

# ADMIN: movies added by the admin are saved in a "movies" collection in the SAME database.
# (users.database is the database object, so database/mongodb.py needs no change.)
extra_movies = users.database["movies"]

app = Flask(__name__)

# secret_key is needed for Flask "session" (it signs the session cookie).
app.secret_key = os.getenv("SECRET_KEY", "movie_max_secret_key")


# -----------------------------------------------------------
# Booking settings (change them here, in one place)
# -----------------------------------------------------------
TICKET_PRICE = 200                                   # Rs. per seat (default price for a movie)
SHOW_TIMES = ["10:00 AM", "1:30 PM", "4:30 PM", "6:30 PM", "9:30 PM"]
DAYS_AHEAD = 4                                       # today + next 3 days
SEAT_ROWS = list("ABCDEFGH")                         # rows A to H
SEATS_PER_ROW = 10                                   # seats 1 to 10 in each row
AISLE_AFTER = 5                                      # walking gap after seat 5
MAX_SEATS = 8                                        # max seats per booking

# ADMIN: the one and only admin account (change them here)
# (DEPLOY: can be overridden with ADMIN_ID / ADMIN_PASSWORD environment variables;
#  if they are not set, the same values as before are used)
ADMIN_ID = os.getenv("ADMIN_ID", "Satish")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "123456")

# Email rule: lowercase letters/digits, must START with a letter, ends with @gmail.com
GMAIL_PATTERN = r'[a-z][a-z0-9]*@gmail\.com'
GMAIL_ERROR = "Please enter a valid lowercase Gmail address."


def is_valid_gmail(email):
    # fullmatch = the WHOLE text must match (so "a@gmail.com.extra" fails)
    return re.fullmatch(GMAIL_PATTERN, email) is not None


def get_all_movies():
    """ADMIN: the 8 movies from movies.py + every movie the admin added.
    Each movie gets a "price" (movies.py movies use TICKET_PRICE)."""
    all_movies = [dict(m, price=m.get("price", TICKET_PRICE)) for m in movies]
    for m in extra_movies.find({}, {"_id": 0, "created_at": 0}).sort("created_at", 1):
        m.setdefault("price", TICKET_PRICE)
        all_movies.append(m)
    return all_movies


def get_show_dates():
    """Dates are built from today's system date every time - nothing is hard-coded."""
    result = []
    for i in range(DAYS_AHEAD):
        d = date.today() + timedelta(days=i)
        result.append({
            "value": d.isoformat(),                      # 2026-10-09 (saved in MongoDB)
            "label": d.strftime("%d %B"),                # 09 October (shown on button)
            "weekday": d.strftime("%a"),                 # Fri
            "display": d.strftime("%d %B %Y"),           # 09 October 2026 (confirmation)
        })
    return result


def get_booked_seats(movie_title, show_date, show_time):
    """Seats already taken for THIS movie + date + show time only."""
    taken = []
    for b in bookings.find({"movie_title": movie_title,
                            "show_date": show_date,
                            "show_time": show_time}, {"seats": 1}):
        taken.extend(b["seats"])
    return taken


def all_seat_ids():
    return {f"{r}{n}" for r in SEAT_ROWS for n in range(1, SEATS_PER_ROW + 1)}


def make_booking_id():
    """Example: MM-827391. We check MongoDB so the same ID is never used twice."""
    while True:
        booking_id = "MM-" + str(random.randint(100000, 999999))
        if bookings.find_one({"booking_id": booking_id}) is None:
            return booking_id


# -----------------------------------------------------------
# Routes
# -----------------------------------------------------------

@app.route('/')
def index():
    """ADMIN: first page - asks "User or Admin?"."""
    # If somebody is already logged in, skip straight to their page
    if 'user_id' in session:
        return redirect(url_for('home'))
    if session.get('is_admin'):
        return redirect(url_for('admin_add_movie'))
    return render_template('role.html')


@app.route('/user')
def user_welcome():
    """ADMIN: the old first page (Register as New User / Login), now reached through "User"."""
    if 'user_id' in session:
        return redirect(url_for('home'))
    return render_template('welcome.html')


@app.route('/home')
def home():
    """Movie home page - ONLY for logged-in users."""
    if 'user_id' not in session:
        return redirect(url_for('index'))

    all_movies = get_all_movies()               # ADMIN: movies.py + admin-added movies

    # Build the list of genres for the genre buttons (no duplicates)
    all_genres = set()
    for movie in all_movies:
        for g in movie["genre"].split(","):
            all_genres.add(g.strip())

    # Everything the booking popup needs is handed to JavaScript as one dictionary
    booking_config = {
        "dates": get_show_dates(),
        "times": SHOW_TIMES,
        "price": TICKET_PRICE,
        "rows": SEAT_ROWS,
        "perRow": SEATS_PER_ROW,
        "aisleAfter": AISLE_AFTER,
        "maxSeats": MAX_SEATS,
    }

    return render_template('home.html', movies=all_movies, genres=sorted(all_genres),
                           booking_config=booking_config)


@app.route('/register', methods=['GET', 'POST'])
def register():
    """Shows the registration form (GET) and handles form submission (POST)."""

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        # NOTE: we do NOT lower-case the email here. "Satish@gmail.com" must be rejected.
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        gender = request.form.get('gender', '')
        password = request.form.get('password', '')

        # Genre checkboxes share name="genre", so getlist() collects all.
        genre_list = request.form.getlist('genre')
        genres = ", ".join(genre_list)   # e.g. "Action, Comedy, Drama"

        # "old" keeps what the user typed so the form isn't emptied on error
        old = {"name": name, "email": email, "phone": phone,
               "gender": gender, "genre": genre_list}

        # ---- Server-side validation ----
        if not re.match(r'^[A-Za-z ]{2,40}$', name):
            return render_template('register.html', old=old,
                error="Name should only contain letters and spaces (2-40 characters).")

        if not is_valid_gmail(email):
            return render_template('register.html', old=old, error=GMAIL_ERROR)

        if not re.match(r'^[0-9]{10}$', phone):
            return render_template('register.html', old=old,
                error="Phone number must be exactly 10 digits.")

        if gender not in ('Male', 'Female'):
            return render_template('register.html', old=old,
                error="Please select a gender.")

        if len(genre_list) == 0:
            return render_template('register.html', old=old,
                error="Please select at least one favourite genre.")

        if len(password) < 6:
            return render_template('register.html', old=old,
                error="Password must be at least 6 characters long.")

        # Check whether this email is already registered
        if users.find_one({"email": email}):
            return render_template('register.html', old=old,
                error="This email is already registered. Please login instead.")

        # Save the new user (the password is stored as a hash, not plain text)
        new_user = {
            "name": name,
            "email": email,
            "phone": phone,
            "gender": gender,
            "genres": genres,
            "password": generate_password_hash(password)
        }

        try:
            result = users.insert_one(new_user)
        except DuplicateKeyError:
            # Safety net if two people register the same email at once
            return render_template('register.html', old=old,
                error="This email is already registered. Please login instead.")

        # Registration complete -> log the user in and open the home page
        session['user_id'] = str(result.inserted_id)
        session['user_name'] = name
        return redirect(url_for('home'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Shows the login form (GET) and checks login details (POST)."""

    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        # Same Gmail rule as registration (backend check, not only browser check)
        if not is_valid_gmail(email):
            return render_template('login.html', error=GMAIL_ERROR)

        user = users.find_one({"email": email})

        if user and check_password_hash(user["password"], password):
            # Store who is logged in. MongoDB's _id must be turned into text.
            session['user_id'] = str(user["_id"])
            session['user_name'] = user["name"]
            return redirect(url_for('home'))

        return render_template('login.html', error="Invalid email or password")

    return render_template('login.html')


@app.route('/dashboard')
def dashboard():
    """Shows the logged-in user's own details."""

    if 'user_id' not in session:
        return redirect(url_for('login'))

    try:
        user = users.find_one({"_id": ObjectId(session['user_id'])})
    except InvalidId:
        user = None

    if user is None:
        session.clear()
        return redirect(url_for('login'))

    return render_template('dashboard.html', user=user)


@app.route('/logout')
def logout():
    """Clears the session, then goes to the home page."""
    session.clear()
    return redirect(url_for('index'))


# -----------------------------------------------------------
# Booking API (called by static/js/booking.js using fetch)
# -----------------------------------------------------------

@app.route('/api/booked-seats')
def api_booked_seats():
    """Returns the already-booked seats for one movie + date + show time."""
    if 'user_id' not in session:
        return jsonify({"error": "Please login first."}), 401

    seats = get_booked_seats(request.args.get('movie', ''),
                             request.args.get('date', ''),
                             request.args.get('time', ''))
    return jsonify({"seats": seats})


@app.route('/api/book', methods=['POST'])
def api_book():
    """Validates the choice, saves the booking, then sends the email."""
    if 'user_id' not in session:
        return jsonify({"error": "Please login first."}), 401

    data = request.get_json(silent=True) or {}
    movie_title = data.get('movie', '')
    show_date = data.get('date', '')
    show_time = data.get('time', '')
    seats = data.get('seats', [])

    # ---- 1. Validate everything again on the server (never trust the browser) ----
    all_movies = get_all_movies()                                  # ADMIN: includes added movies
    movie = next((m for m in all_movies if m["title"] == movie_title), None)
    if movie is None:
        return jsonify({"error": "Movie not found."}), 400

    date_info = next((d for d in get_show_dates() if d["value"] == show_date), None)
    if date_info is None:
        return jsonify({"error": "Please select a valid date."}), 400

    if show_time not in SHOW_TIMES:
        return jsonify({"error": "Please select a valid show time."}), 400

    if not isinstance(seats, list) or not all(isinstance(s, str) for s in seats):
        return jsonify({"error": "Invalid seat selection."}), 400

    if len(seats) == 0:
        return jsonify({"error": "Please select at least one seat."}), 400

    if len(seats) > MAX_SEATS:
        return jsonify({"error": f"You can book at most {MAX_SEATS} seats at a time."}), 400

    if len(set(seats)) != len(seats) or not set(seats) <= all_seat_ids():
        return jsonify({"error": "Invalid seat selection."}), 400

    # Seats already taken for THIS movie + date + time?
    already_taken = set(seats) & set(get_booked_seats(movie_title, show_date, show_time))
    if already_taken:
        return jsonify({"error": "Sorry, these seats were just booked: "
                                 + ", ".join(sorted(already_taken)),
                        "reload_seats": True}), 409

    # ---- 2. Get the logged-in user's details from the existing users collection ----
    try:
        user = users.find_one({"_id": ObjectId(session['user_id'])})
    except InvalidId:
        user = None
    if user is None:
        session.clear()
        return jsonify({"error": "Please login again."}), 401

    # Keep seats in a tidy order: A1, A2, B3 ...
    seats = sorted(seats, key=lambda s: (s[0], int(s[1:])))

    # ---- 3. Save the booking in MongoDB ----
    now = datetime.now()
    price = movie["price"]                                         # ADMIN: price of THIS movie
    booking = {
        "booking_id": make_booking_id(),
        "user_id": session['user_id'],
        "customer_name": user["name"],
        "customer_email": user["email"],
        "customer_phone": user.get("phone", ""),
        "movie_id": all_movies.index(movie) + 1,
        "movie_title": movie["title"],
        "movie_poster": movie["poster"],
        "booking_date": now.strftime("%Y-%m-%d"),
        "show_date": date_info["value"],
        "show_date_display": date_info["display"],
        "show_time": show_time,
        "seats": seats,
        "seat_count": len(seats),
        "ticket_price": price,
        "total_amount": price * len(seats),
        "status": "Confirmed",
        "created_at": now,
    }

    try:
        bookings.insert_one(booking)
    except DuplicateKeyError:
        # Someone else grabbed a seat between our check and the save
        return jsonify({"error": "Sorry, one of those seats was just booked. "
                                 "Please choose again.", "reload_seats": True}), 409

    # ---- 4. Booking is saved. NOW send the email. ----
    # If this fails the booking stays in MongoDB (the function only returns False).
    booking["seats_text"] = ", ".join(seats)
    email_sent = send_booking_email(booking)

    # ---- 5. Data for the success screen ----
    return jsonify({
        "booking_id": booking["booking_id"],
        "movie": booking["movie_title"],
        "date": booking["show_date_display"],
        "time": booking["show_time"],
        "seats": seats,
        "seat_count": booking["seat_count"],
        "price": price,
        "total": booking["total_amount"],
        "name": booking["customer_name"],
        "email": booking["customer_email"],
        "status": booking["status"],
        "email_sent": email_sent,
    })


# -----------------------------------------------------------
# ADMIN: separate admin login + 2 pages (Add Movie, Booked Details)
# -----------------------------------------------------------

def admin_required(view):
    """Only a logged-in admin may open the admin pages."""
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not session.get('is_admin'):
            return redirect(url_for('admin_login'))
        return view(*args, **kwargs)
    return wrapper


def read_movie_form(form):
    """Checks the 'Add Movie' form. Returns (movie_dict, None) or (None, error_message)."""
    title = " ".join(form.get('title', '').split())
    poster = form.get('poster', '').strip()
    rating_text = form.get('rating', '').strip()
    genre_list = [g.strip() for g in form.get('genre', '').split(',') if g.strip()]
    cast_list = [c.strip() for c in form.get('cast', '').split(',') if c.strip()]
    director = form.get('director', '').strip()
    music = form.get('music', '').strip() or "-"
    description = form.get('description', '').strip()
    price_text = form.get('price', '').strip()

    if not 2 <= len(title) <= 60:
        return None, "Movie title must be 2-60 characters."
    if title.lower() in [m["title"].lower() for m in get_all_movies()]:
        return None, "A movie with this title already exists."
    if not poster.startswith(("http://", "https://", "/static/")):
        return None, "Poster must be an image link starting with http:// or https://"
    try:
        rating = float(rating_text)
    except ValueError:
        return None, "Rating must be a number between 0 and 10."
    if not 0 <= rating <= 10:
        return None, "Rating must be a number between 0 and 10."
    if not genre_list:
        return None, "Please enter at least one genre (separate with commas)."
    if not cast_list:
        return None, "Please enter at least one cast member (separate with commas)."
    if not director:
        return None, "Please enter the director's name."
    if not 10 <= len(description) <= 600:
        return None, "Description must be 10-600 characters."
    if not re.fullmatch(r'[0-9]{1,4}', price_text) or not 1 <= int(price_text) <= 5000:
        return None, "Ticket price must be a whole number between 1 and 5000."

    return {
        "title": title,
        "poster": poster,
        "rating": f"{rating:.1f}",
        "genre": ", ".join(genre_list),
        "cast": cast_list,
        "director": director,
        "music": music,
        "description": description,
        "price": int(price_text),
    }, None


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Admin login only - there is NO admin registration."""
    if session.get('is_admin'):
        return redirect(url_for('admin_add_movie'))

    if request.method == 'POST':
        admin_id = request.form.get('admin_id', '').strip()
        password = request.form.get('password', '')

        if admin_id == ADMIN_ID and password == ADMIN_PASSWORD:
            session.clear()
            session['is_admin'] = True
            return redirect(url_for('admin_add_movie'))

        return render_template('admin_login.html', error="Invalid admin ID or password")

    return render_template('admin_login.html')


@app.route('/admin')
@admin_required
def admin_home():
    return redirect(url_for('admin_add_movie'))


@app.route('/admin/add-movie', methods=['GET', 'POST'])
@admin_required
def admin_add_movie():
    """Admin page 1: add a new movie (it appears on the user home page straight away)."""
    if request.method == 'POST':
        movie, error = read_movie_form(request.form)
        if error:
            return render_template('admin_add_movie.html', active='add', error=error,
                                   old={k: request.form.get(k, '') for k in request.form})

        movie["created_at"] = datetime.now()
        extra_movies.insert_one(movie)
        flash('Movie "' + movie["title"] + '" was added successfully.')
        return redirect(url_for('admin_add_movie'))

    return render_template('admin_add_movie.html', active='add', old={})


@app.route('/admin/bookings')
@admin_required
def admin_bookings():
    """Admin page 2: who booked which movie tickets."""
    rows = list(bookings.find({}).sort("created_at", -1))
    total_tickets = 0
    total_amount = 0
    for b in rows:
        b["booked_on"] = b["created_at"].strftime("%d %b %Y, %I:%M %p") if b.get("created_at") else "-"
        total_tickets += b.get("seat_count", 0)
        total_amount += b.get("total_amount", 0)

    return render_template('admin_bookings.html', active='bookings', bookings=rows,
                           total_tickets=total_tickets, total_amount=total_amount)


if __name__ == '__main__':
    app.run(debug=True)
